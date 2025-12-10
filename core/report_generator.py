"""
Real-time CSV Report Generator
Regenerates CSV reports when journal entries are added and stores them in database
"""
import logging
from database.models import (
    JournalEntry, JournalEntryLine, ReportBundle, Report, BankTransaction
)
from database.db import get_db
from core.company_manager import CompanyManager
from utils.accounting_reports import (
    generate_journal_entries_csv_string,
    generate_trial_balance_csv_string,
    generate_ledger_csv_string,
    extract_account_names,
    generate_profit_loss_csv_string,
    generate_cash_flow_csv_string
)
from core.financial_report_agent import (
    generate_profit_loss_statement,
    generate_cash_flow_statement
)
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


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
                report_type="journal_entries",
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
                report_type="trial_balance",
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
                    report_type="ledger",
                    account_name=account_name,
                    content=ledger_csv,
                    filename=f"Ledger - {safe_name}.csv",
                    size_bytes=len(ledger_csv.encode('utf-8'))
                )
                db.add(report)
        
        # Generate Profit & Loss Statement using AI agent
        try:
            logger.info("Generating Profit & Loss statement...")
            period_start = entries[0].date.isoformat() if entries else datetime.now().replace(day=1).isoformat()
            period_end = entries[-1].date.isoformat() if entries else datetime.now().isoformat()
            
            pnl_data = generate_profit_loss_statement(
                journal_entries_data,
                period_start=period_start,
                period_end=period_end
            )
            
            if pnl_data:
                pnl_csv = generate_profit_loss_csv_string(pnl_data)
                if pnl_csv:
                    report = Report(
                        bundle_id=bundle.bundle_id,
                        report_type="profit_loss",
                        content=pnl_csv,
                        filename="Profit and Loss.csv",
                        size_bytes=len(pnl_csv.encode('utf-8'))
                    )
                    db.add(report)
                    logger.info("Successfully generated Profit & Loss statement")
            else:
                logger.warning("AI agent did not generate P&L data")
        except Exception as e:
            logger.error(f"Failed to generate P&L statement: {e}", exc_info=True)
            # Continue with other reports even if P&L fails
        
        # Generate Cash Flow Statement using AI agent
        try:
            logger.info("Generating Cash Flow statement...")
            
            # Get bank transactions for cash flow
            bank_transactions = db.query(BankTransaction).filter(
                BankTransaction.company_id == current_company.company_id
            ).order_by(BankTransaction.date).all()
            
            bank_txns_list = [
                {
                    "date": txn.date,
                    "amount": txn.amount,
                    "type": str(txn.type),
                    "description": txn.description or ""
                }
                for txn in bank_transactions
            ]
            
            cash_flow_data = generate_cash_flow_statement(
                journal_entries_data,
                bank_txns_list,
                period_start=period_start,
                period_end=period_end
            )
            
            if cash_flow_data:
                cash_flow_csv = generate_cash_flow_csv_string(cash_flow_data)
                if cash_flow_csv:
                    report = Report(
                        bundle_id=bundle.bundle_id,
                        report_type="cash_flow",
                        content=cash_flow_csv,
                        filename="Cash Flow.csv",
                        size_bytes=len(cash_flow_csv.encode('utf-8'))
                    )
                    db.add(report)
                    logger.info("Successfully generated Cash Flow statement")
            else:
                logger.warning("AI agent did not generate Cash Flow data")
        except Exception as e:
            logger.error(f"Failed to generate Cash Flow statement: {e}", exc_info=True)
            # Continue even if Cash Flow fails
        
        db.commit()
        return bundle.bundle_id
        
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
