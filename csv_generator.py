"""
CSV Generator for Accounting Outputs
Converts agent outputs to CSV format matching Vishwakarma_Metal_Corp_Accounts
"""
import csv
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict


def generate_journal_entries_csv(journal_entries_data, output_path):
    """
    Generate Journal Entries CSV in the format:
    Date, Particulars, Type, Amount
    """
    rows = []
    
    # Handle both JSON string and dict
    if isinstance(journal_entries_data, str):
        try:
            journal_entries_data = json.loads(journal_entries_data)
        except:
            # Try to extract JSON from markdown code blocks
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', journal_entries_data, re.DOTALL)
            if json_match:
                journal_entries_data = json.loads(json_match.group(1))
            else:
                print("Warning: Could not parse journal entries data")
                return
    
    entries = journal_entries_data.get("journal_entries", [])
    
    for entry in entries:
        date = entry.get("date", "")
        narration = entry.get("narration", "")
        reference = entry.get("reference", "")
        
        # Format date from YYYY-MM-DD to DD-MM-YYYY
        if date:
            try:
                dt = datetime.strptime(date, "%Y-%m-%d")
                date = dt.strftime("%d-%m-%Y")
            except:
                pass
        
        # Get account lines
        lines = entry.get("lines", [])
        
        # Group by account for debit and credit
        debit_accounts = []
        credit_accounts = []
        
        for line in lines:
            account_name = line.get("account_name", "")
            debit = line.get("debit", 0)
            credit = line.get("credit", 0)
            
            if debit > 0:
                debit_accounts.append((account_name, debit))
            if credit > 0:
                credit_accounts.append((account_name, credit))
        
        # Create journal entry rows
        # First row: Debit entry
        if debit_accounts:
            for account_name, amount in debit_accounts:
                # Remove "A/c" suffix if already present to avoid duplication
                clean_name = account_name.replace(" A/c", "").strip()
                rows.append({
                    "Date": date,
                    "Particulars": f"{clean_name} A/c",
                    "Type": "Dr",
                    "Amount": f"{int(amount)}",
                })
        
        # Credit entries
        if credit_accounts:
            for account_name, amount in credit_accounts:
                # Remove "A/c" suffix if already present
                clean_name = account_name.replace(" A/c", "").strip()
                rows.append({
                    "Date": date,
                    "Particulars": f"To {clean_name} A/c",
                    "Type": "Cr",
                    "Amount": f"{int(amount)}",
                })
    
    # Write CSV
    if rows:
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["Date", "Particulars", "Type", "Amount"])
            writer.writeheader()
            writer.writerows(rows)
        print(f"Generated Journal Entries CSV: {output_path}")
    else:
        print(f"Warning: No journal entries to write to {output_path}")


def generate_ledger_csv(ledger_name, journal_entries_data, output_path):
    """
    Generate Ledger CSV for a specific account in the format:
    Date, Particulars, Debit, Credit
    """
    rows = []
    
    # Handle both JSON string and dict
    if isinstance(journal_entries_data, str):
        try:
            journal_entries_data = json.loads(journal_entries_data)
        except:
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', journal_entries_data, re.DOTALL)
            if json_match:
                journal_entries_data = json.loads(json_match.group(1))
            else:
                print(f"Warning: Could not parse journal entries for ledger {ledger_name}")
                return
    
    entries = journal_entries_data.get("journal_entries", [])
    
    for entry in entries:
        date = entry.get("date", "")
        narration = entry.get("narration", "")
        reference = entry.get("reference", "")
        
        # Format date
        if date:
            try:
                dt = datetime.strptime(date, "%Y-%m-%d")
                date = dt.strftime("%d-%m-%Y")
            except:
                pass
        
        lines = entry.get("lines", [])
        
        for line in lines:
            account_name = line.get("account_name", "")
            debit = line.get("debit", 0)
            credit = line.get("credit", 0)
            
            # Match account name more flexibly
            account_match = False
            if ledger_name.lower() in account_name.lower():
                account_match = True
            elif account_name.lower() in ledger_name.lower():
                account_match = True
            elif "debtors" in ledger_name.lower() and "debtors" in account_name.lower():
                account_match = True
            elif "sales" in ledger_name.lower() and "sales" in account_name.lower():
                account_match = True
            elif "igst" in ledger_name.lower() and "igst" in account_name.lower():
                account_match = True
            
            if account_match:
                # Determine particulars based on other accounts in the entry
                other_accounts = [l.get("account_name", "") for l in lines if l.get("account_name", "") != account_name]
                if other_accounts:
                    if debit > 0:
                        # This is a debit entry, show credit side (what we're receiving)
                        # Format: "By Sales – Customer Name" or "By Sales A/c"
                        other_account = other_accounts[0]
                        clean_other = other_account.replace(" A/c", "").strip()
                        if "Sales" in other_account:
                            # Extract customer name from narration
                            if narration and "to" in narration.lower():
                                customer_name = narration.split("to")[-1].strip()
                                particulars = f"By Sales – {customer_name}"
                            elif reference:
                                particulars = f"By Sales – {reference.replace('INV-', '')}"
                            else:
                                particulars = f"By {clean_other}"
                        else:
                            particulars = f"By {clean_other}"
                    else:
                        # This is a credit entry, show debit side (what we're giving)
                        # Format: "To Debtors – Customer Name" or "To IGST on Invoice XXX"
                        other_account = other_accounts[0]
                        clean_other = other_account.replace(" A/c", "").strip()
                        if "Debtors" in other_account:
                            # Extract customer name from account name
                            if "–" in account_name:
                                customer_name = account_name.split("–")[-1].strip()
                                particulars = f"To Debtors – {customer_name}"
                            elif reference:
                                particulars = f"To Debtors – {reference.replace('INV-', '')}"
                            else:
                                particulars = f"To {clean_other}"
                        elif "IGST" in other_account or "CGST" in other_account or "SGST" in other_account:
                            if reference:
                                tax_type = clean_other.split(" Payable")[0] if " Payable" in clean_other else clean_other
                                particulars = f"To {tax_type} on Invoice {reference.replace('INV-', '')}"
                            else:
                                particulars = f"To {clean_other}"
                        else:
                            particulars = f"To {clean_other}"
                else:
                    particulars = narration or reference
                
                rows.append({
                    "Date": date,
                    "Particulars": particulars,
                    "Debit": f"{int(debit)}" if debit > 0 else "",
                    "Credit": f"{int(credit)}" if credit > 0 else "",
                })
    
    # Write CSV
    if rows:
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["Date", "Particulars", "Debit", "Credit"])
            writer.writeheader()
            writer.writerows(rows)
        print(f"Generated Ledger CSV for {ledger_name}: {output_path}")
    else:
        print(f"Warning: No entries found for ledger {ledger_name}")


def generate_trial_balance_csv(journal_entries_data, output_path):
    """
    Generate Trial Balance CSV in the format:
    Account, Debit, Credit
    """
    account_totals = defaultdict(lambda: {"debit": 0, "credit": 0})
    
    # Handle both JSON string and dict
    if isinstance(journal_entries_data, str):
        try:
            journal_entries_data = json.loads(journal_entries_data)
        except:
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', journal_entries_data, re.DOTALL)
            if json_match:
                journal_entries_data = json.loads(json_match.group(1))
            else:
                print("Warning: Could not parse journal entries for trial balance")
                return
    
    entries = journal_entries_data.get("journal_entries", [])
    
    # Aggregate all account balances
    for entry in entries:
        lines = entry.get("lines", [])
        for line in lines:
            account_name = line.get("account_name", "")
            debit = line.get("debit", 0)
            credit = line.get("credit", 0)
            
            account_totals[account_name]["debit"] += debit
            account_totals[account_name]["credit"] += credit
    
    # Create rows
    rows = []
    for account_name, totals in sorted(account_totals.items()):
        debit = totals["debit"]
        credit = totals["credit"]
        
        # Only include accounts with non-zero balances
        if debit > 0 or credit > 0:
            rows.append({
                "Account": account_name,
                "Debit": f"{debit:.0f}" if debit > 0 else "0",
                "Credit": f"{credit:.0f}" if credit > 0 else "0",
            })
    
    # Write CSV
    if rows:
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["Account", "Debit", "Credit"])
            writer.writeheader()
            writer.writerows(rows)
        print(f"Generated Trial Balance CSV: {output_path}")
    else:
        print("Warning: No accounts found for trial balance")


def generate_all_csvs(journal_entries_data, ledger_data, output_dir):
    """Generate all CSV files in the output directory."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Generate Journal Entries
    generate_journal_entries_csv(
        journal_entries_data,
        output_path / "Journal Entries-Table 1.csv"
    )
    
    # Generate Ledgers for common accounts
    # Extract account names from journal entries
    if isinstance(journal_entries_data, str):
        try:
            journal_entries_data = json.loads(journal_entries_data)
        except:
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', journal_entries_data, re.DOTALL)
            if json_match:
                journal_entries_data = json.loads(json_match.group(1))
    
    entries = journal_entries_data.get("journal_entries", [])
    account_names = set()
    for entry in entries:
        for line in entry.get("lines", []):
            account_name = line.get("account_name", "")
            if account_name:
                account_names.add(account_name)
    
    # Generate ledger for each account
    for account_name in account_names:
        # Clean account name for filename
        safe_name = account_name.replace(" ", " ").replace("/", "-")
        generate_ledger_csv(
            account_name,
            journal_entries_data,
            output_path / f"Ledger - {safe_name}-Table 1.csv"
        )
    
    # Generate Trial Balance
    generate_trial_balance_csv(
        journal_entries_data,
        output_path / "Trial Balance-Table 1.csv"
    )


if __name__ == "__main__":
    # Test with sample data
    test_data = {
        "journal_entries": [
            {
                "entry_id": "JE-2025-001",
                "date": "2025-01-31",
                "narration": "Sales to Kiran Enterprises",
                "reference": "INV-241389",
                "lines": [
                    {"account_code": "1100", "account_name": "Debtors – Kiran Enterprises", "debit": 437544, "credit": 0},
                    {"account_code": "4100", "account_name": "Sales A/c", "debit": 0, "credit": 370800},
                    {"account_code": "2310", "account_name": "IGST Payable A/c", "debit": 0, "credit": 66744},
                ],
                "total_debit": 437544,
                "total_credit": 437544,
            }
        ]
    }
    
    generate_all_csvs(test_data, None, "test_output")

