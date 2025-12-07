# Excel-like Table Libraries for Bookkeeper Reports

This document provides recommendations for displaying CSV reports in an Excel-like format within the bookkeeping application.

## Current Setup

The application currently uses **vanilla JavaScript** (not React), so all recommendations are for vanilla JS or framework-agnostic libraries.

## Recommended Libraries

### 1. **Tabulator.js** ⭐ (Recommended)

**Best for:** Vanilla JS applications, free and open-source

**Features:**
- Excel-like appearance and behavior
- Sorting, filtering, pagination
- Column resizing and reordering
- Cell editing
- Export to Excel/CSV/PDF
- Responsive design
- Free and open-source (MIT License)

**Installation:**
```bash
npm install tabulator-tables
# OR via CDN
<script src="https://unpkg.com/tabulator-tables@5.5.2/dist/js/tabulator.min.js"></script>
<link href="https://unpkg.com/tabulator-tables@5.5.2/dist/css/tabulator.min.css" rel="stylesheet">
```

**Usage Example:**
```javascript
// Load CSV data and display in Tabulator
async function displayReport(endpoint) {
    const response = await fetch(`${API_BASE}${endpoint}`);
    const csvText = await response.text();
    const data = parseCSV(csvText);
    
    new Tabulator("#report-table", {
        data: data,
        layout: "fitColumns",
        pagination: true,
        paginationSize: 50,
        movableColumns: true,
        resizableColumns: true,
        initialSort: [{column: "Date", dir: "desc"}]
    });
}
```

**Documentation:** https://tabulator.info/

---

### 2. **ag-Grid Community Edition**

**Best for:** Enterprise-grade features, large datasets

**Features:**
- Very fast rendering (virtual scrolling)
- Excel-like filtering and sorting
- Column grouping and pivoting
- Cell editing and validation
- Export to Excel/CSV
- Free Community Edition (MIT License)
- Enterprise features available (paid)

**Installation:**
```bash
npm install ag-grid-community
# OR via CDN
<script src="https://cdn.jsdelivr.net/npm/ag-grid-community@31.0.0/dist/ag-grid-community.min.js"></script>
```

**Usage Example:**
```javascript
const gridOptions = {
    columnDefs: [
        { field: 'Date', sortable: true, filter: true },
        { field: 'Particulars', sortable: true, filter: true },
        { field: 'Debit', sortable: true, filter: 'agNumberColumnFilter' },
        { field: 'Credit', sortable: true, filter: 'agNumberColumnFilter' }
    ],
    defaultColDef: {
        resizable: true,
        sortable: true,
        filter: true
    },
    rowData: data
};

new agGrid.Grid(document.querySelector('#report-grid'), gridOptions);
```

**Documentation:** https://www.ag-grid.com/

---

### 3. **Handsontable**

**Best for:** True Excel-like editing experience

**Features:**
- Excel-like cell editing
- Copy/paste from Excel
- Formula support
- Data validation
- Cell formatting
- **Note:** Free for non-commercial use, requires license for commercial projects

**Installation:**
```bash
npm install handsontable
```

**Documentation:** https://handsontable.com/

---

## Comparison Table

| Library | License | Vanilla JS | Performance | Excel Export | Best For |
|---------|---------|------------|-------------|--------------|----------|
| **Tabulator.js** | MIT (Free) |  Yes | ⭐⭐⭐⭐ |  Built-in | General use, easy setup |
| **ag-Grid** | MIT (Community) |  Yes | ⭐⭐⭐⭐⭐ |  Built-in | Large datasets, enterprise |
| **Handsontable** | Commercial |  Yes | ⭐⭐⭐ |  Built-in | Excel editing, formulas |

## Recommendation for Bookkeeper

**Use Tabulator.js** because:
1.  Free and open-source (no licensing concerns)
2.  Works perfectly with vanilla JavaScript
3.  Easy to integrate with existing codebase
4.  Excel-like appearance and features
5.  Built-in CSV/Excel export
6.  Good documentation and community support
7.  Lightweight and performant

## Implementation Plan

### Phase 1: Basic Table View
1. Add Tabulator.js via CDN to reports page
2. Create a modal/dialog to view reports
3. Parse CSV data and display in Tabulator
4. Add basic sorting and filtering

### Phase 2: Enhanced Features
1. Add column resizing and reordering
2. Implement pagination for large reports
3. Add export buttons (Excel, PDF, CSV)
4. Add search/filter functionality

### Phase 3: Advanced Features (Optional)
1. Cell editing (for manual adjustments)
2. Column grouping
3. Custom formatting (currency, dates)
4. Print functionality

## Example Integration

### Step 1: Add Tabulator to reports.html
```html
<!-- Add to <head> -->
<link href="https://unpkg.com/tabulator-tables@5.5.2/dist/css/tabulator.min.css" rel="stylesheet">
<script src="https://unpkg.com/tabulator-tables@5.5.2/dist/js/tabulator.min.js"></script>
```

### Step 2: Add View Button to Report Cards
```javascript
// In renderReportCard function
<a href="#" onclick="viewReport('${report.endpoint}'); return false;" class="btn-secondary mr-2">
    <i class="fas fa-eye mr-2"></i>View
</a>
```

### Step 3: Create View Function
```javascript
async function viewReport(endpoint) {
    // Fetch CSV
    const response = await fetch(`${API_BASE}${endpoint}`);
    const csvText = await response.text();
    
    // Parse CSV (use PapaParse or simple parser)
    const data = parseCSV(csvText);
    
    // Create modal with Tabulator
    const modal = createModal();
    new Tabulator(modal.querySelector('#report-table'), {
        data: data,
        layout: "fitColumns",
        pagination: true,
        paginationSize: 50
    });
}
```

## Alternative: Supabase Grid (Not Recommended)

Supabase previously had a `@supabase/grid` component, but:
- ❌ It's now deprecated and read-only
- ❌ Designed specifically for Supabase PostgreSQL tables
- ❌ Not suitable for CSV data display
- ❌ Requires React

## Next Steps

1. **Choose a library** (recommend Tabulator.js)
2. **Test with sample CSV data** from reports
3. **Integrate into reports.html** with a "View" button
4. **Add export functionality** for Excel/PDF
5. **Test with real report data**

## Resources

- Tabulator.js: https://tabulator.info/
- ag-Grid: https://www.ag-grid.com/
- Handsontable: https://handsontable.com/
- CSV Parser (PapaParse): https://www.papaparse.com/

