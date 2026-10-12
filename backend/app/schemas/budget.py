from __future__ import annotations
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.models.category import CATEGORIES


class BudgetBase(BaseModel):
    category: str = Field(min_length=1, max_length=100)
    monthly_limit: Decimal = Field(gt=0, decimal_places=2)
    month: Optional[int] = Field(default=None, ge=1, le=12)
    year: Optional[int] = Field(default=None, ge=2000, le=2100)

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v not in CATEGORIES:
            raise ValueError(f"Category '{v}' must be one of the canonical categories: {CATEGORIES}")
        return v


class BudgetCreate(BudgetBase):
    pass


class BudgetUpdate(BaseModel):
    monthly_limit: Decimal = Field(gt=0, decimal_places=2)


class BudgetResponse(BudgetBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BudgetStatus(BaseModel):
    """A budget joined with actual spending for one month."""
    # Included so the UI can edit or delete a budget straight from the status list
    # without a second round trip to /api/budgets.
    budget_id: uuid.UUID
    category: str
    monthly_limit: Decimal
    actual_spent: Decimal
    remaining: Decimal
    percentage_used: float
    is_over_budget: bool
    month: int
    year: int
