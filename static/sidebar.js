// Sidebar component - reusable across all pages
function renderSidebar(activePage) {
    const sidebarConfig = {
        'index.html': 'Dashboard',
        'invoices.html': 'Invoices',
        'bank-statements.html': 'Bank Statements',
        'reports.html': 'Reports',
        'vendors.html': 'Vendors',
        'buyers.html': 'Buyers',
        'users.html': 'Users',
        'company.html': 'Company'
    };

    const menuItems = [
        { href: 'index.html', icon: 'fa-chart-line', label: 'Dashboard' },
        { href: 'invoices.html', icon: 'fa-file-invoice', label: 'Invoices' },
        { href: 'bank-statements.html', icon: 'fa-university', label: 'Bank Statements' },
        { href: 'reports.html', icon: 'fa-chart-bar', label: 'Reports' },
        { href: 'vendors.html', icon: 'fa-truck', label: 'Vendors' },
        { href: 'buyers.html', icon: 'fa-users', label: 'Buyers' },
        { href: 'users.html', icon: 'fa-user-shield', label: 'Users' },
        { href: 'company.html', icon: 'fa-building', label: 'Company' }
    ];

    const currentPage = activePage || window.location.pathname.split('/').pop() || 'index.html';
    
    return `
        <aside class="w-64 bg-white border-r border-gray-200 flex flex-col h-full">
            <div class="p-6 border-b border-gray-200">
                <h1 class="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                    <i class="fas fa-book text-blue-600 mr-2"></i>Bookkeeper
                </h1>
            </div>
            <nav class="flex-1 p-4 space-y-2 overflow-y-auto">
                ${menuItems.map(item => `
                    <a href="${item.href}" class="nav-link ${currentPage === item.href ? 'active' : ''}">
                        <i class="fas ${item.icon} w-5"></i>
                        <span>${item.label}</span>
                    </a>
                `).join('')}
            </nav>
            <div class="p-4 border-t border-gray-200 flex-shrink-0">
                <button onclick="window.logout()" class="w-full btn-secondary">
                    <i class="fas fa-sign-out-alt mr-2"></i>Logout
                </button>
            </div>
        </aside>
    `;
}

// Function to initialize sidebar
function initSidebar(activePage) {
    const sidebarContainer = document.getElementById('sidebar-container');
    if (sidebarContainer) {
        sidebarContainer.innerHTML = renderSidebar(activePage);
    }
}

