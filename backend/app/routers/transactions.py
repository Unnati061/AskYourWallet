import math
import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.transaction import (
    ImportResult,
    TransactionCreate,
    TransactionPage,
    TransactionResponse,
    TransactionUpdate,
)
from app.services.transaction import (
    bulk_create_transactions,
    count_transactions,
    create_transaction,
    delete_transaction,
    get_transaction,
    get_transactions,
    parse_csv_statement,
    update_transaction,
)

router = APIRouter(prefix="/api/transactions", tags=["transactions"])

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB is generous for a CSV statement


@router.get("", response_model=TransactionPage)
async def read_transactions(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    type: Optional[str] = Query(default=None, pattern="^(income|expense)$"),
    category: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=25, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List the user's transactions, filtered and paginated."""
    offset = (page - 1) * size
    filters = {
        "start_date": start_date,
        "end_date": end_date,
        "type_": type,
        "category": category,
        "search": search,
    }

    items = await get_transactions(db, current_user.id, limit=size, offset=offset, **filters)
    total = await count_transactions(db, current_user.id, **filters)

    return TransactionPage(
        items=[TransactionResponse.model_validate(tx) for tx in items],
        total=total,
        page=page,
        size=size,
        pages=max(1, math.ceil(total / size)),
    )


@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def add_transaction(
    data: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a transaction manually. Category is auto-derived when omitted."""
    return await create_transaction(db, data, current_user.id)


@router.post("/import", response_model=ImportResult, status_code=status.HTTP_201_CREATED)
async def import_transactions(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Import transactions from a CSV bank statement."""
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .csv files are supported.",
        )

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File is larger than the 5 MB limit.",
        )

    try:
        parsed = parse_csv_statement(content)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:  # noqa: BLE001 -- malformed CSV shapes surface here
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not parse the CSV file: {exc}",
        )

    if not parsed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No importable rows found. Check that the file has date, description and amount columns.",
        )

    count = await bulk_create_transactions(db, parsed, current_user.id)
    return ImportResult(
        imported_count=count,
        message=f"Imported {count} transaction{'s' if count != 1 else ''}.",
    )


# Declared after /import so the literal path is not swallowed by the UUID route.
@router.get("/{transaction_id}", response_model=TransactionResponse)
async def read_transaction(
    transaction_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single transaction by ID."""
    tx = await get_transaction(db, transaction_id, current_user.id)
    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return tx


@router.put("/{transaction_id}", response_model=TransactionResponse)
async def edit_transaction(
    transaction_id: uuid.UUID,
    data: TransactionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Modify an existing transaction."""
    tx = await update_transaction(db, transaction_id, current_user.id, data)
    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return tx


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_transaction(
    transaction_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a transaction."""
    if not await delete_transaction(db, transaction_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return None
