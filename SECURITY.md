# Security Guidelines

## Environment Variables

**NEVER commit `.env` files or any files containing real credentials to the repository.**

### Current Status

- ✅ `.env` is properly ignored by `.gitignore`
- ✅ `.env.example` template is provided for reference
- ✅ All credentials are loaded from environment variables, not hardcoded

### If Credentials Were Exposed

If you suspect credentials were committed to git history:

1. **Rotate all exposed credentials immediately:**
   - Change SMTP password
   - Regenerate JWT_SECRET_KEY
   - Regenerate API keys (OpenAI, etc.)
   - Change database passwords

2. **Remove from git history (if needed):**
   ```bash
   # Use git filter-branch or BFG Repo-Cleaner
   # This rewrites history - coordinate with team first
   ```

3. **Verify credentials are not in history:**
   ```bash
   git log --all --full-history -p | grep -i "your_credential"
   ```

### Best Practices

- Always use `.env.example` as a template
- Never commit `.env` files
- Use different credentials for development and production
- Rotate credentials regularly
- Use secret management services for production (AWS Secrets Manager, etc.)

### GitGuardian Alerts

If GitGuardian alerts you about exposed credentials:

1. Check if credentials are actually in git history (they shouldn't be)
2. GitGuardian may detect patterns in documentation - this is usually safe
3. If real credentials are found, rotate them immediately
4. Consider using GitGuardian's remediation tools if credentials were committed

