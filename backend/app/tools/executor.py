"""
Tool execution layer for the chat assistant.

Every function here runs a real query against the signed-in user's own rows and
returns plain JSON-serializable data. The LLM never sees the database and never
supplies a user id -- `user_id` is bound from the authenticated request, so a
model that hallucinates one cannot reach another user's data.

Functions never raise: a bad argument comes back as {"error": ...} which is fed
to the model as the tool result, letting it correct itself or explain the failure.
"""

import logging
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction
from app.services.budget import get_budget_status_list, month_bounds
from app.services.transaction import get_transactions
from app.tools.definitions import TOOL_NAMES

logger = logging.getLogger(__name__)

MAX_ROWS = 100
DEFAULT_ROWS = 25
MAX_TREND_MONTHS = 24


def _money(value: Decimal | float | int | None) -> float:
    """Render a monetary value as a JSON number rounded to cents."""
    return float(round(Decimal(str(value or 0)), 2))


def _parse_month(raw: Any) -> tuple[int, int]:
    """
    Interpret a model-supplied month as (year, month), defaulting to today.

    Accepts "YYYY-MM" and tolerates a full "YYYY-MM-DD", which models sometimes
    emit despite the schema.
    """
    now = datetime.now()
    if not raw:
        return now.year, now.month
    text = str(raw).strip()
    for fmt in ("%Y-%m", "%Y-%m-%d", "%Y/%m"):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.year, parsed.month
        except ValueError:
            continue
    logger.warning("Could not parse month %r from tool call; using current month", raw)
    return now.year, now.month


def _parse_date(raw: Any) -> date | None:
    """Parse a YYYY-MM-DD argument, returning None when unusable."""
    if not raw:
        return None
    try:
        return datetime.strptime(str(raw).strip()[:10], "%Y-%m-%d").date()
    except ValueError:
        logger.warning("Could not parse date %r from tool call; ignoring filter", raw)
        return None


def _clamp_int(raw: Any, default: int, low: int, high: int) -> int:
    try:
        return max(low, min(high, int(raw)))
    except (TypeError, ValueError):
        return default


def _shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    index = (year * 12 + (month - 1)) + delta
    return index // 12, index % 12 + 1


# --- Tool implementations -----------------------------------------------------

async def get_transactions_tool(
    db: AsyncSession, user_id: uuid.UUID, args: dict
) -> dict:
    """Filtered list of the user's transactions."""
    limit = _clamp_int(args.get("limit"), DEFAULT_ROWS, 1, MAX_ROWS)
    tx_type = args.get("type") if args.get("type") in ("income", "expense") else None

    rows = await get_transactions(
        db,
        user_id=user_id,
        start_date=_parse_date(args.get("start_date")),
        end_date=_parse_date(args.get("end_date")),
        type_=tx_type,
        category=args.get("category") or None,
        search=args.get("search") or None,
        limit=limit,
        offset=0,
    )

    items = [
        {
            "date": tx.date.isoformat(),
            "description": tx.description,
            "merchant": tx.merchant,
            "category": tx.category or "Other",
            "type": tx.type,
            "amount": _money(tx.amount),
        }
        for tx in rows
    ]
    total = sum(item["amount"] for item in items)

    return {
        "count": len(items),
        "total_amount": round(total, 2),
        "truncated": len(items) == limit,
        "transactions": items,
    }


async def get_spending_by_category_tool(
    db: AsyncSession, user_id: uuid.UUID, args: dict
) -> dict:
    """Expenses for one month grouped by category, highest first."""
    year, month = _parse_month(args.get("month"))
    start, end = month_bounds(year, month)

    result = await db.execute(
        select(Transaction.category, func.sum(Transaction.amount), func.count(Transaction.id))
        .where(
            and_(
                Transaction.user_id == user_id,
                Transaction.type == "expense",
                Transaction.date >= start,
                Transaction.date < end,
            )
        )
        .group_by(Transaction.category)
        .order_by(func.sum(Transaction.amount).desc())
    )
    rows = result.all()
    total = sum(Decimal(str(row[1] or 0)) for row in rows)

    return {
        "month": f"{year}-{month:02d}",
        "total_spent": _money(total),
        "categories": [
            {
                "category": row[0] or "Other",
                "amount": _money(row[1]),
                "transaction_count": int(row[2] or 0),
                "share_of_spending_pct": round(
                    float(Decimal(str(row[1] or 0)) / total * 100), 1
                ) if total > 0 else 0.0,
            }
            for row in rows
        ],
    }


async def get_budget_status_tool(
    db: AsyncSession, user_id: uuid.UUID, args: dict
) -> dict:
    """Budgets versus actual spending for one month."""
    year, month = _parse_month(args.get("month"))
    statuses = await get_budget_status_list(db, user_id, month, year)

    if not statuses:
        return {
            "month": f"{year}-{month:02d}",
            "budgets": [],
            "note": "The user has not set any budgets for this month.",
        }

    return {
        "month": f"{year}-{month:02d}",
        "over_budget_count": sum(1 for s in statuses if s.is_over_budget),
        "budgets": [
            {
                "category": s.category,
                "monthly_limit": _money(s.monthly_limit),
                "spent": _money(s.actual_spent),
                "remaining": _money(s.remaining),
                "percent_used": round(s.percentage_used, 1),
                "over_budget": s.is_over_budget,
            }
            for s in statuses
        ],
    }


async def get_monthly_trend_tool(
    db: AsyncSession, user_id: uuid.UUID, args: dict
) -> dict:
    """Income, expenses and net per month, oldest first."""
    months = _clamp_int(args.get("months"), 6, 1, MAX_TREND_MONTHS)
    now = datetime.now()

    first_year, first_month = _shift_month(now.year, now.month, -(months - 1))
    window_start = date(first_year, first_month, 1)
    _, window_end = month_bounds(now.year, now.month)

    result = await db.execute(
        select(Transaction.date, Transaction.type, Transaction.amount).where(
            and_(
                Transaction.user_id == user_id,
                Transaction.date >= window_start,
                Transaction.date < window_end,
            )
        )
    )

    buckets: dict[str, dict[str, Decimal]] = {}
    for tx_date, tx_type, amount in result.all():
        bucket = buckets.setdefault(
            f"{tx_date.year}-{tx_date.month:02d}",
            {"income": Decimal("0.00"), "expenses": Decimal("0.00")},
        )
        key = "income" if tx_type == "income" else "expenses"
        bucket[key] += Decimal(str(amount))

    series = []
    for offset in range(-(months - 1), 1):
        y, m = _shift_month(now.year, now.month, offset)
        bucket = buckets.get(
            f"{y}-{m:02d}", {"income": Decimal("0.00"), "expenses": Decimal("0.00")}
        )
        series.append({
            "month": f"{y}-{m:02d}",
            "income": _money(bucket["income"]),
            "expenses": _money(bucket["expenses"]),
            "net": _money(bucket["income"] - bucket["expenses"]),
        })

    return {"months_returned": len(series), "trend": series}


# Dispatch table. Keys must match TOOL_DEFINITIONS exactly.
TOOL_HANDLERS = {
    "get_transactions": get_transactions_tool,
    "get_spending_by_category": get_spending_by_category_tool,
    "get_budget_status": get_budget_status_tool,
    "get_monthly_trend": get_monthly_trend_tool,
}

assert set(TOOL_HANDLERS) == set(TOOL_NAMES), "Tool definitions and handlers are out of sync"


async def execute_tool(
    name: str, arguments: dict, db: AsyncSession, user_id: uuid.UUID
) -> dict:
    """
    Run one tool call and return its result as a JSON-serializable dict.

    Errors are returned rather than raised so the chat loop can hand them back to
    the model as an ordinary tool result.
    """
    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        return {"error": f"Unknown tool '{name}'."}

    try:
        return await handler(db, user_id, arguments or {})
    except Exception as exc:  # noqa: BLE001 -- a tool failure must not 500 the chat
        logger.exception("Tool %s failed", name)
        return {"error": f"Tool '{name}' failed: {exc}"}
