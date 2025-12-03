import os
from dotenv import load_dotenv
from crewai import Crew, Agent, Task, LLM
import yaml, glob

# Load environment variables from .env automatically
load_dotenv(".env")

# Setup LLM using environment variables
llm = LLM(
    model=os.getenv("OPENAI_MODEL_NAME", "openai/gpt-oss-20b:free"),
    base_url=os.getenv("OPENAI_API_BASE", "https://openrouter.ai/api/v1"),
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0.0
)

# Load agents
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

# Load tasks - first pass: create all tasks without context
task_data_list = []
task_name_map = {}  # Map task file names to Task objects for context references

for file in glob.glob("tasks/*.yaml"):
    data = yaml.safe_load(open(file))
    task_name = os.path.splitext(os.path.basename(file))[0]  # e.g., "ingest_financial_data"
    task_data_list.append((task_name, data, file))

# Sort tasks by dependency order (tasks with no dependencies first)
# Dependency chain: ingest -> journal -> ledger -> reporting
# reconcile_bank_transactions has no dependencies
task_order = ["ingest_financial_data", "reconcile_bank_transactions", 
              "generate_journal_entries", "update_general_ledger", 
              "generate_financial_statements"]

# Reorder task_data_list based on task_order
task_data_list_sorted = []
for task_name in task_order:
    for name, data, file in task_data_list:
        if name == task_name:
            task_data_list_sorted.append((name, data, file))
            break
# Add any tasks not in the order list
for name, data, file in task_data_list:
    if name not in task_order:
        task_data_list_sorted.append((name, data, file))

# Create tasks in dependency order
tasks = []
for task_name, data, file in task_data_list_sorted:
    agent_instance = agents[data["agent"]]
    # Check if this task has context dependencies
    context_tasks = []
    if "context" in data and data["context"]:
        # Convert context task names to Task objects (they should already exist)
        context_tasks = [task_name_map[ctx_task] for ctx_task in data["context"] if ctx_task in task_name_map]
    
    # Only add context parameter if there are dependencies
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

# Sample input data for tasks (must match all template variables in your YAMLs)
crew_input = {
    # Data for invoice extraction
    "data_sources": [
        "Invoice INV-1001 PDF",
        "Invoice INV-1002 PDF",
        "Invoice INV-1003 PDF"
    ],
    "extracted_data": [
        {"invoice_number": "INV-1001", "vendor_name": "Vendor A", "vendor_gstin": "27AAAAA0000A1Z5",
         "invoice_date": "2025-11-01", "subtotal_amount": 10000, "tax_amount": 1800,
         "total_amount": 11800, "currency": "INR", "items": ["Item1", "Item2"]},
        {"invoice_number": "INV-1002", "vendor_name": "Vendor B", "vendor_gstin": "27BBBBB1111B2Z6",
         "invoice_date": "2025-11-02", "subtotal_amount": 5000, "tax_amount": 900,
         "total_amount": 5900, "currency": "INR", "items": ["Item3"]},
        {"invoice_number": "INV-1003", "vendor_name": "Vendor C", "vendor_gstin": "27CCCCC2222C3Z7",
         "invoice_date": "2025-11-03", "subtotal_amount": 7500, "tax_amount": 1350,
         "total_amount": 8850, "currency": "INR", "items": ["Item4", "Item5"]}
    ],

    # Data for bank transactions
    "bank_transactions": [
        {"date": "2025-11-01", "account": "Cash", "amount": 5000, "type": "debit"},
        {"date": "2025-11-02", "account": "Cash", "amount": 10000, "type": "credit"}
    ],

    # Approved journal entries
    "approved_entries": [
        {"invoice_number": "INV-1001", "amount": 11800, "status": "approved"},
        {"invoice_number": "INV-1002", "amount": 5900, "status": "approved"}
    ],

    # Current ledger snapshot
    "current_ledger": {
        "Cash": 50000,
        "Accounts Payable": 20000,
        "Revenue": 100000
    },

    # Trial balance for reporting
    "trial_balance": {
        "Cash": 61800,
        "Accounts Payable": 25900,
        "Revenue": 100000
    },

    # Reporting period
    "period_start": "2025-11-01",
    "period_end": "2025-11-30",
    
    # Prior period data for comparison
    "prior_period_data": {
        "trial_balance": {
            "Cash": 45000,
            "Accounts Payable": 15000,
            "Revenue": 90000
        }
    },

    # Chart of accounts for ledger tasks
    "chart_of_accounts": [
        {"account_name": "Cash", "type": "Asset"},
        {"account_name": "Accounts Payable", "type": "Liability"},
        {"account_name": "Revenue", "type": "Income"}
    ],

    # Outstanding receivables
    "outstanding_receivables": [
        {"customer": "Customer A", "amount": 10000, "due_date": "2025-11-15"},
        {"customer": "Customer B", "amount": 5000, "due_date": "2025-11-20"}
    ],
    # Outstanding payables
    "outstanding_payables": [
    {"vendor": "Vendor A", "amount": 7000, "due_date": "2025-11-25"},
    {"vendor": "Vendor B", "amount": 4000, "due_date": "2025-11-28"}
]
}


# Run Crew
crew = Crew(agents=list(agents.values()), tasks=tasks, verbose=True)
result = crew.kickoff(crew_input)

print("FINAL RESULT:")
print(result)