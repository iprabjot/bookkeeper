"""
Current Company Manager
Manages the company whose books we are maintaining
"""
from typing import Optional
from database.models import Company
from database.db import get_db


class CompanyManager:
    """Manages the current company context"""
    
    @staticmethod
    def get_current_company() -> Optional[Company]:
        """Get the current company (the one whose books we maintain)"""
        db = next(get_db())
        try:
            company = db.query(Company).filter(Company.is_current == True).first()
            return company
        finally:
            db.close()
    
    @staticmethod
    def set_current_company(company_id: int) -> Company:
        """Set a company as the current company"""
        db = next(get_db())
        try:
            # Unset all companies
            db.query(Company).update({Company.is_current: False})
            
            # Set the new current company
            company = db.query(Company).filter(Company.company_id == company_id).first()
            if not company:
                raise ValueError(f"Company with ID {company_id} not found")
            
            company.is_current = True
            db.commit()
            db.refresh(company)
            return company
        finally:
            db.close()
    
    @staticmethod
    def create_company(name: str, gstin: str, is_current: bool = False) -> Company:
        """Create a new company"""
        db = next(get_db())
        try:
            # If setting as current, unset others
            if is_current:
                db.query(Company).update({Company.is_current: False})
            
            company = Company(
                name=name,
                gstin=gstin,
                is_current=is_current
            )
            db.add(company)
            db.commit()
            db.refresh(company)
            return company
        finally:
            db.close()
    
    @staticmethod
    def get_company_by_gstin(gstin: str) -> Optional[Company]:
        """Get company by GSTIN"""
        db = next(get_db())
        try:
            return db.query(Company).filter(Company.gstin == gstin).first()
        finally:
            db.close()

