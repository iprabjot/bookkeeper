"""
Real-time CSV Report Generator
Regenerates CSV reports when journal entries are added and stores them in database
"""
from database.models import (
    JournalEntry, JournalEntryLine, ReportBundle, Report
)
from database.db import get_db
from core.company_manager import CompanyManager
from utils.accounting_reports import (
    generate_journal_entries_csv_string,
    generate_trial_balance_csv_string,
    generate_ledger_csv_string,
    extract_account_names
)
from datetime import datetime
from typing import Optional


def regenerate_csvs(user_id: Optional[int] = None, description: Optional[str] = None):
    """
    Regenerate all CSV reports from database and store in database
    Called automatically when journal entries are added
    
    Args:
        user_id: Optional user ID who triggered the generation
        description: Optional description for the report bundle
    """
    db = next(get_db())
    try:
        current_company = CompanyManager.get_current_company()
        if not current_company:
            raise ValueError("No current company set")
        
        # Get all journal entries
        entries = db.query(JournalEntry).filter(
            JournalEntry.company_id == current_company.company_id
        ).order_by(JournalEntry.date).all()
        
        # Convert to format expected by accounting_reports
        journal_entries_data = {
            "journal_entries": []
        }
        
        for entry in entries:
            # Get lines for this entry
            lines = db.query(JournalEntryLine).filter(
                JournalEntryLine.entry_id == entry.entry_id
            ).all()
            
            entry_dict = {
                "entry_id": f"JE-{entry.entry_id}",
                "date": entry.date.isoformat() if entry.date else None,
                "narration": entry.narration,
                "reference": entry.reference,
                "lines": [
                    {
                        "account_code": line.account_code,
                        "account_name": line.account_name,
                        "debit": line.debit,
                        "credit": line.credit
                    }
                    for line in lines
                ],
                "total_debit": sum(line.debit for line in lines),
                "total_credit": sum(line.credit for line in lines),
                "status": entry.status
            }
            
            journal_entries_data["journal_entries"].append(entry_dict)
        
        # Create a new report bundle
        if description:
            bundle_description = description
        else:
            bundle_description = f"Auto-generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        bundle = ReportBundle(
            company_id=current_company.company_id,
            generated_by_user_id=user_id,
            description=bundle_description
        )
        db.add(bundle)
        db.flush()  # Get bundle_id
        
        # Generate Journal Entries CSV
        journal_csv = generate_journal_entries_csv_string(journal_entries_data)
        if journal_csv:
            report = Report(
                bundle_id=bundle.bundle_id,
                report_type="journal_entries",  # Pass string directly to avoid SQLAlchemy enum conversion
                content=journal_csv,
                filename="Journal Entries.csv",
                size_bytes=len(journal_csv.encode('utf-8'))
            )
            db.add(report)
        
        # Generate Trial Balance CSV
        trial_balance_csv = generate_trial_balance_csv_string(journal_entries_data)
        if trial_balance_csv:
            report = Report(
                bundle_id=bundle.bundle_id,
                report_type="trial_balance",  # Pass string directly to avoid SQLAlchemy enum conversion
                content=trial_balance_csv,
                filename="Trial Balance.csv",
                size_bytes=len(trial_balance_csv.encode('utf-8'))
            )
            db.add(report)
        
        # Generate Ledgers for all accounts
        account_names = extract_account_names(journal_entries_data)
        for account_name in account_names:
            ledger_csv = generate_ledger_csv_string(account_name, journal_entries_data)
            if ledger_csv:
                safe_name = account_name.replace(" ", " ").replace("/", "-")
                report = Report(
                    bundle_id=bundle.bundle_id,
                    report_type="ledger",  # Pass string directly to avoid SQLAlchemy enum conversion
                    account_name=account_name,
                    content=ledger_csv,
                    filename=f"Ledger - {safe_name}.csv",
                    size_bytes=len(ledger_csv.encode('utf-8'))
                )
                db.add(report)
        
        db.commit()
        return bundle.bundle_id
        
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

