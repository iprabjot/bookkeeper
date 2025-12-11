# Quick Start: Resend on Railway

## Step 1: Get Resend API Key

1. Go to https://resend.com
2. Sign up or log in
3. Navigate to **API Keys** in the sidebar
4. Click **"Create API Key"**
5. Give it a name (e.g., "Bookkeeper Production")
6. Copy your API key (starts with `re_`)

## Step 2: Configure Railway Environment Variables

In your Railway project:

1. Go to your service → **Variables** tab
2. Add these variables:

```env
RESEND_API_KEY=re_your-api-key-here
EMAIL_FROM=onboarding@resend.dev
EMAIL_FROM_NAME=Bookkeeper
```

**Important:**
- Replace `re_your-api-key-here` with your actual API key (starts with `re_`)
- For testing, use `onboarding@resend.dev` as `EMAIL_FROM`
- For production, verify your domain in Resend and use your domain email

## Step 3: Deploy

1. Commit and push your changes
2. Railway will automatically redeploy
3. Check logs to verify email sending

## Step 4: Test

1. **Test API configuration**:
   ```bash
   curl https://your-app.railway.app/api/auth/test-email-config
   ```

2. **Create a test user** via signup
3. **Check Railway logs** for: `Email sent successfully via Resend`
4. **Check Resend dashboard** → **Logs** to see sent emails

## Troubleshooting

**"Resend API key not configured"**
- Verify `RESEND_API_KEY` is set in Railway
- Check for typos in variable name
- Ensure key starts with `re_`

**"Invalid API key"**
- Verify the API key is correct (starts with `re_`)
- Make sure the key is active in Resend dashboard
- Check for extra spaces or newlines

**"Domain not verified"**
- For testing: Use `onboarding@resend.dev`
- For production: Verify your sending domain in Resend dashboard
- Add DNS records (SPF, DKIM) as shown in Resend

## Free Tier Limits

- **3,000 emails/month** (100/day)
- Perfect for MVP/testing
- No credit card required

## Need More?

See full documentation: [RESEND_SETUP.md](./RESEND_SETUP.md)

