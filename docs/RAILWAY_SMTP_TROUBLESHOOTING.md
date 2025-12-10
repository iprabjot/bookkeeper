# Railway SMTP Troubleshooting Guide

## Common Issue: "Timed out connecting to smtp.gmail.com"

If you're getting timeout errors when trying to send emails from Railway, this is likely due to Railway's network restrictions blocking outbound SMTP connections.

## Why This Happens

Railway (and many cloud platforms) often block outbound SMTP connections on ports 587 and 465 to prevent spam. This is a security measure.

## Solutions

### Option 1: Use SendGrid (Recommended for Railway)

SendGrid works reliably on Railway and has a free tier:

1. **Sign up**: https://sendgrid.com (free tier: 100 emails/day)

2. **Get SMTP credentials**:
   - Go to Settings → API Keys → Create API Key
   - Or use SMTP credentials from Settings → SMTP

3. **Update Railway environment variables**:
   ```
   SMTP_HOST=smtp.sendgrid.net
   SMTP_PORT=587
   SMTP_USER=apikey
   SMTP_PASSWORD=your-sendgrid-api-key-here
   EMAIL_FROM=your-verified-email@domain.com
   EMAIL_FROM_NAME=Bookkeeper
   ```

4. **Verify sender email** in SendGrid dashboard

**Benefits:**
- ✅ Works reliably on Railway
- ✅ Free tier (100 emails/day)
- ✅ Better deliverability
- ✅ Analytics dashboard

### Option 2: Try Port 465 with SSL

Sometimes port 465 works when 587 doesn't:

1. **Update Railway environment variables**:
   ```
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=465
   SMTP_USER=your-email@gmail.com
   SMTP_PASSWORD=your-app-password
   EMAIL_FROM=your-email@gmail.com
   EMAIL_FROM_NAME=Bookkeeper
   ```

2. **Restart your Railway service**

**Note**: Port 465 uses direct SSL/TLS, which may bypass some restrictions.

### Option 3: Use Mailgun (Alternative)

Mailgun also works well on Railway:

1. **Sign up**: https://www.mailgun.com (free tier: 5,000 emails/month)

2. **Get SMTP credentials** from Settings → SMTP

3. **Update Railway environment variables**:
   ```
   SMTP_HOST=smtp.mailgun.org
   SMTP_PORT=587
   SMTP_USER=postmaster@your-domain.mailgun.org
   SMTP_PASSWORD=your-mailgun-smtp-password
   EMAIL_FROM=noreply@your-domain.com
   EMAIL_FROM_NAME=Bookkeeper
   ```

### Option 4: Use Brevo (Sendinblue)

Another reliable option:

1. **Sign up**: https://www.brevo.com (free tier: 300 emails/day)

2. **Get SMTP credentials**

3. **Update Railway environment variables**:
   ```
   SMTP_HOST=smtp-relay.brevo.com
   SMTP_PORT=587
   SMTP_USER=your-brevo-email@example.com
   SMTP_PASSWORD=your-brevo-smtp-key
   EMAIL_FROM=your-verified-email@domain.com
   EMAIL_FROM_NAME=Bookkeeper
   ```

## Quick Fix: Switch to SendGrid

**Fastest solution for Railway:**

1. Sign up at https://sendgrid.com
2. Verify your email address
3. Create API key (Settings → API Keys)
4. Update Railway variables:
   ```
   SMTP_HOST=smtp.sendgrid.net
   SMTP_PORT=587
   SMTP_USER=apikey
   SMTP_PASSWORD=<your-api-key>
   EMAIL_FROM=<your-verified-email>
   EMAIL_FROM_NAME=Bookkeeper
   ```
5. Redeploy on Railway

## Testing

After updating SMTP settings:

1. **Check Railway logs**: `railway logs` or Railway dashboard
2. **Test signup**: Create a new user account
3. **Check email inbox**: Should receive welcome email
4. **Check logs**: Should see "Email sent successfully" (not timeout errors)

## Why Gmail Might Not Work on Railway

- Railway may block outbound connections to Gmail SMTP
- Gmail may rate-limit connections from cloud platforms
- Network policies may restrict SMTP ports
- Firewall rules may block port 587/465

## Recommendation

**For Railway deployments, use SendGrid** - it's:
- ✅ Reliable on Railway
- ✅ Free tier available
- ✅ Better deliverability
- ✅ Easy to set up
- ✅ Analytics included

## Still Having Issues?

1. **Check Railway logs** for detailed error messages
2. **Verify environment variables** are set correctly
3. **Test SMTP connection** locally first (if possible)
4. **Try different SMTP provider** (SendGrid recommended)
5. **Check Railway status page** for network issues

## Email Service Status

The email service is now **asynchronous** - emails are sent in the background and won't block API responses. If email fails, it's logged but doesn't affect the user experience.

Check logs with:
```bash
railway logs | grep -i email
```

