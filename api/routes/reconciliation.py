"""
Reconciliation routes
"""
import logging
from fastapi import APIRouter, HTTPException, Depends
from api.schemas import ReconciliationResponse, SettlementRequest
from core.reconciliation import reconcile_transactions, settle_reconciliation, manual_settle
from core.auth import get_current_user
from database.models import User
from typing import Dict, List

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/reconcile", response_model=Dict)
async def run_reconciliation(current_user: User = Depends(get_current_user)):
    """Run automatic reconciliation"""
    try:
        result = reconcile_transactions(company_id=current_user.company_id)
        return result
    except Exception as e:
        logger.error(f"Reconciliation error: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to run reconciliation. Please try again later or contact support."
        )


@router.post("/reconcile/settle", response_model=ReconciliationResponse)
async def settle_reconciliation_endpoint(request: SettlementRequest, current_user: User = Depends(get_current_user)):
    """Manually settle a transaction with an invoice"""
    try:
        reconciliation = manual_settle(request.transaction_id, request.invoice_id)
        return reconciliation
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/reconciliations", response_model=List[ReconciliationResponse])
async def list_reconciliations(current_user: User = Depends(get_current_user)):
    """List all reconciliations for the authenticated user's company"""
    from database.models import Reconciliation, BankTransaction
    from database.db import get_db
    
    db = next(get_db())
    try:
        reconciliations = db.query(Reconciliation).join(
            BankTransaction, Reconciliation.transaction_id == BankTransaction.transaction_id
        ).filter(
            BankTransaction.company_id == current_user.company_id
        ).order_by(Reconciliation.created_at.desc()).all()
        
        return reconciliations
    finally:
        db.close()


@router.post("/reconciliations/{reconciliation_id}/settle", response_model=ReconciliationResponse)
async def settle_reconciliation_by_id(reconciliation_id: int, current_user: User = Depends(get_current_user)):
    """Settle a specific reconciliation"""
    try:
        reconciliation = settle_reconciliation(reconciliation_id)
        return reconciliation
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/reconcile/settle-all", response_model=Dict)
async def settle_all_pending(current_user: User = Depends(get_current_user)):
    """Settle all pending reconciliations with high confidence (>= 0.95)"""
    from database.models import Reconciliation, ReconciliationStatus, BankTransaction
    from database.db import get_db
    
    db = next(get_db())
    try:
        # Get all pending reconciliations with high confidence for user's company
        pending_recs = db.query(Reconciliation).join(
            BankTransaction, Reconciliation.transaction_id == BankTransaction.transaction_id
        ).filter(
            BankTransaction.company_id == current_user.company_id,
            Reconciliation.status == ReconciliationStatus.PENDING,
            Reconciliation.match_confidence >= 0.95
        ).all()
        
        settled_count = 0
        for rec in pending_recs:
            try:
                settle_reconciliation(rec.reconciliation_id)
                settled_count += 1
            except Exception as e:
                print(f"Error settling reconciliation {rec.reconciliation_id}: {e}")
        
        return {
            "total_pending": len(pending_recs),
            "settled": settled_count
        }
    finally:
        db.close()

