"""
Report generation routes - Database-backed report management
"""
import logging
import zipfile
import io
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import Response
from database.db import get_db
from core.auth import get_current_user
from database.models import (
    User, ReportBundle, Report, Company
)
from sqlalchemy.orm import Session
from sqlalchemy import desc
from urllib.parse import unquote, quote
from typing import Optional

logger = logging.getLogger(__name__)
router = APIRouter()


def encode_filename_for_header(filename: str) -> str:
    """
    Encode filename for Content-Disposition header.
    Uses RFC 2231 encoding for Unicode characters.
    """
    try:
        # Try to encode as ASCII first (simple case)
        filename.encode('ascii')
        return f'filename="{filename}"'
    except UnicodeEncodeError:
        # Use RFC 2231 encoding for Unicode characters
        encoded = quote(filename, safe='')
        return f"filename*=UTF-8''{encoded}"


def get_latest_bundle(db: Session, company_id: int) -> Optional[ReportBundle]:
    """Get the latest report bundle for a company"""
    return db.query(ReportBundle).filter(
        ReportBundle.company_id == company_id
    ).order_by(desc(ReportBundle.generated_at)).first()


@router.get("/reports/bundles")
async def list_bundles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all report bundles for the current company"""
    bundles = db.query(ReportBundle).filter(
        ReportBundle.company_id == current_user.company_id
    ).order_by(desc(ReportBundle.generated_at)).all()
    
    return {
        "bundles": [
            {
                "bundle_id": bundle.bundle_id,
                "generated_at": bundle.generated_at.isoformat(),
                "generated_by": bundle.generated_by.name if bundle.generated_by else None,
                "description": bundle.description,
                "report_count": len(bundle.reports)
            }
            for bundle in bundles
        ]
    }


@router.get("/reports/bundles/{bundle_id}")
async def get_bundle(
    bundle_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get details of a specific report bundle"""
    bundle = db.query(ReportBundle).filter(
        ReportBundle.bundle_id == bundle_id,
        ReportBundle.company_id == current_user.company_id
    ).first()
    
    if not bundle:
        raise HTTPException(status_code=404, detail="Report bundle not found")
    
    reports = []
    for report in bundle.reports:
        # report_type is stored as string, so use it directly
        report_type_str = str(report.report_type)
        reports.append({
            "report_id": report.report_id,
            "report_type": report_type_str,
            "account_name": report.account_name,
            "filename": report.filename,
            "size_bytes": report.size_bytes,
            "download_url": f"/reports/{report.report_id}/download"
        })
    
    return {
        "bundle_id": bundle.bundle_id,
        "generated_at": bundle.generated_at.isoformat(),
        "generated_by": bundle.generated_by.name if bundle.generated_by else None,
        "description": bundle.description,
        "reports": reports
    }


@router.get("/reports/{report_id}/download")
async def download_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download a specific report by ID"""
    report = db.query(Report).join(
        ReportBundle, Report.bundle_id == ReportBundle.bundle_id
    ).filter(
        Report.report_id == report_id,
        ReportBundle.company_id == current_user.company_id
    ).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return Response(
        content=report.content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; {encode_filename_for_header(report.filename)}'
        }
    )


@router.get("/reports/journal-entries")
async def get_journal_entries_csv(
    bundle_id: Optional[int] = Query(None, description="Specific bundle ID, or latest if not provided"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download Journal Entries CSV from latest or specified bundle"""
    if bundle_id:
        bundle = db.query(ReportBundle).filter(
            ReportBundle.bundle_id == bundle_id,
            ReportBundle.company_id == current_user.company_id
        ).first()
    else:
        bundle = get_latest_bundle(db, current_user.company_id)
    
    if not bundle:
        raise HTTPException(
            status_code=404,
            detail="No reports found. Generate reports first."
        )
    
    report = db.query(Report).filter(
        Report.bundle_id == bundle.bundle_id,
        Report.report_type == "journal_entries"  # Compare with string value
    ).first()
    
    if not report:
        raise HTTPException(
            status_code=404,
            detail="Journal Entries report not found in this bundle"
        )
    
    return Response(
        content=report.content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; {encode_filename_for_header(report.filename)}'
        }
    )


@router.get("/reports/trial-balance")
async def get_trial_balance_csv(
    bundle_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download Trial Balance CSV from latest or specified bundle"""
    if bundle_id:
        bundle = db.query(ReportBundle).filter(
            ReportBundle.bundle_id == bundle_id,
            ReportBundle.company_id == current_user.company_id
        ).first()
    else:
        bundle = get_latest_bundle(db, current_user.company_id)
    
    if not bundle:
        raise HTTPException(
            status_code=404,
            detail="No reports found. Generate reports first."
        )
    
    report = db.query(Report).filter(
        Report.bundle_id == bundle.bundle_id,
        Report.report_type == "trial_balance"  # Compare with string value
    ).first()
    
    if not report:
        raise HTTPException(
            status_code=404,
            detail="Trial Balance report not found in this bundle"
        )
    
    return Response(
        content=report.content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; {encode_filename_for_header(report.filename)}'
        }
    )


@router.get("/reports/profit-loss")
async def get_profit_loss_csv(
    bundle_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download Profit & Loss Statement CSV from latest or specified bundle"""
    if bundle_id:
        bundle = db.query(ReportBundle).filter(
            ReportBundle.bundle_id == bundle_id,
            ReportBundle.company_id == current_user.company_id
        ).first()
    else:
        bundle = get_latest_bundle(db, current_user.company_id)
    
    if not bundle:
        raise HTTPException(
            status_code=404,
            detail="No reports found. Generate reports first."
        )
    
    report = db.query(Report).filter(
        Report.bundle_id == bundle.bundle_id,
        Report.report_type == "profit_loss"
    ).first()
    
    if not report:
        raise HTTPException(
            status_code=404,
            detail="Profit & Loss statement not found in this bundle"
        )
    
    return Response(
        content=report.content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; {encode_filename_for_header(report.filename)}'
        }
    )


@router.get("/reports/cash-flow")
async def get_cash_flow_csv(
    bundle_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download Cash Flow Statement CSV from latest or specified bundle"""
    if bundle_id:
        bundle = db.query(ReportBundle).filter(
            ReportBundle.bundle_id == bundle_id,
            ReportBundle.company_id == current_user.company_id
        ).first()
    else:
        bundle = get_latest_bundle(db, current_user.company_id)
    
    if not bundle:
        raise HTTPException(
            status_code=404,
            detail="No reports found. Generate reports first."
        )
    
    report = db.query(Report).filter(
        Report.bundle_id == bundle.bundle_id,
        Report.report_type == "cash_flow"
    ).first()
    
    if not report:
        raise HTTPException(
            status_code=404,
            detail="Cash Flow statement not found in this bundle"
        )
    
    return Response(
        content=report.content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; {encode_filename_for_header(report.filename)}'
        }
    )


@router.get("/reports/ledger/{account_name:path}")
async def get_ledger_csv(
    account_name: str,
    bundle_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download Ledger CSV for a specific account from latest or specified bundle"""
    decoded_name = unquote(account_name)
    
    if bundle_id:
        bundle = db.query(ReportBundle).filter(
            ReportBundle.bundle_id == bundle_id,
            ReportBundle.company_id == current_user.company_id
        ).first()
    else:
        bundle = get_latest_bundle(db, current_user.company_id)
    
    if not bundle:
        raise HTTPException(
            status_code=404,
            detail="No reports found. Generate reports first."
        )
    
    report = db.query(Report).filter(
        Report.bundle_id == bundle.bundle_id,
        Report.report_type == "ledger",  # Compare with string value
        Report.account_name == decoded_name
    ).first()
    
    if not report:
        raise HTTPException(
            status_code=404,
            detail=f"Ledger for {decoded_name} not found in this bundle"
        )
    
    return Response(
        content=report.content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; {encode_filename_for_header(report.filename)}'
        }
    )


@router.get("/reports/list")
async def list_reports(
    bundle_id: Optional[int] = Query(None, description="Specific bundle ID, or latest if not provided"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all reports in latest or specified bundle"""
    if bundle_id:
        bundle = db.query(ReportBundle).filter(
            ReportBundle.bundle_id == bundle_id,
            ReportBundle.company_id == current_user.company_id
        ).first()
    else:
        bundle = get_latest_bundle(db, current_user.company_id)
    
    if not bundle:
        return {"reports": [], "ledgers": [], "bundle_id": None}
    
    reports = []
    ledgers = []
    
    for report in bundle.reports:
        # report_type is stored as string, so compare with string values
        report_type_str = str(report.report_type)  # Ensure it's a string
        
        if report_type_str == "journal_entries":
            reports.append({
                "name": "Journal Entries",
                "type": "standard",
                "endpoint": f"/api/reports/journal-entries?bundle_id={bundle.bundle_id}",
                "download_url": f"/reports/{report.report_id}/download",
                "filename": report.filename
            })
        elif report_type_str == "trial_balance":
            reports.append({
                "name": "Trial Balance",
                "type": "standard",
                "endpoint": f"/api/reports/trial-balance?bundle_id={bundle.bundle_id}",
                "download_url": f"/reports/{report.report_id}/download",
                "filename": report.filename
            })
        elif report_type_str == "profit_loss":
            reports.append({
                "name": "Profit & Loss",
                "type": "financial_statement",
                "endpoint": f"/api/reports/profit-loss?bundle_id={bundle.bundle_id}",
                "download_url": f"/reports/{report.report_id}/download",
                "filename": report.filename
            })
        elif report_type_str == "cash_flow":
            reports.append({
                "name": "Cash Flow",
                "type": "financial_statement",
                "endpoint": f"/api/reports/cash-flow?bundle_id={bundle.bundle_id}",
                "download_url": f"/reports/{report.report_id}/download",
                "filename": report.filename
            })
        elif report_type_str == "ledger":
            from urllib.parse import quote
            encoded_name = quote(report.account_name, safe='')
            ledgers.append({
                "name": report.account_name,
                "type": "ledger",
                "endpoint": f"/api/reports/ledger/{encoded_name}?bundle_id={bundle.bundle_id}",
                "download_url": f"/reports/{report.report_id}/download",
                "filename": report.filename
            })
    
    return {
        "bundle_id": bundle.bundle_id,
        "generated_at": bundle.generated_at.isoformat(),
        "reports": reports,
        "ledgers": ledgers
    }


@router.post("/reports/generate")
async def generate_reports(
    description: Optional[str] = Query(None, description="Optional description for this report bundle"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Manually trigger report generation"""
    from core.report_generator import regenerate_csvs
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        bundle_id = regenerate_csvs(company_id=current_user.company_id, user_id=current_user.user_id, description=description)
        bundle = db.query(ReportBundle).filter(
            ReportBundle.bundle_id == bundle_id
        ).first()
        
        if description and bundle:
            bundle.description = description
            db.commit()
        
        return {
            "message": "Reports generated successfully",
            "bundle_id": bundle_id,
            "generated_at": bundle.generated_at.isoformat() if bundle else None
        }
    except Exception as e:
        # Log the full error
        logger.error(f"Failed to generate reports: {type(e).__name__}: {str(e)}", exc_info=True)
        # Return generic message to client
        raise HTTPException(
            status_code=500,
            detail="Failed to generate reports. Please try again later or contact support."
        )


@router.get("/reports/bundles/{bundle_id}/download-zip")
async def download_bundle_zip(
    bundle_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download all reports in a bundle as a ZIP file"""
    bundle = db.query(ReportBundle).filter(
        ReportBundle.bundle_id == bundle_id,
        ReportBundle.company_id == current_user.company_id
    ).first()
    
    if not bundle:
        raise HTTPException(status_code=404, detail="Report bundle not found")
    
    if not bundle.reports:
        raise HTTPException(status_code=404, detail="No reports found in this bundle")
    
    # Create ZIP file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for report in bundle.reports:
            # Add each report to the ZIP
            zip_file.writestr(report.filename, report.content)
    
    zip_buffer.seek(0)
    
    # Generate filename with bundle info
    date_str = bundle.generated_at.strftime("%Y%m%d_%H%M%S")
    zip_filename = f"reports_bundle_{bundle_id}_{date_str}.zip"
    
    return Response(
        content=zip_buffer.read(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; {encode_filename_for_header(zip_filename)}'
        }
    )


@router.delete("/reports/bundles/{bundle_id}")
async def delete_bundle(
    bundle_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a report bundle and all its reports"""
    bundle = db.query(ReportBundle).filter(
        ReportBundle.bundle_id == bundle_id,
        ReportBundle.company_id == current_user.company_id
    ).first()
    
    if not bundle:
        raise HTTPException(status_code=404, detail="Report bundle not found")
    
    db.delete(bundle)
    db.commit()
    
    return {"message": "Report bundle deleted successfully"}


@router.get("/status")
async def get_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current system status and balances"""
    from database.models import Invoice, BankTransaction, InvoiceStatus, TransactionStatus, Company
    
    current_company = db.query(Company).filter(
        Company.company_id == current_user.company_id
    ).first()
    
    if not current_company:
        from api.schemas import StatusResponse
        return StatusResponse(
            current_company=None,
            total_invoices=0,
            pending_invoices=0,
            paid_invoices=0,
            total_transactions=0,
            unmatched_transactions=0,
            total_debtors=0.0,
            total_creditors=0.0
        )
    
    # Count invoices for user's company
    total_invoices = db.query(Invoice).filter(
        Invoice.company_id == current_user.company_id
    ).count()
    
    pending_invoices = db.query(Invoice).filter(
        Invoice.company_id == current_user.company_id,
        Invoice.status == InvoiceStatus.PENDING
    ).count()
    
    paid_invoices = db.query(Invoice).filter(
        Invoice.company_id == current_user.company_id,
        Invoice.status == InvoiceStatus.PAID
    ).count()
    
    # Count transactions for user's company
    total_transactions = db.query(BankTransaction).filter(
        BankTransaction.company_id == current_user.company_id
    ).count()
    
    unmatched_transactions = db.query(BankTransaction).filter(
        BankTransaction.company_id == current_user.company_id,
        BankTransaction.status == TransactionStatus.UNMATCHED
    ).count()
    
    # Calculate balances from journal entries
    from database.models import JournalEntryLine, JournalEntry
    
    debtors_lines = db.query(JournalEntryLine).join(
        JournalEntry, JournalEntryLine.entry_id == JournalEntry.entry_id
    ).filter(
        JournalEntry.company_id == current_user.company_id,
        JournalEntryLine.account_name.like("Debtors%")
    ).all()
    
    creditors_lines = db.query(JournalEntryLine).join(
        JournalEntry, JournalEntryLine.entry_id == JournalEntry.entry_id
    ).filter(
        JournalEntry.company_id == current_user.company_id,
        JournalEntryLine.account_name.like("Creditors%")
    ).all()
    
    total_debtors = sum(line.debit - line.credit for line in debtors_lines)
    total_creditors = sum(line.credit - line.debit for line in creditors_lines)
    
    from api.schemas import StatusResponse
    return StatusResponse(
        current_company=current_company,
        total_invoices=total_invoices,
        pending_invoices=pending_invoices,
        paid_invoices=paid_invoices,
        total_transactions=total_transactions,
        unmatched_transactions=unmatched_transactions,
        total_debtors=max(0, total_debtors),
        total_creditors=max(0, total_creditors)
    )
