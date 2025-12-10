// API client for bookkeeper
// Automatically detect API base URL (works for localhost and production)
const API_BASE = window.location.origin + '/api';

// Auth token management
function getAccessToken() {
    return localStorage.getItem('access_token');
}

function getRefreshToken() {
    return localStorage.getItem('refresh_token');
}

function setTokens(accessToken, refreshToken) {
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
}

function clearTokens() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
}

async function refreshAccessToken() {
    const refreshToken = getRefreshToken();
    if (!refreshToken) {
        throw new Error('No refresh token available');
    }
    
    try {
        const response = await fetch(`${API_BASE}/auth/refresh`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: refreshToken })
        });
        
        if (!response.ok) {
            // If refresh fails (e.g., invalid token, signature mismatch), clear tokens
            clearTokens();
            const errorData = await response.json().catch(() => ({ detail: 'Token refresh failed' }));
            throw new Error(errorData.detail || 'Token refresh failed');
        }
        
        const data = await response.json();
        setTokens(data.access_token, data.refresh_token);
        return data.access_token;
    } catch (error) {
        clearTokens();
        // Redirect to login if on a protected page
        if (!window.location.pathname.includes('login.html') && !window.location.pathname.includes('signup.html')) {
            window.location.href = 'login.html';
        }
        throw error;
    }
}

async function apiRequest(endpoint, options = {}) {
    // Skip auth for public endpoints (login, signup, refresh, verify-email)
    // Protected auth endpoints: /auth/me, /auth/send-verification-email
    const publicEndpoints = ['/auth/login', '/auth/signup', '/auth/refresh', '/auth/verify-email', '/health'];
    const protectedAuthEndpoints = ['/auth/me', '/auth/send-verification-email'];
    const isPublicEndpoint = publicEndpoints.includes(endpoint) || 
                            (endpoint.startsWith('/auth/') && !protectedAuthEndpoints.includes(endpoint));
    
    try {
        // Add auth token if available and not a public endpoint
        const headers = { ...options.headers };
        if (!isPublicEndpoint) {
            const token = getAccessToken();
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }
        }
        
        let response = await fetch(`${API_BASE}${endpoint}`, {
            ...options,
            headers
        });
        
        // If 401 Unauthorized, try to refresh token first, then clear if refresh fails
        if (response.status === 401) {
            // Don't try refresh for login/signup endpoints (we don't have tokens yet)
            const isAuthEndpoint = endpoint === '/auth/login' || endpoint === '/auth/signup';
            
            // If not a public endpoint, try to refresh token once
            if (!isPublicEndpoint && !isAuthEndpoint) {
                try {
                    const newToken = await refreshAccessToken();
                    // Retry request with new token
                    headers['Authorization'] = `Bearer ${newToken}`;
                    response = await fetch(`${API_BASE}${endpoint}`, {
                        ...options,
                        headers
                    });
                    
                    // If still 401 after refresh, clear tokens and redirect to login
                    if (response.status === 401) {
                        clearTokens();
                        if (!window.location.pathname.includes('login.html') && !window.location.pathname.includes('signup.html')) {
                            window.location.href = 'login.html';
                        }
                        throw new Error('Authentication required. Please log in again.');
                    }
                } catch (refreshError) {
                    // Refresh failed, clear tokens and redirect to login
                    clearTokens();
                    if (!window.location.pathname.includes('login.html') && !window.location.pathname.includes('signup.html')) {
                        window.location.href = 'login.html';
                    }
                    throw new Error('Authentication required. Please log in again.');
                }
            } else {
                // Public endpoint with 401 (like /auth/refresh), clear tokens and throw error
                if (!isAuthEndpoint) {
                    clearTokens();
                }
                throw new Error('Authentication required');
            }
        }
        
        // Handle blob responses (for file downloads) - check before error handling
        const contentType = response.headers.get('content-type') || '';
        const isBlobRequest = options.responseType === 'blob' || 
                              contentType.includes('application/zip') || 
                              contentType.includes('text/csv') ||
                              contentType.includes('application/octet-stream');
        
        if (isBlobRequest) {
            if (!response.ok) {
                // Try to get error message from JSON if available
                try {
                    const error = await response.json();
                    throw new Error(error.detail || error.message || `HTTP ${response.status}`);
                } catch (e) {
                    if (e instanceof Error && e.message) {
                        throw e;
                    }
                    throw new Error(`Download failed: ${response.statusText}`);
                }
            }
            return await response.blob();
        }
        
        if (!response.ok) {
            let errorDetail = response.statusText;
            try {
                const error = await response.json();
                errorDetail = error.detail || error.message || errorDetail;
            } catch (e) {
                // If JSON parsing fails, use status text
                const text = await response.text().catch(() => '');
                errorDetail = text || errorDetail;
            }
            throw new Error(errorDetail || `HTTP ${response.status}`);
        }
        
        if (contentType && contentType.includes('application/json')) {
            return await response.json();
        } else {
            // If not JSON, return text or empty object
            const text = await response.text().catch(() => '');
            return text ? { message: text } : {};
        }
    } catch (error) {
        console.error('API Error:', error);
        // Ensure we always throw an Error object
        if (error instanceof Error) {
            throw error;
        } else {
            throw new Error(String(error));
        }
    }
}

// Auth functions
async function login(email, password) {
    const response = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
    });
    
    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(error.detail || 'Login failed');
    }
    
    const data = await response.json();
    setTokens(data.access_token, data.refresh_token);
    return data;
}

async function signup(data) {
    const response = await fetch(`${API_BASE}/auth/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    
    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(error.detail || 'Signup failed');
    }
    
    return await response.json();
}

async function getCurrentUser() {
    return apiRequest('/auth/me');
}

function logout() {
    clearTokens();
    window.location.href = 'login.html';
}

async function getStatus() {
    return apiRequest('/status');
}

async function getCompanies() {
    return apiRequest('/companies');
}

async function getCurrentCompany() {
    return apiRequest('/companies/current');
}

async function createCompany(data) {
    return apiRequest('/companies', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
}

async function updateCompany(data) {
    return apiRequest('/companies/current', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
}

async function getInvoices() {
    return apiRequest('/invoices');
}

async function uploadInvoice(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    return apiRequest('/invoices', {
        method: 'POST',
        body: formData
    });
}

async function getBankTransactions() {
    return apiRequest('/bank-transactions');
}

async function uploadBankStatement(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    return apiRequest('/bank-statements', {
        method: 'POST',
        body: formData
    });
}

async function runReconciliation() {
    return apiRequest('/reconcile', {
        method: 'POST'
    });
}

async function getReconciliations() {
    return apiRequest('/reconciliations');
}

async function settleReconciliation(reconciliationId) {
    return apiRequest(`/reconciliations/${reconciliationId}/settle`, {
        method: 'POST'
    });
}

async function getVendors() {
    return apiRequest('/vendors');
}

async function getBuyers() {
    return apiRequest('/buyers');
}

async function createVendor(data) {
    return apiRequest('/vendors', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
}

async function createBuyer(data) {
    return apiRequest('/buyers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
}

async function generateReports(description) {
    const url = description 
        ? `/reports/generate?description=${encodeURIComponent(description)}`
        : '/reports/generate';
    return apiRequest(url, {
        method: 'POST'
    });
}

async function listReports(bundleId) {
    const url = bundleId 
        ? `/reports/list?bundle_id=${bundleId}`
        : '/reports/list';
    return apiRequest(url);
}

async function listBundles() {
    return apiRequest('/reports/bundles');
}

async function getBundle(bundleId) {
    return apiRequest(`/reports/bundles/${bundleId}`);
}

async function deleteBundle(bundleId) {
    return apiRequest(`/reports/bundles/${bundleId}`, {
        method: 'DELETE'
    });
}

// User management functions
async function getUsers() {
    return apiRequest('/users');
}

async function createUser(data) {
    return apiRequest('/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
}

async function updateUser(userId, data) {
    return apiRequest(`/users/${userId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
}

async function deleteUser(userId) {
    return apiRequest(`/users/${userId}`, {
        method: 'DELETE'
    });
}

// Email verification functions
async function sendVerificationEmail() {
    return apiRequest('/auth/send-verification-email', {
        method: 'POST'
    });
}

async function verifyEmail(token) {
    return apiRequest('/auth/verify-email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token })
    });
}

// Make available globally
window.generateReports = generateReports;
window.listReports = listReports;
window.listBundles = listBundles;
window.getBundle = getBundle;
window.deleteBundle = deleteBundle;

async function downloadReport(endpoint, filename) {
    try {
        // Use apiRequest which handles authentication automatically
        const response = await apiRequest(endpoint, {
            method: 'GET',
            responseType: 'blob'
        });
        
        if (response instanceof Blob) {
            downloadBlob(response, filename);
        } else {
            // If apiRequest returns JSON error, handle it
            throw new Error(response.detail || 'Failed to download report');
        }
    } catch (error) {
        console.error('Download error:', error);
        alert(`Error downloading report: ${error.message || error}`);
    }
}

function downloadBlob(blob, filename) {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename || 'report.csv';
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
}

// Make all API functions available globally
window.apiRequest = apiRequest;
window.login = login;
window.signup = signup;
window.getCurrentUser = getCurrentUser;
window.logout = logout;
window.getStatus = getStatus;
window.getAccessToken = getAccessToken;
window.refreshAccessToken = refreshAccessToken;
window.getCompanies = getCompanies;
window.getCurrentCompany = getCurrentCompany;
window.createCompany = createCompany;
window.updateCompany = updateCompany;
window.getInvoices = getInvoices;
window.uploadInvoice = uploadInvoice;
window.getBankTransactions = getBankTransactions;
window.uploadBankStatement = uploadBankStatement;
window.runReconciliation = runReconciliation;
window.getReconciliations = getReconciliations;
window.settleReconciliation = settleReconciliation;
window.getVendors = getVendors;
window.getBuyers = getBuyers;
window.createVendor = createVendor;
window.createBuyer = createBuyer;
window.generateReports = generateReports;
window.listReports = listReports;
window.listBundles = listBundles;
window.getBundle = getBundle;
window.deleteBundle = deleteBundle;
window.downloadReport = downloadReport;
window.getUsers = getUsers;
window.createUser = createUser;
window.updateUser = updateUser;
window.deleteUser = deleteUser;
window.sendVerificationEmail = sendVerificationEmail;
window.verifyEmail = verifyEmail;

