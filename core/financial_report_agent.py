"""
Financial Report Agent Service
Uses CrewAI to generate Profit & Loss and Cash Flow statements from trial balance data
"""
import os
import json
import re
import logging
from typing import Dict, Optional, List
from datetime import datetime
from dotenv import load_dotenv
from crewai import Crew, Agent, Task, LLM
import yaml

load_dotenv()

logger = logging.getLogger(__name__)

# Check if AI is available
AI_AVAILABLE = bool(os.getenv("OPENAI_API_KEY"))


def _load_reporting_agent() -> Optional[Agent]:
    """Load the reporting agent from YAML file"""
    try:
        agent_file = os.path.join(os.path.dirname(__file__), "..", "agents", "reporting_agent.yaml")
        if not os.path.exists(agent_file):
            logger.error(f"Agent file not found: {agent_file}")
            return None
        
        with open(agent_file, 'r') as f:
            data = yaml.safe_load(f)
        
        llm = LLM(
            model=os.getenv("OPENAI_MODEL_NAME", "openai/gpt-4o-mini"),
            base_url=os.getenv("OPENAI_API_BASE", "https://openrouter.ai/api/v1"),
            api_key=os.getenv("OPENAI_API_KEY"),
            temperature=0.0
        )
        
        agent_obj = Agent(
            name=data["agent"]["name"],
            role=data["agent"]["role"],
            goal=data["agent"]["goal"],
            backstory=data["agent"].get("backstory", ""),
            verbose=False,  # Set to False to reduce noise in logs
            allow_delegation=data["agent"].get("allow_delegation", False),
            llm=llm
        )
        
        return agent_obj
    except Exception as e:
        logger.error(f"Failed to load reporting agent: {e}", exc_info=True)
        return None


def _load_financial_statements_task(agent: Agent) -> Optional[Task]:
    """Load the financial statements task from YAML file"""
    try:
        task_file = os.path.join(os.path.dirname(__file__), "..", "tasks", "generate_financial_statements.yaml")
        if not os.path.exists(task_file):
            logger.error(f"Task file not found: {task_file}")
            return None
        
        with open(task_file, 'r') as f:
            data = yaml.safe_load(f)
        
        task_obj = Task(
            description=data.get("description", ""),
            agent=agent,
            expected_output=data.get("expected_output", "")
        )
        
        return task_obj
    except Exception as e:
        logger.error(f"Failed to load financial statements task: {e}", exc_info=True)
        return None


def _parse_json_from_response(response_text: str) -> Optional[Dict]:
    """Extract JSON from AI agent response"""
    try:
        # Try to find JSON in markdown code blocks
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        
        # Try to find JSON object directly
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        
        # Try parsing the entire response as JSON
        return json.loads(response_text)
    except Exception as e:
        logger.error(f"Failed to parse JSON from response: {e}")
        logger.debug(f"Response text: {response_text[:500]}")
        return None


def _format_trial_balance_for_agent(trial_balance_data: Dict) -> str:
    """Format trial balance data as a readable string for the AI agent"""
    if isinstance(trial_balance_data, str):
        try:
            trial_balance_data = json.loads(trial_balance_data)
        except:
            return str(trial_balance_data)
    
    # Extract account balances from journal entries
    account_balances = {}
    entries = trial_balance_data.get("journal_entries", [])
    
    for entry in entries:
        for line in entry.get("lines", []):
            account_name = line.get("account_name", "")
            debit = line.get("debit", 0)
            credit = line.get("credit", 0)
            
            if account_name not in account_balances:
                account_balances[account_name] = {"debit": 0, "credit": 0}
            
            account_balances[account_name]["debit"] += debit
            account_balances[account_name]["credit"] += credit
    
    # Format as readable text
    lines = ["Trial Balance:"]
    for account_name in sorted(account_balances.keys()):
        debit = account_balances[account_name]["debit"]
        credit = account_balances[account_name]["credit"]
        balance = debit - credit
        lines.append(f"  {account_name}: Debit={debit}, Credit={credit}, Balance={balance}")
    
    return "\n".join(lines)


def _format_bank_transactions_for_agent(bank_transactions: List[Dict]) -> str:
    """Format bank transactions as a readable string for the AI agent"""
    if not bank_transactions:
        return "No bank transactions available."
    
    lines = ["Bank Transactions:"]
    for txn in bank_transactions:
        date_str = txn.get("date", "")
        if isinstance(date_str, datetime):
            date_str = date_str.isoformat()
        amount = txn.get("amount", 0)
        txn_type = txn.get("type", "")
        description = txn.get("description", "")
        lines.append(f"  {date_str}: {txn_type} ₹{amount} - {description}")
    
    return "\n".join(lines)


def generate_profit_loss_statement(
    trial_balance_data: Dict,
    period_start: Optional[str] = None,
    period_end: Optional[str] = None
) -> Optional[Dict]:
    """
    Generate Profit & Loss Statement using AI agent
    
    Args:
        trial_balance_data: Trial balance data (from journal entries)
        period_start: Start date of reporting period (ISO format)
        period_end: End date of reporting period (ISO format)
    
    Returns:
        Dictionary with P&L data, or None if generation fails
    """
    if not AI_AVAILABLE:
        logger.warning("OpenAI API key not configured. Cannot generate P&L statement.")
        return None
    
    try:
        agent = _load_reporting_agent()
        if not agent:
            return None
        
        task = _load_financial_statements_task(agent)
        if not task:
            return None
        
        # Format trial balance for agent
        trial_balance_text = _format_trial_balance_for_agent(trial_balance_data)
        
        # Set default period if not provided
        if not period_start:
            period_start = datetime.now().replace(day=1).isoformat()
        if not period_end:
            period_end = datetime.now().isoformat()
        
        # Prepare input for agent (focus on P&L only)
        crew_input = {
            "trial_balance": trial_balance_text,
            "period_start": period_start,
            "period_end": period_end,
            "prior_period_data": "{}"  # Empty for now, can be enhanced later
        }
        
        # Create task description focused on P&L
        pnl_task_description = f"""Generate Profit & Loss Statement from the trial balance.

TRIAL BALANCE:
{trial_balance_text}

REPORTING PERIOD:
{period_start} to {period_end}

Generate a Profit & Loss Statement with:
- Revenue from operations
- Other income
- Cost of materials consumed
- Employee benefits expense
- Other expenses
- Tax expense
- Profit/(Loss) for the period

Return ONLY a JSON object with this structure:
{{
    "profit_and_loss": {{
        "period": "{period_start} to {period_end}",
        "revenue": {{
            "revenue_from_operations": 0,
            "other_income": 0,
            "total_revenue": 0
        }},
        "expenses": {{
            "cost_of_materials": 0,
            "employee_benefits": 0,
            "other_expenses": 0,
            "total_expenses": 0
        }},
        "profit_before_tax": 0,
        "tax_expense": 0,
        "net_profit": 0
    }}
}}"""
        
        pnl_task = Task(
            description=pnl_task_description,
            agent=agent,
            expected_output="JSON object with profit_and_loss structure"
        )
        
        # Run crew
        crew = Crew(agents=[agent], tasks=[pnl_task], verbose=False)
        result = crew.kickoff(crew_input)
        
        # Parse result
        result_text = str(result)
        parsed_data = _parse_json_from_response(result_text)
        
        if parsed_data and "profit_and_loss" in parsed_data:
            logger.info("Successfully generated P&L statement")
            return parsed_data.get("profit_and_loss")
        else:
            logger.warning(f"AI agent did not return expected P&L structure. Response: {result_text[:200]}")
            return None
            
    except Exception as e:
        logger.error(f"Failed to generate P&L statement: {e}", exc_info=True)
        return None


def generate_cash_flow_statement(
    trial_balance_data: Dict,
    bank_transactions: List[Dict],
    period_start: Optional[str] = None,
    period_end: Optional[str] = None
) -> Optional[Dict]:
    """
    Generate Cash Flow Statement using AI agent
    
    Args:
        trial_balance_data: Trial balance data (from journal entries)
        bank_transactions: List of bank transaction dictionaries
        period_start: Start date of reporting period (ISO format)
        period_end: End date of reporting period (ISO format)
    
    Returns:
        Dictionary with Cash Flow data, or None if generation fails
    """
    if not AI_AVAILABLE:
        logger.warning("OpenAI API key not configured. Cannot generate Cash Flow statement.")
        return None
    
    try:
        agent = _load_reporting_agent()
        if not agent:
            return None
        
        # Format data for agent
        trial_balance_text = _format_trial_balance_for_agent(trial_balance_data)
        bank_transactions_text = _format_bank_transactions_for_agent(bank_transactions)
        
        # Set default period if not provided
        if not period_start:
            period_start = datetime.now().replace(day=1).isoformat()
        if not period_end:
            period_end = datetime.now().isoformat()
        
        # Prepare input for agent
        crew_input = {
            "trial_balance": trial_balance_text,
            "bank_transactions": bank_transactions_text,
            "period_start": period_start,
            "period_end": period_end,
            "prior_period_data": "{}"
        }
        
        # Create task description focused on Cash Flow
        cash_flow_task_description = f"""Generate Cash Flow Statement (Indirect Method) from trial balance and bank transactions.

TRIAL BALANCE:
{trial_balance_text}

BANK TRANSACTIONS:
{bank_transactions_text}

REPORTING PERIOD:
{period_start} to {period_end}

Generate a Cash Flow Statement using Indirect Method with:
- Operating activities (net profit, adjustments, working capital changes)
- Investing activities (asset purchases/sales)
- Financing activities (loans, equity, dividends)

Return ONLY a JSON object with this structure:
{{
    "cash_flow": {{
        "operating_activities": {{
            "net_profit": 0,
            "adjustments_for_non_cash_items": 0,
            "changes_in_working_capital": 0,
            "cash_from_operating_activities": 0
        }},
        "investing_activities": {{
            "purchase_of_assets": 0,
            "sale_of_assets": 0,
            "cash_from_investing_activities": 0
        }},
        "financing_activities": {{
            "loan_received": 0,
            "loan_repayment": 0,
            "equity_raised": 0,
            "dividends_paid": 0,
            "cash_from_financing_activities": 0
        }},
        "net_increase_in_cash": 0,
        "opening_cash_balance": 0,
        "closing_cash_balance": 0
    }}
}}"""
        
        cash_flow_task = Task(
            description=cash_flow_task_description,
            agent=agent,
            expected_output="JSON object with cash_flow structure"
        )
        
        # Run crew
        crew = Crew(agents=[agent], tasks=[cash_flow_task], verbose=False)
        result = crew.kickoff(crew_input)
        
        # Parse result
        result_text = str(result)
        parsed_data = _parse_json_from_response(result_text)
        
        if parsed_data and "cash_flow" in parsed_data:
            logger.info("Successfully generated Cash Flow statement")
            return parsed_data.get("cash_flow")
        else:
            logger.warning(f"AI agent did not return expected Cash Flow structure. Response: {result_text[:200]}")
            return None
            
    except Exception as e:
        logger.error(f"Failed to generate Cash Flow statement: {e}", exc_info=True)
        return None

