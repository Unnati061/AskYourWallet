import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import String, DateTime, Integer, Numeric, ForeignKey, Uuid, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Budget(Base):
    __tablename__ = "budgets"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    # Monthly spending ceiling for this category, in the user's currency.
    monthly_limit: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    # month/year scope the budget to one period; both NULL = recurring every month.
    month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # One budget per category per period per user
    __table_args__ = (
        UniqueConstraint("user_id", "category", "month", "year", name="uq_user_category_period"),
    )

    user = relationship("User", back_populates="budgets")
