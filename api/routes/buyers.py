"""
Buyer management routes
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from pydantic import BaseModel
from api.schemas import BuyerResponse
from core.vendor_buyer_manager import VendorBuyerManager
from core.auth import get_current_user
from database.models import User

router = APIRouter()


class BuyerCreate(BaseModel):
    name: str
    gstin: str = None
    address: str = None
    contact_info: str = None


@router.get("/buyers", response_model=List[BuyerResponse])
async def list_buyers(current_user: User = Depends(get_current_user)):
    """List all buyers for the authenticated user's company"""
    # Pass company_id directly to ensure proper filtering
    buyers = VendorBuyerManager.list_buyers(company_id=current_user.company_id)
    return buyers


@router.post("/buyers", response_model=BuyerResponse)
async def create_buyer(buyer: BuyerCreate, current_user: User = Depends(get_current_user)):
    """Create a new buyer"""
    try:
        new_buyer = VendorBuyerManager.create_buyer(
            name=buyer.name,
            gstin=buyer.gstin,
            address=buyer.address,
            contact_info=buyer.contact_info,
            company_id=current_user.company_id
        )
        # Verify it belongs to user's company
        if new_buyer.company_id != current_user.company_id:
            raise HTTPException(status_code=403, detail="Buyer created for different company")
        return new_buyer
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/buyers/{buyer_id}", response_model=BuyerResponse)
async def get_buyer(buyer_id: int, current_user: User = Depends(get_current_user)):
    """Get a specific buyer"""
    buyer = VendorBuyerManager.get_buyer(buyer_id)
    if not buyer:
        raise HTTPException(status_code=404, detail="Buyer not found")
    # Verify it belongs to user's company
    if buyer.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Buyer belongs to different company")
    return buyer

