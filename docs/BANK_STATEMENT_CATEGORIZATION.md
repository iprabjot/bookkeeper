# Bank Statement Categorization System

## Overview

The bank statement categorization system uses AI (CrewAI) to automatically categorize all bank transactions into appropriate accounting categories. It supports both CSV and PDF bank statements from Indian banks (HDFC, ICICI, SBI, etc.).

## Features

1. **PDF Bank Statement Parsing**: Extracts transactions from PDF bank statements using table extraction and text parsing
2. **AI-Powered Categorization**: Uses CrewAI with comprehensive category taxonomy for accurate categorization
3. **Reconciled Transaction Support**: Uses invoice data when transactions are matched with invoices
4. **Confidence Scoring**: Provides HIGH, MEDIUM, or LOW confidence levels for each categorization
5. **Review Flagging**: Automatically flags uncertain transactions for human review

## Category Taxonomy

The system categorizes transactions into:

### Income Categories
- **Operating Revenue**: Product Sales (Domestic/Export), Service Revenue (Time & Materials/Fixed-price), Subscriptions, SaaS fees
- **Other Operating Income**: Commissions, Royalties, Rental Income
- **Non-Operating Income**: Interest, Dividends, Asset Gains, Investment Income, Grants

### Expense Categories
- **Operating Expenses - G&A**: Salaries, Rent, Utilities, Office Supplies, Insurance, Professional Fees, Travel, Communications
- **Operating Expenses - IT**: Software Licenses, Cloud Hosting, Payment Gateway Fees, DevOps Tools
- **Operating Expenses - Marketing**: Advertising, Sales Commissions, Events, Marketing Software
- **Direct Expenses**: Contractor Payments, Subcontractor Costs
- **COGS**: Raw Materials, Direct Labor, Manufacturing Overhead, Freight
- **Financial Expenses**: Interest, Bank Charges, Foreign Exchange Loss
- **Taxation**: Income Tax, GST/VAT, Professional Tax

### Non-P&L Categories
- **Internal Transfers**: Transfers between own accounts

## Usage

### API Endpoint

```
POST /api/bank-statements
```

**Parameters:**
- `file`: Bank statement file (CSV or PDF)
- `categorize`: Boolean (default: true) - Whether to categorize transactions

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/bank-statements?categorize=true" \
  -H "Authorization: Bearer <token>" \
  -F "file=@Acct_Statement_XX7340_25022025.pdf"
```

### Response Format

Each transaction includes:
- `transaction_id`: Unique transaction ID
- `date`: Transaction date
- `amount`: Transaction amount
- `description`: Bank narration
- `reference`: Reference number (UTR, Cheque No, etc.)
- `type`: "credit" or "debit"
- `status`: "unmatched", "matched", or "settled"
- `category`: Category code (e.g., "EXP-GA-UTIL", "INC-SVC-TM")
- `created_at`: Timestamp

## How It Works

### 1. PDF Parsing

The system extracts transactions from PDF bank statements by:
- Extracting tables using `pdfplumber`
- Parsing text when tables aren't available
- Supporting multiple bank formats (HDFC, ICICI, SBI)

### 2. Categorization Process

For each transaction:

1. **Check Reconciliation Status**: If transaction is matched with an invoice, use invoice data as primary signal
2. **Extract Context**: Parse bank narration for merchant names, UPI IDs, NEFT/RTGS references
3. **Pattern Matching**: Match against known merchant patterns (AWS → Cloud, Airtel → Communications, etc.)
4. **AI Analysis**: Use CrewAI to analyze transaction context and assign category
5. **Confidence Scoring**: Assign HIGH/MEDIUM/LOW confidence based on clarity of signals

### 3. Review Flagging

Transactions are flagged for review when:
- Confidence is LOW
- Amount exceeds ₹1,00,000
- Transaction is ambiguous or could fit multiple categories

## Configuration

### Environment Variables

```bash
# Required for AI categorization
OPENAI_API_KEY=your_api_key
OPENAI_API_BASE=https://openrouter.ai/api/v1  # Optional, defaults to OpenRouter
OPENAI_MODEL_NAME=openai/gpt-4o-mini  # Optional, defaults to gpt-4o-mini
```

### Category Customization

Categories are defined in `core/transaction_categorizer.py`:
- `CATEGORY_TAXONOMY`: Maps category codes to human-readable names
- `CATEGORY_PATHS`: Maps category codes to full hierarchy paths

## Database Schema

### Migration Required

Run the migration to add the `category` field:

```bash
alembic upgrade head
```

The migration file: `alembic/versions/add_category_to_bank_transactions.py`

### BankTransaction Model

Added field:
- `category`: String (nullable) - Stores the category code (e.g., "EXP-GA-UTIL")

## Examples

### Example 1: Utility Payment (High Confidence)

**Transaction:**
- Description: "NEFT/HDFC/UTR123/BESCOM ELECTRICITY BILL"
- Amount: -5,000 (debit)
- Type: Debit

**Categorization:**
- Category: `EXP-GA-UTIL` (Utilities)
- Confidence: HIGH
- Reasoning: "BESCOM is a known electricity provider pattern"

### Example 2: Service Revenue (Reconciled)

**Transaction:**
- Description: "RTGS/SBI/UTR456/TECHSOLUTIONS PVT LTD"
- Amount: 118,000 (credit)
- Type: Credit
- Reconciled: Yes
- Invoice: "Web Development Services - January 2025"

**Categorization:**
- Category: `INC-SVC-TM` (Service Revenue — Time & Materials)
- Confidence: HIGH
- Reasoning: "Invoice line item explicitly mentions hourly billing"

### Example 3: Ambiguous Transaction (Low Confidence)

**Transaction:**
- Description: "NEFT/ICICI/UTR789/SHARMA ENTERPRISES"
- Amount: -75,000 (debit)
- Type: Debit
- Reconciled: No

**Categorization:**
- Category: `EXP-UNCAT` (Uncategorized Expense)
- Confidence: LOW
- Requires Review: Yes
- Reasoning: "Beneficiary 'Sharma Enterprises' is generic. Could be supplier payment, contractor, or other vendor."

## Troubleshooting

### PDF Parsing Issues

If PDF parsing fails:
1. Check if PDF is image-based (scanned) - may need OCR
2. Verify PDF structure - some banks use non-standard formats
3. Check logs for specific error messages

### Categorization Not Working

If categorization is not working:
1. Verify `OPENAI_API_KEY` is set in environment
2. Check API quota/limits
3. Review logs for API errors
4. Fallback to rule-based categorization if AI unavailable

### Low Accuracy

To improve categorization accuracy:
1. Reconcile transactions with invoices when possible
2. Review and correct miscategorized transactions
3. System learns from manual corrections (future enhancement)

## Future Enhancements

1. **Learning from Corrections**: Store manual corrections to improve future categorizations
2. **Merchant Dictionary**: Build database of merchant → category mappings
3. **Batch Processing**: Optimize for large statement files
4. **Custom Categories**: Allow users to define custom categories
5. **Category Rules**: User-defined rules for specific patterns

## Support

For issues or questions:
1. Check logs in `core/bank_parser.py` and `core/transaction_categorizer.py`
2. Review API error messages
3. Verify environment configuration

