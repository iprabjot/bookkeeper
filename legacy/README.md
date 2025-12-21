# Legacy Tools

This folder contains legacy tools and scripts that are no longer used by the FastAPI application but are kept for reference or CLI usage.

## Files

- **`demo_agents.py`**: Demo script for CrewAI agents (not used in production)
- **`invoice_cli.py`**: Command-line interface for processing invoices (legacy, uses disk-based reports)
- **`invoice_workflow.py`**: Legacy invoice processing workflow (uses disk-based CSV generation)

## Note

These tools use the old disk-based report generation system. The production FastAPI application uses database-backed report storage instead.

If you need CLI functionality, consider creating new tools that use the FastAPI endpoints or the database-backed report system.






