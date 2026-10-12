import io
import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

import pandas as pd
from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction
from app.schemas.transaction import TransactionCreate, TransactionUpdate
from app.services.categorization.llm import categorize_merchant_with_llm
from app.services.categorization.rules import categorize_by_rules, extract_merchant


async def get_transaction(
    db: AsyncSession, transaction_id: uuid.UUID, user_id: uuid.UUID
) -> Optional[Transaction]:
    """Retrieve a single transaction, scoped to its owner."""
    result = await db.execute(
        select(Transaction).where(
            and_(Transaction.id == transaction_id, Transaction.user_id == user_id)
        )
    )
    return result.scalar_one_or_none()


def _apply_filters(
    stmt: Select,
    user_id: uuid.UUID,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    type_: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
) -> Select:
    """Shared WHERE clause so the page query and the COUNT query can never drift."""
    stmt = stmt.where(Transaction.user_id == user_id)
    if start_date:
        stmt = stmt.where(Transaction.date >= start_date)
    if end_date:
        stmt = stmt.where(Transaction.date <= end_date)
    if type_:
        stmt = stmt.where(Transaction.type == type_)
    if category:
        stmt = stmt.where(Transaction.category == category)
    if search and search.strip():
        # func.lower(...) LIKE is case-insensitive on both Postgres and sqlite,
        # unlike ILIKE (Postgres-only) or LIKE (case-sensitive on Postgres).
        term = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Transaction.description).like(term),
                func.lower(Transaction.merchant).like(term),
                func.lower(Transaction.category).like(term),
            )
        )
    return stmt


async def get_transactions(
    db: AsyncSession,
    user_id: uuid.UUID,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    type_: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Transaction]:
    """Fetch a filtered page of transactions, newest first."""
    stmt = _apply_filters(
        select(Transaction), user_id, start_date, end_date, type_, category, search
    )
    stmt = stmt.order_by(Transaction.date.desc(), Transaction.created_at.desc())
    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def count_transactions(
    db: AsyncSession,
    user_id: uuid.UUID,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    type_: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
) -> int:
    """Total rows matching the same filters, for pagination metadata."""
    stmt = _apply_filters(
        select(func.count(Transaction.id)), user_id, start_date, end_date, type_, category, search
    )
    return int((await db.execute(stmt)).scalar() or 0)


async def resolve_category(
    description: str,
    merchant: Optional[str] = None,
    explicit_category: Optional[str] = None,
) -> str:
    """
    Decide a transaction's category: explicit choice > keyword rules > LLM.

    An explicit user choice is always honoured, including "Other" -- otherwise a
    deliberate override would be silently reclassified on every edit.
    """
    if explicit_category:
        return explicit_category

    matched = categorize_by_rules(description)
    if matched:
        return matched

    # Rules missed. Ask the LLM about the cleaned merchant name rather than the
    # full statement line, which is mostly terminal ids and dates.
    probe = merchant or extract_merchant(description) or description
    return await categorize_merchant_with_llm(probe)


async def create_transaction(
    db: AsyncSession, data: TransactionCreate, user_id: uuid.UUID
) -> Transaction:
    """Create a transaction, auto-categorizing when the caller left it unset."""
    merchant = data.merchant or extract_merchant(data.description)
    category = await resolve_category(data.description, merchant, data.category)

    db_transaction = Transaction(
        user_id=user_id,
        date=data.date,
        description=data.description,
        amount=data.amount,
        type=data.type,
        category=category,
        merchant=merchant,
        notes=data.notes,
    )
    db.add(db_transaction)
    await db.commit()
    await db.refresh(db_transaction)
    return db_transaction


async def update_transaction(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    user_id: uuid.UUID,
    data: TransactionUpdate,
) -> Optional[Transaction]:
    """Apply a partial update, re-categorizing only when it makes sense to."""
    db_transaction = await get_transaction(db, transaction_id, user_id)
    if not db_transaction:
        return None

    update_dict = data.model_dump(exclude_unset=True)

    for key, value in update_dict.items():
        setattr(db_transaction, key, value)

    # Re-derive the category only when the description changed and the caller did
    # not set a category in the same request (an explicit choice always wins).
    if "description" in update_dict and not update_dict.get("category"):
        db_transaction.merchant = update_dict.get("merchant") or extract_merchant(
            update_dict["description"]
        )
        db_transaction.category = await resolve_category(
            update_dict["description"], db_transaction.merchant, None
        )

    await db.commit()
    await db.refresh(db_transaction)
    return db_transaction


async def delete_transaction(
    db: AsyncSession, transaction_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
    """Delete a transaction. False when it does not exist for this user."""
    db_transaction = await get_transaction(db, transaction_id, user_id)
    if not db_transaction:
        return False
    await db.delete(db_transaction)
    await db.commit()
    return True


# --- CSV import ---------------------------------------------------------------

# Candidate header names, in priority order, for each field we need. Bank exports
# have no standard schema, so detection is by known name first then substring.
_DATE_HEADERS = ["date", "transaction date", "post date", "posting date", "booking date", "tx date"]
_DESC_HEADERS = ["description", "payee", "merchant", "details", "memo", "name", "narration", "transaction"]
_AMOUNT_HEADERS = ["amount", "value", "payment", "charge", "sum", "total"]


def _find_column(headers: list[str], exact: list[str], fuzzy: list[str]) -> Optional[str]:
    """Match a header by exact name first, then by substring."""
    for candidate in exact:
        if candidate in headers:
            return candidate
    for header in headers:
        if any(token in header for token in fuzzy):
            return header
    return None


def _to_decimal(raw) -> Optional[Decimal]:
    """Parse a spreadsheet cell into a Decimal, tolerating $, commas and (123)."""
    if raw is None or pd.isna(raw):
        return None
    text = str(raw).strip().replace("$", "").replace(",", "").replace(" ", "")
    if not text:
        return None
    # Accounting notation: (45.00) means -45.00
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1]
    try:
        value = Decimal(text)
    except (InvalidOperation, ValueError, TypeError):
        return None
    return -value if negative else value


def parse_csv_statement(file_content: bytes) -> list[dict]:
    """
    Parse a CSV bank statement into transaction dicts ready for bulk insert.

    Handles both single-signed-amount statements (negative = expense) and
    separate debit/credit column pairs. Rows that cannot be parsed are skipped
    rather than failing the whole import.
    """
    df = pd.read_csv(io.BytesIO(file_content))
    if df.empty:
        raise ValueError("The CSV file contains no data rows.")

    headers = [str(col).strip().lower() for col in df.columns]
    df.columns = headers

    date_col = _find_column(headers, _DATE_HEADERS, ["date"])
    desc_col = _find_column(headers, _DESC_HEADERS, ["payee", "desc", "merchant", "name", "narrat"])

    debit_col = next((c for c in headers if "debit" in c or "withdraw" in c), None)
    credit_col = next((c for c in headers if "credit" in c or "deposit" in c), None)
    amount_col = None
    if not (debit_col and credit_col):
        amount_col = _find_column(headers, _AMOUNT_HEADERS, ["amount", "val"])

    if not date_col:
        raise ValueError("Could not find a date column in the CSV.")
    if not desc_col:
        raise ValueError("Could not find a description/payee column in the CSV.")
    if not amount_col and not (debit_col and credit_col):
        raise ValueError("Could not find an amount column (or debit/credit pair) in the CSV.")

    imported_on = datetime.now().strftime("%Y-%m-%d")
    transactions: list[dict] = []

    for _, row in df.iterrows():
        raw_date = row[date_col]
        if pd.isna(raw_date):
            continue
        try:
            parsed_date = pd.to_datetime(raw_date, dayfirst=False).date()
        except Exception:
            continue

        raw_desc = str(row[desc_col]).strip()
        if not raw_desc or raw_desc.lower() == "nan":
            continue

        if debit_col and credit_col:
            debit = _to_decimal(row[debit_col])
            credit = _to_decimal(row[credit_col])
            if debit and debit != 0:
                amount_val, tx_type = abs(debit), "expense"
            elif credit and credit != 0:
                amount_val, tx_type = abs(credit), "income"
            else:
                continue
        else:
            value = _to_decimal(row[amount_col])
            if value is None or value == 0:
                continue
            # Convention: a negative amount is money out.
            amount_val = abs(value)
            tx_type = "expense" if value < 0 else "income"

        # Rules-only during import: an LLM call per row would make a 500-row
        # statement unusably slow. Unmatched rows land in "Other" (or "Income"
        # for credits) and can be re-categorized individually afterwards.
        category = categorize_by_rules(raw_desc) or "Other"
        if tx_type == "income" and category == "Other":
            category = "Income"

        transactions.append({
            "date": parsed_date,
            "description": raw_desc[:500],
            "amount": amount_val.quantize(Decimal("0.01")),
            "type": tx_type,
            "category": category,
            "merchant": extract_merchant(raw_desc),
            "notes": f"Imported via CSV on {imported_on}",
        })

    return transactions


async def bulk_create_transactions(
    db: AsyncSession, transactions_data: list[dict], user_id: uuid.UUID
) -> int:
    """Insert parsed CSV rows in one commit."""
    if not transactions_data:
        return 0

    db.add_all([
        Transaction(
            user_id=user_id,
            date=tx["date"],
            description=tx["description"],
            amount=tx["amount"],
            type=tx["type"],
            category=tx["category"],
            merchant=tx["merchant"],
            notes=tx["notes"],
        )
        for tx in transactions_data
    ])
    await db.commit()
    return len(transactions_data)
