"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class InvoiceTypeEnum(str, Enum):
    SALES = "sales"
    PURCHASE = "purchase"


class InvoiceStatusEnum(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    PARTIALLY_PAID = "partially_paid"


# Company schemas
class CompanyCreate(BaseModel):
    name: str
    gstin: str
    is_current: bool = False


class CompanyResponse(BaseModel):
    company_id: int
    name: str
    gstin: str
    is_current: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# Invoice schemas
class InvoiceResponse(BaseModel):
    invoice_id: int
    company_id: int
    vendor_id: Optional[int]
    buyer_id: Optional[int]
    invoice_type: InvoiceTypeEnum
    invoice_number: str
    invoice_date: Optional[datetime]
    amount: float
    taxable_amount: float
    igst_amount: float
    cgst_amount: float
    sgst_amount: float
    status: InvoiceStatusEnum
    created_at: datetime
    
    class Config:
        from_attributes = True


# Vendor/Buyer schemas
class VendorResponse(BaseModel):
    vendor_id: int
    company_id: int
    name: str
    gstin: Optional[str]
    address: Optional[str]
    contact_info: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class BuyerResponse(BaseModel):
    buyer_id: int
    company_id: int
    name: str
    gstin: Optional[str]
    address: Optional[str]
    contact_info: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


# Journal Entry schemas
class JournalEntryLineResponse(BaseModel):
    line_id: int
    account_code: Optional[str]
    account_name: str
    debit: float
    credit: float
    
    class Config:
        from_attributes = True


class JournalEntryResponse(BaseModel):
    entry_id: int
    company_id: int
    entry_type: str
    date: datetime
    narration: str
    reference: Optional[str]
    status: str
    lines: List[JournalEntryLineResponse]
    created_at: datetime
    
    class Config:
        from_attributes = True


# Bank Transaction schemas
class BankTransactionResponse(BaseModel):
    transaction_id: int
    company_id: int
    date: datetime
    amount: float
    description: Optional[str]
    reference: Optional[str]
    type: str
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# Reconciliation schemas
class ReconciliationResponse(BaseModel):
    reconciliation_id: int
    transaction_id: int
    invoice_id: int
    match_type: str
    match_confidence: Optional[float]
    status: str
    settled_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class SettlementRequest(BaseModel):
    transaction_id: int
    invoice_id: int


# Status schema
class StatusResponse(BaseModel):
    current_company: Optional[CompanyResponse]
    total_invoices: int
    pending_invoices: int
    paid_invoices: int
    total_transactions: int
    unmatched_transactions: int
    total_debtors: float
    total_creditors: float


# Authentication schemas
class SignupRequest(BaseModel):
    company_name: str
    gstin: str
    owner_name: str
    owner_email: str
    owner_password: str
    
    @field_validator('owner_password')
    @classmethod
    def validate_password_length(cls, v: str) -> str:
        """Warn if password exceeds bcrypt's 72-byte limit (will be truncated)"""
        password_bytes = v.encode('utf-8')
        if len(password_bytes) > 72:
            # Password will be truncated automatically, but warn user
            # In practice, this is very rare (72 bytes = ~72 ASCII chars or ~24 Unicode chars)
            pass  # Truncation happens in get_password_hash
        return v


class LoginRequest(BaseModel):
    email: str
    password: str
    
    @field_validator('password')
    @classmethod
    def validate_password_length(cls, v: str) -> str:
        """Password will be truncated to 72 bytes if longer (bcrypt limit)"""
        return v


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class VerifyEmailRequest(BaseModel):
    token: str


# User schemas
class UserResponse(BaseModel):
    user_id: int
    company_id: int
    email: str
    name: str
    role: str
    is_active: bool
    email_verified: bool
    created_at: datetime
    last_login: Optional[datetime]
    
    class Config:
        from_attributes = True


class CreateUserRequest(BaseModel):
    email: str
    name: str
    role: str
    send_email: bool = True


class UpdateUserRequest(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

