"""
Accounting Reports Generator
Generates accounting reports in CSV format from journal entries.
Creates Journal Entries, Ledger, and Trial Balance reports matching standard accounting formats.
"""
import csv
import json
from datetime import datetime
from collections import defaultdict
from io import StringIO


# Helper functions that return CSV strings (for database storage)
def generate_journal_entries_csv_string(journal_entries_data):
    """Generate Journal Entries CSV as string"""
    output = StringIO()
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
                return None
    
    entries = journal_entries_data.get("journal_entries", [])
    
    for entry in entries:
        date = entry.get("date", "")
        lines = entry.get("lines", [])
        
        # Format date
        if date:
            try:
                dt = datetime.strptime(date, "%Y-%m-%d")
                date = dt.strftime("%d-%m-%Y")
            except:
                pass
        
        debit_accounts = [(line.get("account_name", ""), line.get("debit", 0)) 
                          for line in lines if line.get("debit", 0) > 0]
        credit_accounts = [(line.get("account_name", ""), line.get("credit", 0)) 
                           for line in lines if line.get("credit", 0) > 0]
        
        for account_name, amount in debit_accounts:
            clean_name = account_name.replace(" A/c", "").strip()
            rows.append({"Date": date, "Particulars": f"{clean_name} A/c", "Type": "Dr", "Amount": f"{int(amount)}"})
        
        for account_name, amount in credit_accounts:
            clean_name = account_name.replace(" A/c", "").strip()
            rows.append({"Date": date, "Particulars": f"To {clean_name} A/c", "Type": "Cr", "Amount": f"{int(amount)}"})
    
    if rows:
        writer = csv.DictWriter(output, fieldnames=["Date", "Particulars", "Type", "Amount"])
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue()
    return None


def generate_trial_balance_csv_string(journal_entries_data):
    """Generate Trial Balance CSV as string"""
    output = StringIO()
    account_balances = defaultdict(lambda: {"debit": 0, "credit": 0})
    
    if isinstance(journal_entries_data, str):
        try:
            journal_entries_data = json.loads(journal_entries_data)
        except:
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', journal_entries_data, re.DOTALL)
            if json_match:
                journal_entries_data = json.loads(json_match.group(1))
            else:
                return None
    
    entries = journal_entries_data.get("journal_entries", [])
    
    for entry in entries:
        for line in entry.get("lines", []):
            account_name = line.get("account_name", "")
            account_balances[account_name]["debit"] += line.get("debit", 0)
            account_balances[account_name]["credit"] += line.get("credit", 0)
    
    if account_balances:
        rows = []
        total_debit = 0
        total_credit = 0
        
        for account_name in sorted(account_balances.keys()):
            debit = account_balances[account_name]["debit"]
            credit = account_balances[account_name]["credit"]
            balance = debit - credit
            
            rows.append({
                "Account": account_name,
                "Debit": f"{int(debit)}" if debit > 0 else "",
                "Credit": f"{int(credit)}" if credit > 0 else "",
                "Balance": f"{int(balance)}" if balance != 0 else ""
            })
            total_debit += debit
            total_credit += credit
        
        rows.append({
            "Account": "Total",
            "Debit": f"{int(total_debit)}",
            "Credit": f"{int(total_credit)}",
            "Balance": ""
        })
        
        writer = csv.DictWriter(output, fieldnames=["Account", "Debit", "Credit", "Balance"])
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue()
    return None


def generate_ledger_csv_string(ledger_name, journal_entries_data):
    """Generate Ledger CSV as string for a specific account"""
    output = StringIO()
    rows = []
    balance = 0
    
    if isinstance(journal_entries_data, str):
        try:
            journal_entries_data = json.loads(journal_entries_data)
        except:
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', journal_entries_data, re.DOTALL)
            if json_match:
                journal_entries_data = json.loads(json_match.group(1))
            else:
                return None
    
    entries = journal_entries_data.get("journal_entries", [])
    
    for entry in entries:
        date = entry.get("date", "")
        narration = entry.get("narration", "")
        reference = entry.get("reference", "")
        
        if date:
            try:
                dt = datetime.strptime(date, "%Y-%m-%d")
                date = dt.strftime("%d-%m-%Y")
            except:
                pass
        
        for line in entry.get("lines", []):
            if line.get("account_name", "") == ledger_name:
                debit = line.get("debit", 0)
                credit = line.get("credit", 0)
                balance += debit - credit
                
                rows.append({
                    "Date": date,
                    "Particulars": narration or reference,
                    "Debit": f"{int(debit)}" if debit > 0 else "",
                    "Credit": f"{int(credit)}" if credit > 0 else "",
                    "Balance": f"{int(balance)}"
                })
    
    if rows:
        rows.append({
            "Date": "",
            "Particulars": "Closing Balance",
            "Debit": "",
            "Credit": "",
            "Balance": f"{int(balance)}"
        })
        
        writer = csv.DictWriter(output, fieldnames=["Date", "Particulars", "Debit", "Credit", "Balance"])
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue()
    return None


def extract_account_names(journal_entries_data):
    """Extract unique account names from journal entries"""
    if isinstance(journal_entries_data, str):
        try:
            journal_entries_data = json.loads(journal_entries_data)
        except:
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', journal_entries_data, re.DOTALL)
            if json_match:
                journal_entries_data = json.loads(json_match.group(1))
            else:
                return set()
    
    entries = journal_entries_data.get("journal_entries", [])
    account_names = set()
    for entry in entries:
        for line in entry.get("lines", []):
            account_name = line.get("account_name", "")
            if account_name:
                account_names.add(account_name)
    return account_names

