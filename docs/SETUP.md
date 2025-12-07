# Setup Guide

## Prerequisites

1. PostgreSQL installed and running
2. Python 3.8+ with virtual environment
3. All dependencies installed

## Quick Start

### 1. Install Dependencies

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Database

Create a `.env` file in the project root:

```env
DATABASE_URL=postgresql://username:password@localhost:5432/bookkeeper
OPENAI_API_KEY=your_key_here
OPENAI_API_BASE=https://openrouter.ai/api/v1
OPENAI_MODEL_NAME=openai/gpt-oss-20b:free
```

### 3. Initialize Database

Run Alembic migrations to create all tables:

```bash
alembic upgrade head
```

This creates all necessary tables in PostgreSQL. See `docs/ALEMBIC_SETUP.md` for more details.

### 4. Start the API Server

```bash
python run_api.py
```

API will be available at:
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## First Steps

### 1. Create Your Company

```bash
curl -X POST "http://localhost:8000/api/companies" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Your Company Name",
    "gstin": "YOUR_GSTIN",
    "is_current": true
  }'
```

### 2. Upload an Invoice

```bash
curl -X POST "http://localhost:8000/api/invoices" \
  -F "file=@path/to/invoice.pdf"
```

The system will:
- Extract invoice data
- Classify as sales or purchase
- Create vendor/buyer if needed
- Create journal entry
- Regenerate CSV reports

### 3. Upload Bank Statement

```bash
curl -X POST "http://localhost:8000/api/bank-statements" \
  -F "file=@path/to/statement.csv"
```

### 4. Run Reconciliation

```bash
curl -X POST "http://localhost:8000/api/reconcile"
```

### 5. Download Reports

CSV reports are automatically generated in the `reports/` directory and can be downloaded via API.

## Testing

Use the Swagger UI at http://localhost:8000/docs to test all endpoints interactively.

## Troubleshooting

### Database Connection Issues

- Ensure PostgreSQL is running
- Check DATABASE_URL in .env
- Verify database exists: `psql -l | grep bookkeeper`

### Import Errors

- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Activate virtual environment: `source .venv/bin/activate`

### CSV Generation Issues

- Ensure `reports/` directory exists
- Check file permissions

