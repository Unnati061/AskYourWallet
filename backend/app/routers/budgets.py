import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.budget import BudgetCreate, BudgetResponse, BudgetStatus, BudgetUpdate
from app.services.budget import (
    create_budget,
    delete_budget,
    get_budget_status_list,
    get_budgets,
    update_budget,
    upsert_budget,
)

router = APIRouter(prefix="/api/budgets", tags=["budgets"])


def _resolve_period(month: Optional[int], year: Optional[int]) -> tuple[int, int]:
    """Default an unspecified month/year to the current calendar month."""
    now = datetime.now()
    return (month if month is not None else now.month, year if year is not None else now.year)


@router.get("", response_model=list[BudgetResponse])
async def read_budgets(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all budgets for the user."""
    return await get_budgets(db, current_user.id)


# Declared before /{budget_id} so "status" is not parsed as a UUID path param.
@router.get("/status", response_model=list[BudgetStatus])
async def read_budget_status(
    month: Optional[int] = Query(default=None, ge=1, le=12),
    year: Optional[int] = Query(default=None, ge=2000, le=2100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Budget limits joined with actual spending for a month."""
    target_month, target_year = _resolve_period(month, year)
    return await get_budget_status_list(db, current_user.id, target_month, target_year)


@router.post("", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
async def add_budget(
    data: BudgetCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a budget. 409 if one already exists for that category and period."""
    try:
        return await create_budget(db, data, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.put("", response_model=BudgetResponse)
async def set_budget(
    data: BudgetCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create or overwrite the limit for a category and period (idempotent)."""
    return await upsert_budget(db, data, current_user.id)


@router.put("/{budget_id}", response_model=BudgetResponse)
async def edit_budget(
    budget_id: uuid.UUID,
    data: BudgetUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing budget's monthly limit."""
    budget = await update_budget(db, budget_id, current_user.id, data)
    if not budget:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    return budget


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_budget(
    budget_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a budget."""
    if not await delete_budget(db, budget_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    return None
