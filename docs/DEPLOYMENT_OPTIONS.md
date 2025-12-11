# Deployment Options for Bookkeeper

This guide covers the best deployment options for the Bookkeeper application, focusing on free and low-cost solutions.

## Quick Comparison

| Platform | Cost | Ease | Best For |
|----------|------|------|----------|
| **Railway** | Free tier, then $5/month | ⭐⭐⭐⭐⭐ | Easiest deployment |
| **Render** | Free tier available | ⭐⭐⭐⭐ | Good balance |
| **AWS Lightsail** | $3.50/month | ⭐⭐⭐⭐ | AWS users, cheapest |
| **Fly.io** | Free tier available | ⭐⭐⭐⭐ | Global distribution |
| **AWS EC2** | Free for 12 months | ⭐⭐⭐ | AWS users, more setup |

## Recommended: Railway (Easiest & Free)

**Why Railway:**
- ✅ Free tier with $5 credit/month
- ✅ Zero-config deployment
- ✅ Built-in PostgreSQL
- ✅ Automatic HTTPS
- ✅ Docker support
- ✅ Simple git-based deployment

**Steps:**

1. **Sign up**: Go to [railway.app](https://railway.app) and sign up with GitHub

2. **Create New Project**:
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Connect your repository

3. **Add PostgreSQL**:
   - Click "New" → "Database" → "PostgreSQL"
   - Railway will automatically set `DATABASE_URL` environment variable

4. **Configure Environment Variables**:
   - Go to your app service → Variables
   - Add all variables from `.env.example`:
     ```
     JWT_SECRET_KEY=<generate-a-random-secret>
     RESEND_API_KEY=re_your-api-key-here
     EMAIL_FROM=noreply@yourdomain.com
     EMAIL_FROM_NAME=Bookkeeper
     OPENAI_API_KEY=your-key (optional)
     ```

5. **Deploy**:
   - Railway will automatically detect `Dockerfile` and deploy
   - Or use `docker-compose.yml` (Railway supports it)

6. **Set Custom Domain** (optional):
   - Go to Settings → Domains
   - Add your custom domain

**Cost**: Free tier includes $5/month credit (usually enough for small apps)

---

## Option 2: Render (Free Tier)

**Why Render:**
- ✅ Free tier available
- ✅ Automatic SSL
- ✅ PostgreSQL included
- ✅ Easy deployment

**Steps:**

1. **Sign up**: [render.com](https://render.com)

2. **Create PostgreSQL Database**:
   - New → PostgreSQL
   - Choose free tier
   - Copy the connection string

3. **Create Web Service**:
   - New → Web Service
   - Connect GitHub repo
   - Build Command: `docker build -t bookkeeper .`
   - Start Command: `docker run -p 10000:8000 bookkeeper`
   - Or use Dockerfile directly

4. **Set Environment Variables**:
   - Add all variables from `.env.example`
   - Set `DATABASE_URL` from PostgreSQL service

**Cost**: Free tier available (with limitations)

---

## Option 3: AWS Lightsail (Cheapest Paid)

**Why AWS Lightsail:**
- ✅ $3.50/month (cheapest reliable option)
- ✅ Includes PostgreSQL
- ✅ Full AWS integration
- ✅ Easy scaling

**Steps:**

1. **Create Lightsail Instance**:
   - Go to AWS Lightsail console
   - Create instance → Choose "Linux/Unix" → "Docker"
   - Select $3.50/month plan

2. **Set up Docker Compose**:
   ```bash
   # SSH into instance
   git clone <your-repo>
   cd bookkeeper
   
   # Create .env file
   nano .env
   # Add all environment variables
   
   # Start services
   docker-compose up -d
   ```

3. **Configure Static IP**:
   - Lightsail → Networking → Create static IP
   - Attach to your instance

4. **Set up Domain** (optional):
   - Point DNS to static IP
   - Lightsail handles SSL automatically

**Cost**: $3.50/month (includes 512MB RAM, 1 vCPU, 20GB SSD)

---

## Option 4: Fly.io (Free Tier)

**Why Fly.io:**
- ✅ Generous free tier
- ✅ Global edge deployment
- ✅ PostgreSQL included
- ✅ Great for global users

**Steps:**

1. **Install Fly CLI**:
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. **Login and Create App**:
   ```bash
   fly auth login
   fly launch
   ```

3. **Create PostgreSQL Database**:
   ```bash
   fly postgres create --name bookkeeper-db
   fly postgres attach bookkeeper-db
   ```

4. **Set Secrets**:
   ```bash
   fly secrets set JWT_SECRET_KEY=<your-secret>
   fly secrets set RESEND_API_KEY=re_your-api-key-here
   # ... etc
   ```

5. **Deploy**:
   ```bash
   fly deploy
   ```

**Cost**: Free tier includes 3 shared-cpu VMs and 3GB storage

---

## Option 5: AWS EC2 (Free for 12 Months)

**Why AWS EC2:**
- ✅ Free tier for 12 months
- ✅ Full control
- ✅ Scalable

**Steps:**

1. **Launch EC2 Instance**:
   - AWS Console → EC2 → Launch Instance
   - Choose Ubuntu 22.04 LTS
   - Select t2.micro (free tier eligible)
   - Configure security group (open ports 22, 80, 443, 8000)

2. **Set up RDS PostgreSQL** (or use Docker):
   - RDS → Create Database → PostgreSQL (free tier)
   - Or use PostgreSQL in Docker on EC2

3. **SSH and Deploy**:
   ```bash
   ssh ubuntu@<your-ec2-ip>
   sudo apt-get update
   sudo apt-get install docker.io docker-compose
   git clone <your-repo>
   cd bookkeeper
   # Create .env file
   docker-compose up -d
   ```

4. **Set up Nginx Reverse Proxy** (recommended):
   ```bash
   sudo apt-get install nginx
   # Configure nginx to proxy to localhost:8000
   ```

**Cost**: Free for 12 months, then ~$10/month

---

## Environment Variables Setup

Regardless of platform, you'll need these environment variables:

```bash
# Database (usually auto-set by platform)
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# JWT (REQUIRED - generate a random secret)
JWT_SECRET_KEY=<generate-random-32-char-string>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Email (Resend API)
RESEND_API_KEY=re_your-api-key-here
EMAIL_FROM=noreply@yourdomain.com
EMAIL_FROM_NAME=Bookkeeper

# OpenAI (optional, for AI extraction)
OPENAI_API_KEY=your-key
OPENAI_API_BASE=https://openrouter.ai/api/v1
OPENAI_MODEL_NAME=openai/gpt-4o-mini
```

**Generate JWT Secret**:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## Post-Deployment Checklist

- [ ] Database migrations run successfully (`alembic upgrade head`)
- [ ] Health check endpoint works (`/api/health`)
- [ ] HTTPS/SSL is configured
- [ ] Environment variables are set
- [ ] File uploads directory has write permissions
- [ ] Email sending works (test signup/login)
- [ ] Static files are served correctly
- [ ] CORS is configured for your domain

---

## Quick Start Commands

### Railway
```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Link project
railway link

# Deploy
railway up
```

### Render
- Just connect GitHub repo, Render handles the rest

### AWS Lightsail
```bash
# SSH into instance
ssh ubuntu@<ip>

# Clone and deploy
git clone <repo>
cd bookkeeper
docker-compose up -d
```

---

## Recommendation

**For fastest deployment**: Use **Railway** - it's the easiest and has a good free tier.

**For cheapest paid option**: Use **AWS Lightsail** at $3.50/month.

**For AWS integration**: Use **AWS Lightsail** or **EC2** (if you want free tier).

**For global distribution**: Use **Fly.io** for edge deployment.

