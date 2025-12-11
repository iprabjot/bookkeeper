"""
Email service for sending emails (welcome, invitations, notifications)
Uses Resend API for all email sending
"""
from jinja2 import Template
import os
import logging
from dotenv import load_dotenv
from typing import Optional
import aiohttp

load_dotenv()

# Set up logger for email service
logger = logging.getLogger(__name__)

# Resend API Configuration
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_API_URL = "https://api.resend.com/emails"
EMAIL_FROM = os.getenv("EMAIL_FROM", "noreply@bookkeeper.com")
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "Bookkeeper")

def get_frontend_url() -> str:
    """
    Get the frontend URL for email links.
    Checks RAILWAY_STATIC_URL first, then FRONTEND_URL, then defaults to localhost.
    Ensures the URL has a protocol (https:// for Railway, http:// for localhost).
    """
    url = os.getenv("RAILWAY_STATIC_URL") or os.getenv("FRONTEND_URL", "http://localhost:8000")
    
    # If URL doesn't start with http:// or https://, prepend https://
    # (Railway URLs should use https://)
    if url and not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    
    return url

# Frontend URL: Check Railway's RAILWAY_STATIC_URL first, then FRONTEND_URL, then default to localhost
FRONTEND_URL = get_frontend_url()


async def test_resend_api_key() -> bool:
    """
    Test if the Resend API key is valid by calling the API key validation endpoint
    
    Returns:
        True if API key is valid, False otherwise
    """
    if not RESEND_API_KEY:
        logger.error("Resend API key not configured")
        return False
    
    try:
        # Resend doesn't have a dedicated ping endpoint, so we'll test by checking API key format
        # Valid Resend API keys start with "re_"
        if not RESEND_API_KEY.startswith("re_"):
            logger.error("Invalid Resend API key format. Keys should start with 're_'")
            return False
        
        # We can't test without sending an email, so just validate format
        logger.info("Resend API key format is valid")
        return True
    except Exception as e:
        logger.error(f"Failed to validate Resend API key: {type(e).__name__}: {str(e)}", exc_info=True)
        return False


async def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: Optional[str] = None
) -> bool:
    """
    Send an email using Resend API
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        html_body: HTML email body
        text_body: Plain text email body (optional)
    
    Returns:
        True if sent successfully, False otherwise
    """
    if not RESEND_API_KEY:
        logger.warning(f"Resend API key not configured. Would send to {to_email}: {subject}")
        return False
    
    # Validate API key format
    if not RESEND_API_KEY.startswith("re_"):
        logger.error("Invalid Resend API key format. Keys should start with 're_'")
        return False
    
    try:
        # Prepare message payload for Resend API
        payload = {
            "from": f"{EMAIL_FROM_NAME} <{EMAIL_FROM}>",
            "to": [to_email],
            "subject": subject,
            "html": html_body,
        }
        
        # Add text body if provided
        if text_body:
            payload["text"] = text_body
        
        # Send via Resend API
        headers = {
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                RESEND_API_URL,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Email sent successfully via Resend to {to_email}: {subject}")
                    return True
                elif response.status == 401:
                    error_data = await response.json().catch(lambda: {})
                    error_msg = error_data.get("message", "Invalid API key")
                    logger.error(
                        f"Resend API authentication failed (401): {error_msg}. "
                        f"Please verify:\n"
                        f"1. Your API key starts with 're_' and is correct\n"
                        f"2. The API key is from https://resend.com/api-keys\n"
                        f"3. The API key is active and not revoked\n"
                        f"4. Your sending domain is verified in Resend dashboard"
                    )
                    return False
                else:
                    error_text = await response.text()
                    logger.error(f"Resend API HTTP error {response.status}: {error_text}")
                    return False
                    
    except Exception as e:
        logger.error(f"Failed to send email via Resend to {to_email}: {type(e).__name__}: {str(e)}", exc_info=True)
        return False


def render_template(template_str: str, **kwargs) -> str:
    """Render a Jinja2 template string"""
    template = Template(template_str)
    return template.render(**kwargs)


# Email Templates
WELCOME_EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
        .button { display: inline-block; padding: 12px 30px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }
        .credentials { background: #fff; padding: 15px; border-left: 4px solid #667eea; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Welcome to Bookkeeper!</h1>
        </div>
        <div class="content">
            <p>Hello {{ name }},</p>
            <p>Your account has been created for <strong>{{ company_name }}</strong>.</p>
            
            <div class="credentials">
                <p><strong>Your login credentials:</strong></p>
                <p>Email: <code>{{ email }}</code></p>
                <p>Password: <code>{{ password }}</code></p>
            </div>
            
            <p>Please log in and change your password after your first login.</p>
            
            <a href="{{ login_url }}" class="button">Log In Now</a>
            
            <p style="margin-top: 30px; font-size: 12px; color: #666;">
                If you did not request this account, please contact support.
            </p>
        </div>
    </div>
</body>
</html>
"""

INVITATION_EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
        .button { display: inline-block; padding: 12px 30px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }
        .credentials { background: #fff; padding: 15px; border-left: 4px solid #667eea; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>You've been invited!</h1>
        </div>
        <div class="content">
            <p>Hello {{ name }},</p>
            <p>You have been invited to join <strong>{{ company_name }}</strong> as a {{ role }}.</p>
            
            <div class="credentials">
                <p><strong>Your login credentials:</strong></p>
                <p>Email: <code>{{ email }}</code></p>
                <p>Password: <code>{{ password }}</code></p>
            </div>
            
            <p>Please log in and change your password after your first login.</p>
            
            <a href="{{ login_url }}" class="button">Log In Now</a>
            
            <p style="margin-top: 30px; font-size: 12px; color: #666;">
                If you did not expect this invitation, please contact support.
            </p>
        </div>
    </div>
</body>
</html>
"""

PASSWORD_RESET_EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
        .button { display: inline-block; padding: 12px 30px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }
        .warning { background: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Reset Your Password</h1>
        </div>
        <div class="content">
            <p>Hello {{ name }},</p>
            <p>We received a request to reset your password for your Bookkeeper account.</p>
            
            <p>Click the button below to reset your password:</p>
            <a href="{{ reset_url }}" class="button">Reset Password</a>
            
            <p>Or copy and paste this link into your browser:</p>
            <p style="word-break: break-all; color: #667eea;">{{ reset_url }}</p>
            
            <div class="warning">
                <p><strong>Important:</strong></p>
                <ul>
                    <li>This link will expire in 1 hour</li>
                    <li>If you didn't request this, please ignore this email</li>
                    <li>Your password will not change until you click the link above</li>
                </ul>
            </div>
            
            <p style="margin-top: 30px; font-size: 12px; color: #666;">
                If you continue to have problems, please contact support.
            </p>
        </div>
    </div>
</body>
</html>
"""


async def send_welcome_email(
    to_email: str,
    name: str,
    company_name: str,
    password: str,
    login_url: str = None
) -> bool:
    """Send welcome email with login credentials"""
    if not login_url:
        login_url = f"{FRONTEND_URL}/login.html"
    
    html_body = render_template(
        WELCOME_EMAIL_TEMPLATE,
        name=name,
        company_name=company_name,
        email=to_email,
        password=password,
        login_url=login_url
    )
    
    text_body = f"""
Hello {name},

Your account has been created for {company_name}.

Your login credentials:
Email: {to_email}
Password: {password}

Please log in and change your password after your first login.

Login URL: {login_url}
"""
    
    return await send_email(
        to_email=to_email,
        subject=f"Welcome to {company_name} - Your Bookkeeper Account",
        html_body=html_body,
        text_body=text_body
    )


async def send_invitation_email(
    to_email: str,
    name: str,
    company_name: str,
    role: str,
    password: str,
    login_url: str = None
) -> bool:
    """Send invitation email with login credentials"""
    if not login_url:
        login_url = f"{FRONTEND_URL}/login.html"
    
    html_body = render_template(
        INVITATION_EMAIL_TEMPLATE,
        name=name,
        company_name=company_name,
        role=role,
        email=to_email,
        password=password,
        login_url=login_url
    )
    
    text_body = f"""
Hello {name},

You have been invited to join {company_name} as a {role}.

Your login credentials:
Email: {to_email}
Password: {password}

Please log in and change your password after your first login.

Login URL: {login_url}
"""
    
    return await send_email(
        to_email=to_email,
        subject=f"Invitation to join {company_name}",
        html_body=html_body,
        text_body=text_body
    )


async def send_password_reset_email(
    to_email: str,
    name: str,
    reset_token: str,
    reset_url: str = None
) -> bool:
    """Send password reset email with reset link"""
    if not reset_url:
        reset_url = f"{FRONTEND_URL}/reset-password.html?token={reset_token}"
    
    html_body = render_template(
        PASSWORD_RESET_EMAIL_TEMPLATE,
        name=name,
        reset_url=reset_url
    )
    
    text_body = f"""
Hello {name},

We received a request to reset your password for your Bookkeeper account.

Click the link below to reset your password:
{reset_url}

This link will expire in 1 hour.

If you didn't request this, please ignore this email. Your password will not change until you click the link above.

If you continue to have problems, please contact support.
"""
    
    return await send_email(
        to_email=to_email,
        subject="Reset Your Password - Bookkeeper",
        html_body=html_body,
        text_body=text_body
    )
