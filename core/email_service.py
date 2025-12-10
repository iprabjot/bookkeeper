"""
Email service for sending emails (welcome, invitations, notifications)
"""
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Template
import os
import logging
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

# Set up logger for email service
logger = logging.getLogger(__name__)

# SMTP Configuration
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USER)
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "Bookkeeper")


async def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: Optional[str] = None
) -> bool:
    """
    Send an email using SMTP
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        html_body: HTML email body
        text_body: Plain text email body (optional)
    
    Returns:
        True if sent successfully, False otherwise
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning(f"Email not configured. Would send to {to_email}: {subject}")
        return False
    
    try:
        message = MIMEMultipart("alternative")
        message["From"] = f"{EMAIL_FROM_NAME} <{EMAIL_FROM}>"
        message["To"] = to_email
        message["Subject"] = subject
        
        if text_body:
            message.attach(MIMEText(text_body, "plain"))
        message.attach(MIMEText(html_body, "html"))
        
        # Use SMTP class directly for better control over STARTTLS
        # Port 587: Use STARTTLS (upgrade plain connection to TLS)
        # Port 465: Use SSL/TLS directly
        # Add timeout to prevent hanging (10 seconds)
        timeout = 10
        
        if SMTP_PORT == 465:
            # Port 465 requires immediate SSL/TLS connection
            smtp = aiosmtplib.SMTP(
                hostname=SMTP_HOST,
                port=SMTP_PORT,
                use_tls=True,  # Direct TLS for port 465
                timeout=timeout
            )
        else:
            # Port 587 (or other ports) use STARTTLS
            smtp = aiosmtplib.SMTP(
                hostname=SMTP_HOST,
                port=SMTP_PORT,
                use_tls=False,  # Start with plain connection
                start_tls=True,  # Automatically upgrade to TLS after connect
                timeout=timeout
            )
        
        await smtp.connect(timeout=timeout)
        
        # Note: If start_tls=True is set in constructor, it's handled automatically
        # Only call starttls() manually if start_tls was not set
        # For port 587, the start_tls=True parameter should handle it
        
        await smtp.login(SMTP_USER, SMTP_PASSWORD)
        await smtp.send_message(message)
        await smtp.quit()
        
        logger.info(f"Email sent successfully to {to_email}: {subject}")
        return True
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        
        # Check if this is a Railway SMTP timeout issue
        is_railway_timeout = (
            "SMTPConnectTimeoutError" in error_type or 
            "Timed out connecting" in error_msg or
            "timeout" in error_msg.lower()
        )
        
        if is_railway_timeout and SMTP_HOST == "smtp.gmail.com":
            logger.error(
                f"Failed to send email to {to_email}: Gmail SMTP timeout on Railway. "
                f"This is expected - Railway blocks Gmail SMTP. "
                f"Please switch to SendGrid (see docs/RAILWAY_SMTP_TROUBLESHOOTING.md). "
                f"Error: {error_type}: {error_msg}",
                exc_info=True
            )
        else:
            logger.error(f"Failed to send email to {to_email}: {error_type}: {error_msg}", exc_info=True)
        
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


async def send_welcome_email(
    to_email: str,
    name: str,
    company_name: str,
    password: str,
    login_url: str = "http://localhost:8000/login.html"
) -> bool:
    """Send welcome email with login credentials"""
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
    login_url: str = "http://localhost:8000/login.html"
) -> bool:
    """Send invitation email with login credentials"""
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

