import calendar
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import CATEGORY_ICONS
from app.models.transaction import Transaction
from app.schemas.dashboard import (
    CategoryBreakdownItem,
    DashboardPayload,
    DashboardSummaryCards,
    MonthlyTrendItem,
)
from app.schemas.transaction import TransactionResponse
from app.services.budget import get_budget_status_list, month_bounds

RECENT_TRANSACTION_LIMIT = 8
TREND_MONTHS = 6


def _shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    """Move (year, month) by `delta` months without relying on timedelta."""
    index = (year * 12 + (month - 1)) + delta
    return index // 12, index % 12 + 1


async def get_dashboard_data(
    db: AsyncSession, user_id: uuid.UUID, month: int, year: int
) -> DashboardPayload:
    """Aggregate every figure the dashboard renders, for one target month."""
    start_date, end_date = month_bounds(year, month)

    # --- 1. Month totals ------------------------------------------------------
    totals_result = await db.execute(
        select(
            Transaction.type,
            func.sum(Transaction.amount),
            func.count(Transaction.id),
        )
        .where(
            and_(
                Transaction.user_id == user_id,
                Transaction.date >= start_date,
                Transaction.date < end_date,
            )
        )
        .group_by(Transaction.type)
    )

    total_spent = Decimal("0.00")
    total_income = Decimal("0.00")
    transaction_count = 0
    for tx_type, total, count in totals_result.all():
        transaction_count += int(count or 0)
        if tx_type == "expense":
            total_spent = Decimal(str(total or 0))
        elif tx_type == "income":
            total_income = Decimal(str(total or 0))

    net_savings = total_income - total_spent
    # Percentage of income kept. Undefined without income, so reported as 0.
    savings_rate = float(net_savings / total_income * 100) if total_income > 0 else 0.0

    # --- 2. Budget health -----------------------------------------------------
    budget_statuses = await get_budget_status_list(db, user_id, month, year)
    if not budget_statuses:
        budget_health = "No budgets"
    elif any(s.is_over_budget for s in budget_statuses):
        budget_health = "Critical"
    elif any(s.percentage_used >= 80 for s in budget_statuses):
        budget_health = "Warning"
    else:
        budget_health = "Good"

    summary = DashboardSummaryCards(
        total_spent=total_spent,
        total_income=total_income,
        net_savings=net_savings,
        savings_rate=round(savings_rate, 2),
        budget_health=budget_health,
        transaction_count=transaction_count,
    )

    # --- 3. Category breakdown (expenses only) --------------------------------
    breakdown_result = await db.execute(
        select(Transaction.category, func.sum(Transaction.amount))
        .where(
            and_(
                Transaction.user_id == user_id,
                Transaction.type == "expense",
                Transaction.date >= start_date,
                Transaction.date < end_date,
            )
        )
        .group_by(Transaction.category)
        .order_by(func.sum(Transaction.amount).desc())
    )

    category_breakdown = [
        CategoryBreakdownItem(
            category=(row[0] or "Other"),
            amount=Decimal(str(row[1] or 0)),
            percentage=round(
                float(Decimal(str(row[1] or 0)) / total_spent * 100) if total_spent > 0 else 0.0, 2
            ),
            icon=CATEGORY_ICONS.get(row[0] or "Other", "circle-dot"),
        )
        for row in breakdown_result.all()
    ]

    # --- 4. Monthly trend -----------------------------------------------------
    # One grouped query over the whole window rather than six per-month queries.
    # strftime/date_trunc differ across dialects, so the month key is derived in
    # Python from the raw rows -- the window is small (a few hundred rows).
    trend_start_year, trend_start_month = _shift_month(year, month, -(TREND_MONTHS - 1))
    trend_start = date(trend_start_year, trend_start_month, 1)

    trend_rows = await db.execute(
        select(Transaction.date, Transaction.type, Transaction.amount).where(
            and_(
                Transaction.user_id == user_id,
                Transaction.date >= trend_start,
                Transaction.date < end_date,
            )
        )
    )

    buckets: dict[str, dict[str, Decimal]] = {}
    for tx_date, tx_type, amount in trend_rows.all():
        key = f"{tx_date.year}-{tx_date.month:02d}"
        bucket = buckets.setdefault(key, {"income": Decimal("0.00"), "expenses": Decimal("0.00")})
        if tx_type == "income":
            bucket["income"] += Decimal(str(amount))
        else:
            bucket["expenses"] += Decimal(str(amount))

    monthly_trend: list[MonthlyTrendItem] = []
    for offset in range(-(TREND_MONTHS - 1), 1):
        y, m = _shift_month(year, month, offset)
        key = f"{y}-{m:02d}"
        bucket = buckets.get(key, {"income": Decimal("0.00"), "expenses": Decimal("0.00")})
        monthly_trend.append(
            MonthlyTrendItem(
                month=key,
                label=f"{calendar.month_abbr[m]} {str(y)[-2:]}",
                income=bucket["income"],
                expenses=bucket["expenses"],
                net=bucket["income"] - bucket["expenses"],
            )
        )

    # --- 5. Recent transactions ----------------------------------------------
    recent_result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .order_by(Transaction.date.desc(), Transaction.created_at.desc())
        .limit(RECENT_TRANSACTION_LIMIT)
    )

    return DashboardPayload(
        month=month,
        year=year,
        summary=summary,
        category_breakdown=category_breakdown,
        monthly_trend=monthly_trend,
        budget_status=budget_statuses,
        recent_transactions=[
            TransactionResponse.model_validate(tx) for tx in recent_result.scalars().all()
        ],
    )
