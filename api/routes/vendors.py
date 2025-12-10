"""
Vendor management routes
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from pydantic import BaseModel
from api.schemas import VendorResponse
from core.vendor_buyer_manager import VendorBuyerManager
from core.auth import get_current_user
from database.models import User

router = APIRouter()


class VendorCreate(BaseModel):
    name: str
    gstin: str = None
    address: str = None
    contact_info: str = None


@router.get("/vendors", response_model=List[VendorResponse])
async def list_vendors(current_user: User = Depends(get_current_user)):
    """List all vendors for the authenticated user's company"""
    # Pass company_id directly to ensure proper filtering
    vendors = VendorBuyerManager.list_vendors(company_id=current_user.company_id)
    return vendors


@router.post("/vendors", response_model=VendorResponse)
async def create_vendor(vendor: VendorCreate, current_user: User = Depends(get_current_user)):
    """Create a new vendor"""
    try:
        new_vendor = VendorBuyerManager.create_vendor(
            name=vendor.name,
            gstin=vendor.gstin,
            address=vendor.address,
            contact_info=vendor.contact_info,
            company_id=current_user.company_id
        )
        # Verify it belongs to user's company
        if new_vendor.company_id != current_user.company_id:
            raise HTTPException(status_code=403, detail="Vendor created for different company")
        return new_vendor
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/vendors/{vendor_id}", response_model=VendorResponse)
async def get_vendor(vendor_id: int, current_user: User = Depends(get_current_user)):
    """Get a specific vendor"""
    vendor = VendorBuyerManager.get_vendor(vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    # Verify it belongs to user's company
    if vendor.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Vendor belongs to different company")
    return vendor

