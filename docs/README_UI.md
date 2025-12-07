# Bookkeeper UI

A web-based user interface for the bookkeeping system.

## Access the UI

1. Start the API server:
   ```bash
   python run_api.py
   ```

2. Open your browser and navigate to:
   ```
   http://localhost:8000
   ```

## Features

### Dashboard
- View company status
- See invoice and transaction summaries
- Quick access to common actions

### Invoices
- Upload PDF invoices (drag & drop or click to select)
- View all invoices with details
- Automatic AI-based extraction

### Bank Statements
- Upload CSV bank statements
- View all bank transactions
- Run reconciliation to match transactions with invoices

### Reports
- Generate CSV reports
- Download Journal Entries, Trial Balance, and Ledgers

### Companies
- Create and manage companies
- Set current company

### Vendors
- View all vendors (auto-created from purchase invoices)

### Buyers
- View all buyers (auto-created from sales invoices)

## API Endpoints

The UI uses the REST API at `http://localhost:8000/api`. All endpoints are documented at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
