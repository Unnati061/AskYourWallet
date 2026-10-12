import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.budget import Budget
from app.models.transaction import Transaction
from app.schemas.budget import BudgetCreate, BudgetStatus, BudgetUpdate


def month_bounds(year: int, month: int) -> tuple[date, date]:
    """[start, end) date range for a calendar month, handling the December rollover."""
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start, end


async def get_budget(
    db: AsyncSession, budget_id: uuid.UUID, user_id: uuid.UUID
) -> Optional[Budget]:
    """Retrieve a single budget, scoped to its owner."""
    result = await db.execute(
        select(Budget).where(and_(Budget.id == budget_id, Budget.user_id == user_id))
    )
    return result.scalar_one_or_none()


async def get_budgets(db: AsyncSession, user_id: uuid.UUID) -> list[Budget]:
    """Retrieve all budgets for a user."""
    result = await db.execute(
        select(Budget).where(Budget.user_id == user_id).order_by(Budget.category)
    )
    return list(result.scalars().all())


async def _find_for_period(
    db: AsyncSession, user_id: uuid.UUID, category: str, month: Optional[int], year: Optional[int]
) -> Optional[Budget]:
    """Look up the budget occupying an exact (category, month, year) slot."""
    result = await db.execute(
        select(Budget).where(
            and_(
                Budget.user_id == user_id,
                Budget.category == category,
                Budget.month.is_(None) if month is None else Budget.month == month,
                Budget.year.is_(None) if year is None else Budget.year == year,
            )
        )
    )
    return result.scalar_one_or_none()


async def create_budget(db: AsyncSession, data: BudgetCreate, user_id: uuid.UUID) -> Budget:
    """Create a budget. Raises ValueError if the period slot is already taken."""
    if await _find_for_period(db, user_id, data.category, data.month, data.year):
        raise ValueError(f"A budget for '{data.category}' already exists for this period.")

    db_budget = Budget(
        user_id=user_id,
        category=data.category,
        monthly_limit=data.monthly_limit,
        month=data.month,
        year=data.year,
    )
    db.add(db_budget)
    await db.commit()
    await db.refresh(db_budget)
    return db_budget


async def upsert_budget(db: AsyncSession, data: BudgetCreate, user_id: uuid.UUID) -> Budget:
    """
    Set a category's limit for a period, creating or overwriting as needed.

    The UI uses this instead of POST so that re-submitting a category the user has
    already budgeted updates the limit rather than dead-ending on a 409.
    """
    existing = await _find_for_period(db, user_id, data.category, data.month, data.year)
    if existing:
        existing.monthly_limit = data.monthly_limit
        await db.commit()
        await db.refresh(existing)
        return existing
    return await create_budget(db, data, user_id)


async def update_budget(
    db: AsyncSession, budget_id: uuid.UUID, user_id: uuid.UUID, data: BudgetUpdate
) -> Optional[Budget]:
    """Update a budget's monthly limit."""
    db_budget = await get_budget(db, budget_id, user_id)
    if not db_budget:
        return None
    db_budget.monthly_limit = data.monthly_limit
    await db.commit()
    await db.refresh(db_budget)
    return db_budget


async def delete_budget(db: AsyncSession, budget_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    """Remove a budget. False when it does not exist for this user."""
    db_budget = await get_budget(db, budget_id, user_id)
    if not db_budget:
        return False
    await db.delete(db_budget)
    await db.commit()
    return True


async def get_spending_by_category(
    db: AsyncSession, user_id: uuid.UUID, month: int, year: int
) -> dict[str, Decimal]:
    """Total expense amount per category for one month."""
    start, end = month_bounds(year, month)
    result = await db.execute(
        select(Transaction.category, func.sum(Transaction.amount))
        .where(
            and_(
                Transaction.user_id == user_id,
                Transaction.type == "expense",
                Transaction.date >= start,
                Transaction.date < end,
            )
        )
        .group_by(Transaction.category)
    )
    return {(row[0] or "Other"): Decimal(str(row[1] or 0)) for row in result.all()}


async def get_budget_status_list(
    db: AsyncSession, user_id: uuid.UUID, month: int, year: int
) -> list[BudgetStatus]:
    """Join each applicable budget with its actual spending for the given month."""
    # Applicable budgets = those pinned to this exact period, plus recurring ones
    # (month and year both NULL) that apply to every month.
    budgets_result = await db.execute(
        select(Budget).where(
            and_(
                Budget.user_id == user_id,
                or_(
                    and_(Budget.month == month, Budget.year == year),
                    and_(Budget.month.is_(None), Budget.year.is_(None)),
                ),
            )
        )
    )

    # A period-specific budget overrides a recurring one for the same category.
    budget_map: dict[str, Budget] = {}
    for budget in budgets_result.scalars().all():
        existing = budget_map.get(budget.category)
        if existing is None or (existing.month is None and budget.month is not None):
            budget_map[budget.category] = budget

    spending = await get_spending_by_category(db, user_id, month, year)

    statuses: list[BudgetStatus] = []
    for category, budget in budget_map.items():
        actual_spent = spending.get(category, Decimal("0.00"))
        monthly_limit = Decimal(str(budget.monthly_limit))
        percentage_used = (
            float(actual_spent / monthly_limit * 100) if monthly_limit > 0 else 0.0
        )
        statuses.append(
            BudgetStatus(
                budget_id=budget.id,
                category=category,
                monthly_limit=monthly_limit,
                actual_spent=actual_spent,
                remaining=monthly_limit - actual_spent,
                percentage_used=round(percentage_used, 2),
                is_over_budget=actual_spent > monthly_limit,
                month=month,
                year=year,
            )
        )

    # Most-consumed first, so the at-risk jars lead the grid.
    statuses.sort(key=lambda s: s.percentage_used, reverse=True)
    return statuses
