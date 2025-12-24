# Logging Guide

This guide explains how to check logs for the Bookkeeper application in different environments.

## Local Development

### Option 1: Terminal Output (Direct Run)

When running the API directly with `python run_api.py` or `uvicorn`, logs appear in your terminal:

```bash
# Run the API server
python run_api.py

# Or directly with uvicorn
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

Logs will show:
- API requests/responses
- Application errors
- Database queries (if SQLAlchemy logging is enabled)
- Migration output

### Option 2: Docker Compose Logs

If running with `docker-compose`, view logs:

```bash
# View all logs (both app and database)
docker-compose logs

# View only app logs
docker-compose logs app

# Follow logs in real-time (like tail -f)
docker-compose logs -f app

# View last 100 lines
docker-compose logs --tail=100 app

# View logs for specific service
docker-compose logs db
```

### Option 3: Docker Container Logs

If running individual containers:

```bash
# View logs for a specific container
docker logs bookkeeper_app

# Follow logs in real-time
docker logs -f bookkeeper_app

# View last 50 lines
docker logs --tail=50 bookkeeper_app
```

## Railway Deployment

### Option 1: Railway Dashboard (Easiest)

1. Go to [railway.app/dashboard](https://railway.app/dashboard)
2. Click on your project
3. Click on your **app service** (not the database)
4. Click on **"Deployments"** tab
5. Click on the latest deployment
6. Click **"View Logs"** or **"Logs"** tab

You'll see:
- Build logs (during deployment)
- Runtime logs (application output)
- Real-time updates

### Option 2: Railway CLI

Install Railway CLI and view logs:

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login to Railway
railway login

# Link to your project (if not already linked)
railway link

# View logs (follows in real-time)
railway logs

# View logs for specific service
railway logs --service <service-name>

# View last N lines
railway logs --tail=100
```

### Option 3: Railway Dashboard - Real-time Logs

1. Go to Railway dashboard
2. Select your project → App service
3. Click **"Logs"** tab (at the top)
4. Logs stream in real-time
5. Use filters/search to find specific entries

## Log Levels

The application uses Python's `logging` module with these levels:

- **INFO**: General information (API requests, successful operations)
- **WARNING**: Warnings (non-critical issues)
- **ERROR**: Errors (exceptions, failures)
- **DEBUG**: Detailed debugging information (not enabled by default)

## What Gets Logged

### Application Logs

- API requests and responses
- Database operations (if enabled)
- Invoice processing status
- Report generation
- Bank reconciliation
- Authentication events
- Email sending status

### Error Logs

- Unhandled exceptions (with full traceback)
- Database connection errors
- File processing errors
- API errors (500 errors)

## Filtering Logs

### Railway Dashboard

- Use the search box to filter logs
- Filter by log level (INFO, ERROR, etc.)
- Filter by time range
- Filter by deployment

### Command Line (Docker)

```bash
# Filter for errors only
docker-compose logs app | grep ERROR

# Filter for specific endpoint
docker-compose logs app | grep "/api/invoices"

# Filter for specific time
docker-compose logs app | grep "2025-01-"
```

### Railway CLI

```bash
# Filter logs
railway logs | grep ERROR

# Filter by service
railway logs --service app
```

## Common Log Messages

### Successful Operations

```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Database Migrations

```
Running database migrations...
INFO [alembic.runtime.migration] Running upgrade -> abc123, initial migration
```

### API Requests

```
INFO:     127.0.0.1:51117 - "GET /api/health HTTP/1.1" 200 OK
INFO:     127.0.0.1:51117 - "POST /api/invoices HTTP/1.1" 200 OK
```

### Errors

```
ERROR:    Unhandled exception: ValueError: Invalid invoice data
ERROR:    Traceback (most recent call last):
          ...
```

## Enabling Debug Logging

### Local Development

Update `api/main.py`:

```python
logging.basicConfig(
    level=logging.DEBUG,  # Change from INFO to DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Railway

Set environment variable:

```
LOG_LEVEL=DEBUG
```

Then update `api/main.py` to read from environment:

```python
import os
log_level = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

## Database Query Logging

To see SQL queries, enable SQLAlchemy logging:

```python
# In api/main.py or database/db.py
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

## Troubleshooting with Logs

### Application Won't Start

```bash
# Check startup logs
docker-compose logs app | grep -i error
railway logs | grep -i error
```

### Database Connection Issues

```bash
# Check database connection logs
docker-compose logs app | grep -i database
docker-compose logs db
```

### API Errors

```bash
# Check API error logs
docker-compose logs app | grep "500\|ERROR"
railway logs | grep ERROR
```

### Migration Issues

```bash
# Check migration logs
docker-compose logs app | grep -i migration
railway logs | grep -i migration
```

## Log Retention

### Railway

- **Free Tier**: Logs retained for 7 days
- **Paid Plans**: Extended retention available

### Docker

- Logs stored in container until container is removed
- Use `docker-compose logs` to view historical logs
- Consider using log rotation for production

## Best Practices

1. **Monitor Error Logs**: Regularly check for ERROR level logs
2. **Use Log Levels**: Use appropriate log levels (INFO, ERROR, etc.)
3. **Include Context**: Logs include request path, method, and error details
4. **Don't Log Sensitive Data**: Avoid logging passwords, tokens, or personal data
5. **Use Structured Logging**: Consider JSON logging for better parsing

## Quick Reference

### Local Development
```bash
# Docker Compose
docker-compose logs -f app

# Direct run
python run_api.py  # Logs appear in terminal
```

### Railway
```bash
# CLI
railway logs

# Dashboard
railway.app → Project → Service → Logs tab
```

---

**Need Help?**
- Check Railway logs first for deployment issues
- Check Docker logs for local development issues
- Look for ERROR level logs to find problems







