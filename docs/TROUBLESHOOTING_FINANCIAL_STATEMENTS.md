# Troubleshooting Financial Statements Feature

## Issue: Changes Not Reflecting

If the new Profit & Loss and Cash Flow reports are not appearing, follow these steps:

### Step 1: Run Database Migration

The database enum needs to be updated to include the new report types:

```bash
alembic upgrade head
```

This will add `profit_loss` and `cash_flow` to the `reporttype` enum in PostgreSQL.

**Verify migration ran:**
```bash
alembic current
```

Should show: `1765381524 (head)`

### Step 2: Restart the Server

After running the migration, restart your FastAPI server to load the new code:

```bash
# If running locally
# Stop the server (Ctrl+C) and restart:
uvicorn api.main:app --reload

# If running with Docker
docker-compose restart

# If running on Railway
# The server should auto-restart after deployment
```

### Step 3: Check Environment Variables

Ensure OpenAI/OpenRouter API is configured:

```bash
# Check if these are set:
echo $OPENAI_API_KEY
echo $OPENAI_API_BASE
echo $OPENAI_MODEL_NAME
```

If not set, add to `.env`:
```
OPENAI_API_KEY=your-key-here
OPENAI_API_BASE=https://openrouter.ai/api/v1
OPENAI_MODEL_NAME=openai/gpt-4o-mini
```

### Step 4: Generate Reports

1. **Via UI**: Go to Reports page → Click "Generate Reports"
2. **Via API**: `POST /api/reports/generate`

### Step 5: Check Logs

Look for these log messages:

**Success:**
```
INFO - Generating Profit & Loss statement...
INFO - Successfully generated Profit & Loss statement
INFO - Generating Cash Flow statement...
INFO - Successfully generated Cash Flow statement
```

**If AI is not configured:**
```
WARNING - OpenAI API key not configured. Cannot generate P&L statement.
```

**If AI fails:**
```
ERROR - Failed to generate P&L statement: [error details]
```

### Step 6: Verify Database

Check if reports were created:

```sql
-- Check if enum values exist
SELECT enumlabel FROM pg_enum WHERE enumtypid = 'reporttype'::regtype;

-- Should include: journal_entries, trial_balance, ledger, profit_loss, cash_flow

-- Check if reports exist
SELECT report_type, filename FROM reports ORDER BY report_id DESC LIMIT 10;
```

### Step 7: Test API Endpoints

```bash
# Get P&L report
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/reports/profit-loss

# Get Cash Flow report
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/reports/cash-flow
```

## Common Issues

### Issue: "reporttype enum does not exist"
**Solution**: Run `alembic upgrade head`

### Issue: "Invalid input value for enum reporttype: 'profit_loss'"
**Solution**: Migration not run. Run `alembic upgrade head`

### Issue: "ModuleNotFoundError: No module named 'crewai'"
**Solution**: Install dependencies: `pip install crewai`

### Issue: Reports generate but P&L/Cash Flow are missing
**Possible causes:**
1. OpenAI API key not configured → Check logs for warning
2. AI agent failed → Check logs for error details
3. No journal entries → Upload invoices first
4. No bank transactions (for Cash Flow) → Upload bank statements

### Issue: "AI agent did not return expected structure"
**Solution**: 
- Check OpenAI API key is valid
- Check API quota/limits
- Review logs for AI response
- Try generating reports again

## Verification Checklist

- [ ] Migration `1765381524` has been applied (`alembic current`)
- [ ] Server has been restarted after code changes
- [ ] `OPENAI_API_KEY` is set in environment
- [ ] Journal entries exist in database
- [ ] Reports page shows "Generate Reports" button
- [ ] After generating, check logs for success/error messages
- [ ] API endpoints return 200 OK (not 404)

## Still Not Working?

1. Check server logs for errors
2. Verify all files are committed and deployed
3. Check database connection
4. Verify CrewAI and dependencies are installed
5. Test with a simple invoice upload first

