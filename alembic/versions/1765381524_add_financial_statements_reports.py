"""add_financial_statements_reports

Revision ID: 1765381524
Revises: 43601fc5956f
Create Date: 2025-12-10 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1765381524'
down_revision: Union[str, Sequence[str], None] = '43601fc5956f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add profit_loss and cash_flow to reporttype enum."""
    # Add new enum values to existing reporttype enum
    op.execute(sa.text("ALTER TYPE reporttype ADD VALUE IF NOT EXISTS 'profit_loss'"))
    op.execute(sa.text("ALTER TYPE reporttype ADD VALUE IF NOT EXISTS 'cash_flow'"))


def downgrade() -> None:
    """Remove profit_loss and cash_flow from reporttype enum."""
    # Note: PostgreSQL doesn't support removing enum values directly
    # This would require recreating the enum type, which is complex
    # For now, we'll leave a comment that manual intervention is needed
    # In production, this should be handled carefully with data migration
    pass

