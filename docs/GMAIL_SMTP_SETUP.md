# Gmail SMTP Setup Guide

## Quick Setup Steps

### 1. Enable 2-Factor Authentication

1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable **2-Step Verification** if not already enabled
3. Complete the setup process

### 2. Generate App Password

1. Go to [App Passwords](https://myaccount.google.com/apppasswords)
   - Or: Google Account → Security → 2-Step Verification → App passwords
2. Select **Mail** as the app
3. Select **Other (Custom name)** as the device
4. Enter "Bookkeeper" as the name
5. Click **Generate**
6. **Copy the 16-character password** (it looks like: `abcd efgh ijkl mnop`)

### 3. Configure .env File

Add these lines to your `.env` file:

```env
# Gmail SMTP Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=abcd efgh ijkl mnop
EMAIL_FROM=your-email@gmail.com
EMAIL_FROM_NAME=Bookkeeper
```

**Important:**
- Replace `your-email@gmail.com` with your Gmail address
- Replace `abcd efgh ijkl mnop` with your actual 16-character app password
- Keep spaces in the app password (or remove them, both work)

### 4. Test Email

You can test the email configuration by:

1. **Starting the server:**
   ```bash
   python run_api.py
   ```

2. **Creating a test user** via the signup endpoint or API

3. **Check the console** - you should see:
   ```
    Email sent to user@example.com: Welcome to Company - Your Bookkeeper Account
   ```

## Troubleshooting

### "Invalid credentials" error
- Make sure you're using the **App Password**, not your regular Gmail password
- Verify 2FA is enabled
- Regenerate the app password if needed

### "Connection refused" or timeout
- Check your firewall/network settings
- Verify `SMTP_PORT=587` (not 465)
- Try `SMTP_PORT=465` with `use_tls=False` if 587 doesn't work

### Email not sending
- Check console logs for error messages
- Verify all environment variables are set correctly
- Test with a simple email client first

## Gmail Limits

- **Free Gmail**: 500 emails/day
- **Google Workspace**: 2,000 emails/day

If you hit the limit, you'll need to wait 24 hours or upgrade to Google Workspace.

## Security Notes

 **Important:**
- Never commit your `.env` file to git
- Keep your app password secure
- Use environment variables in production
- Consider using SendGrid for production (better limits and deliverability)

## Example .env File

```env
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/bookkeeper

# JWT
JWT_SECRET_KEY=your-secret-key-here-min-32-characters

# Gmail SMTP
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password-here
EMAIL_FROM=your-email@gmail.com
EMAIL_FROM_NAME=Bookkeeper

# OpenAI (optional, for AI invoice extraction)
OPENAI_API_KEY=your-openai-key
OPENAI_API_BASE=https://openrouter.ai/api/v1
OPENAI_MODEL_NAME=openai/gpt-4o-mini
```

## Next Steps

Once configured:
1.  Restart your server
2.  Test by creating a user account
3.  Check email inbox for welcome email
4.  Verify email templates look good

That's it! Your Gmail SMTP is now configured. 🎉

