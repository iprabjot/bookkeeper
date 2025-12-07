"""add_report_bundles_and_reports_tables

Revision ID: 21b0095185da
Revises: 0001
Create Date: 2025-12-07 21:22:46.957648

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '21b0095185da'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add report_bundles and reports tables."""
    # Create reporttype enum
    op.execute(sa.text("DROP TYPE IF EXISTS reporttype CASCADE"))
    op.execute(sa.text("CREATE TYPE reporttype AS ENUM ('journal_entries', 'trial_balance', 'ledger')"))
    
    reporttype_enum = postgresql.ENUM('journal_entries', 'trial_balance', 'ledger', name='reporttype', create_type=False)
    
    # Create report_bundles table
    op.create_table(
        'report_bundles',
        sa.Column('bundle_id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('generated_by_user_id', sa.Integer(), nullable=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.company_id'], ),
        sa.ForeignKeyConstraint(['generated_by_user_id'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('bundle_id')
    )
    op.create_index(op.f('ix_report_bundles_bundle_id'), 'report_bundles', ['bundle_id'], unique=False)
    
    # Create reports table
    op.create_table(
        'reports',
        sa.Column('report_id', sa.Integer(), nullable=False),
        sa.Column('bundle_id', sa.Integer(), nullable=False),
        sa.Column('report_type', reporttype_enum, nullable=False),
        sa.Column('account_name', sa.String(), nullable=True),
        sa.Column('content', sa.String(), nullable=False),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['bundle_id'], ['report_bundles.bundle_id'], ),
        sa.PrimaryKeyConstraint('report_id')
    )
    op.create_index(op.f('ix_reports_report_id'), 'reports', ['report_id'], unique=False)


def downgrade() -> None:
    """Remove report_bundles and reports tables."""
    op.drop_index(op.f('ix_reports_report_id'), table_name='reports')
    op.drop_table('reports')
    op.drop_index(op.f('ix_report_bundles_bundle_id'), table_name='report_bundles')
    op.drop_table('report_bundles')
    op.execute(sa.text("DROP TYPE IF EXISTS reporttype CASCADE"))
