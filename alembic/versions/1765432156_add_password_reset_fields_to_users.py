"""add_password_reset_fields_to_users

Revision ID: 1765432156
Revises: 43601fc5956f
Create Date: 2025-01-XX XX:XX:XX.XXXXXX

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1765432156'
down_revision: Union[str, Sequence[str], None] = '1765381524'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add password reset fields to users table."""
    op.add_column('users', sa.Column('password_reset_token', sa.String(), nullable=True))
    op.add_column('users', sa.Column('password_reset_expires', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_users_password_reset_token'), 'users', ['password_reset_token'], unique=False)


def downgrade() -> None:
    """Remove password reset fields from users table."""
    op.drop_index(op.f('ix_users_password_reset_token'), table_name='users')
    op.drop_column('users', 'password_reset_expires')
    op.drop_column('users', 'password_reset_token')

