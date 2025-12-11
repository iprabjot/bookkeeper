# Resend Email Setup Guide

## Overview

Resend is a modern, developer-friendly transactional email service perfect for sending automated emails like welcome messages, password resets, and notifications.

**Why Resend?**
- ✅ **3,000 emails/month free** (100/day)
- ✅ Simple, clean API
- ✅ Works perfectly on Railway
- ✅ Easy setup - no complex authentication
- ✅ Great deliverability
- ✅ Developer-friendly

## Step 1: Create Resend Account

1. **Sign up for Resend**:
   - Go to https://resend.com
   - Click "Get Started" or "Sign Up"
   - Create your account (free tier available)

2. **Verify your email**:
   - Check your inbox and verify your email address

## Step 2: Get Your API Key

1. **Log in to Resend**:
   - Go to https://resend.com/login

2. **Create an API Key**:
   - Navigate to **API Keys** in the sidebar
   - Click **"Create API Key"**
   - Give it a name (e.g., "Bookkeeper Production")
   - Select permissions (default is fine)
   - Click **"Add"**
   - **Copy the API key immediately** (it starts with `re_` and you won't see it again!)

## Step 3: Verify Your Domain (Optional but Recommended)

For production, you should verify your sending domain:

1. Go to **Domains** in Resend dashboard
2. Click **"Add Domain"**
3. Enter your domain (e.g., `yourdomain.com`)
4. Add the DNS records Resend provides:
   - SPF record
   - DKIM records
   - DMARC record (optional)
5. Wait for verification (usually a few minutes)

**For testing**, you can use Resend's default domain, but emails will show "via resend.dev" in the sender.

## Step 4: Configure Railway Environment Variables

In your Railway project dashboard:

1. Go to your service → **Variables** tab
2. Add the following environment variables:

```env
RESEND_API_KEY=re_your-api-key-here
EMAIL_FROM=noreply@yourdomain.com
EMAIL_FROM_NAME=Bookkeeper
```

**Important:**
- Replace `re_your-api-key-here` with your actual API key (starts with `re_`)
- Replace `noreply@yourdomain.com` with your verified domain email
- For testing, you can use `onboarding@resend.dev` as `EMAIL_FROM`

## Step 5: Test Your Setup

After deploying to Railway:

1. **Test via API endpoint**:
   ```bash
   curl http://your-app.railway.app/api/auth/test-email-config
   ```

2. **Create a test user** via signup
3. **Check Railway logs** for email sending status
4. **Check Resend dashboard** → **Logs** to see sent emails

## Resend Limits

- **Free Tier**: 3,000 emails/month (100/day)
- **Paid Plans**: Start at $20/month for 50,000 emails
- **No daily limits** on paid plans

## Troubleshooting

### "Invalid API key" error
- Verify the API key starts with `re_`
- Make sure you copied the full key
- Check that the key is active in Resend dashboard
- Ensure no extra spaces or newlines in the key

### "Domain not verified"
- Verify your sending domain in Resend dashboard
- Check DNS records are correct
- Wait a few minutes for DNS propagation
- For testing, use `onboarding@resend.dev`

### "Email not sending"
- Check Railway logs for error messages
- Verify environment variables are set correctly
- Test API key in Resend dashboard → API Keys
- Check Resend dashboard → Logs for delivery status

### API Key Format
- Valid keys start with `re_`
- Example: `re_123456789abcdefghijklmnopqrstuvwxyz`
- Length: Usually 40-50 characters

## Quick Start for Testing

1. Sign up at https://resend.com
2. Get API key from **API Keys** section
3. Set in Railway:
   ```env
   RESEND_API_KEY=re_your-key-here
   EMAIL_FROM=onboarding@resend.dev
   EMAIL_FROM_NAME=Bookkeeper
   ```
4. Deploy and test!

## Support

- Resend Docs: https://resend.com/docs
- API Reference: https://resend.com/docs/api-reference
- Support: support@resend.com


