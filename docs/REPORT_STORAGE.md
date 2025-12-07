# Report Storage System

## Overview

All reports are stored **exclusively in the database** (PostgreSQL), not on disk. This ensures:
-  No file system dependencies
-  Works seamlessly on remote servers
-  Easy backup and restore
-  Version control through report bundles
-  No disk space management needed

## How It Works

### Database Storage

Reports are stored in two tables:

1. **`report_bundles`**: Groups reports generated together
   - `bundle_id`: Unique identifier
   - `company_id`: Company these reports belong to
   - `generated_at`: Timestamp
   - `generated_by_user_id`: User who generated them
   - `description`: Optional description

2. **`reports`**: Individual CSV reports
   - `report_id`: Unique identifier
   - `bundle_id`: Links to bundle
   - `report_type`: `journal_entries`, `trial_balance`, or `ledger`
   - `account_name`: For ledgers only
   - `content`: **CSV content stored as text** (not file path)
   - `filename`: Display name (e.g., "Journal Entries.csv")
   - `size_bytes`: Size of content

### Report Generation Flow

1. **Invoice Processing** (`core/processing.py`):
   - Invoice uploaded → Journal entry created
   - Automatically calls `regenerate_csvs()`

2. **Report Generation** (`core/report_generator.py`):
   - Reads all journal entries from database
   - Generates CSV content as strings (using `accounting_reports.py`)
   - Creates new `ReportBundle`
   - Stores each CSV as a `Report` record with content in database
   - **No disk writes**

3. **API Endpoints** (`api/routes/reports.py`):
   - `GET /api/reports/{report_id}/download`: Returns CSV content directly from database
   - `GET /api/reports/bundles`: Lists all bundles
   - `POST /api/reports/generate`: Manually trigger generation

### Report Naming

Reports use clean, descriptive filenames:
- `Journal Entries.csv`
- `Trial Balance.csv`
- `Ledger - {Account Name}.csv`

(Previously had "-Table 1" suffix, now removed)

## Legacy Code

Some legacy scripts still write to disk (not used by API):
- `invoice_workflow.py`: Used only by CLI tools
- `run_full_workflow.py`: Test/utility script
- `accounting_reports.py`: Contains `generate_all_csvs()` for disk-based generation (legacy)

**These are NOT used by the FastAPI application.**

## Deployment Considerations

### Remote Server Setup

No special configuration needed:
-  No need to create `reports/` directory
-  No need to manage disk space
-  No need to configure file permissions
-  Works with any PostgreSQL setup

### Database Size

CSV reports are stored as text in the database. For a typical company:
- Journal Entries: ~1-5 KB per report
- Trial Balance: ~1-3 KB per report
- Ledger: ~1-2 KB per account

A bundle with 10 accounts = ~15-30 KB total.

### Backup

Since everything is in the database:
- Standard PostgreSQL backup includes all reports
- No separate file system backup needed
- Restore database = restore all reports

## API Usage

### Generate Reports
```bash
POST /api/reports/generate?description=End%20of%20month
```

### List Bundles
```bash
GET /api/reports/bundles
```

### Download Report
```bash
GET /api/reports/{report_id}/download
```

### List Reports in Bundle
```bash
GET /api/reports/list?bundle_id=123
```

## Summary

 **All reports stored in database**  
 **No disk writes in production code**  
 **Works on any server with PostgreSQL**  
 **Clean, descriptive filenames**  
 **Version control through bundles**

