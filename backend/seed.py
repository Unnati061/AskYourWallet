"""
Seed the database with a realistic demo dataset.

Idempotent: re-running replaces the demo user's transactions and budgets rather
than duplicating them. Deterministic (fixed RNG seed) so screenshots and the
dashboard look the same on every machine.

Usage (from the backend directory, with the venv active):
    python seed.py
"""

import asyncio
import random
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import delete, select

from app.database import async_session
from app.models.budget import Budget
from app.models.transaction import Transaction
from app.models.user import User
from app.services.auth import hash_password, normalize_email
from app.services.categorization.rules import categorize_by_rules, extract_merchant

DEMO_EMAIL = "demo@askyourwallet.app"
DEMO_PASSWORD = "demo12345"
DEMO_NAME = "Demo User"

MONTHS_OF_HISTORY = 6
rng = random.Random(20260829)


def shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    index = (year * 12 + (month - 1)) + delta
    return index // 12, index % 12 + 1


# (description, category, low, high) -- amounts vary per occurrence.
GROCERY_MERCHANTS = [
    ("Whole Foods Market", 48, 145),
    ("Trader Joe's", 32, 88),
    ("Kroger", 25, 110),
    ("Costco Wholesale", 90, 260),
]
DINING_MERCHANTS = [
    ("Starbucks", 5, 14),
    ("Chipotle Mexican Grill", 11, 24),
    ("DoorDash", 18, 52),
    ("Blue Bottle Coffee", 6, 13),
    ("Pizza Napoli", 22, 46),
]
TRANSPORT_MERCHANTS = [
    ("Uber Trip", 9, 38),
    ("Shell Gas Station", 34, 72),
    ("Metro Transit Pass", 2, 8),
]
SHOPPING_MERCHANTS = [
    ("Amazon Marketplace", 14, 165),
    ("Best Buy", 45, 320),
    ("Nike Store", 55, 180),
    ("IKEA", 38, 240),
]
FIXED_MONTHLY = [
    ("Rent Payment - Ridgeview Apartments", Decimal("1650.00"), 1),
    ("Comcast Xfinity Internet", Decimal("79.99"), 4),
    ("City Electric Utility", Decimal("112.40"), 6),
    ("Geico Auto Insurance", Decimal("128.00"), 8),
    ("Netflix", Decimal("22.99"), 12),
    ("Spotify Premium", Decimal("11.99"), 14),
    ("Adobe Creative Cloud", Decimal("54.99"), 17),
    ("Anytime Fitness Gym", Decimal("39.00"), 3),
]

BUDGETS = [
    ("Groceries", Decimal("600.00")),
    ("Dining", Decimal("300.00")),
    ("Transport", Decimal("250.00")),
    ("Shopping", Decimal("350.00")),
    ("Entertainment", Decimal("120.00")),
    ("Utilities", Decimal("250.00")),
    ("Housing", Decimal("1700.00")),
]


def amount_between(low: float, high: float) -> Decimal:
    return Decimal(str(round(rng.uniform(low, high), 2)))


def make_transaction(user_id, when: date, description: str, amount: Decimal, tx_type: str) -> Transaction:
    """Build a Transaction, deriving category/merchant through the real rules engine."""
    category = categorize_by_rules(description) or ("Income" if tx_type == "income" else "Other")
    return Transaction(
        user_id=user_id,
        date=when,
        description=description,
        amount=amount,
        type=tx_type,
        category=category,
        merchant=extract_merchant(description),
        notes=None,
    )


def build_month(user_id, year: int, month: int, day_limit: int) -> list[Transaction]:
    """Generate one month of plausible activity, capped at `day_limit` days."""
    rows: list[Transaction] = []

    def day(n: int) -> date:
        return date(year, month, min(n, day_limit))

    # Salary, paid on the 1st and the 15th.
    for pay_day in (1, 15):
        if pay_day <= day_limit:
            rows.append(make_transaction(
                user_id, day(pay_day), "Payroll Direct Deposit - Northwind Systems",
                Decimal("2480.00"), "income",
            ))

    # Recurring fixed costs.
    for description, amount, due_day in FIXED_MONTHLY:
        if due_day <= day_limit:
            rows.append(make_transaction(user_id, day(due_day), description, amount, "expense"))

    # Variable spending, spread across the month.
    def scatter(merchants, count):
        for _ in range(count):
            name, low, high = rng.choice(merchants)
            rows.append(make_transaction(
                user_id, day(rng.randint(1, day_limit)), name, amount_between(low, high), "expense"
            ))

    scatter(GROCERY_MERCHANTS, rng.randint(4, 7))
    scatter(DINING_MERCHANTS, rng.randint(6, 12))
    scatter(TRANSPORT_MERCHANTS, rng.randint(4, 9))
    scatter(SHOPPING_MERCHANTS, rng.randint(2, 5))

    # Occasional one-offs so the category breakdown has a long tail.
    if rng.random() < 0.5 and day_limit > 10:
        rows.append(make_transaction(
            user_id, day(rng.randint(5, day_limit)), "CVS Pharmacy Prescription",
            amount_between(12, 90), "expense",
        ))
    if rng.random() < 0.35 and day_limit > 12:
        rows.append(make_transaction(
            user_id, day(rng.randint(8, day_limit)), "Delta Air Lines Flight",
            amount_between(180, 520), "expense",
        ))
    if rng.random() < 0.3:
        rows.append(make_transaction(
            user_id, day(rng.randint(1, day_limit)), "GoFundMe Donation",
            amount_between(20, 75), "expense",
        ))

    return rows


async def seed() -> None:
    today = date.today()

    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.email == normalize_email(DEMO_EMAIL))
        )
        user = result.scalar_one_or_none()

        if user is None:
            user = User(
                email=normalize_email(DEMO_EMAIL),
                hashed_password=hash_password(DEMO_PASSWORD),
                full_name=DEMO_NAME,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            print(f"Created demo user {DEMO_EMAIL}")
        else:
            # Idempotent re-seed: clear this user's data first.
            await session.execute(delete(Transaction).where(Transaction.user_id == user.id))
            await session.execute(delete(Budget).where(Budget.user_id == user.id))
            await session.commit()
            print(f"Reset existing demo user {DEMO_EMAIL}")

        transactions: list[Transaction] = []
        for offset in range(-(MONTHS_OF_HISTORY - 1), 1):
            year, month = shift_month(today.year, today.month, offset)
            if (year, month) == (today.year, today.month):
                day_limit = today.day  # partial current month
            else:
                next_year, next_month = shift_month(year, month, 1)
                day_limit = (date(next_year, next_month, 1) - timedelta(days=1)).day
            transactions.extend(build_month(user.id, year, month, day_limit))

        session.add_all(transactions)

        # Recurring budgets (month/year NULL = applies to every month).
        session.add_all([
            Budget(user_id=user.id, category=category, monthly_limit=limit, month=None, year=None)
            for category, limit in BUDGETS
        ])

        await session.commit()

        print(f"Seeded {len(transactions)} transactions and {len(BUDGETS)} budgets.")
        print(f"Log in with  {DEMO_EMAIL}  /  {DEMO_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(seed())
