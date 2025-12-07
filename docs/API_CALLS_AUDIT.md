# Frontend API Calls Audit - Token Handling

##  All API Calls Verified

### Public Endpoints (No Token Required)
These endpoints correctly use direct `fetch()` calls:
-  `/auth/login` - `login.html` (line 85)
-  `/auth/signup` - `signup.html` (line 173)
-  `/auth/refresh` - `api.js` (line 30) - internal use

### Protected Endpoints (Token Required)
All these endpoints use `apiRequest()` which automatically includes the token:

#### From `api.js` (All use `apiRequest()`):
-  `/auth/me` - `getCurrentUser()` - **FIXED**: Now correctly sends token
-  `/status` - `getStatus()`
-  `/companies` - `getCompanies()`
-  `/companies/current` - `getCurrentCompany()`
-  `/companies` (POST) - `createCompany()`
-  `/companies/current` (PUT) - `updateCompany()`
-  `/invoices` - `getInvoices()`
-  `/invoices` (POST) - `uploadInvoice()`
-  `/bank-transactions` - `getBankTransactions()`
-  `/bank-statements` (POST) - `uploadBankStatement()`
-  `/reconcile` (POST) - `runReconciliation()`
-  `/reconciliations` - `getReconciliations()`
-  `/reconciliations/{id}/settle` (POST) - `settleReconciliation()`
-  `/vendors` - `getVendors()`
-  `/buyers` - `getBuyers()`
-  `/vendors` (POST) - `createVendor()`
-  `/buyers` (POST) - `createBuyer()`
-  `/reports/generate` (POST) - `generateReports()`
-  `/reports/list` - `listReports()`

#### From HTML Files (All use `window.*` functions which call `apiRequest()`):
-  `index.html` - Uses `window.getCurrentUser()`
-  `bank-statements.html` - Uses `window.getBankTransactions()`, `window.apiRequest('/reconcile')`, `window.getCurrentCompany()`
-  `dashboard.js` - Uses `window.apiRequest('/reconcile')`
-  `reports.html` - Uses `window.getCurrentCompany()`
-  `vendors.html` - Uses `window.getVendors()`, `window.getCurrentCompany()`
-  `invoices.html` - Uses `window.getInvoices()`, `window.getCurrentCompany()`
-  `company.html` - **FIXED**: Now uses `window.updateCompany()` instead of direct fetch
-  `companies.html` - Uses `window.getCompanies()`
-  `buyers.html` - Uses `window.getBuyers()`, `window.getCurrentCompany()`

## Token Handling Logic

### `apiRequest()` Function (api.js)
```javascript
// Public endpoints that don't need tokens
const publicEndpoints = ['/auth/login', '/auth/signup', '/auth/refresh', '/health'];
const isPublicEndpoint = publicEndpoints.includes(endpoint) || 
                        (endpoint.startsWith('/auth/') && endpoint !== '/auth/me');

// Automatically adds token for non-public endpoints
if (!isPublicEndpoint) {
    const token = getAccessToken();
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
}
```

### Token Storage
- Tokens are stored in `localStorage`:
  - `access_token` - Used for API requests
  - `refresh_token` - Used to refresh expired access tokens

### Token Refresh
- If a request returns 401, `apiRequest()` automatically tries to refresh the token
- If refresh fails, user is redirected to login page

## Summary

 **All API calls are correctly handling tokens:**
- Public endpoints (login, signup) use direct `fetch()` -  Correct
- Protected endpoints use `apiRequest()` which includes token -  Correct
- `/auth/me` now correctly sends token (was previously treated as public) -  Fixed
- `company.html` now uses `window.updateCompany()` instead of direct fetch -  Fixed

## No Issues Found

All frontend API calls are properly configured to include authentication tokens where required.

