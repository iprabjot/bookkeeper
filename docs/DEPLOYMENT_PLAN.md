# Deployment Plan - Bookkeeping MVP

## Overview
This document outlines the plan for adding authentication, user management, email functionality, and preparing the application for deployment.

## Phase 1: Authentication & User Management

### 1.1 Database Schema
- **User Model**: email, password_hash, name, role, company_id, is_active, created_at
- **User Roles**: OWNER, ADMIN, ACCOUNTANT, VIEWER
- **Company-User Relationship**: Many-to-many (users can belong to multiple companies in future, but MVP: one company per user)

### 1.2 Authentication System
- JWT-based authentication (access + refresh tokens)
- Password hashing with bcrypt
- Token refresh mechanism
- Protected API routes with dependency injection

### 1.3 User Management
- Company signup (creates company + owner user)
- User login
- Owner can invite users (send email with credentials)
- Owner can list/manage users in their company
- Role-based access control

### 1.4 Email Service
- SMTP configuration (Gmail, SendGrid, or similar)
- Email templates for:
  - Welcome email (with login credentials)
  - Password reset
  - User invitation
  - Invoice processing notifications (optional)

## Phase 2: Code Cleanup

### 2.1 Remove Unused Files
- `demo_agents.py` (if not used)
- `invoice_workflow.py` (if replaced by direct processing)
- Test scripts that are no longer needed

### 2.2 Organize Structure
```
bookkeeper/
├── api/
│   ├── auth/          # New: authentication routes
│   ├── users/          # New: user management routes
│   └── routes/         # Existing routes
├── core/
│   ├── auth.py         # New: JWT, password hashing
│   ├── email_service.py # New: email sending
│   └── ...            # Existing core logic
├── database/
│   ├── models.py       # Add User model
│   └── ...
├── static/
│   ├── auth/           # New: login, signup pages
│   └── ...            # Existing UI
└── ...
```

### 2.3 Environment Variables
Create comprehensive `.env.example`:
```env
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/bookkeeper

# JWT
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=noreply@bookkeeper.com
EMAIL_FROM_NAME=Bookkeeper

# OpenAI (for invoice extraction)
OPENAI_API_KEY=your-key
OPENAI_API_BASE=https://openrouter.ai/api/v1
OPENAI_MODEL_NAME=openai/gpt-4o-mini
```

## Phase 3: Docker Deployment

### 3.1 Dockerfile
- Multi-stage build for production
- Python 3.11 base image
- Install dependencies
- Copy application code
- Expose port 8000

### 3.2 docker-compose.yml
- PostgreSQL service
- FastAPI application service
- Volume mounts for:
  - Database data persistence
  - Reports directory
  - Uploaded invoices
- Environment variables
- Health checks

### 3.3 Production Considerations
- Use environment variables for all secrets
- Add nginx reverse proxy (optional)
- SSL/TLS certificates (Let's Encrypt)
- Database backups
- Logging configuration

## Phase 4: Migration Strategy

### 4.1 Database Migration
- Use Alembic for schema changes
- Create migration for User table
- Migrate existing companies to have owner users

### 4.2 Data Migration
- For existing companies, create owner user
- Generate temporary passwords
- Send password reset emails

## Implementation Order

1.  Database: Add User model and relationships
2.  Authentication: JWT, password hashing, login/signup
3.  User Management: CRUD operations, role management
4.  Email Service: SMTP setup, email templates
5.  API Protection: Add auth middleware to routes
6.  UI: Login/signup pages
7.  Code Cleanup: Remove unused files
8.  Docker: Dockerfile and docker-compose.yml
9.  Documentation: Update README, deployment guide

## Security Considerations

- Password hashing (bcrypt with salt rounds >= 12)
- JWT secret key rotation
- Rate limiting on auth endpoints
- CORS configuration for production
- Input validation on all endpoints
- SQL injection prevention (SQLAlchemy ORM)
- XSS prevention (frontend sanitization)

## Deployment Options

1. **Docker Compose** (Recommended for MVP)
   - Single server deployment
   - Easy to set up and maintain
   - Good for small to medium scale

2. **Cloud Platforms**
   - **Railway**: Easy deployment, PostgreSQL included
   - **Render**: Free tier available, auto-deploy
   - **DigitalOcean App Platform**: Simple, scalable
   - **AWS/GCP/Azure**: More complex, but scalable

3. **VPS Deployment**
   - Ubuntu/Debian server
   - Docker Compose
   - Nginx reverse proxy
   - Let's Encrypt SSL

