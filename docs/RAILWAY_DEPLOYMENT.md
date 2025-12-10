# Railway Deployment Guide

This guide walks you through deploying Bookkeeper to Railway step-by-step.

## Prerequisites

- GitHub account
- Railway account (sign up at [railway.app](https://railway.app))
- Gmail account (for SMTP, optional but recommended)

## Step 1: Prepare Your Repository

1. **Push your code to GitHub** (if not already):
   ```bash
   git add .
   git commit -m "Prepare for Railway deployment"
   git push origin main
   ```

2. **Generate JWT Secret**:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
   Save this value - you'll need it in Step 4.

## Step 2: Create Railway Project

1. Go to [railway.app](https://railway.app) and sign up/login
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Authorize Railway to access your GitHub
5. Select your `bookkeeper` repository
6. Railway will automatically detect your `Dockerfile` and start deploying

## Step 3: Add PostgreSQL Database

1. In your Railway project, click **"New"**
2. Select **"Database"** → **"Add PostgreSQL"**
3. Railway will automatically:
   - Create a PostgreSQL database
   - Set the `DATABASE_URL` environment variable
   - Link it to your app service

## Step 4: Configure Environment Variables

1. Click on your **app service** (not the database)
2. Go to the **"Variables"** tab
3. Click **"New Variable"** and add each variable:

### Required Variables

**JWT_SECRET_KEY** (REQUIRED)
- Value: Paste the secret you generated in Step 1
- Example: `wqq94B7nZp_ab_wMhvJVJlGXKQoCsPSs2ywFp9yVZi4`

**JWT_ALGORITHM**
- Value: `HS256`

**ACCESS_TOKEN_EXPIRE_MINUTES**
- Value: `30`

**REFRESH_TOKEN_EXPIRE_DAYS**
- Value: `7`

**DATABASE_URL** (Auto-set by Railway)
- Railway automatically sets this when you add PostgreSQL
- You don't need to add it manually - it's already there!

### Optional Variables (for full functionality)

**SMTP Configuration** (for email notifications):

**⚠️ Important**: Gmail SMTP may not work on Railway due to network restrictions. **Use SendGrid instead** (see [SMTP Troubleshooting](RAILWAY_SMTP_TROUBLESHOOTING.md)).

**Option 1: SendGrid (Recommended for Railway)**
- `SMTP_HOST`: `smtp.sendgrid.net`
- `SMTP_PORT`: `587`
- `SMTP_USER`: `apikey`
- `SMTP_PASSWORD`: Your SendGrid API key
- `EMAIL_FROM`: Your verified email address
- `EMAIL_FROM_NAME`: `Bookkeeper`

**Option 2: Gmail (May not work on Railway)**
- `SMTP_HOST`: `smtp.gmail.com`
- `SMTP_PORT`: `587` (or `465` if 587 doesn't work)
- `SMTP_USER`: Your Gmail address
- `SMTP_PASSWORD`: Your Gmail App Password ([see Gmail setup guide](GMAIL_SMTP_SETUP.md))
- `EMAIL_FROM`: Your Gmail address
- `EMAIL_FROM_NAME`: `Bookkeeper`

**OpenAI API** (for AI invoice extraction):
- `OPENAI_API_KEY`: Your OpenAI or OpenRouter API key
- `OPENAI_API_BASE`: `https://openrouter.ai/api/v1` (if using OpenRouter)
- `OPENAI_MODEL_NAME`: `openai/gpt-4o-mini`

## Step 5: Deploy

Railway will automatically:
- Detect your Dockerfile
- Build the Docker image
- Run database migrations on startup (configured in Dockerfile)
- Start the FastAPI server
- Assign a public URL

**No additional configuration needed!** The Dockerfile is already configured to:
- Run database migrations automatically (`alembic upgrade head`)
- Start the FastAPI server on the correct port
- Support Railway's PORT environment variable

## Step 6: Get Your App URL

1. Once deployed, Railway will provide a URL like:
   `https://bookkeeper-production.up.railway.app`
2. Click on your app service → **"Settings"** → **"Generate Domain"** (if not auto-generated)
3. Or add a custom domain in **"Settings"** → **"Domains"**

## Step 7: Verify Everything Works

The frontend automatically detects the API base URL from the current domain, so it will work automatically in production!

**Test your deployment:**
1. Visit your Railway URL (e.g., `https://bookkeeper-production.up.railway.app`)
2. Test signup/login
3. Upload an invoice
4. Generate reports
5. Test email functionality (if configured)

**Note**: The frontend will automatically use the correct API URL - no configuration needed!

## Troubleshooting

### Database Connection Issues

- Verify `DATABASE_URL` is set correctly
- Check that PostgreSQL service is running
- Ensure migrations ran: Check logs for "Running database migrations..."

### Build Failures

- Check Railway build logs
- Verify Dockerfile is correct
- Ensure all dependencies are in `requirements.txt`

### App Crashes

- Check Railway logs: App service → "Deployments" → Click deployment → "View Logs"
- Common issues:
  - Missing environment variables
  - Database not ready (migrations failed)
  - Port conflicts

### Static Files Not Loading

- Verify `static/` directory is included in Dockerfile
- Check that FastAPI is serving static files correctly
- Verify CORS settings allow your domain

## Railway-Specific Tips

1. **Auto-Deploy**: Railway auto-deploys on git push to main branch
2. **Environment Variables**: Can be set per-service or globally
3. **Logs**: View real-time logs in Railway dashboard
4. **Metrics**: Railway provides basic metrics (CPU, memory, network)
5. **Scaling**: Railway can scale horizontally (paid plans)

## Cost

- **Free Tier**: $5 credit/month (usually enough for MVP)
- **Hobby Plan**: $5/month (if you exceed free tier)
- **Pro Plan**: $20/month (for production)

## Next Steps

- Set up custom domain (optional)
- Configure backups (Railway handles this automatically)
- Set up monitoring (Railway provides basic monitoring)
- Configure CORS for your domain (update `api/main.py`)

## Quick Reference

**Railway Dashboard**: https://railway.app/dashboard

**Useful Commands** (Railway CLI):
```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Link to project
railway link

# View logs
railway logs

# Open shell
railway shell
```

---

**Need Help?**
- Railway Docs: https://docs.railway.app
- Railway Discord: https://discord.gg/railway
