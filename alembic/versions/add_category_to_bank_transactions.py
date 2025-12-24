"""add_category_to_bank_transactions

Revision ID: add_category_bank_txn
Revises: 43601fc5956f
Create Date: 2025-02-25 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_category_bank_txn'
down_revision: Union[str, Sequence[str], None] = '1765432156'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add category column to bank_transactions table."""
    op.add_column('bank_transactions', sa.Column('category', sa.String(), nullable=True))


def downgrade() -> None:
    """Remove category column from bank_transactions table."""
    op.drop_column('bank_transactions', 'category')

