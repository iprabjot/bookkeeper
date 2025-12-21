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
        
        # Format date to readable format (DD-MMM-YYYY)
        if date:
            try:
                # Try ISO format first
                if 'T' in date:
                    dt = datetime.fromisoformat(date.replace('Z', '+00:00'))
                else:
                    dt = datetime.strptime(date, "%Y-%m-%d")
                date = dt.strftime("%d-%b-%Y")  # e.g., "14-Feb-2025"
            except:
                try:
                    # Try other formats
                    dt = datetime.strptime(date, "%d-%m-%Y")
                    date = dt.strftime("%d-%b-%Y")
                except:
                    pass  # Keep original if can't parse
        
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
        
        # Format date to readable format (DD-MMM-YYYY)
        if date:
            try:
                # Try ISO format first
                if 'T' in date:
                    dt = datetime.fromisoformat(date.replace('Z', '+00:00'))
                else:
                    dt = datetime.strptime(date, "%Y-%m-%d")
                date = dt.strftime("%d-%b-%Y")  # e.g., "14-Feb-2025"
            except:
                try:
                    # Try other formats
                    dt = datetime.strptime(date, "%d-%m-%Y")
                    date = dt.strftime("%d-%b-%Y")
                except:
                    pass  # Keep original if can't parse
        
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


def generate_profit_loss_csv_string(profit_loss_data):
    """Generate Profit & Loss Statement CSV as string"""
    output = StringIO()
    rows = []
    
    # Handle both dict and JSON string
    if isinstance(profit_loss_data, str):
        try:
            profit_loss_data = json.loads(profit_loss_data)
        except:
            return None
    
    if not profit_loss_data:
        return None
    
    revenue = profit_loss_data.get("revenue", {})
    expenses = profit_loss_data.get("expenses", {})
    
    # Revenue section
    revenue_from_ops = revenue.get("revenue_from_operations", 0)
    other_income = revenue.get("other_income", 0)
    total_revenue = revenue.get("total_revenue", revenue_from_ops + other_income)
    
    rows.append({"Category": "Revenue", "Subcategory": "Revenue from Operations", "Amount": f"{int(revenue_from_ops)}"})
    rows.append({"Category": "Revenue", "Subcategory": "Other Income", "Amount": f"{int(other_income)}"})
    rows.append({"Category": "Total Revenue", "Subcategory": "", "Amount": f"{int(total_revenue)}"})
    rows.append({"Category": "", "Subcategory": "", "Amount": ""})  # Empty row
    
    # Expenses section
    cost_of_materials = expenses.get("cost_of_materials", 0)
    employee_benefits = expenses.get("employee_benefits", 0)
    other_expenses = expenses.get("other_expenses", 0)
    total_expenses = expenses.get("total_expenses", cost_of_materials + employee_benefits + other_expenses)
    
    rows.append({"Category": "Expenses", "Subcategory": "Cost of Materials", "Amount": f"{int(cost_of_materials)}"})
    rows.append({"Category": "Expenses", "Subcategory": "Employee Benefits", "Amount": f"{int(employee_benefits)}"})
    rows.append({"Category": "Expenses", "Subcategory": "Other Expenses", "Amount": f"{int(other_expenses)}"})
    rows.append({"Category": "Total Expenses", "Subcategory": "", "Amount": f"{int(total_expenses)}"})
    rows.append({"Category": "", "Subcategory": "", "Amount": ""})  # Empty row
    
    # Profit section
    profit_before_tax = profit_loss_data.get("profit_before_tax", total_revenue - total_expenses)
    tax_expense = profit_loss_data.get("tax_expense", 0)
    net_profit = profit_loss_data.get("net_profit", profit_before_tax - tax_expense)
    
    rows.append({"Category": "Profit Before Tax", "Subcategory": "", "Amount": f"{int(profit_before_tax)}"})
    rows.append({"Category": "Tax Expense", "Subcategory": "", "Amount": f"{int(tax_expense)}"})
    rows.append({"Category": "Net Profit", "Subcategory": "", "Amount": f"{int(net_profit)}"})
    
    writer = csv.DictWriter(output, fieldnames=["Category", "Subcategory", "Amount"])
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def generate_cash_flow_csv_string(cash_flow_data):
    """Generate Cash Flow Statement CSV as string"""
    output = StringIO()
    rows = []
    
    # Handle both dict and JSON string
    if isinstance(cash_flow_data, str):
        try:
            cash_flow_data = json.loads(cash_flow_data)
        except:
            return None
    
    if not cash_flow_data:
        return None
    
    operating = cash_flow_data.get("operating_activities", {})
    investing = cash_flow_data.get("investing_activities", {})
    financing = cash_flow_data.get("financing_activities", {})
    
    # Operating Activities
    net_profit = operating.get("net_profit", 0)
    adjustments = operating.get("adjustments_for_non_cash_items", 0)
    working_capital = operating.get("changes_in_working_capital", 0)
    cash_from_operating = operating.get("cash_from_operating_activities", net_profit + adjustments + working_capital)
    
    rows.append({"Category": "Operating Activities", "Item": "Net Profit", "Amount": f"{int(net_profit)}"})
    rows.append({"Category": "Operating Activities", "Item": "Adjustments for non-cash items", "Amount": f"{int(adjustments)}"})
    rows.append({"Category": "Operating Activities", "Item": "Changes in working capital", "Amount": f"{int(working_capital)}"})
    rows.append({"Category": "Cash from Operating Activities", "Item": "", "Amount": f"{int(cash_from_operating)}"})
    rows.append({"Category": "", "Item": "", "Amount": ""})  # Empty row
    
    # Investing Activities
    purchase_assets = investing.get("purchase_of_assets", 0)
    sale_assets = investing.get("sale_of_assets", 0)
    cash_from_investing = investing.get("cash_from_investing_activities", sale_assets - purchase_assets)
    
    rows.append({"Category": "Investing Activities", "Item": "Purchase of assets", "Amount": f"{int(-purchase_assets)}"})
    rows.append({"Category": "Investing Activities", "Item": "Sale of assets", "Amount": f"{int(sale_assets)}"})
    rows.append({"Category": "Cash from Investing Activities", "Item": "", "Amount": f"{int(cash_from_investing)}"})
    rows.append({"Category": "", "Item": "", "Amount": ""})  # Empty row
    
    # Financing Activities
    loan_received = financing.get("loan_received", 0)
    loan_repayment = financing.get("loan_repayment", 0)
    equity_raised = financing.get("equity_raised", 0)
    dividends_paid = financing.get("dividends_paid", 0)
    cash_from_financing = financing.get("cash_from_financing_activities", loan_received - loan_repayment + equity_raised - dividends_paid)
    
    rows.append({"Category": "Financing Activities", "Item": "Loan received", "Amount": f"{int(loan_received)}"})
    rows.append({"Category": "Financing Activities", "Item": "Loan repayment", "Amount": f"{int(-loan_repayment)}"})
    rows.append({"Category": "Financing Activities", "Item": "Equity raised", "Amount": f"{int(equity_raised)}"})
    rows.append({"Category": "Financing Activities", "Item": "Dividends paid", "Amount": f"{int(-dividends_paid)}"})
    rows.append({"Category": "Cash from Financing Activities", "Item": "", "Amount": f"{int(cash_from_financing)}"})
    rows.append({"Category": "", "Item": "", "Amount": ""})  # Empty row
    
    # Summary
    net_increase = cash_flow_data.get("net_increase_in_cash", cash_from_operating + cash_from_investing + cash_from_financing)
    opening_balance = cash_flow_data.get("opening_cash_balance", 0)
    closing_balance = cash_flow_data.get("closing_cash_balance", opening_balance + net_increase)
    
    rows.append({"Category": "Net Increase in Cash", "Item": "", "Amount": f"{int(net_increase)}"})
    rows.append({"Category": "Opening Cash Balance", "Item": "", "Amount": f"{int(opening_balance)}"})
    rows.append({"Category": "Closing Cash Balance", "Item": "", "Amount": f"{int(closing_balance)}"})
    
    writer = csv.DictWriter(output, fieldnames=["Category", "Item", "Amount"])
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()

