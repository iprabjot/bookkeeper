# Deployment & Setup Guide

## Quick Start

### 1. Install Dependencies
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment
Copy `.env.example` to `.env` and set:
- `DATABASE_URL` - PostgreSQL connection string
- `JWT_SECRET_KEY` - Secure random string (min 32 chars)
- `SMTP_*` - Email configuration (optional, see SMTP_RECOMMENDATIONS.md)

### 3. Run Database Migrations

**For clean/new database:**
```bash
# Creates all tables (companies, vendors, buyers, journal_entries, invoices, etc.)
alembic upgrade head
```

**For existing database with tables:**
```bash
# Option 1: Add users table only
alembic revision --autogenerate -m "Add users table"
alembic upgrade head

# Option 2: Mark existing state as baseline
alembic stamp head
```

### 4. Start Server
```bash
python run_api.py
```

Or with Docker:
```bash
docker-compose up -d
```

## Alembic Migrations

### First Time Setup

If you have an **existing database** with tables:
```bash
# Mark current state as baseline
alembic stamp head
```

If starting **fresh**:
```bash
# Apply all migrations
alembic upgrade head
```

### Common Commands

```bash
# Check current migration
alembic current

# View history
alembic history

# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

See `MIGRATION_GUIDE.md` for detailed documentation.

## Free SMTP Services

### Recommended: Gmail (Easiest)

1. Enable 2FA on Gmail
2. Create App Password: Google Account → Security → App passwords
3. Configure `.env`:
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-16-char-app-password
EMAIL_FROM=your-email@gmail.com
EMAIL_FROM_NAME=Bookkeeper
```

**Limits**: 500 emails/day (free Gmail)

### Alternative: SendGrid (Best for Production)

1. Sign up at https://sendgrid.com
2. Verify sender email
3. Create API key
4. Configure `.env`:
```env
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=your-sendgrid-api-key
EMAIL_FROM=your-verified-email@domain.com
EMAIL_FROM_NAME=Bookkeeper
```

**Limits**: 100 emails/day (free tier)

See `SMTP_RECOMMENDATIONS.md` for more options (Mailgun, Brevo, Amazon SES).

## Docker Deployment

### Using Docker Compose

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild after changes
docker-compose up -d --build
```

### Environment Variables

Create `.env` file or set in `docker-compose.yml`:
- Database credentials
- JWT secret key
- SMTP settings
- OpenAI API key

## Production Checklist

- [ ] Set secure `JWT_SECRET_KEY` (32+ characters)
- [ ] Use strong database passwords
- [ ] Configure SMTP for email notifications
- [ ] Set up HTTPS/SSL
- [ ] Configure CORS properly (not `*`)
- [ ] Set up database backups
- [ ] Enable rate limiting
- [ ] Set up monitoring/logging
- [ ] Test email delivery
- [ ] Test authentication flow

## API Endpoints

### Public
- `POST /api/auth/signup` - Create company account
- `POST /api/auth/login` - Login
- `POST /api/auth/refresh` - Refresh token
- `GET /api/health` - Health check

### Protected (Require Auth)
- `GET /api/auth/me` - Current user
- `GET /api/users` - List users (owner/admin)
- `POST /api/users` - Create user (owner/admin)
- All other `/api/*` endpoints

## Troubleshooting

### Migration Issues
- Check `DATABASE_URL` is correct
- Verify database is running
- Check `alembic current` for current state

### Email Not Sending
- Verify SMTP credentials
- Check firewall/network
- Test with Gmail first (easiest)
- Check console logs for errors

### Authentication Issues
- Verify `JWT_SECRET_KEY` is set
- Check token expiration settings
- Clear browser localStorage if needed

## Documentation

- `MIGRATION_GUIDE.md` - Alembic migration workflows
- `SMTP_RECOMMENDATIONS.md` - Free SMTP service options
- `AUTH_COMPLETE.md` - Authentication implementation details
- `DEPLOYMENT_PLAN.md` - Full deployment plan

