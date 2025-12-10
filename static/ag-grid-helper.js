// AG Grid Helper - Shared utilities and configurations
// AG Grid Community Edition (free) with filtering, sorting, and basic features

// Common cell renderers
const cellRenderers = {
    // Badge renderer for status/type columns
    badge: (params) => {
        const value = params.value || '';
        const type = params.colDef.badgeType || 'default';
        const badgeClasses = {
            'success': 'bg-green-100 text-green-800',
            'error': 'bg-red-100 text-red-800',
            'warning': 'bg-yellow-100 text-yellow-800',
            'info': 'bg-blue-100 text-blue-800',
            'default': 'bg-gray-100 text-gray-800'
        };
        const className = badgeClasses[type] || badgeClasses.default;
        return `<span class="px-2 py-1 rounded-full text-xs font-medium ${className}">${escapeHtml(value)}</span>`;
    },
    
    // Date renderer
    date: (params) => {
        if (!params.value) return '-';
        const date = new Date(params.value);
        return date.toLocaleDateString('en-IN', { 
            year: 'numeric', 
            month: 'short', 
            day: 'numeric' 
        });
    },
    
    // Currency renderer (Indian Rupees)
    currency: (params) => {
        if (params.value === null || params.value === undefined) return '-';
        return `₹${Number(params.value).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    },
    
    // Actions renderer (buttons)
    actions: (params) => {
        const actions = params.colDef.actions || [];
        return actions.map(action => {
            const icon = action.icon || 'fa-edit';
            const color = action.color || 'text-blue-600';
            return `<button 
                onclick="${action.onClick}(event, ${params.data[params.colDef.idField || 'id']})" 
                class="${color} hover:opacity-75 p-1 rounded transition-colors" 
                title="${action.title || ''}"
            >
                <i class="fas ${icon}"></i>
            </button>`;
        }).join(' ');
    }
};

// Helper function to escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Default column definitions with common settings
function getDefaultColDef() {
    return {
        sortable: true,
        filter: true,
        resizable: true,
        floatingFilter: false, // Hide filter inputs by default for simpler view
        menuTabs: ['filterMenuTab'] // Only show filter menu
    };
}

// Common filter configurations
const filterConfigs = {
    text: {
        filter: 'agTextColumnFilter',
        filterParams: {
            debounceMs: 200,
            buttons: ['reset', 'apply']
        }
    },
    number: {
        filter: 'agNumberColumnFilter',
        filterParams: {
            debounceMs: 200,
            buttons: ['reset', 'apply']
        }
    },
    date: {
        filter: 'agDateColumnFilter',
        filterParams: {
            debounceMs: 200,
            buttons: ['reset', 'apply'],
            comparator: (filterLocalDateAtMidnight, cellValue) => {
                const cellDate = new Date(cellValue);
                if (cellDate < filterLocalDateAtMidnight) {
                    return -1;
                } else if (cellDate > filterLocalDateAtMidnight) {
                    return 1;
                } else {
                    return 0;
                }
            }
        }
    }
};

// Initialize AG Grid with common configuration
function initAGGrid(containerId, columnDefs, rowData, options = {}) {
    const defaultOptions = {
        defaultColDef: getDefaultColDef(),
        columnDefs: columnDefs,
        rowData: rowData,
        pagination: true,
        paginationPageSize: 50,
        paginationPageSizeSelector: [25, 50, 100, 200],
        domLayout: 'normal',
        suppressMenuHide: true,
        animateRows: true,
        rowSelection: options.rowSelection || 'single',
        enableRangeSelection: false,
        suppressRowClickSelection: options.suppressRowClickSelection || false,
        onGridReady: (params) => {
            // Auto-size columns on first load
            if (params.api && params.api.sizeColumnsToFit) {
                params.api.sizeColumnsToFit();
            }
            if (options.onGridReady) {
                options.onGridReady(params);
            }
        },
        onFirstDataRendered: (params) => {
            // Auto-size columns after data is loaded
            if (params.api && params.api.sizeColumnsToFit) {
                params.api.sizeColumnsToFit();
            }
            if (options.onFirstDataRendered) {
                options.onFirstDataRendered(params);
            }
        }
    };
    
    // Merge user options, allowing them to override defaults
    const gridOptions = Object.assign({}, defaultOptions, options);
    
    const gridDiv = document.querySelector(`#${containerId}`);
    if (!gridDiv) {
        console.error(`Grid container #${containerId} not found`);
        return null;
    }
    
    // Clear any existing content
    gridDiv.innerHTML = '';
    
    // Create and initialize grid
    const gridApi = agGrid.createGrid(gridDiv, gridOptions);
    
    return gridApi;
}

// Update grid data
function updateGridData(gridApi, newData) {
    if (gridApi && gridApi.api) {
        gridApi.api.setGridOption('rowData', newData);
    }
}

// Export grid data to CSV
function exportGridToCSV(gridApi, filename = 'export.csv') {
    if (gridApi && gridApi.api) {
        gridApi.api.exportDataAsCsv({
            fileName: filename
        });
    }
}

// Get selected rows
function getSelectedRows(gridApi) {
    if (gridApi && gridApi.api) {
        return gridApi.api.getSelectedRows();
    }
    return [];
}

// Make functions available globally
window.agGridHelper = {
    cellRenderers,
    getDefaultColDef,
    filterConfigs,
    initAGGrid,
    updateGridData,
    exportGridToCSV,
    getSelectedRows,
    escapeHtml
};

