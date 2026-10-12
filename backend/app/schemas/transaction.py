from __future__ import annotations
import uuid
from datetime import date as date_type, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field


class TransactionBase(BaseModel):
    date: date_type
    description: str = Field(min_length=1, max_length=500)
    amount: Decimal = Field(gt=0, decimal_places=2)
    type: Literal["income", "expense"] = "expense"
    # None means "decide for me": the service runs the rules engine and, if that
    # misses, the LLM fallback. Sending "Other" explicitly is treated as a
    # deliberate choice and is never overwritten.
    category: Optional[str] = Field(default=None, max_length=100)
    merchant: Optional[str] = Field(default=None, max_length=255)
    notes: Optional[str] = None


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    # The alias matters here: with postponed annotations (PEP 563) the string
    # "Optional[date]" is resolved against the class namespace too, where the
    # field's own `= None` default shadows the imported `date` type. That made
    # the annotation collapse to Optional[None], so every PUT with a real date
    # was rejected with "date: Input should be None".
    date: Optional[date_type] = None
    description: Optional[str] = Field(default=None, min_length=1, max_length=500)
    amount: Optional[Decimal] = Field(default=None, gt=0, decimal_places=2)
    type: Optional[Literal["income", "expense"]] = None
    category: Optional[str] = Field(default=None, max_length=100)
    merchant: Optional[str] = Field(default=None, max_length=255)
    notes: Optional[str] = None


class TransactionResponse(TransactionBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class TransactionSummary(BaseModel):
    total_income: Decimal
    total_expenses: Decimal
    net_savings: Decimal
    savings_rate: float


class TransactionPage(BaseModel):
    """Paginated envelope so the table can render page controls."""
    items: list[TransactionResponse]
    total: int
    page: int
    size: int
    pages: int


class ImportResult(BaseModel):
    imported_count: int
    message: str
