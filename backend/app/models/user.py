import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    # Uuid (not postgresql.UUID) so the same model renders on Postgres *and*
    # sqlite -- native UUID on PG, CHAR(32) elsewhere.
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Lazy-loaded: eager "selectin" here would pull every transaction on every
    # get_current_user() call, which runs on all authenticated requests.
    # passive_deletes defers row removal to the FK's ON DELETE CASCADE instead of
    # loading every child object first.
    transactions = relationship(
        "Transaction", back_populates="user", lazy="noload", passive_deletes=True
    )
    budgets = relationship(
        "Budget", back_populates="user", lazy="noload", passive_deletes=True
    )
