# Clear Data on Railway PostgreSQL

This guide shows you how to delete data from database tables on Railway PostgreSQL while keeping the table structure intact.

## Option 1: Run Script Locally with Railway DATABASE_URL (Recommended)

This is the easiest method - run the script on your local machine but connect to Railway's database.

### Steps:

1. **Get Railway DATABASE_URL**:
   - Go to [railway.app/dashboard](https://railway.app/dashboard)
   - Click on your project
   - Click on your **PostgreSQL database service** (not the app)
   - Go to the **"Variables"** tab
   - Copy the `DATABASE_URL` value (it looks like: `postgresql://postgres:password@hostname:port/railway`)

2. **Set DATABASE_URL and run script**:
   ```bash
   # Set the Railway DATABASE_URL temporarily
   export DATABASE_URL="postgresql://postgres:password@hostname:port/railway"
   
   # Run the simple clear script
   python scripts/clear_data_simple.py
   
   # Or run the full clear script
   python scripts/clear_data.py
   ```

3. **Or use Railway CLI to get the URL**:
   ```bash
   # Install Railway CLI if not already installed
   npm i -g @railway/cli
   
   # Login and link to your project
   railway login
   railway link
   
   # Get the DATABASE_URL
   railway variables
   
   # Then export it and run the script
   export DATABASE_URL=$(railway variables --json | jq -r '.DATABASE_URL')
   python scripts/clear_data_simple.py
   ```

## Option 2: Use Railway CLI Shell

Run the script directly on Railway using their shell:

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login and link
railway login
railway link

# Open a shell in your Railway app
railway shell

# Once in the shell, run:
python scripts/clear_data_simple.py
```

**Note**: This requires the scripts to be in your deployed code. Since `scripts/` is in `.gitignore`, you'll need to temporarily remove it from `.gitignore` or copy the script content.

## Option 3: Use Railway CLI to Connect to Postgres - RECOMMENDED

Use Railway CLI to connect directly to PostgreSQL and run SQL:

```bash
# Install Railway CLI if not already installed
npm i -g @railway/cli

# Login and link to your project
railway login
railway link

# Connect to PostgreSQL (opens psql shell)
railway connect Postgres
```

Once connected, you can:
- **Paste SQL commands directly** into the psql shell
- **Or pipe the SQL file**:
  ```bash
  railway connect Postgres < scripts/delete_data.sql
  ```

**Or run SQL commands directly:**
```bash
# Connect and run SQL in one command
railway connect Postgres -c "SET session_replication_role = 'replica'; DELETE FROM \"reports\"; DELETE FROM \"report_bundles\"; DELETE FROM \"file_uploads\"; DELETE FROM \"reconciliations\"; DELETE FROM \"journal_entry_lines\"; DELETE FROM \"bank_transactions\"; DELETE FROM \"journal_entries\"; DELETE FROM \"invoices\"; DELETE FROM \"buyers\"; DELETE FROM \"vendors\"; SET session_replication_role = 'origin';"
```

**Better approach - use the SQL file:**
```bash
# Pipe the SQL file into Railway Postgres
railway connect Postgres < scripts/delete_data.sql
```

## Option 4: Use Railway Database Console (Web UI)

Connect directly to Railway's PostgreSQL and run SQL commands:

1. **Get Connection Details**:
   - Go to Railway dashboard → Your PostgreSQL service
   - Click **"Query"** tab (or **"Connect"** → **"Query"**)
   - Railway provides a web-based PostgreSQL console

2. **Run SQL Commands** (Delete data, keep tables):
   ```sql
   -- Disable foreign key checks temporarily
   SET session_replication_role = 'replica';
   
   -- Delete data in dependency order (children first)
   DELETE FROM "reports";
   DELETE FROM "report_bundles";
   DELETE FROM "file_uploads";
   DELETE FROM "reconciliations";
   DELETE FROM "journal_entry_lines";
   DELETE FROM "bank_transactions";
   DELETE FROM "journal_entries";
   DELETE FROM "invoices";
   DELETE FROM "buyers";
   DELETE FROM "vendors";
   
   -- Re-enable foreign key checks
   SET session_replication_role = 'origin';
   ```

3. **Or use the SQL file**:
   - Copy contents from `scripts/delete_data.sql`
   - Paste into Railway's Query console
   - Execute

4. **Verify deletion** (optional):
   ```sql
   SELECT COUNT(*) FROM "reports";
   SELECT COUNT(*) FROM "invoices";
   SELECT COUNT(*) FROM "journal_entries";
   SELECT COUNT(*) FROM "users";  -- Should still have data
   SELECT COUNT(*) FROM "companies";  -- Should still have data
   ```

## Option 5: Create a Railway One-Off Command

You can create a one-off command in Railway:

1. Go to Railway dashboard → Your app service
2. Go to **"Deployments"** tab
3. Click **"New Deployment"** → **"One-Off Command"**
4. Enter: `python scripts/clear_data_simple.py`
5. Run it

**Note**: Again, this requires scripts to be in your deployed code.

## Recommended Approach

**Option 3** (Railway CLI connect Postgres) is recommended because:
- ✅ No need to install anything or run scripts locally
- ✅ Direct access to Railway's database
- ✅ Can see results immediately
- ✅ Simple copy-paste SQL commands
- ✅ Table structures are preserved (only data is deleted)

## Safety Tips

⚠️ **WARNING**: These commands will **DELETE ALL DATA** from transaction tables (except users and companies)!

- ✅ Table structures are **preserved** (tables are not dropped)
- ✅ Users and companies data is **kept**
- ⚠️ All invoices, journal entries, bank transactions, etc. will be **deleted**
- Always backup your database before clearing
- Double-check you're connected to the right database
- Consider using Railway's database backup feature first

## Quick Reference

**Easiest Method - Railway CLI:**
```bash
# Connect and run SQL file
railway connect Postgres < scripts/delete_data.sql
```

**Or connect interactively:**
```bash
railway connect Postgres
# Then paste SQL commands or use \i to include file
```

**SQL Commands (for copy-paste):**
```sql
SET session_replication_role = 'replica';
DELETE FROM "reports";
DELETE FROM "report_bundles";
DELETE FROM "file_uploads";
DELETE FROM "reconciliations";
DELETE FROM "journal_entry_lines";
DELETE FROM "bank_transactions";
DELETE FROM "journal_entries";
DELETE FROM "invoices";
DELETE FROM "buyers";
DELETE FROM "vendors";
SET session_replication_role = 'origin';
```

## Troubleshooting

**Connection refused**:
- Check that your Railway database is running
- Verify the DATABASE_URL is correct
- Check Railway logs for database issues

**Permission denied**:
- Ensure the DATABASE_URL has the correct credentials
- Railway auto-generates these, so they should work

**Script not found**:
- Make sure you're in the project root directory
- Verify the scripts directory exists (even if gitignored)

