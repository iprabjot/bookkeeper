# Free SMTP Services for Bookkeeper

## Recommended Free SMTP Services

### 1. **Gmail SMTP** ⭐ (Easiest to Start)

**Best for**: Quick setup, personal/small business use

**Setup:**
1. Enable 2-Factor Authentication on your Gmail account
2. Generate an App Password:
   - Go to Google Account → Security → 2-Step Verification → App passwords
   - Create app password for "Mail"
3. Use these settings:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-16-char-app-password
EMAIL_FROM=your-email@gmail.com
EMAIL_FROM_NAME=Bookkeeper
```

**Limits:**
- 500 emails/day (free Gmail account)
- 2,000 emails/day (Google Workspace)

**Pros:**
-  Free
-  Easy setup
-  Reliable
-  Good deliverability

**Cons:**
- ❌ Daily sending limits
- ❌ Requires app password setup

---

### 2. **SendGrid** ⭐⭐ (Best for Production)

**Best for**: Production apps, higher volume

**Setup:**
1. Sign up at https://sendgrid.com (free tier)
2. Verify your sender email
3. Create API key (Settings → API Keys)
4. Use these settings:

```env
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=your-sendgrid-api-key
EMAIL_FROM=your-verified-email@domain.com
EMAIL_FROM_NAME=Bookkeeper
```

**Limits:**
- 100 emails/day (free tier)
- Unlimited (paid plans start at $15/month)

**Pros:**
-  Free tier available
-  Good deliverability
-  Analytics dashboard
-  Easy to scale
-  API and SMTP support

**Cons:**
- ❌ Need to verify sender email
- ❌ Free tier has daily limit

---

### 3. **Mailgun** ⭐⭐

**Best for**: Developers, API-first approach

**Setup:**
1. Sign up at https://www.mailgun.com
2. Verify domain or use sandbox domain
3. Get SMTP credentials from Settings → SMTP

```env
SMTP_HOST=smtp.mailgun.org
SMTP_PORT=587
SMTP_USER=postmaster@your-domain.mailgun.org
SMTP_PASSWORD=your-mailgun-smtp-password
EMAIL_FROM=noreply@your-domain.com
EMAIL_FROM_NAME=Bookkeeper
```

**Limits:**
- 5,000 emails/month (free tier)
- 100 emails/day (sandbox domain)

**Pros:**
-  Generous free tier
-  Great for developers
-  Good API
-  Good deliverability

**Cons:**
- ❌ Sandbox domain has restrictions
- ❌ Need to verify domain for production

---

### 4. **Amazon SES** (AWS)

**Best for**: AWS users, high volume

**Setup:**
1. Create AWS account
2. Verify email/domain in SES
3. Get SMTP credentials

```env
SMTP_HOST=email-smtp.us-east-1.amazonaws.com
SMTP_PORT=587
SMTP_USER=your-ses-smtp-username
SMTP_PASSWORD=your-ses-smtp-password
EMAIL_FROM=your-verified-email@domain.com
EMAIL_FROM_NAME=Bookkeeper
```

**Limits:**
- 200 emails/day (sandbox)
- 62,000 emails/month (production, free tier)

**Pros:**
-  Very cheap ($0.10 per 1,000 emails after free tier)
-  Highly scalable
-  Great deliverability

**Cons:**
- ❌ Requires AWS account
- ❌ Sandbox mode initially
- ❌ More complex setup

---

### 5. **Brevo (formerly Sendinblue)**

**Best for**: Small businesses, marketing emails

**Setup:**
1. Sign up at https://www.brevo.com
2. Verify sender email
3. Get SMTP credentials

```env
SMTP_HOST=smtp-relay.brevo.com
SMTP_PORT=587
SMTP_USER=your-brevo-email@example.com
SMTP_PASSWORD=your-brevo-smtp-key
EMAIL_FROM=your-verified-email@domain.com
EMAIL_FROM_NAME=Bookkeeper
```

**Limits:**
- 300 emails/day (free tier)

**Pros:**
-  Free tier
-  Good deliverability
-  User-friendly

**Cons:**
- ❌ Daily sending limits

---

## Recommendation for Bookkeeper MVP

### For Development/Testing:
**Use Gmail SMTP** - Easiest to set up, good for testing

### For Production:
**Use SendGrid** - Best balance of free tier, reliability, and ease of use

## Quick Setup Guide

### Gmail Setup (Recommended for MVP):

1. **Enable 2FA on Gmail**
2. **Create App Password:**
   ```
   Google Account → Security → 2-Step Verification → App passwords
   → Select "Mail" and "Other (Custom name)" → Enter "Bookkeeper"
   → Copy the 16-character password
   ```

3. **Add to `.env`:**
   ```env
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your-email@gmail.com
   SMTP_PASSWORD=xxxx xxxx xxxx xxxx
   EMAIL_FROM=your-email@gmail.com
   EMAIL_FROM_NAME=Bookkeeper
   ```

4. **Test:**
   ```python
   from core.email_service import send_welcome_email
   await send_welcome_email(
       to_email="test@example.com",
       name="Test User",
       company_name="Test Company",
       password="temp123"
   )
   ```

## Email Service Configuration

The email service in `core/email_service.py` supports:
-  TLS encryption
-  HTML and plain text emails
-  Custom email templates
-  Graceful fallback (prints to console if SMTP not configured)

## Production Considerations

1. **Domain Authentication**: Use SPF, DKIM, DMARC for better deliverability
2. **Rate Limiting**: Respect SMTP provider limits
3. **Error Handling**: Log email failures, retry logic
4. **Monitoring**: Track email delivery rates
5. **Bounce Handling**: Handle bounced emails (future enhancement)

## Testing Email Without SMTP

If SMTP is not configured, the email service will:
- Print email details to console
- Return `False` (email not sent)
- Continue execution without errors

This allows development without SMTP setup.

