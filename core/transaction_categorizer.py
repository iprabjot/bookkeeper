"""
Transaction Categorization using CrewAI
Categorizes bank statement transactions into accounting categories
"""
import json
import os
import logging
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
from crewai import Agent, Task, Crew

load_dotenv()

logger = logging.getLogger(__name__)

# Try to import LLM for AI-based categorization
AI_CATEGORIZATION_AVAILABLE = False
try:
    from crewai import LLM
    if os.getenv("OPENAI_API_KEY"):
        AI_CATEGORIZATION_AVAILABLE = True
except ImportError:
    pass


# Category taxonomy mapping
CATEGORY_TAXONOMY = {
    # Income categories
    "INC-PRD-DOM": "Product Sales — Domestic",
    "INC-PRD-EXP": "Product Sales — Export",
    "INC-SVC-TM": "Service Revenue — Time & Materials",
    "INC-SVC-FP": "Service Revenue — Fixed-price",
    "INC-SUB": "Subscription/Recurring Revenue",
    "INC-SAAS": "SaaS / Platform Fees",
    "INC-DISC-C": "Sales Discounts (contra)",
    "INC-RET-C": "Sales Returns & Allowances (contra)",
    "INC-COMM": "Commission Income",
    "INC-ROYALTY": "Royalty Income",
    "INC-RENT": "Rental Income (operating)",
    "INC-AFF": "Affiliate / Referral Fees",
    "INC-INT": "Interest Income",
    "INC-DIV": "Dividend Income",
    "INC-ASSET-GAIN": "Gain on Sale of Assets",
    "INC-FX-GAIN": "Foreign Exchange Gains",
    "INC-INVEST": "Investment Income",
    "INC-GRANT": "Grants / Subsidies",
    "INC-EXCEPT": "One-time / Exceptional",
    "INC-UNCAT": "Uncategorized Income",
    
    # COGS categories
    "COGS-RAW": "Raw Materials / Components",
    "COGS-LABOR": "Direct Labor (manufacturing)",
    "COGS-MOH": "Manufacturing Overhead",
    "COGS-FREIGHT": "Freight-in / Import Duty",
    "COGS-PACK": "Packaging & Shipping",
    "COGS-INV-ADJ": "Inventory Adjustments",
    "COGS-DISC-C": "Purchase Discounts (contra)",
    "COGS-UNCAT": "Uncategorized COGS",
    
    # Operating Expenses - Marketing
    "EXP-MKT-ADS": "Advertising & Promotion",
    "EXP-MKT-COMM": "Sales Commissions",
    "EXP-MKT-EVENT": "Events / Sponsorships",
    "EXP-MKT-SW": "Marketing Software",
    
    # Operating Expenses - G&A
    "EXP-GA-SAL": "Salaries & Wages (Admin)",
    "EXP-GA-PAYROLL": "Payroll Taxes & Benefits",
    "EXP-GA-RENT": "Office Rent & Lease",
    "EXP-GA-UTIL": "Utilities",
    "EXP-GA-SUPPLY": "Office Supplies",
    "EXP-GA-INS": "Insurance (General)",
    "EXP-GA-PROF": "Professional Fees",
    "EXP-GA-TRAVEL": "Travel & Entertainment",
    "EXP-GA-HR": "Recruitment / Training",
    "EXP-GA-BANK": "Bank Charges & Merchant Fees",
    "EXP-GA-COMM": "Communications",
    "EXP-GA-PENDING": "General & Administrative — Pending Classification",
    
    # Operating Expenses - IT
    "EXP-IT-SW": "Software Licenses",
    "EXP-IT-CLOUD": "Cloud Hosting / CDN",
    "EXP-IT-PG": "Payment Gateway Fees",
    "EXP-IT-DEVOPS": "Platform / DevOps",
    "EXP-IT-PENDING": "IT Pending Classification",
    
    # Direct Expenses
    "EXP-DIR-CONTR": "Contractor Payments",
    "EXP-DIR-SUB": "Subcontractor Costs",
    "EXP-DIR-LIC": "License/Royalty Costs",
    
    # Financial Expenses
    "EXP-FIN-INT": "Interest Expense",
    "EXP-FIN-BANK": "Bank Charges",
    "EXP-FIN-FX": "Foreign Exchange Loss",
    
    # Taxation
    "EXP-TAX-INC": "Income Tax Expense",
    "EXP-TAX-GST": "GST/VAT Payment",
    "EXP-TAX-PT": "Professional Tax",
    
    # Other
    "EXP-OTH-CSR": "Donations & CSR",
    "EXP-OTH-MEM": "Memberships & Subscriptions",
    "EXP-OTH-MISC": "Miscellaneous",
    "EXP-UNCAT": "Uncategorized Expense",
    
    # Non-P&L
    "TRANSFER-INTERNAL": "Internal Transfer",
    "TRANSFER-PENDING": "Potential Internal Transfer",
    "UNCATEGORIZED": "Fully Uncategorized — Manual Review Required",
}

# Category paths for full hierarchy
CATEGORY_PATHS = {
    "INC-PRD-DOM": "Income > Operating Revenue > Product Sales — Domestic",
    "INC-PRD-EXP": "Income > Operating Revenue > Product Sales — Export",
    "INC-SVC-TM": "Income > Operating Revenue > Service Revenue — Time & Materials",
    "INC-SVC-FP": "Income > Operating Revenue > Service Revenue — Fixed-price",
    "INC-SUB": "Income > Operating Revenue > Subscription/Recurring Revenue",
    "INC-SAAS": "Income > Operating Revenue > SaaS / Platform Fees",
    "EXP-IT-CLOUD": "Expense > Operating Expenses > IT/Product > Cloud Hosting / CDN",
    "EXP-GA-COMM": "Expense > Operating Expenses > G&A > Communications",
    "EXP-GA-UTIL": "Expense > Operating Expenses > G&A > Utilities",
    "EXP-GA-RENT": "Expense > Operating Expenses > G&A > Office Rent & Lease",
    "EXP-GA-SAL": "Expense > Operating Expenses > G&A > Salaries & Wages (Admin)",
    "EXP-GA-PAYROLL": "Expense > Operating Expenses > G&A > Payroll Taxes & Benefits",
    "EXP-GA-TRAVEL": "Expense > Operating Expenses > G&A > Travel & Entertainment",
    "EXP-GA-PROF": "Expense > Operating Expenses > G&A > Professional Fees",
    "EXP-GA-SUPPLY": "Expense > Operating Expenses > G&A > Office Supplies",
    "EXP-GA-INS": "Expense > Operating Expenses > G&A > Insurance (General)",
    "EXP-GA-BANK": "Expense > Operating Expenses > G&A > Bank Charges & Merchant Fees",
    "EXP-IT-SW": "Expense > Operating Expenses > IT/Product > Software Licenses",
    "EXP-IT-PG": "Expense > Operating Expenses > IT/Product > Payment Gateway Fees",
    "EXP-DIR-CONTR": "Expense > Direct Expenses > Contractor Payments",
    "COGS-RAW": "Expense > Cost of Goods Sold > Raw Materials / Components",
    "EXP-OTH-MISC": "Expense > Other Expenses > Miscellaneous",
    "EXP-UNCAT": "Expense > Uncategorized > Pending Review",
    "INC-UNCAT": "Income > Uncategorized > Pending Review",
    "TRANSFER-INTERNAL": "Non-P&L > Internal Transfer",
    "UNCATEGORIZED": "Uncategorized > Pending Manual Review",
}


def get_category_path(category_code: str) -> str:
    """Get full category path for a category code"""
    return CATEGORY_PATHS.get(category_code, f"Category > {CATEGORY_TAXONOMY.get(category_code, category_code)}")


def categorize_transaction_with_ai(transaction: Dict[str, Any]) -> Dict[str, Any]:
    """
    Categorize a single transaction using AI
    
    Args:
        transaction: Transaction dict with fields:
            - transaction_id (str)
            - date (str, YYYY-MM-DD)
            - amount (float, positive for credits, negative for debits)
            - bank_description (str)
            - is_reconciled (bool)
            - reconciled_invoice (dict or None) with:
                - invoice_number (str or None)
                - invoice_description (str or None)
                - customer_vendor_name (str or None)
                - line_items (list or None)
    
    Returns:
        Dict with categorization results
    """
    if not AI_CATEGORIZATION_AVAILABLE:
        logger.warning("AI categorization not available, using rule-based fallback")
        return categorize_transaction_rule_based(transaction)
    
    try:
        from crewai import LLM
        
        llm = LLM(
            model=os.getenv("OPENAI_MODEL_NAME", "openai/gpt-4o-mini"),
            base_url=os.getenv("OPENAI_API_BASE", "https://openrouter.ai/api/v1"),
            api_key=os.getenv("OPENAI_API_KEY"),
            temperature=0.0
        )
        
        # Build prompt from the comprehensive system prompt
        prompt = build_categorization_prompt(transaction)
        
        response = llm.call(prompt)
        
        # Parse JSON response
        response_text = str(response)
        
        # Extract JSON from response (might have markdown code blocks)
        import re
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            result = json.loads(json_str)
            
            # Validate and enhance result
            category_code = result.get("category_code", "UNCATEGORIZED")
            category_name = CATEGORY_TAXONOMY.get(category_code, category_code)
            category_path = get_category_path(category_code)
            
            return {
                "transaction_id": transaction.get("transaction_id"),
                "category_code": category_code,
                "category_name": category_name,
                "category_path": category_path,
                "confidence": result.get("confidence", "MEDIUM"),
                "reasoning": result.get("reasoning", ""),
                "requires_review": result.get("requires_review", False),
                "review_reason": result.get("review_reason"),
                "alternative_categories": result.get("alternative_categories"),
            }
        else:
            logger.warning(f"AI response did not contain valid JSON: {response_text[:200]}")
            return categorize_transaction_rule_based(transaction)
            
    except Exception as e:
        error_str = str(e).lower()
        
        # Check for rate limit errors
        if "rate limit" in error_str or "429" in error_str or "too many requests" in error_str:
            logger.warning(f"Rate limit exceeded for transaction {transaction.get('transaction_id')}: {e}")
            # Return error so caller can handle retry
            return {
                "transaction_id": transaction.get("transaction_id"),
                "error": True,
                "error_type": "RATE_LIMIT",
                "error_message": str(e),
            }
        
        logger.error(f"AI categorization failed: {e}", exc_info=True)
        return categorize_transaction_rule_based(transaction)


def build_categorization_prompt(transaction: Dict[str, Any]) -> str:
    """Build the comprehensive categorization prompt"""
    
    # Format transaction data
    transaction_json = json.dumps(transaction, indent=2)
    
    prompt = f"""You are a Transaction Categorization Agent for an AI-powered accounting platform designed for Indian SMEs. 
Your task is to accurately categorize bank statement transactions into the appropriate accounting categories.

## Input Transaction

{transaction_json}

## Category Taxonomy

### INCOME (Credit Transactions)
- INC-PRD-DOM: Product Sales — Domestic
- INC-PRD-EXP: Product Sales — Export  
- INC-SVC-TM: Service Revenue — Time & Materials
- INC-SVC-FP: Service Revenue — Fixed-price
- INC-SUB: Subscription/Recurring Revenue
- INC-SAAS: SaaS / Platform Fees
- INC-COMM: Commission Income
- INC-RENT: Rental Income (operating)
- INC-INT: Interest Income
- INC-DIV: Dividend Income
- INC-UNCAT: Uncategorized Income

### EXPENSES (Debit Transactions)

**Operating Expenses - G&A:**
- EXP-GA-SAL: Salaries & Wages (Admin)
- EXP-GA-PAYROLL: Payroll Taxes & Benefits
- EXP-GA-RENT: Office Rent & Lease
- EXP-GA-UTIL: Utilities
- EXP-GA-SUPPLY: Office Supplies
- EXP-GA-INS: Insurance (General)
- EXP-GA-PROF: Professional Fees
- EXP-GA-TRAVEL: Travel & Entertainment
- EXP-GA-COMM: Communications
- EXP-GA-BANK: Bank Charges & Merchant Fees

**Operating Expenses - IT:**
- EXP-IT-SW: Software Licenses
- EXP-IT-CLOUD: Cloud Hosting / CDN
- EXP-IT-PG: Payment Gateway Fees
- EXP-IT-DEVOPS: Platform / DevOps

**Direct Expenses:**
- EXP-DIR-CONTR: Contractor Payments
- EXP-DIR-SUB: Subcontractor Costs

**COGS:**
- COGS-RAW: Raw Materials / Components
- COGS-LABOR: Direct Labor (manufacturing)
- COGS-FREIGHT: Freight-in / Import Duty

**Financial:**
- EXP-FIN-INT: Interest Expense
- EXP-FIN-BANK: Bank Charges

**Taxation:**
- EXP-TAX-INC: Income Tax Expense
- EXP-TAX-GST: GST/VAT Payment

**Other:**
- EXP-OTH-MISC: Miscellaneous
- EXP-UNCAT: Uncategorized Expense

**Non-P&L:**
- TRANSFER-INTERNAL: Internal Transfer
- UNCATEGORIZED: Fully Uncategorized

## Instructions

1. For RECONCILED transactions (is_reconciled = true):
   - Use invoice line items and description as primary signal
   - Use bank narration as secondary validation
   - Use customer/vendor name for context

2. For UNRECONCILED transactions (is_reconciled = false):
   - **CRITICAL: Look for explicit categorization hints in bank_description/narration:**
     * "INVOICE PAYMENT", "INVOICE PAY", "PAYMENT FOR INVOICE" → Likely vendor payment (EXP-DIR-CONTR or EXP-DIR-SUB)
     * "DIESEL PAYMENT", "FUEL PAYMENT", "PETROL", "DIESEL" → EXP-GA-TRAVEL (vehicle fuel)
     * "SALARY", "SALARY PAYMENT", "PAYROLL" → EXP-GA-SAL or EXP-GA-PAYROLL
     * "RENT", "RENT PAYMENT" → EXP-GA-RENT
     * "UTILITY", "ELECTRICITY", "WATER", "GAS", "POWER" → EXP-GA-UTIL
     * "INTEREST", "INTEREST PAYMENT" → EXP-FIN-INT
     * "GST", "TAX", "TAX PAYMENT", "INCOME TAX" → EXP-TAX-GST or EXP-TAX-INC
     * "SUBSCRIPTION", "SaaS", "SOFTWARE" → EXP-IT-SW or INC-SUB
     * "COMMISSION", "COMMISSION INCOME" → INC-COMM
     * "SALES", "REVENUE", "INCOME", "PAYMENT RECEIVED" → INC-* categories
     * "RAW MATERIAL", "MATERIAL", "COMPONENT" → COGS-RAW
     * "FREIGHT", "SHIPPING", "LOGISTICS" → COGS-FREIGHT or EXP-GA-SUPPLY
   - Parse bank description for merchant names, UPI IDs, NEFT/RTGS references
   - Identify common patterns (UPI, NEFT, RTGS, IMPS, POS, etc.)
   - Apply amount-based heuristics

3. Common Indian merchant patterns:
   - SWIGGY, ZOMATO → EXP-GA-TRAVEL (meals)
   - AMAZON, FLIPKART → EXP-GA-SUPPLY or COGS-RAW
   - UBER, OLA → EXP-GA-TRAVEL
   - AIRTEL, JIO, VI → EXP-GA-COMM
   - BESCOM, TATAPOWER → EXP-GA-UTIL
   - AWS, GOOGLE CLOUD → EXP-IT-CLOUD
   - GITHUB, ATLASSIAN → EXP-IT-DEVOPS
   - ZOHO, FRESHWORKS → EXP-IT-SW
   - RAZORPAY, CASHFREE → EXP-IT-PG (if debit) or INC-* (if credit)

4. Confidence levels:
   - HIGH: Clear invoice line items, explicit payment purpose in narration (e.g., "INVOICE PAYMENT", "DIESEL PAYMENT"), or unambiguous merchant pattern
   - MEDIUM: Partial match or generic description
   - LOW: Vague narration, ambiguous purpose

5. Flag for review if:
   - Confidence is LOW
   - Amount > ₹1,00,000
   - Transaction is ambiguous
   - No explicit categorization hint found in narration AND merchant pattern is unclear

## Output Format

Return ONLY valid JSON in this exact format:

{{
  "transaction_id": "string",
  "category_code": "string (from taxonomy above)",
  "category_name": "string (human-readable)",
  "category_path": "string (full hierarchy)",
  "confidence": "HIGH | MEDIUM | LOW",
  "reasoning": "string (brief explanation)",
  "requires_review": boolean,
  "review_reason": "string | null",
  "alternative_categories": [
    {{
      "category_code": "string",
      "category_name": "string",
      "confidence": number (0-1)
    }}
  ] | null
}}

Return ONLY the JSON object, no other text.
"""
    
    return prompt


def categorize_transaction_rule_based(transaction: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fallback rule-based categorization when AI is not available
    """
    description = (transaction.get("bank_description") or "").upper()
    amount = transaction.get("amount", 0)
    is_reconciled = transaction.get("is_reconciled", False)
    reconciled_invoice = transaction.get("reconciled_invoice")
    
    # Determine if credit or debit
    is_credit = amount > 0
    
    # Check for internal transfers
    if any(keyword in description for keyword in ["SELF TRANSFER", "OWN ACCOUNT", "INTERNAL"]):
        return {
            "transaction_id": transaction.get("transaction_id"),
            "category_code": "TRANSFER-INTERNAL",
            "category_name": "Internal Transfer",
            "category_path": "Non-P&L > Internal Transfer",
            "confidence": "HIGH",
            "reasoning": "Narration indicates internal transfer",
            "requires_review": False,
            "review_reason": None,
            "alternative_categories": None,
        }
    
    # If reconciled, try to infer from invoice
    if is_reconciled and reconciled_invoice:
        invoice_desc = (reconciled_invoice.get("invoice_description") or "").upper()
        vendor_name = (reconciled_invoice.get("customer_vendor_name") or "").upper()
        
        # Check for service revenue patterns
        if any(keyword in invoice_desc for keyword in ["SERVICE", "CONSULTING", "DEVELOPMENT", "SUPPORT"]):
            return {
                "transaction_id": transaction.get("transaction_id"),
                "category_code": "INC-SVC-TM" if is_credit else "EXP-DIR-CONTR",
                "category_name": "Service Revenue — Time & Materials" if is_credit else "Contractor Payments",
                "category_path": get_category_path("INC-SVC-TM" if is_credit else "EXP-DIR-CONTR"),
                "confidence": "MEDIUM",
                "reasoning": "Invoice description suggests service transaction",
                "requires_review": False,
                "review_reason": None,
                "alternative_categories": None,
            }
    
    # Pattern matching for common merchants
    merchant_patterns = {
        # Utilities
        ("BESCOM", "TATA POWER", "TATAPOWER", "ADANI", "TORRENT"): "EXP-GA-UTIL",
        # Communications
        ("AIRTEL", "JIO", "VI ", "VODAFONE", "IDEA"): "EXP-GA-COMM",
        # Travel
        ("UBER", "OLA", "SWIGGY", "ZOMATO"): "EXP-GA-TRAVEL",
        # Cloud/IT
        ("AWS", "AMAZON WEB SERVICES", "GOOGLE CLOUD", "AZURE", "DIGITALOCEAN"): "EXP-IT-CLOUD",
        ("GITHUB", "GITLAB", "ATLASSIAN", "JIRA"): "EXP-IT-DEVOPS",
        ("ZOHO", "FRESHWORKS", "MICROSOFT", "ADOBE"): "EXP-IT-SW",
        # Payment Gateways
        ("RAZORPAY", "CASHFREE", "PAYU", "STRIPE"): "EXP-IT-PG" if not is_credit else "INC-SAAS",
        # E-commerce
        ("AMAZON", "FLIPKART"): "EXP-GA-SUPPLY",
        # Insurance
        ("LIC", "HDFC ERGO", "ICICI LOMBARD", "BAJAJ ALLIANZ"): "EXP-GA-INS",
        # Salary
        ("SALARY", "PAYROLL", "SAL"): "EXP-GA-SAL",
        # GST/Tax
        ("GST", "GSTN", "INCOMETAX", "TDS"): "EXP-TAX-GST" if "GST" in description else "EXP-TAX-INC",
    }
    
    for patterns, category in merchant_patterns.items():
        if any(pattern in description for pattern in patterns):
            return {
                "transaction_id": transaction.get("transaction_id"),
                "category_code": category,
                "category_name": CATEGORY_TAXONOMY.get(category, category),
                "category_path": get_category_path(category),
                "confidence": "MEDIUM",
                "reasoning": f"Matched merchant pattern in bank narration",
                "requires_review": abs(amount) > 100000,
                "review_reason": "Large amount" if abs(amount) > 100000 else None,
                "alternative_categories": None,
            }
    
    # Default categorization
    if is_credit:
        category_code = "INC-UNCAT"
        category_name = "Uncategorized Income"
    else:
        category_code = "EXP-UNCAT"
        category_name = "Uncategorized Expense"
    
    return {
        "transaction_id": transaction.get("transaction_id"),
        "category_code": category_code,
        "category_name": category_name,
        "category_path": get_category_path(category_code),
        "confidence": "LOW",
        "reasoning": "No clear pattern matched, requires manual review",
        "requires_review": True,
        "review_reason": "Unclear transaction purpose",
        "alternative_categories": None,
    }


def categorize_transactions_batch(transactions: List[Dict[str, Any]], batch_size: int = 10) -> List[Dict[str, Any]]:
    """
    Categorize multiple transactions in batch using a single API call
    
    Args:
        transactions: List of transaction dicts
        batch_size: Number of transactions to process in one API call (default: 10)
    
    Returns:
        List of categorization results
    """
    if not transactions:
        return []
    
    # For very large batches, use rule-based to avoid rate limits
    if len(transactions) > 100:
        logger.info(f"Large batch ({len(transactions)} transactions). Using rule-based categorization.")
        return [categorize_transaction_rule_based(txn) for txn in transactions]
    
    import time
    
    results = []
    
    # Process in batches to avoid token limits and rate limits
    for i in range(0, len(transactions), batch_size):
        batch = transactions[i:i + batch_size]
        batch_num = i//batch_size + 1
        logger.info(f"Processing batch {batch_num} ({len(batch)} transactions)")
        
        # Add delay between batches to avoid rate limits (except for first batch)
        if i > 0:
            delay = 2.0  # 2 seconds between batches
            logger.debug(f"Waiting {delay}s before processing next batch...")
            time.sleep(delay)
        
        try:
            # Try batch API call first
            batch_results = categorize_transactions_batch_api(batch)
            results.extend(batch_results)
            logger.info(f"Batch {batch_num} completed successfully")
        except Exception as e:
            logger.warning(f"Batch {batch_num} categorization failed, falling back to rule-based: {e}")
            # Fallback to rule-based for this batch
            for txn in batch:
                results.append(categorize_transaction_rule_based(txn))
    
    return results


def categorize_transactions_batch_api(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Categorize multiple transactions in a single API call
    
    Args:
        transactions: List of transaction dicts (max 10-20 recommended)
    
    Returns:
        List of categorization results
    """
    if not AI_CATEGORIZATION_AVAILABLE:
        return [categorize_transaction_rule_based(txn) for txn in transactions]
    
    try:
        from crewai import LLM
        
        llm = LLM(
            model=os.getenv("OPENAI_MODEL_NAME", "openai/gpt-4o-mini"),
            base_url=os.getenv("OPENAI_API_BASE", "https://openrouter.ai/api/v1"),
            api_key=os.getenv("OPENAI_API_KEY"),
            temperature=0.0
        )
        
        # Build batch prompt
        prompt = build_batch_categorization_prompt(transactions)
        
        response = llm.call(prompt)
        
        # Parse JSON response
        response_text = str(response)
        
        # Extract JSON array from response
        import re
        json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            batch_results = json.loads(json_str)
            
            # Validate and enhance results
            results = []
            for i, result in enumerate(batch_results):
                if result.get("error"):
                    # If batch failed, use rule-based for this transaction
                    results.append(categorize_transaction_rule_based(transactions[i]))
                else:
                    category_code = result.get("category_code", "UNCATEGORIZED")
                    category_name = CATEGORY_TAXONOMY.get(category_code, category_code)
                    category_path = get_category_path(category_code)
                    
                    results.append({
                        "transaction_id": result.get("transaction_id") or transactions[i].get("transaction_id"),
                        "category_code": category_code,
                        "category_name": category_name,
                        "category_path": category_path,
                        "confidence": result.get("confidence", "MEDIUM"),
                        "reasoning": result.get("reasoning", ""),
                        "requires_review": result.get("requires_review", False),
                        "review_reason": result.get("review_reason"),
                        "alternative_categories": result.get("alternative_categories"),
                    })
            
            return results
        else:
            logger.warning("Batch API response did not contain valid JSON array, using rule-based fallback")
            return [categorize_transaction_rule_based(txn) for txn in transactions]
            
    except Exception as e:
        error_str = str(e).lower()
        
        # Check for rate limit errors
        if "rate limit" in error_str or "429" in error_str or "too many requests" in error_str:
            logger.warning(f"Rate limit exceeded for batch categorization: {e}")
            # Use rule-based fallback
            return [categorize_transaction_rule_based(txn) for txn in transactions]
        
        logger.error(f"Batch AI categorization failed: {e}", exc_info=True)
        return [categorize_transaction_rule_based(txn) for txn in transactions]


def build_batch_categorization_prompt(transactions: List[Dict[str, Any]]) -> str:
    """Build prompt for batch categorization"""
    
    transactions_json = json.dumps(transactions, indent=2, default=str)
    
    prompt = f"""You are a Transaction Categorization Agent for an AI-powered accounting platform designed for Indian SMEs. 
Your task is to accurately categorize bank statement transactions into the appropriate accounting categories.

## Input Transactions (Batch)

{transactions_json}

## Category Taxonomy

### INCOME (Credit Transactions)
- INC-PRD-DOM: Product Sales — Domestic
- INC-PRD-EXP: Product Sales — Export  
- INC-SVC-TM: Service Revenue — Time & Materials
- INC-SVC-FP: Service Revenue — Fixed-price
- INC-SUB: Subscription/Recurring Revenue
- INC-SAAS: SaaS / Platform Fees
- INC-COMM: Commission Income
- INC-RENT: Rental Income (operating)
- INC-INT: Interest Income
- INC-DIV: Dividend Income
- INC-UNCAT: Uncategorized Income

### EXPENSES (Debit Transactions)

**Operating Expenses - G&A:**
- EXP-GA-SAL: Salaries & Wages (Admin)
- EXP-GA-PAYROLL: Payroll Taxes & Benefits
- EXP-GA-RENT: Office Rent & Lease
- EXP-GA-UTIL: Utilities
- EXP-GA-SUPPLY: Office Supplies
- EXP-GA-INS: Insurance (General)
- EXP-GA-PROF: Professional Fees
- EXP-GA-TRAVEL: Travel & Entertainment
- EXP-GA-COMM: Communications
- EXP-GA-BANK: Bank Charges & Merchant Fees

**Operating Expenses - IT:**
- EXP-IT-SW: Software Licenses
- EXP-IT-CLOUD: Cloud Hosting / CDN
- EXP-IT-PG: Payment Gateway Fees
- EXP-IT-DEVOPS: Platform / DevOps

**Direct Expenses:**
- EXP-DIR-CONTR: Contractor Payments
- EXP-DIR-SUB: Subcontractor Costs

**COGS:**
- COGS-RAW: Raw Materials / Components
- COGS-LABOR: Direct Labor (manufacturing)
- COGS-FREIGHT: Freight-in / Import Duty

**Financial:**
- EXP-FIN-INT: Interest Expense
- EXP-FIN-BANK: Bank Charges

**Taxation:**
- EXP-TAX-INC: Income Tax Expense
- EXP-TAX-GST: GST/VAT Payment

**Other:**
- EXP-OTH-MISC: Miscellaneous
- EXP-UNCAT: Uncategorized Expense

**Non-P&L:**
- TRANSFER-INTERNAL: Internal Transfer
- UNCATEGORIZED: Fully Uncategorized

## Instructions

1. For RECONCILED transactions (is_reconciled = true):
   - Use invoice line items and description as primary signal
   - Use bank narration as secondary validation
   - Use customer/vendor name for context

2. For UNRECONCILED transactions (is_reconciled = false):
   - **CRITICAL: Look for explicit categorization hints in bank_description/narration:**
     * "INVOICE PAYMENT", "INVOICE PAY", "PAYMENT FOR INVOICE" → Likely vendor payment (EXP-DIR-CONTR or EXP-DIR-SUB)
     * "DIESEL PAYMENT", "FUEL PAYMENT", "PETROL", "DIESEL" → EXP-GA-TRAVEL (vehicle fuel)
     * "SALARY", "SALARY PAYMENT", "PAYROLL" → EXP-GA-SAL or EXP-GA-PAYROLL
     * "RENT", "RENT PAYMENT" → EXP-GA-RENT
     * "UTILITY", "ELECTRICITY", "WATER", "GAS", "POWER" → EXP-GA-UTIL
     * "INTEREST", "INTEREST PAYMENT" → EXP-FIN-INT
     * "GST", "TAX", "TAX PAYMENT", "INCOME TAX" → EXP-TAX-GST or EXP-TAX-INC
     * "SUBSCRIPTION", "SaaS", "SOFTWARE" → EXP-IT-SW or INC-SUB
     * "COMMISSION", "COMMISSION INCOME" → INC-COMM
     * "SALES", "REVENUE", "INCOME", "PAYMENT RECEIVED" → INC-* categories
     * "RAW MATERIAL", "MATERIAL", "COMPONENT" → COGS-RAW
     * "FREIGHT", "SHIPPING", "LOGISTICS" → COGS-FREIGHT or EXP-GA-SUPPLY
   - Parse bank description for merchant names, UPI IDs, NEFT/RTGS references
   - Identify common patterns (UPI, NEFT, RTGS, IMPS, POS, etc.)
   - Apply amount-based heuristics

3. Common Indian merchant patterns:
   - SWIGGY, ZOMATO → EXP-GA-TRAVEL (meals)
   - AMAZON, FLIPKART → EXP-GA-SUPPLY or COGS-RAW
   - UBER, OLA → EXP-GA-TRAVEL
   - AIRTEL, JIO, VI → EXP-GA-COMM
   - BESCOM, TATAPOWER → EXP-GA-UTIL
   - AWS, GOOGLE CLOUD → EXP-IT-CLOUD
   - GITHUB, ATLASSIAN → EXP-IT-DEVOPS
   - ZOHO, FRESHWORKS → EXP-IT-SW
   - RAZORPAY, CASHFREE → EXP-IT-PG (if debit) or INC-* (if credit)

4. Confidence levels:
   - HIGH: Clear invoice line items, explicit payment purpose in narration (e.g., "INVOICE PAYMENT", "DIESEL PAYMENT"), or unambiguous merchant pattern
   - MEDIUM: Partial match or generic description
   - LOW: Vague narration, ambiguous purpose

5. Flag for review if:
   - Confidence is LOW
   - Amount > ₹1,00,000
   - Transaction is ambiguous
   - No explicit categorization hint found in narration AND merchant pattern is unclear

## Output Format

Return ONLY valid JSON array in this exact format:

[
  {{
    "transaction_id": "string",
    "category_code": "string (from taxonomy above)",
    "category_name": "string (human-readable)",
    "category_path": "string (full hierarchy)",
    "confidence": "HIGH | MEDIUM | LOW",
    "reasoning": "string (brief explanation)",
    "requires_review": boolean,
    "review_reason": "string | null",
    "alternative_categories": [
      {{
        "category_code": "string",
        "category_name": "string",
        "confidence": number (0-1)
      }}
    ] | null
  }},
  ...
]

Return ONLY the JSON array, no other text. Process all {len(transactions)} transactions.
"""
    
    return prompt

