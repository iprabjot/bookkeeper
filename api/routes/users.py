"""
User management routes: create, list, update users
"""
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import List
from api.schemas import UserResponse, CreateUserRequest, UpdateUserRequest
from database.models import User, UserRole
from database.db import get_db
from core.auth import get_current_user, require_owner_or_admin, get_password_hash
from core.email_service import send_invitation_email
import secrets
import string

router = APIRouter()


def generate_temp_password(length: int = 12) -> str:
    """Generate a secure temporary password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


@router.post("/users", response_model=UserResponse)
async def create_user(
    request: CreateUserRequest,
    current_user: User = Depends(require_owner_or_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new user in the current user's company
    Only owners and admins can create users
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == request.email.lower()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Validate role
    try:
        role = UserRole(request.role.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {[r.value for r in UserRole]}"
        )
    
    # Only owner can create owner or admin users
    if role in [UserRole.OWNER, UserRole.ADMIN] and current_user.role != UserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners can create owner or admin users"
        )
    
    # Generate temporary password
    temp_password = generate_temp_password()
    
    # Create user
    user = User(
        company_id=current_user.company_id,
        email=request.email.lower(),
        password_hash=get_password_hash(temp_password),
        name=request.name,
        role=role,
        is_active=True,
        email_verified=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Send invitation email if requested
    if request.send_email:
        try:
            from database.models import Company
            company = db.query(Company).filter(Company.company_id == current_user.company_id).first()
            await send_invitation_email(
                to_email=user.email,
                name=user.name,
                company_name=company.name if company else "the company",
                role=role.value,
                password=temp_password
            )
        except Exception as e:
            print(f"Warning: Failed to send invitation email: {e}")
    
    return user


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    current_user: User = Depends(require_owner_or_admin),
    db: Session = Depends(get_db)
):
    """
    List all users in the current user's company
    Only owners and admins can list users
    """
    users = db.query(User).filter(
        User.company_id == current_user.company_id
    ).order_by(User.created_at.desc()).all()
    
    return users


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(require_owner_or_admin),
    db: Session = Depends(get_db)
):
    """
    Get a specific user
    Only owners and admins can view users
    """
    user = db.query(User).filter(
        User.user_id == user_id,
        User.company_id == current_user.company_id
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    request: UpdateUserRequest,
    current_user: User = Depends(require_owner_or_admin),
    db: Session = Depends(get_db)
):
    """
    Update a user
    Only owners and admins can update users
    """
    user = db.query(User).filter(
        User.user_id == user_id,
        User.company_id == current_user.company_id
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent modifying owner role (only owner can do this)
    if request.role and request.role.lower() == UserRole.OWNER.value:
        if current_user.role != UserRole.OWNER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only owners can assign owner role"
            )
    
    # Update fields
    if request.name is not None:
        user.name = request.name
    if request.role is not None:
        try:
            user.role = UserRole(request.role.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role. Must be one of: {[r.value for r in UserRole]}"
            )
    if request.is_active is not None:
        # Prevent deactivating yourself
        if user_id == current_user.user_id and not request.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate your own account"
            )
        user.is_active = request.is_active
    
    db.commit()
    db.refresh(user)
    
    return user


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_owner_or_admin),
    db: Session = Depends(get_db)
):
    """
    Delete a user (soft delete by deactivating)
    Only owners can delete users
    """
    if current_user.role != UserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners can delete users"
        )
    
    user = db.query(User).filter(
        User.user_id == user_id,
        User.company_id == current_user.company_id
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent deleting yourself
    if user_id == current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    # Soft delete by deactivating
    user.is_active = False
    db.commit()
    
    return {"message": "User deactivated successfully"}

