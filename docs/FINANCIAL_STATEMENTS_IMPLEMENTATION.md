# Financial Statements Implementation

## Overview

Added Profit & Loss Statement and Cash Flow Statement generation using AI agents. These reports are generated from trial balance and bank transaction data, stored in the database, and accessible via API endpoints.

## Implementation Summary

### Phase 1: Database Schema Updates
- Added `PROFIT_LOSS` and `CASH_FLOW` to `ReportType` enum in `database/models.py`
- Created Alembic migration `1765381524_add_financial_statements_reports.py`
- Updated PostgreSQL enum type to include new report types

### Phase 2: AI Agent Service
- Created `core/financial_report_agent.py`
- Integrated CrewAI reporting agent from `agents/reporting_agent.yaml`
- Implemented `generate_profit_loss_statement()` function
- Implemented `generate_cash_flow_statement()` function
- Added JSON parsing and error handling

### Phase 3: CSV Generation Functions
- Added `generate_profit_loss_csv_string()` to `utils/accounting_reports.py`
- Added `generate_cash_flow_csv_string()` to `utils/accounting_reports.py`
- Both functions format AI agent output into CSV format

### Phase 4: Report Generator Integration
- Updated `core/report_generator.py` to call AI agent for P&L and Cash Flow
- Integrated bank transaction data for Cash Flow statement
- Added error handling to continue report generation even if AI fails
- Reports are automatically generated when journal entries are added

### Phase 5: API Endpoints
- Added `GET /api/reports/profit-loss` endpoint
- Added `GET /api/reports/cash-flow` endpoint
- Updated `list_reports()` to include new report types
- Reports are downloadable as CSV files

### Phase 6: Frontend Support
- Added `getProfitLossCsv()` and `getCashFlowCsv()` to `static/api.js`
- Frontend automatically displays new reports when available
- Download buttons work with existing infrastructure

## How It Works

1. **Trigger**: When journal entries are created (e.g., from invoice processing), `regenerate_csvs()` is called
2. **Data Collection**: Trial balance data is extracted from journal entries, bank transactions are fetched
3. **AI Processing**: 
   - CrewAI reporting agent analyzes trial balance
   - Classifies accounts as Revenue/Expenses for P&L
   - Analyzes bank transactions for Cash Flow
4. **CSV Generation**: AI output is formatted into CSV strings
5. **Storage**: Reports are stored in `reports` table with `report_type` = `profit_loss` or `cash_flow`
6. **API Access**: Reports are accessible via API endpoints
7. **Frontend Display**: Reports appear in the reports page with download buttons

## CSV Format

### Profit & Loss Statement
```csv
Category,Subcategory,Amount
Revenue,Revenue from Operations,4500000
Revenue,Other Income,50000
Total Revenue,,4550000
Expenses,Cost of Materials,2000000
Expenses,Employee Benefits,800000
Expenses,Other Expenses,1000000
Total Expenses,,3800000
Profit Before Tax,,750000
Tax Expense,,187500
Net Profit,,562500
```

### Cash Flow Statement
```csv
Category,Item,Amount
Operating Activities,Net Profit,562500
Operating Activities,Adjustments for non-cash items,50000
Operating Activities,Changes in working capital,-100000
Cash from Operating Activities,,512500
Investing Activities,Purchase of assets,-200000
Cash from Investing Activities,,-200000
Financing Activities,Loan received,300000
Financing Activities,Loan repayment,-100000
Cash from Financing Activities,,200000
Net Increase in Cash,,512500
Opening Cash Balance,,100000
Closing Cash Balance,,612500
```

## Configuration

### Required Environment Variables
- `OPENAI_API_KEY`: API key for OpenAI or OpenRouter
- `OPENAI_API_BASE`: Base URL (e.g., `https://openrouter.ai/api/v1`)
- `OPENAI_MODEL_NAME`: Model name (e.g., `openai/gpt-4o-mini`)

### AI Agent Configuration
- Agent: `agents/reporting_agent.yaml`
- Task: `tasks/generate_financial_statements.yaml`
- Temperature: 0.0 (for consistent results)

## Error Handling

- If AI agent fails, error is logged but report generation continues
- P&L and Cash Flow reports are optional - other reports still generate
- Frontend gracefully handles missing reports
- Errors are logged with full stack traces for debugging

## Testing

To test the implementation:

1. Upload invoices to create journal entries
2. Upload bank statements
3. Generate reports via API or UI
4. Check logs for AI agent execution
5. Download P&L and Cash Flow reports
6. Verify CSV format and data accuracy

## Future Enhancements

- Balance Sheet (requires asset management)
- Financial ratios (requires Balance Sheet)
- Prior period comparison
- PDF export
- Custom report periods
- Caching AI responses for identical data

## Files Modified

- `database/models.py`
- `alembic/versions/1765381524_add_financial_statements_reports.py`
- `core/financial_report_agent.py` (new)
- `utils/accounting_reports.py`
- `core/report_generator.py`
- `api/routes/reports.py`
- `static/api.js`

## Dependencies

- CrewAI (already installed)
- OpenAI/OpenRouter API access
- PostgreSQL with enum support
- Existing report infrastructure

