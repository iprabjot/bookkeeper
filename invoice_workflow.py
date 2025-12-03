"""
Invoice Processing Workflow
Main workflow script that processes PDF invoices and generates accounting reports.

Workflow:
1. Extract data from PDF invoices
2. Process through CrewAI agents (optional)
3. Generate journal entries
4. Export accounting reports (CSV format)
"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from crewai import Crew, Agent, Task, LLM
import yaml
import glob

from invoice_extractor import process_invoices_from_folder
from accounting_reports import generate_all_csvs

# Load environment variables
load_dotenv(".env")

# Setup LLM
llm = LLM(
    model=os.getenv("OPENAI_MODEL_NAME", "openai/gpt-oss-20b:free"),
    base_url=os.getenv("OPENAI_API_BASE", "https://openrouter.ai/api/v1"),
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0.0
)


def load_agents():
    """Load all agents from YAML files."""
    agents = {}
    for file in glob.glob("agents/*.yaml"):
        data = yaml.safe_load(open(file))
        agent_name = data["agent"]["name"]
        agent_obj = Agent(
            name=agent_name,
            role=data["agent"]["role"],
            goal=data["agent"]["goal"],
            backstory=data["agent"].get("backstory", ""),
            verbose=True,
            allow_delegation=data["agent"].get("allow_delegation", False),
            llm=llm
        )
        agents[agent_name] = agent_obj
    return agents


def load_tasks(agents):
    """Load all tasks from YAML files with proper dependency ordering."""
    task_data_list = []
    
    for file in glob.glob("tasks/*.yaml"):
        data = yaml.safe_load(open(file))
        task_name = os.path.splitext(os.path.basename(file))[0]
        task_data_list.append((task_name, data, file))
    
    # Sort tasks by dependency order
    task_order = ["ingest_financial_data", "reconcile_bank_transactions", 
                  "generate_journal_entries", "update_general_ledger", 
                  "generate_financial_statements"]
    
    task_data_list_sorted = []
    for task_name in task_order:
        for name, data, file in task_data_list:
            if name == task_name:
                task_data_list_sorted.append((name, data, file))
                break
    
    for name, data, file in task_data_list:
        if name not in task_order:
            task_data_list_sorted.append((name, data, file))
    
    # Create tasks in dependency order
    tasks = []
    task_name_map = {}
    
    for task_name, data, file in task_data_list_sorted:
        agent_instance = agents[data["agent"]]
        context_tasks = []
        if "context" in data and data["context"]:
            context_tasks = [task_name_map[ctx_task] for ctx_task in data["context"] if ctx_task in task_name_map]
        
        task_kwargs = {
            "description": data.get("description", ""),
            "agent": agent_instance,
            "expected_output": data.get("expected_output", "")
        }
        if context_tasks:
            task_kwargs["context"] = context_tasks
        
        task_obj = Task(**task_kwargs)
        tasks.append(task_obj)
        task_name_map[task_name] = task_obj
    
    return tasks


def prepare_crew_input(invoices_data):
    """Prepare input data for CrewAI from extracted invoice data."""
    # Convert invoice data to the format expected by agents
    data_sources = [f"Invoice {inv.get('invoice_number', 'Unknown')} PDF" for inv in invoices_data]
    
    extracted_data = []
    for inv in invoices_data:
        extracted_data.append({
            "invoice_number": inv.get("invoice_number", ""),
            "vendor_name": inv.get("vendor_name", ""),
            "vendor_gstin": inv.get("vendor_gstin", ""),
            "customer_name": inv.get("customer_name", ""),
            "customer_gstin": inv.get("customer_gstin", ""),
            "invoice_date": inv.get("invoice_date", ""),
            "subtotal_amount": inv.get("taxable_amount", 0),
            "tax_amount": inv.get("igst", 0) + inv.get("cgst", 0) + inv.get("sgst", 0),
            "igst_amount": inv.get("igst", 0),
            "cgst_amount": inv.get("cgst", 0),
            "sgst_amount": inv.get("sgst", 0),
            "total_amount": inv.get("total_amount", 0),
            "currency": "INR",
        })
    
    # Create chart of accounts based on invoices
    chart_of_accounts = [
        {"account_name": "Debtors", "type": "Asset"},
        {"account_name": "Sales A/c", "type": "Income"},
        {"account_name": "IGST Payable A/c", "type": "Liability"},
        {"account_name": "CGST Payable A/c", "type": "Liability"},
        {"account_name": "SGST Payable A/c", "type": "Liability"},
    ]
    
    # Prepare approved entries (all invoices are approved for now)
    approved_entries = []
    for inv in invoices_data:
        approved_entries.append({
            "invoice_number": inv.get("invoice_number", ""),
            "amount": inv.get("total_amount", 0),
            "status": "approved"
        })
    
    crew_input = {
        "data_sources": data_sources,
        "extracted_data": extracted_data,
        "chart_of_accounts": chart_of_accounts,
        "approved_entries": approved_entries,
        "current_ledger": {},
        "trial_balance": {},
        "period_start": min([inv.get("invoice_date", "") for inv in invoices_data] + ["2025-01-01"]),
        "period_end": max([inv.get("invoice_date", "") for inv in invoices_data] + ["2025-01-31"]),
        "prior_period_data": {
            "trial_balance": {}
        },
        "bank_transactions": [],
        "outstanding_receivables": [],
        "outstanding_payables": [],
    }
    
    return crew_input


def process_invoices_to_csvs(input_folder="data", output_folder="output"):
    """
    Main workflow:
    1. Process PDF invoices from input folder
    2. Run through CrewAI agents
    3. Generate CSV outputs
    """
    print("=" * 60)
    print("Invoice Processing Workflow")
    print("=" * 60)
    
    # Step 1: Process PDF invoices
    print("\n[Step 1] Processing PDF invoices...")
    invoices_data = process_invoices_from_folder(input_folder)
    
    if not invoices_data:
        print("No invoices found or processed. Exiting.")
        return
    
    print(f"Processed {len(invoices_data)} invoice(s)")
    for inv in invoices_data:
        print(f"  - Invoice {inv.get('invoice_number')}: ₹{inv.get('total_amount', 0):,.2f}")
    
    # Step 2: Prepare CrewAI input
    print("\n[Step 2] Preparing data for CrewAI agents...")
    crew_input = prepare_crew_input(invoices_data)
    
    # Step 3: Load agents and tasks
    print("\n[Step 3] Loading agents and tasks...")
    agents = load_agents()
    tasks = load_tasks(agents)
    
    # Only run the tasks we need: ingest -> journal entries -> ledger
    required_tasks = []
    task_name_map = {os.path.splitext(os.path.basename(f))[0]: None for f in glob.glob("tasks/*.yaml")}
    
    for task in tasks:
        task_desc = task.description[:50] if task.description else ""
        if "ingest" in task_desc.lower() or "journal" in task_desc.lower() or "ledger" in task_desc.lower():
            required_tasks.append(task)
    
    # Step 4: Run CrewAI
    print("\n[Step 4] Running CrewAI agents...")
    crew = Crew(agents=list(agents.values()), tasks=required_tasks, verbose=True)
    result = crew.kickoff(crew_input)
    
    # Step 5: Extract journal entries from result
    print("\n[Step 5] Extracting journal entries from agent output...")
    
    # The result should contain journal entries from the ledger task
    # We need to find the journal entries in the output
    journal_entries_str = str(result)
    
    # Try to extract JSON from the result
    import re
    json_match = re.search(r'```json\s*(\{.*?\})\s*```', journal_entries_str, re.DOTALL)
    journal_entries_data = None
    
    if json_match:
        try:
            parsed_data = json.loads(json_match.group(1))
            # Check if it has journal_entries
            if "journal_entries" in parsed_data and len(parsed_data.get("journal_entries", [])) > 0:
                journal_entries_data = parsed_data
                print(f"  Found {len(parsed_data['journal_entries'])} journal entries in agent output")
            else:
                print("  Agent output doesn't contain journal entries, creating from invoice data...")
        except Exception as e:
            print(f"  Error parsing agent output: {e}, creating from invoice data...")
    
    # If we couldn't extract from agent output, create from invoice data
    if not journal_entries_data:
        print("  Creating journal entries from invoice data...")
        journal_entries = []
        
        for inv in invoices_data:
            # Determine if this is a sales invoice (vendor selling to customer)
            # Based on the sample, it looks like sales invoices
            customer_name = inv.get("customer_name", "Unknown Customer")
            invoice_number = inv.get("invoice_number", "")
            date = inv.get("invoice_date", "")
            total = inv.get("total_amount", 0)
            taxable = inv.get("taxable_amount", 0)
            igst = inv.get("igst", 0)
            cgst = inv.get("cgst", 0)
            sgst = inv.get("sgst", 0)
            
            lines = [
                {
                    "account_code": "1100",
                    "account_name": f"Debtors – {customer_name}",
                    "debit": total,
                    "credit": 0
                },
                {
                    "account_code": "4100",
                    "account_name": "Sales A/c",
                    "debit": 0,
                    "credit": taxable
                }
            ]
            
            if igst > 0:
                lines.append({
                    "account_code": "2310",
                    "account_name": "IGST Payable A/c",
                    "debit": 0,
                    "credit": igst
                })
            
            if cgst > 0:
                lines.append({
                    "account_code": "2320",
                    "account_name": "CGST Payable A/c",
                    "debit": 0,
                    "credit": cgst
                })
            
            if sgst > 0:
                lines.append({
                    "account_code": "2330",
                    "account_name": "SGST Payable A/c",
                    "debit": 0,
                    "credit": sgst
                })
            
            journal_entries.append({
                "entry_id": f"JE-{invoice_number}",
                "date": date,
                "narration": f"Sales to {customer_name}",
                "reference": f"INV-{invoice_number}",
                "lines": lines,
                "total_debit": total,
                "total_credit": total,
                "status": "approved"
            })
        
        journal_entries_data = {"journal_entries": journal_entries}
    
    # Step 6: Generate CSV files
    print("\n[Step 6] Generating CSV files...")
    output_path = Path(output_folder)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Ensure journal_entries_data is a dict, not a string
    if isinstance(journal_entries_data, str):
        try:
            journal_entries_data = json.loads(journal_entries_data)
        except:
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', journal_entries_data, re.DOTALL)
            if json_match:
                journal_entries_data = json.loads(json_match.group(1))
    
    print(f"  Journal entries data type: {type(journal_entries_data)}")
    if isinstance(journal_entries_data, dict):
        entries_count = len(journal_entries_data.get('journal_entries', []))
        print(f"  Number of journal entries: {entries_count}")
        if entries_count == 0:
            print("  WARNING: No journal entries found!")
    else:
        print(f"  WARNING: journal_entries_data is not a dict: {journal_entries_data[:200] if isinstance(journal_entries_data, str) else 'unknown type'}")
    
    try:
        generate_all_csvs(journal_entries_data, None, output_path)
        print(f"  CSV generation completed")
    except Exception as e:
        print(f"  ERROR generating CSV files: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("Workflow completed successfully!")
    print(f"CSV files generated in: {output_path}")
    print("=" * 60)


if __name__ == "__main__":
    import sys
    
    input_folder = sys.argv[1] if len(sys.argv) > 1 else "data"
    output_folder = sys.argv[2] if len(sys.argv) > 2 else "output"
    
    process_invoices_to_csvs(input_folder, output_folder)

