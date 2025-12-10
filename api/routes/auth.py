"""
Authentication routes: signup, login, token refresh
"""
from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from api.schemas import (
    SignupRequest, LoginRequest, TokenResponse, RefreshTokenRequest,
    CompanyResponse, UserResponse, VerifyEmailRequest
)
from database.models import User, Company, UserRole
from database.db import get_db
from core.auth import (
    get_password_hash, verify_password, create_access_token,
    create_refresh_token, decode_token, get_current_user
)
from core.email_service import send_welcome_email
from core.company_manager import CompanyManager
import secrets
import string

router = APIRouter()


def generate_temp_password(length: int = 12) -> str:
    """Generate a secure temporary password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


@router.post("/signup", response_model=dict)
async def signup(
    request: SignupRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Sign up a new company and create owner user
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == request.owner_email.lower()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if GSTIN already exists
    existing_company = db.query(Company).filter(Company.gstin == request.gstin).first()
    if existing_company:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Company with this GSTIN already exists"
        )
    
    try:
        # Create company
        company = CompanyManager.create_company(
            name=request.company_name,
            gstin=request.gstin,
            is_current=True
        )
        
        # Create owner user
        user = User(
            company_id=company.company_id,
            email=request.owner_email.lower(),
            password_hash=get_password_hash(request.owner_password),
            name=request.owner_name,
            role=UserRole.OWNER,
            is_active=True,
            email_verified=False
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Send welcome email in background (non-blocking)
        async def send_email_background():
            """Background task to send email without blocking response"""
            try:
                await send_welcome_email(
                    to_email=user.email,
                    name=user.name,
                    company_name=company.name,
                    password=request.owner_password
                )
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Background email task failed: {e}", exc_info=True)
        
        # Schedule email to be sent in background
        background_tasks.add_task(send_email_background)
        
        return {
            "message": "Company and user created successfully",
            "company_id": company.company_id,
            "user_id": user.user_id
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create account: {str(e)}"
        )


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Login and get access/refresh tokens
    """
    # Find user by email
    user = db.query(User).filter(User.email == request.email.lower()).first()
    
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Update last login
    user.last_login = datetime.now()
    db.commit()
    
    # Create tokens
    access_token = create_access_token(data={"sub": user.user_id, "email": user.email})
    refresh_token = create_refresh_token(data={"sub": user.user_id})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest):
    """
    Refresh access token using refresh token
    """
    payload = decode_token(request.refresh_token)
    
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    # Convert string user_id back to int
    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token"
        )
    
    # Create new access token
    access_token = create_access_token(data={"sub": user_id})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=request.refresh_token  # Refresh token remains valid
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user


@router.post("/send-verification-email")
async def send_verification_email(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send email verification link to current user"""
    if current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified"
        )
    
    # Create verification token (expires in 24 hours)
    verification_token = create_access_token(
        data={"sub": current_user.user_id, "email": current_user.email, "type": "email_verification"},
        expires_delta=timedelta(hours=24)
    )
    
    # Send verification email
    try:
        from core.email_service import send_email, render_template
        from database.models import Company
        
        company = db.query(Company).filter(Company.company_id == current_user.company_id).first()
        verification_url = f"http://localhost:8000/verify-email.html?token={verification_token}"
        
        html_body = render_template("""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .button { display: inline-block; padding: 12px 30px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }
            </style>
        </head>
        <body>
            <div class="container">
                <h2>Verify Your Email</h2>
                <p>Hello {{ name }},</p>
                <p>Please verify your email address by clicking the button below:</p>
                <a href="{{ verification_url }}" class="button">Verify Email</a>
                <p>Or copy this link: {{ verification_url }}</p>
                <p>This link will expire in 24 hours.</p>
            </div>
        </body>
        </html>
        """, name=current_user.name, verification_url=verification_url)
        
        text_body = f"""
Hello {current_user.name},

Please verify your email address by clicking the link below:

{verification_url}

This link will expire in 24 hours.
"""
        
        await send_email(
            to_email=current_user.email,
            subject="Verify Your Email - Bookkeeper",
            html_body=html_body,
            text_body=text_body
        )
        
        return {"message": "Verification email sent successfully"}
    except Exception as e:
        print(f"Failed to send verification email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email"
        )


@router.post("/verify-email")
async def verify_email(
    request: VerifyEmailRequest,
    db: Session = Depends(get_db)
):
    """Verify email using verification token"""
    payload = decode_token(request.token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    
    if payload.get("type") != "email_verification":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token type"
        )
    
    user_id = int(payload.get("sub"))
    user = db.query(User).filter(User.user_id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.email_verified:
        return {"message": "Email already verified"}
    
    user.email_verified = True
    db.commit()
    
    return {"message": "Email verified successfully"}

