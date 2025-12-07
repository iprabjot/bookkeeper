"""
SQLAlchemy models for all database tables
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.db import Base
import enum


class InvoiceType(str, enum.Enum):
    SALES = "sales"
    PURCHASE = "purchase"


class InvoiceStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    PARTIALLY_PAID = "partially_paid"


class JournalEntryType(str, enum.Enum):
    SALES = "sales"
    PURCHASE = "purchase"
    PAYMENT = "payment"
    RECEIPT = "receipt"
    OTHER = "other"


class TransactionType(str, enum.Enum):
    CREDIT = "credit"
    DEBIT = "debit"


class TransactionStatus(str, enum.Enum):
    UNMATCHED = "unmatched"
    MATCHED = "matched"
    SETTLED = "settled"


class MatchType(str, enum.Enum):
    EXACT = "exact"
    FUZZY = "fuzzy"
    MANUAL = "manual"


class ReconciliationStatus(str, enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    SETTLED = "settled"


class UserRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    ACCOUNTANT = "accountant"
    VIEWER = "viewer"


class Company(Base):
    __tablename__ = "companies"
    
    company_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    gstin = Column(String, unique=True, nullable=False)
    is_current = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    vendors = relationship("Vendor", back_populates="company")
    buyers = relationship("Buyer", back_populates="company")
    journal_entries = relationship("JournalEntry", back_populates="company")
    invoices = relationship("Invoice", back_populates="company")
    bank_transactions = relationship("BankTransaction", back_populates="company")
    users = relationship("User", back_populates="company")


class Vendor(Base):
    __tablename__ = "vendors"
    
    vendor_id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.company_id"), nullable=False)
    name = Column(String, nullable=False)
    gstin = Column(String, nullable=True)
    address = Column(String, nullable=True)
    contact_info = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    company = relationship("Company", back_populates="vendors")
    invoices = relationship("Invoice", back_populates="vendor")


class Buyer(Base):
    __tablename__ = "buyers"
    
    buyer_id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.company_id"), nullable=False)
    name = Column(String, nullable=False)
    gstin = Column(String, nullable=True)
    address = Column(String, nullable=True)
    contact_info = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    company = relationship("Company", back_populates="buyers")
    invoices = relationship("Invoice", back_populates="buyer")


class JournalEntry(Base):
    __tablename__ = "journal_entries"
    
    entry_id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.company_id"), nullable=False)
    entry_type = Column(SQLEnum(JournalEntryType), nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)
    narration = Column(String, nullable=False)
    reference = Column(String, nullable=True)  # Invoice number, etc.
    status = Column(String, default="approved")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    company = relationship("Company", back_populates="journal_entries")
    lines = relationship("JournalEntryLine", back_populates="journal_entry", cascade="all, delete-orphan")


class JournalEntryLine(Base):
    __tablename__ = "journal_entry_lines"
    
    line_id = Column(Integer, primary_key=True, index=True)
    entry_id = Column(Integer, ForeignKey("journal_entries.entry_id"), nullable=False)
    account_code = Column(String, nullable=True)
    account_name = Column(String, nullable=False)
    debit = Column(Float, default=0.0)
    credit = Column(Float, default=0.0)
    
    # Relationships
    journal_entry = relationship("JournalEntry", back_populates="lines")


class Invoice(Base):
    __tablename__ = "invoices"
    
    invoice_id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.company_id"), nullable=False)
    vendor_id = Column(Integer, ForeignKey("vendors.vendor_id"), nullable=True)
    buyer_id = Column(Integer, ForeignKey("buyers.buyer_id"), nullable=True)
    invoice_type = Column(SQLEnum(InvoiceType), nullable=False)
    file_path = Column(String, nullable=False)
    invoice_number = Column(String, nullable=False, default="")
    invoice_date = Column(DateTime(timezone=True), nullable=True)
    amount = Column(Float, nullable=False)
    taxable_amount = Column(Float, default=0.0)
    igst_amount = Column(Float, default=0.0)
    cgst_amount = Column(Float, default=0.0)
    sgst_amount = Column(Float, default=0.0)
    status = Column(SQLEnum(InvoiceStatus), default=InvoiceStatus.PENDING)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    company = relationship("Company", back_populates="invoices")
    vendor = relationship("Vendor", back_populates="invoices")
    buyer = relationship("Buyer", back_populates="invoices")
    reconciliations = relationship("Reconciliation", back_populates="invoice")


class BankTransaction(Base):
    __tablename__ = "bank_transactions"
    
    transaction_id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.company_id"), nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    reference = Column(String, nullable=True)
    type = Column(SQLEnum(TransactionType), nullable=False)  # credit or debit
    status = Column(SQLEnum(TransactionStatus), default=TransactionStatus.UNMATCHED)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    company = relationship("Company", back_populates="bank_transactions")
    reconciliations = relationship("Reconciliation", back_populates="transaction")


class Reconciliation(Base):
    __tablename__ = "reconciliations"
    
    reconciliation_id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("bank_transactions.transaction_id"), nullable=False)
    invoice_id = Column(Integer, ForeignKey("invoices.invoice_id"), nullable=False)
    match_type = Column(SQLEnum(MatchType), nullable=False)
    match_confidence = Column(Float, nullable=True)
    status = Column(SQLEnum(ReconciliationStatus), default=ReconciliationStatus.PENDING)
    settled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    transaction = relationship("BankTransaction", back_populates="reconciliations")
    invoice = relationship("Invoice", back_populates="reconciliations")


class User(Base):
    __tablename__ = "users"
    
    user_id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.company_id"), nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    name = Column(String, nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.VIEWER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    company = relationship("Company", back_populates="users")


class ReportType(str, enum.Enum):
    JOURNAL_ENTRIES = "journal_entries"
    TRIAL_BALANCE = "trial_balance"
    LEDGER = "ledger"


class ReportBundle(Base):
    __tablename__ = "report_bundles"
    
    bundle_id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.company_id"), nullable=False)
    generated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    generated_by_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    description = Column(String, nullable=True)  # Optional description/notes
    
    # Relationships
    company = relationship("Company")
    generated_by = relationship("User")
    reports = relationship("Report", back_populates="bundle", cascade="all, delete-orphan")


class Report(Base):
    __tablename__ = "reports"
    
    report_id = Column(Integer, primary_key=True, index=True)
    bundle_id = Column(Integer, ForeignKey("report_bundles.bundle_id"), nullable=False)
    report_type = Column(
        postgresql.ENUM('journal_entries', 'trial_balance', 'ledger', name='reporttype', create_type=False),
        nullable=False
    )
    account_name = Column(String, nullable=True)  # For ledger reports
    content = Column(String, nullable=False)  # CSV content as string
    filename = Column(String, nullable=False)  # Original filename
    size_bytes = Column(Integer, nullable=False)  # Size of content
    
    # Relationships
    bundle = relationship("ReportBundle", back_populates="reports")

