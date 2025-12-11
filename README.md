# Real-time Bookkeeping System

A modern, real-time bookkeeping system with automated invoice processing, bank reconciliation, and financial report generation. Built with FastAPI, PostgreSQL, and a clean web interface.

## Features

- **Invoice Processing**: Upload PDF invoices with automatic classification (sales/purchase)
- **Company Management**: Multi-company support with current company tracking
- **Vendor & Buyer Management**: Auto-create and manage vendors/buyers from invoices
- **Bank Statement Processing**: Upload CSV bank statements and reconcile automatically
- **Automatic Reconciliation**: Smart matching of bank transactions to invoices
- **Settlement**: Mark invoices as paid and update account balances
- **Real-time Reports**: Auto-generate Journal Entries, Ledgers, and Trial Balance
- **User Management**: Multi-user support with role-based access control
- **Email Verification**: Secure email verification for user accounts
- **Web UI**: Modern, responsive web interface for all operations
- **REST API**: Complete REST API with Swagger documentation

## Prerequisites

- **Python**: 3.8 or higher
- **PostgreSQL**: 12 or higher
- **Node.js**: Not required (static frontend)
- **Optional**: Poppler and Tesseract for OCR support (image-based PDFs)

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd bookkeeper
```

### 2. Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables

Create a `.env` file in the project root by copying the example file:

```bash
cp .env.example .env
```

Then edit `.env` with your actual credentials. See [.env.example](.env.example) for all available environment variables and their descriptions.

### 5. Set Up Database

#### Option A: Using Docker Compose (Recommended)

```bash
# Start PostgreSQL
docker-compose up -d db

# Wait for database to be ready, then run migrations
alembic upgrade head
```

#### Option B: Using Local PostgreSQL

```bash
# Create database
createdb bookkeeper

# Run migrations
alembic upgrade head
```

### 6. Start the Application

```bash
python run_api.py
```

The API will be available at:
- **API**: http://localhost:8000
- **Web UI**: http://localhost:8000
- **API Docs (Swagger)**: http://localhost:8000/docs
- **API Docs (ReDoc)**: http://localhost:8000/redoc

## Quick Start Guide

### 1. Sign Up

1. Visit http://localhost:8000/signup.html
2. Create a company account with your details
3. Verify your email (if email is configured)

### 2. Create Your First Invoice

1. Go to **Invoices** page
2. Upload a PDF invoice
3. The system will:
   - Extract invoice data automatically
   - Classify as sales or purchase
   - Create journal entries
   - Generate reports

### 3. Upload Bank Statement

1. Go to **Bank Statements** page
2. Upload a CSV bank statement
3. Click **Run Reconciliation** to match transactions with invoices

### 4. View Reports

1. Go to **Reports** page
2. Generate reports (Journal Entries, Trial Balance, Ledgers)
3. Download CSV files

## Project Structure

```
bookkeeper/
├── api/                    # FastAPI application
│   ├── main.py            # Application entry point
│   ├── routes/            # API route handlers
│   └── schemas.py         # Pydantic models
├── core/                   # Core business logic
│   ├── auth.py            # Authentication & authorization
│   ├── processing.py      # Invoice processing
│   ├── reconciliation.py  # Bank reconciliation
│   └── report_generator.py # Report generation
├── database/               # Database layer
│   ├── models.py          # SQLAlchemy models
│   └── db.py             # Database connection
├── utils/                  # Utility modules
│   ├── accounting_reports.py  # CSV report generation
│   └── invoice_extractor.py  # PDF invoice extraction
├── static/                 # Web UI (HTML, CSS, JS)
├── alembic/                # Database migrations
├── docs/                   # Documentation
├── legacy/                 # Legacy tools (not used in production)
├── docker-compose.yml      # Docker Compose configuration
├── Dockerfile              # Docker image definition
├── requirements.txt        # Python dependencies
└── run_api.py             # API server entry point
```

## Technology Stack

- **Backend Framework**: FastAPI
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy
- **Migrations**: Alembic
- **Authentication**: JWT (python-jose)
- **Password Hashing**: bcrypt
- **Email**: Resend (aiohttp)
- **PDF Processing**: pdfplumber
- **OCR**: pytesseract, pdf2image (optional)
- **AI/LLM**: CrewAI, OpenAI/OpenRouter (optional)
- **Frontend**: HTML, JavaScript, Tailwind CSS

## API Documentation

### Interactive API Docs

Once the server is running:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Main Endpoints

- `POST /api/auth/signup` - Create company account
- `POST /api/auth/login` - User login
- `POST /api/invoices` - Upload invoice PDF
- `POST /api/bank-statements` - Upload bank statement CSV
- `POST /api/reconcile` - Run reconciliation
- `GET /api/reports/bundles` - List report bundles
- `POST /api/reports/generate` - Generate reports

## Docker Deployment

### Using Docker Compose

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop services
docker-compose down
```

See [docs/DEPLOYMENT_PLAN.md](docs/DEPLOYMENT_PLAN.md) for detailed deployment instructions.

## Documentation

Comprehensive documentation is available in the [`docs/`](docs/) folder:

- **[Setup Guide](docs/SETUP.md)**: Detailed setup instructions
- **[Deployment Options](docs/DEPLOYMENT_OPTIONS.md)**: Free and low-cost deployment platforms (Railway, Render, AWS Lightsail, Fly.io)
- **[Deployment Plan](docs/DEPLOYMENT_PLAN.md)**: Docker deployment strategy
- **[Authentication Guide](docs/AUTH_COMPLETE.md)**: User authentication and management
- **[Database Migrations](docs/ALEMBIC_SETUP.md)**: Alembic migration guide
- **[Report Storage](docs/REPORT_STORAGE.md)**: Database-backed report system
- **[Resend Setup](docs/RESEND_SETUP.md)**: Email configuration guide

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `JWT_SECRET_KEY` | Secret key for JWT tokens | Required |
| `OPENAI_API_KEY` | API key for AI extraction | Optional |
| `RESEND_API_KEY` | Resend API key | Required for emails |
| `EMAIL_FROM` | Sender email address | Optional |
| `EMAIL_FROM_NAME` | Sender name | Optional |
| `FRONTEND_URL` | Frontend application URL (for email links) | Optional (auto-detects `RAILWAY_STATIC_URL` on Railway, defaults to http://localhost:8000) |

### Optional Features

- **OCR Support**: Install Poppler and Tesseract for image-based PDF processing
  - macOS: `brew install poppler tesseract`
  - Ubuntu: `sudo apt-get install poppler-utils tesseract-ocr`
- **AI Extraction**: Set `OPENAI_API_KEY` for enhanced invoice data extraction
- **Email**: Configure Resend API key for user notifications (see [Resend Setup](docs/RESEND_SETUP.md))

## Development

### Running Tests

```bash
# Run with pytest (if tests are added)
pytest
```

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

### Code Structure

- **API Routes**: `api/routes/` - FastAPI route handlers
- **Business Logic**: `core/` - Core processing logic
- **Database Models**: `database/models.py` - SQLAlchemy models
- **Utilities**: `utils/` - Helper functions

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

[Your License Here]

## Support

For issues, questions, or contributions, please open an issue on GitHub.

## Acknowledgments

- FastAPI for the excellent web framework
- SQLAlchemy for the powerful ORM
- CrewAI for AI agent orchestration

---

**Made with ❤️ for modern bookkeeping**
