"""
Vendor and Buyer Manager
Manages vendors (suppliers) and buyers (customers)
Auto-creates them from invoices
"""
from typing import Optional
from database.models import Vendor, Buyer, Company
from database.db import get_db
from core.company_manager import CompanyManager


class VendorBuyerManager:
    """Manages vendors and buyers"""
    
    @staticmethod
    def get_or_create_vendor(name: str, gstin: Optional[str] = None, 
                            address: Optional[str] = None,
                            contact_info: Optional[str] = None,
                            company_id: Optional[int] = None) -> Vendor:
        """Get existing vendor or create new one"""
        db = next(get_db())
        try:
            # Use provided company_id, or fall back to current company
            if company_id is None:
                current_company = CompanyManager.get_current_company()
                if not current_company:
                    raise ValueError("No current company set and no company_id provided")
                company_id = current_company.company_id
            else:
                # Verify company exists
                company = db.query(Company).filter(Company.company_id == company_id).first()
                if not company:
                    raise ValueError(f"Company with ID {company_id} not found")
            
            # Validate name
            if not name or not name.strip():
                raise ValueError("Vendor name cannot be empty")
            
            name = name.strip()
            gstin = gstin.strip() if gstin else None
            
            # Try to find by GSTIN first
            if gstin:
                vendor = db.query(Vendor).filter(
                    Vendor.company_id == company_id,
                    Vendor.gstin == gstin
                ).first()
                if vendor:
                    return vendor
            
            # Try to find by name
            vendor = db.query(Vendor).filter(
                Vendor.company_id == company_id,
                Vendor.name.ilike(f"%{name}%")
            ).first()
            
            if vendor:
                # Update GSTIN if provided and missing
                if gstin and not vendor.gstin:
                    vendor.gstin = gstin
                    db.commit()
                return vendor
            
            # Create new vendor
            vendor = Vendor(
                company_id=company_id,
                name=name,
                gstin=gstin,
                address=address,
                contact_info=contact_info
            )
            db.add(vendor)
            db.commit()
            db.refresh(vendor)
            return vendor
        finally:
            db.close()
    
    @staticmethod
    def get_or_create_buyer(name: str, gstin: Optional[str] = None,
                           address: Optional[str] = None,
                           contact_info: Optional[str] = None,
                           company_id: Optional[int] = None) -> Buyer:
        """Get existing buyer or create new one"""
        db = next(get_db())
        try:
            # Use provided company_id, or fall back to current company
            if company_id is None:
                current_company = CompanyManager.get_current_company()
                if not current_company:
                    raise ValueError("No current company set and no company_id provided")
                company_id = current_company.company_id
            else:
                # Verify company exists
                company = db.query(Company).filter(Company.company_id == company_id).first()
                if not company:
                    raise ValueError(f"Company with ID {company_id} not found")
            
            # Validate name
            if not name or not name.strip():
                raise ValueError("Buyer name cannot be empty")
            
            name = name.strip()
            gstin = gstin.strip() if gstin else None
            
            # Try to find by GSTIN first
            if gstin:
                buyer = db.query(Buyer).filter(
                    Buyer.company_id == company_id,
                    Buyer.gstin == gstin
                ).first()
                if buyer:
                    return buyer
            
            # Try to find by name
            buyer = db.query(Buyer).filter(
                Buyer.company_id == company_id,
                Buyer.name.ilike(f"%{name}%")
            ).first()
            
            if buyer:
                # Update GSTIN if provided and missing
                if gstin and not buyer.gstin:
                    buyer.gstin = gstin
                    db.commit()
                return buyer
            
            # Create new buyer
            buyer = Buyer(
                company_id=company_id,
                name=name,
                gstin=gstin,
                address=address,
                contact_info=contact_info
            )
            db.add(buyer)
            db.commit()
            db.refresh(buyer)
            return buyer
        finally:
            db.close()
    
    @staticmethod
    def get_vendor(vendor_id: int) -> Optional[Vendor]:
        """Get vendor by ID"""
        db = next(get_db())
        try:
            return db.query(Vendor).filter(Vendor.vendor_id == vendor_id).first()
        finally:
            db.close()
    
    @staticmethod
    def get_buyer(buyer_id: int) -> Optional[Buyer]:
        """Get buyer by ID"""
        db = next(get_db())
        try:
            return db.query(Buyer).filter(Buyer.buyer_id == buyer_id).first()
        finally:
            db.close()
    
    @staticmethod
    def list_vendors(company_id: Optional[int] = None):
        """List all vendors for a company"""
        db = next(get_db())
        try:
            if company_id:
                return db.query(Vendor).filter(Vendor.company_id == company_id).all()
            else:
                current_company = CompanyManager.get_current_company()
                if not current_company:
                    return []
                return db.query(Vendor).filter(Vendor.company_id == current_company.company_id).all()
        finally:
            db.close()
    
    @staticmethod
    def list_buyers(company_id: Optional[int] = None):
        """List all buyers for a company"""
        db = next(get_db())
        try:
            if company_id:
                return db.query(Buyer).filter(Buyer.company_id == company_id).all()
            else:
                current_company = CompanyManager.get_current_company()
                if not current_company:
                    return []
                return db.query(Buyer).filter(Buyer.company_id == current_company.company_id).all()
        finally:
            db.close()
    
    @staticmethod
    def create_vendor(name: str, gstin: Optional[str] = None,
                     address: Optional[str] = None,
                     contact_info: Optional[str] = None,
                     company_id: Optional[int] = None) -> Vendor:
        """Create a new vendor (use get_or_create_vendor to avoid duplicates)"""
        return VendorBuyerManager.get_or_create_vendor(name, gstin, address, contact_info, company_id)
    
    @staticmethod
    def create_buyer(name: str, gstin: Optional[str] = None,
                    address: Optional[str] = None,
                    contact_info: Optional[str] = None,
                    company_id: Optional[int] = None) -> Buyer:
        """Create a new buyer (use get_or_create_buyer to avoid duplicates)"""
        return VendorBuyerManager.get_or_create_buyer(name, gstin, address, contact_info, company_id)

