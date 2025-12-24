"""
Bank statement processing routes
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query
from typing import List
from api.schemas import BankTransactionResponse
from core.bank_parser import parse_bank_statement
from core.auth import get_current_user
from database.models import User
import tempfile
import os

router = APIRouter()


@router.post("/bank-statements", response_model=List[BankTransactionResponse])
async def upload_bank_statement(
    file: UploadFile = File(...),
    categorize: bool = Query(True, description="Whether to categorize transactions using AI"),
    current_user: User = Depends(get_current_user)
):
    """Upload and process a bank statement (CSV or PDF) with AI categorization"""
    # Determine file extension
    file_ext = os.path.splitext(file.filename)[1].lower() if file.filename else ""
    
    if file_ext not in ['.csv', '.pdf']:
        raise HTTPException(
            status_code=400,
            detail="Only CSV and PDF files are supported"
        )
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext, mode='wb') as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_path = tmp_file.name
    
    try:
        # Parse bank statement (supports both CSV and PDF)
        transactions = parse_bank_statement(
            tmp_path,
            company_id=current_user.company_id,
            categorize=categorize
        )
        return transactions
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Bank statement upload error: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload bank statement: {str(e)}"
        )
    finally:
        # Clean up temp file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.get("/bank-transactions", response_model=List[BankTransactionResponse])
async def list_transactions(current_user: User = Depends(get_current_user)):
    """List all bank transactions for the authenticated user's company"""
    from database.models import BankTransaction
    from database.db import get_db
    
    db = next(get_db())
    try:
        transactions = db.query(BankTransaction).filter(
            BankTransaction.company_id == current_user.company_id
        ).order_by(BankTransaction.date.desc()).all()
        
        return transactions
    finally:
        db.close()

