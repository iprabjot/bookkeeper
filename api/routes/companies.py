"""
Company management routes
"""
from fastapi import APIRouter, HTTPException, Depends
from api.schemas import CompanyCreate, CompanyResponse
from core.company_manager import CompanyManager
from core.auth import get_current_user
from database.models import User

router = APIRouter()


@router.post("/companies", response_model=CompanyResponse)
async def create_company(company: CompanyCreate, current_user: User = Depends(get_current_user)):
    """Create a new company (Note: Usually done via signup, but keeping for compatibility)"""
    # Only owners can create additional companies
    from database.models import UserRole
    if current_user.role != UserRole.OWNER:
        raise HTTPException(status_code=403, detail="Only owners can create companies")
    
    try:
        new_company = CompanyManager.create_company(
            name=company.name,
            gstin=company.gstin,
            is_current=company.is_current
        )
        return new_company
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/companies/current", response_model=CompanyResponse)
async def get_current_company(current_user: User = Depends(get_current_user)):
    """Get the current company for the authenticated user"""
    # Get company from user's company_id
    from database.db import get_db
    from database.models import Company
    
    db = next(get_db())
    try:
        company = db.query(Company).filter(Company.company_id == current_user.company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        return company
    finally:
        db.close()


@router.put("/companies/{company_id}/set-current", response_model=CompanyResponse)
async def set_current_company(company_id: int, current_user: User = Depends(get_current_user)):
    """Set a company as the current company"""
    # Verify user belongs to this company
    if current_user.company_id != company_id:
        raise HTTPException(status_code=403, detail="You can only set your own company as current")
    
    try:
        company = CompanyManager.set_current_company(company_id)
        return company
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/companies/current", response_model=CompanyResponse)
async def update_current_company(company_data: dict, current_user: User = Depends(get_current_user)):
    """Update the current company"""
    from database.db import get_db
    from database.models import Company
    
    db = next(get_db())
    try:
        company = db.query(Company).filter(Company.company_id == current_user.company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Only owners can update company details
        from database.models import UserRole
        if current_user.role != UserRole.OWNER:
            raise HTTPException(status_code=403, detail="Only owners can update company details")
        
        # Update fields
        if 'name' in company_data:
            company.name = company_data['name']
        if 'gstin' in company_data:
            company.gstin = company_data['gstin']
        
        db.commit()
        db.refresh(company)
        return company
    finally:
        db.close()

