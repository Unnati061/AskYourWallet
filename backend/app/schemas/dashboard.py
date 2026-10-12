from __future__ import annotations
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from app.schemas.budget import BudgetStatus
from app.schemas.transaction import TransactionResponse


class DashboardSummaryCards(BaseModel):
    total_spent: Decimal
    total_income: Decimal
    net_savings: Decimal
    # Already expressed as a percentage (e.g. 30.0 means 30%), so the UI must not
    # multiply it again.
    savings_rate: float
    budget_health: Literal["Good", "Warning", "Critical", "No budgets"]
    transaction_count: int


class CategoryBreakdownItem(BaseModel):
    category: str
    amount: Decimal
    percentage: float
    icon: str


class MonthlyTrendItem(BaseModel):
    month: str  # "YYYY-MM"
    label: str  # "Aug 26" -- pre-formatted for chart axes
    income: Decimal
    expenses: Decimal
    net: Decimal


class DashboardPayload(BaseModel):
    month: int
    year: int
    summary: DashboardSummaryCards
    category_breakdown: list[CategoryBreakdownItem]
    monthly_trend: list[MonthlyTrendItem]
    budget_status: list[BudgetStatus]
    recent_transactions: list[TransactionResponse]
