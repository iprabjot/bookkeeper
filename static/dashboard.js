// Dashboard functionality
async function loadDashboard() {
    const loadingEl = document.getElementById('status-loading');
    const errorEl = document.getElementById('status-error');
    const contentEl = document.getElementById('dashboard-content');
    const companyNavEl = document.getElementById('company-name-nav');
    
    try {
        const status = await getStatus();
        
        // Update company name in nav
        if (status.current_company) {
            companyNavEl.textContent = status.current_company.name;
        } else {
            companyNavEl.textContent = 'No company set';
        }
        
        // Format numbers with Indian locale
        document.getElementById('total-invoices').textContent = status.total_invoices.toLocaleString('en-IN');
        document.getElementById('pending-invoices').textContent = status.pending_invoices.toLocaleString('en-IN');
        document.getElementById('paid-invoices').textContent = status.paid_invoices.toLocaleString('en-IN');
        document.getElementById('total-transactions').textContent = status.total_transactions.toLocaleString('en-IN');
        document.getElementById('unmatched-transactions').textContent = status.unmatched_transactions.toLocaleString('en-IN');
        document.getElementById('total-debtors').textContent = formatCurrency(status.total_debtors);
        document.getElementById('total-creditors').textContent = formatCurrency(status.total_creditors);
        
        loadingEl.classList.add('hidden');
        errorEl.classList.add('hidden');
        contentEl.classList.remove('hidden');
    } catch (error) {
        loadingEl.classList.add('hidden');
        errorEl.classList.remove('hidden');
        errorEl.textContent = `Error loading dashboard: ${error.message}`;
        contentEl.classList.add('hidden');
    }
}

async function runReconciliation() {
    if (!confirm('Run reconciliation to match bank transactions with invoices?')) {
        return;
    }
    
    try {
        // Call the API function directly from api.js (avoid circular reference)
        const result = await window.apiRequest('/reconcile', { method: 'POST' });
        if (!result) {
            alert('Error: Reconciliation returned no result');
            return;
        }
        alert(`Reconciliation complete!\nMatches found: ${result.matches_found || 0}\nExact: ${result.exact_matches || 0}, Fuzzy: ${result.fuzzy_matches || 0}`);
        loadDashboard(); // Refresh
    } catch (error) {
        console.error('Reconciliation error:', error);
        alert(`Error: ${error.message || 'Unknown error occurred'}`);
    }
}

function formatCurrency(amount) {
    return new Intl.NumberFormat('en-IN', {
        maximumFractionDigits: 0
    }).format(amount);
}

// Make runReconciliation available globally
window.runReconciliation = runReconciliation;

// Load dashboard on page load
document.addEventListener('DOMContentLoaded', loadDashboard);
