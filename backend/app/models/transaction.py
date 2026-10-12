import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import String, Date, DateTime, Numeric, ForeignKey, Index, Uuid, func, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    # Always stored as a positive magnitude; direction lives in `type`.
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    # "income" or "expense"
    type: Mapped[str] = mapped_column(String(10), nullable=False, default="expense")
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    merchant: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user = relationship("User", back_populates="transactions")

    # Every list/aggregate query filters by user_id and ranges over date, so a
    # composite index covers the dashboard, transaction list and budget rollups.
    __table_args__ = (
        Index("ix_transactions_user_date", "user_id", "date"),
        Index("ix_transactions_user_category", "user_id", "category"),
    )
