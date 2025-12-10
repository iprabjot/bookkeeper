# File Storage Setup Guide

## Overview

The application supports S3-compatible storage for invoices, reports, and other files. Railway provides **Storage Buckets** which are fully S3-compatible, making it easy to store files persistently.

## Railway Storage Buckets Setup

### Step 1: Create a Storage Bucket

1. Go to your Railway project dashboard
2. Click **"+ New"** or right-click on the canvas
3. Select **"Bucket"**
4. Choose your preferred region (e.g., `us-east-1`)
5. Click **"Deploy"**

### Step 2: Get Connection Credentials

1. Click on your newly created bucket
2. Go to the **"Credentials"** tab
3. You'll see:
   - `S3_BUCKET_NAME`
   - `S3_ACCESS_KEY_ID`
   - `S3_SECRET_ACCESS_KEY`
   - `S3_ENDPOINT_URL`
   - `S3_REGION`

### Step 3: Configure Environment Variables

Add these to your Railway service environment variables:

```bash
S3_BUCKET_NAME=your-bucket-name
S3_ACCESS_KEY_ID=your-access-key
S3_SECRET_ACCESS_KEY=your-secret-key
S3_ENDPOINT_URL=https://your-endpoint-url
S3_REGION=us-east-1
```

**Note**: Railway automatically provides these as environment variables. You can also manually set them.

### Step 4: Install Dependencies

Add `boto3` to your `requirements.txt`:

```bash
pip install boto3
```

Or add to `requirements.txt`:
```
boto3>=1.28.0
```

## Alternative: AWS S3

If you prefer AWS S3 instead of Railway Storage Buckets:

1. Create an S3 bucket in AWS Console
2. Create an IAM user with S3 permissions
3. Set environment variables:
   ```bash
   S3_BUCKET_NAME=your-bucket-name
   S3_ACCESS_KEY_ID=your-aws-access-key
   S3_SECRET_ACCESS_KEY=your-aws-secret-key
   S3_REGION=us-east-1
   # Leave S3_ENDPOINT_URL empty for AWS S3
   ```

## Local Development (Fallback)

If S3 credentials are not configured, the system will:
- Store files locally in a persistent `storage/` directory (or `LOCAL_STORAGE_DIR` if set)
- Files are organized by company and type: `storage/invoices/company_{id}/{filename}`
- **Files are never deleted** - they persist permanently
- Log info messages about using local storage

## File Organization

Files are organized consistently in both S3 and local storage:
```
invoices/company_{company_id}/{filename}.pdf
reports/company_{company_id}/{filename}.csv
bank_statements/company_{company_id}/{filename}.csv
```

**Local Storage**: Files are stored in `storage/` directory (or `LOCAL_STORAGE_DIR` environment variable)
**S3 Storage**: Files are stored in the configured S3 bucket with the same structure

## File Persistence

**Important**: Files are **never deleted** automatically. They persist permanently in:
- **Production**: Railway Storage Buckets (S3-compatible)
- **Local Development**: `storage/` directory in project root

This ensures:
- ✅ Files are always available for download
- ✅ No data loss from container restarts
- ✅ Easy backup and restore
- ✅ Historical record of all invoices

## Migration from Local Storage

If you have existing invoices/reports stored locally:

1. Set up S3 storage (see above)
2. Run migration script to upload existing files:
   ```bash
   python scripts/migrate_files_to_s3.py
   ```
3. Update database records with S3 URLs

## Testing Storage

Test your storage configuration:

```python
from core.storage import get_storage_service

storage = get_storage_service()
if storage.enabled:
    print("✅ S3 storage is enabled")
    print(f"Bucket: {storage.bucket_name}")
else:
    print("⚠️  S3 storage not enabled. Using local fallback.")
```

## Troubleshooting

### Issue: "S3 credentials not configured"
**Solution**: Set all required environment variables (see Step 3)

### Issue: "S3 bucket not found"
**Solution**: 
- Verify bucket name is correct
- Check that bucket exists in Railway dashboard
- Ensure credentials have access to the bucket

### Issue: "boto3 not installed"
**Solution**: 
```bash
pip install boto3
```

### Issue: Files still stored locally
**Solution**: 
- Check environment variables are set correctly
- Restart the application after setting variables
- Check logs for S3 initialization errors

## Benefits of S3 Storage

- ✅ **Persistent**: Files survive container restarts
- ✅ **Scalable**: No disk space limits
- ✅ **Reliable**: Backed by Railway/AWS infrastructure
- ✅ **Accessible**: Can download files anytime via presigned URLs
- ✅ **Organized**: Files organized by company and type

## Cost Considerations

- **Railway Storage Buckets**: Included in Railway pricing
- **AWS S3**: Pay per GB stored and requests (very affordable for small apps)
- **Free Tier**: AWS S3 offers 5GB free storage for 12 months

## Security

- Files are stored per company (isolated by company_id)
- Access controlled via Railway/AWS IAM
- Presigned URLs expire after 1 hour (configurable)
- No public access by default

