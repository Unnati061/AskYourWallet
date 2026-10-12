"""Add composite indexes on transactions

Every list and aggregate query filters by user_id and then ranges over date or
groups by category, so these two composite indexes cover the transaction list,
the dashboard rollups and the budget status calculation.

Revision ID: b1f2a7d94c10
Revises: c3cc2d60835c
Create Date: 2026-08-29 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b1f2a7d94c10"
down_revision: Union[str, None] = "c3cc2d60835c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_transactions_user_date", "transactions", ["user_id", "date"], unique=False
    )
    op.create_index(
        "ix_transactions_user_category", "transactions", ["user_id", "category"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_transactions_user_category", table_name="transactions")
    op.drop_index("ix_transactions_user_date", table_name="transactions")
