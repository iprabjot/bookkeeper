# Initial Migration Guide

## Overview

The initial migration (`0001_initial_schema.py`) creates **all database tables** from scratch. This is perfect for:
-  New deployments
-  Clean database setup
-  Fresh installations

## What Gets Created

The migration creates **9 tables** and **8 enum types**:

### Tables:
1. **companies** - Company information
2. **vendors** - Vendor/supplier details
3. **buyers** - Buyer/customer details
4. **journal_entries** - Journal entry headers
5. **journal_entry_lines** - Journal entry line items
6. **invoices** - Invoice records
7. **bank_transactions** - Bank statement transactions
8. **reconciliations** - Invoice-transaction matches
9. **users** - User accounts and authentication

### Enum Types:
- `invoicetype` (SALES, PURCHASE)
- `invoicestatus` (PENDING, PAID, PARTIALLY_PAID)
- `journalentrytype` (SALES, PURCHASE, PAYMENT, RECEIPT, OTHER)
- `transactiontype` (CREDIT, DEBIT)
- `transactionstatus` (UNMATCHED, MATCHED, SETTLED)
- `matchtype` (EXACT, FUZZY, MANUAL)
- `reconciliationstatus` (PENDING, VERIFIED, SETTLED)
- `userrole` (OWNER, ADMIN, ACCOUNTANT, VIEWER)

## Usage

### For Clean Database

```bash
# Apply initial migration
alembic upgrade head
```

This creates all tables in the correct order (respecting foreign key dependencies).

### For Existing Database

If you already have tables created via `init_db.py`:

**Option 1: Keep existing, add users**
```bash
# Create a new migration just for users
alembic revision --autogenerate -m "Add users table"
alembic upgrade head
```

**Option 2: Start fresh ( Deletes all data!)**
```bash
# Drop all tables manually or:
# Use init_db.py to drop, then:
alembic upgrade head
```

**Option 3: Mark as baseline**
```bash
# Tell Alembic that tables already exist
alembic stamp head
```

## Migration File Location

- **File**: `alembic/versions/0001_initial_schema.py`
- **Revision ID**: `0001`
- **Creates**: All 9 tables + 8 enum types

## Verification

After applying the migration:

```bash
# Check current revision
alembic current

# Should show: 0001 (head)

# Verify tables exist
psql $DATABASE_URL -c "\dt"
```

## Rollback

To rollback (drops all tables):

```bash
alembic downgrade base
```

 **Warning**: This will delete all data!

## Next Steps

After initial migration:
1. Create your first company via signup
2. Start uploading invoices
3. Future schema changes will use new migrations

