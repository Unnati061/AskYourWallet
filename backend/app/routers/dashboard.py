from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.dashboard import DashboardPayload
from app.services.dashboard import get_dashboard_data

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardPayload)
async def read_dashboard(
    month: Optional[int] = Query(default=None, ge=1, le=12),
    year: Optional[int] = Query(default=None, ge=2000, le=2100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Full dashboard aggregate for a month (defaults to the current month)."""
    now = datetime.now()
    return await get_dashboard_data(
        db,
        current_user.id,
        month if month is not None else now.month,
        year if year is not None else now.year,
    )
