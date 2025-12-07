"""Initial schema - create all tables

Revision ID: 0001
Revises: 
Create Date: 2025-12-07 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all database tables from scratch."""
    
    # Create enum types using raw SQL
    # Drop if exists first (for idempotent migration)
    op.execute(sa.text("DROP TYPE IF EXISTS invoicetype CASCADE"))
    op.execute(sa.text("DROP TYPE IF EXISTS invoicestatus CASCADE"))
    op.execute(sa.text("DROP TYPE IF EXISTS journalentrytype CASCADE"))
    op.execute(sa.text("DROP TYPE IF EXISTS transactiontype CASCADE"))
    op.execute(sa.text("DROP TYPE IF EXISTS transactionstatus CASCADE"))
    op.execute(sa.text("DROP TYPE IF EXISTS matchtype CASCADE"))
    op.execute(sa.text("DROP TYPE IF EXISTS reconciliationstatus CASCADE"))
    op.execute(sa.text("DROP TYPE IF EXISTS userrole CASCADE"))
    
    # Create enum types
    op.execute(sa.text("CREATE TYPE invoicetype AS ENUM ('SALES', 'PURCHASE')"))
    op.execute(sa.text("CREATE TYPE invoicestatus AS ENUM ('PENDING', 'PAID', 'PARTIALLY_PAID')"))
    op.execute(sa.text("CREATE TYPE journalentrytype AS ENUM ('SALES', 'PURCHASE', 'PAYMENT', 'RECEIPT', 'OTHER')"))
    op.execute(sa.text("CREATE TYPE transactiontype AS ENUM ('CREDIT', 'DEBIT')"))
    op.execute(sa.text("CREATE TYPE transactionstatus AS ENUM ('UNMATCHED', 'MATCHED', 'SETTLED')"))
    op.execute(sa.text("CREATE TYPE matchtype AS ENUM ('EXACT', 'FUZZY', 'MANUAL')"))
    op.execute(sa.text("CREATE TYPE reconciliationstatus AS ENUM ('PENDING', 'VERIFIED', 'SETTLED')"))
    op.execute(sa.text("CREATE TYPE userrole AS ENUM ('OWNER', 'ADMIN', 'ACCOUNTANT', 'VIEWER')"))
    
    # Create enum objects for use in table definitions (with native_enum=False to use PostgreSQL enum)
    invoicetype_enum = postgresql.ENUM('SALES', 'PURCHASE', name='invoicetype', create_type=False)
    invoicestatus_enum = postgresql.ENUM('PENDING', 'PAID', 'PARTIALLY_PAID', name='invoicestatus', create_type=False)
    journalentrytype_enum = postgresql.ENUM('SALES', 'PURCHASE', 'PAYMENT', 'RECEIPT', 'OTHER', name='journalentrytype', create_type=False)
    transactiontype_enum = postgresql.ENUM('CREDIT', 'DEBIT', name='transactiontype', create_type=False)
    transactionstatus_enum = postgresql.ENUM('UNMATCHED', 'MATCHED', 'SETTLED', name='transactionstatus', create_type=False)
    matchtype_enum = postgresql.ENUM('EXACT', 'FUZZY', 'MANUAL', name='matchtype', create_type=False)
    reconciliationstatus_enum = postgresql.ENUM('PENDING', 'VERIFIED', 'SETTLED', name='reconciliationstatus', create_type=False)
    userrole_enum = postgresql.ENUM('OWNER', 'ADMIN', 'ACCOUNTANT', 'VIEWER', name='userrole', create_type=False)
    
    # Create companies table
    op.create_table('companies',
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('gstin', sa.String(), nullable=False),
        sa.Column('is_current', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('company_id'),
        sa.UniqueConstraint('gstin')
    )
    op.create_index(op.f('ix_companies_company_id'), 'companies', ['company_id'], unique=False)
    
    # Create vendors table
    op.create_table('vendors',
        sa.Column('vendor_id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('gstin', sa.String(), nullable=True),
        sa.Column('address', sa.String(), nullable=True),
        sa.Column('contact_info', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.company_id'], ),
        sa.PrimaryKeyConstraint('vendor_id')
    )
    op.create_index(op.f('ix_vendors_vendor_id'), 'vendors', ['vendor_id'], unique=False)
    
    # Create buyers table
    op.create_table('buyers',
        sa.Column('buyer_id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('gstin', sa.String(), nullable=True),
        sa.Column('address', sa.String(), nullable=True),
        sa.Column('contact_info', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.company_id'], ),
        sa.PrimaryKeyConstraint('buyer_id')
    )
    op.create_index(op.f('ix_buyers_buyer_id'), 'buyers', ['buyer_id'], unique=False)
    
    # Create journal_entries table
    op.create_table('journal_entries',
        sa.Column('entry_id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('entry_type', journalentrytype_enum, nullable=False),
        sa.Column('date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('narration', sa.String(), nullable=False),
        sa.Column('reference', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.company_id'], ),
        sa.PrimaryKeyConstraint('entry_id')
    )
    op.create_index(op.f('ix_journal_entries_entry_id'), 'journal_entries', ['entry_id'], unique=False)
    
    # Create journal_entry_lines table
    op.create_table('journal_entry_lines',
        sa.Column('line_id', sa.Integer(), nullable=False),
        sa.Column('entry_id', sa.Integer(), nullable=False),
        sa.Column('account_code', sa.String(), nullable=True),
        sa.Column('account_name', sa.String(), nullable=False),
        sa.Column('debit', sa.Float(), nullable=True),
        sa.Column('credit', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['entry_id'], ['journal_entries.entry_id'], ),
        sa.PrimaryKeyConstraint('line_id')
    )
    op.create_index(op.f('ix_journal_entry_lines_line_id'), 'journal_entry_lines', ['line_id'], unique=False)
    
    # Create invoices table
    op.create_table('invoices',
        sa.Column('invoice_id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('vendor_id', sa.Integer(), nullable=True),
        sa.Column('buyer_id', sa.Integer(), nullable=True),
        sa.Column('invoice_type', invoicetype_enum, nullable=False),
        sa.Column('file_path', sa.String(), nullable=False),
        sa.Column('invoice_number', sa.String(), nullable=False),
        sa.Column('invoice_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('taxable_amount', sa.Float(), nullable=True),
        sa.Column('igst_amount', sa.Float(), nullable=True),
        sa.Column('cgst_amount', sa.Float(), nullable=True),
        sa.Column('sgst_amount', sa.Float(), nullable=True),
        sa.Column('status', invoicestatus_enum, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.company_id'], ),
        sa.ForeignKeyConstraint(['vendor_id'], ['vendors.vendor_id'], ),
        sa.ForeignKeyConstraint(['buyer_id'], ['buyers.buyer_id'], ),
        sa.PrimaryKeyConstraint('invoice_id')
    )
    op.create_index(op.f('ix_invoices_invoice_id'), 'invoices', ['invoice_id'], unique=False)
    
    # Create bank_transactions table
    op.create_table('bank_transactions',
        sa.Column('transaction_id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('reference', sa.String(), nullable=True),
        sa.Column('type', transactiontype_enum, nullable=False),
        sa.Column('status', transactionstatus_enum, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.company_id'], ),
        sa.PrimaryKeyConstraint('transaction_id')
    )
    op.create_index(op.f('ix_bank_transactions_transaction_id'), 'bank_transactions', ['transaction_id'], unique=False)
    
    # Create reconciliations table
    op.create_table('reconciliations',
        sa.Column('reconciliation_id', sa.Integer(), nullable=False),
        sa.Column('transaction_id', sa.Integer(), nullable=False),
        sa.Column('invoice_id', sa.Integer(), nullable=False),
        sa.Column('match_type', matchtype_enum, nullable=False),
        sa.Column('match_confidence', sa.Float(), nullable=True),
        sa.Column('status', reconciliationstatus_enum, nullable=True),
        sa.Column('settled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['transaction_id'], ['bank_transactions.transaction_id'], ),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.invoice_id'], ),
        sa.PrimaryKeyConstraint('reconciliation_id')
    )
    op.create_index(op.f('ix_reconciliations_reconciliation_id'), 'reconciliations', ['reconciliation_id'], unique=False)
    
    # Create users table
    op.create_table('users',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('password_hash', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('role', userrole_enum, nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('email_verified', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.company_id'], ),
        sa.PrimaryKeyConstraint('user_id'),
        sa.UniqueConstraint('email')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_user_id'), 'users', ['user_id'], unique=False)


def downgrade() -> None:
    """Drop all tables."""
    op.drop_index(op.f('ix_users_user_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    
    op.drop_index(op.f('ix_reconciliations_reconciliation_id'), table_name='reconciliations')
    op.drop_table('reconciliations')
    
    op.drop_index(op.f('ix_bank_transactions_transaction_id'), table_name='bank_transactions')
    op.drop_table('bank_transactions')
    
    op.drop_index(op.f('ix_invoices_invoice_id'), table_name='invoices')
    op.drop_table('invoices')
    
    op.drop_index(op.f('ix_journal_entry_lines_line_id'), table_name='journal_entry_lines')
    op.drop_table('journal_entry_lines')
    
    op.drop_index(op.f('ix_journal_entries_entry_id'), table_name='journal_entries')
    op.drop_table('journal_entries')
    
    op.drop_index(op.f('ix_buyers_buyer_id'), table_name='buyers')
    op.drop_table('buyers')
    
    op.drop_index(op.f('ix_vendors_vendor_id'), table_name='vendors')
    op.drop_table('vendors')
    
    op.drop_index(op.f('ix_companies_company_id'), table_name='companies')
    op.drop_table('companies')
    
    # Drop enum types
    sa.Enum(name='userrole').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='reconciliationstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='matchtype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='transactionstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='transactiontype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='journalentrytype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='invoicestatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='invoicetype').drop(op.get_bind(), checkfirst=True)

