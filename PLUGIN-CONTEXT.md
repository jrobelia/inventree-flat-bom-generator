# Copilot Guide - Flat BOM Generator Plugin

> **Quick reference for AI agents working on this InvenTree plugin**

## Project Overview

InvenTree plugin providing advanced flat bill of materials analysis with intelligent stock tracking, allocation awareness, and production planning capabilities.

**Tech Stack:**
- Backend: Django REST Framework (Python)
- Frontend: React 18 + TypeScript + Mantine UI v7 + mantine-datatable
- Build: Python setuptools + Vite 6
- InvenTree: Plugin system with panel integration

---

## Architecture Overview

```
flat_bom_generator/
├── __init__.py              # Plugin metadata & registration
├── core.py                  # FlatBOMGeneratorPlugin class
├── views.py                 # FlatBOMView API endpoint
├── bom_traversal.py         # Core BOM algorithms
├── categorization.py        # Part type classification
├── serializers.py           # API data serializers
├── static/                  # Compiled frontend assets
└── tests/                   # Unit tests
    ├── test_*.py            # Test modules
    └── test_data/           # Test input data (CSV files)

frontend/
├── src/
│   ├── Panel.tsx           # Main React component
│   ├── locale.tsx          # i18n setup
│   └── vite-env.d.ts       # TypeScript definitions
├── package.json            # Frontend dependencies
└── vite.config.ts          # Build configuration

docs/                        # Documentation & reference
├── README.md                # Documentation overview
├── BOM-ERROR-WARNINGS-RESEARCH.md
├── WARNINGS-ROADMAP.md
├── ARCHITECTURE-WARNINGS.md
├── REFAC-PANEL-PLAN.md
├── PYPI-PUBLISHING-PLAN.md
└── Flat BOM Generator Table.csv  # Reference output format

tools/                       # Development utilities
├── README.md
├── import requests.py       # InvenTree API test script
└── set_default_supplier.py  # Bulk supplier assignment
```

---

## Key Files & Responsibilities

### Backend Files

#### `flat_bom_generator/core.py`
- **Purpose**: Plugin registration with InvenTree
- **Key Class**: `FlatBOMGeneratorPlugin`
- **Exports**:
  - Panel definition: `PANEL_FLAT_BOM`
  - API endpoint: `/plugin/flat-bom-generator/flat-bom/{part_id}/`

#### `flat_bom_generator/views.py`
- **Purpose**: REST API endpoint that enriches BOM data for UI display
- **Endpoint**: `GET /plugin/flat-bom-generator/flat-bom/{part_id}/`
- **Key Responsibilities**:
  - Calls `get_flat_bom()` to get deduplicated leaf parts
  - Enriches with stock data: `total_stock`, `allocated`, `available`, `on_order`, `building`
  - Adds display metadata: `thumbnail`, `image`, `link`, `default_supplier_name`
- **Response Structure**: See API Response Schema below

#### `flat_bom_generator/bom_traversal.py`
- **Purpose**: Core BOM traversal algorithms
- **Critical Functions**:
  1. `traverse_bom()` - Recursive traversal with `visited.copy()` pattern
  2. `get_leaf_parts_only()` - Filters to Fab/Coml/Purchaseable Assembly
  3. `deduplicate_and_sum()` - Aggregates quantities by part_id
  4. `get_flat_bom()` - Orchestrates the 3-step pipeline

**Algorithm Flow:**
```
Part ID → traverse_bom() → get_leaf_parts_only() → deduplicate_and_sum() → Flat BOM
          (build tree)      (filter leaves)         (sum quantities)
```

**Critical Pattern**: `visited.copy()` allows same part in different branches while preventing circular references

#### `flat_bom_generator/categorization.py`
- **Purpose**: Classifies parts into types
- **Function**: `categorize_part(part_name, is_assembly, is_top_level, has_default_supplier)`
- **Categories**:
  - `TLA` - Top Level Assembly
  - `Fab Part` - Fabricated (non-assembly) ← LEAF
  - `Coml Part` - Commercial (non-assembly) ← LEAF
  - `Purchaseable Assembly` - Assembly with default supplier ← LEAF
  - `Assembly` - Standard assembly (not leaf)
  - `Made From` - Fabrication assembly (not leaf)

### Frontend Files

#### `frontend/src/Panel.tsx`
- **Purpose**: Main React component for flat BOM UI
- **Component**: `FlatBOMGeneratorPanel`
- **Key Features**:
  - DataTable with sorting, filtering, pagination
  - Build quantity multiplier
  - Allocation/on-order toggle checkboxes
  - Stats panel with counters
  - CSV export
  - Search by IPN/Part Name

**State Variables:**
```typescript
buildQuantity: number           // Multiplier for requirements
includeAllocations: boolean     // Use available vs total stock
includeOnOrder: boolean         // Include incoming in shortfall
searchQuery: string             // Filter text
sortStatus: DataTableSortStatus // Column + direction
page: number                    // Current page
recordsPerPage: number | 'All'  // Pagination size (can be 'All')
bomData: FlatBomResponse | null // API response
```

**Data Flow:**
```
API Call → bomData → filteredAndSortedData → DataTable
                     (applies search + sort)   (pagination)
```

---

## Data Structures

### BomItem Interface (TypeScript)
```typescript
interface BomItem {
    // Identity
    part_id: number;
    ipn: string;
    part_name: string;
    full_name: string;
    description: string;
    
    // Categorization
    part_type: 'Fab Part' | 'Coml Part' | 'Purchaseable Assembly';
    is_assembly: boolean;
    purchaseable: boolean;
    has_default_supplier: boolean;
    
    // Quantities
    total_qty: number;      // Aggregated from BOM traversal
    unit: string;
    
    // Stock levels
    in_stock: number;       // Total physical stock
    allocated: number;      // Reserved for builds/sales
    available: number;      // in_stock - allocated
    on_order: number;       // Incoming from POs
    building?: number;      // In production
    
    // Display
    image?: string;
    thumbnail?: string;
    link: string;
    default_supplier_name?: string;
}
```

### API Response Schema
```json
{
  "part_id": 123,
  "part_name": "Assembly Name",
  "ipn": "ASM-001",
  "total_unique_parts": 45,
  "total_imps_processed": 12,
  "bom_items": [/* array of BomItem */]
}
```

---

## Critical Calculations

### Shortfall Calculation
```typescript
const stockToUse = includeAllocations ? record.available : record.in_stock;
const onOrderToUse = includeOnOrder ? record.on_order : 0;
const totalRequired = record.total_qty * buildQuantity;
const shortfall = Math.max(0, totalRequired - stockToUse - onOrderToUse);
```

### Stock Allocations (Backend)
```python
allocated = part_obj.allocation_count()  # Sum of build + sales order allocations
available = part_obj.available_stock     # Property: total_stock - allocation_count()
```

---

## DataTable Column Configuration

**12 Columns** (all sortable):
1. **Component** - Thumbnail + clickable full_name
2. **IPN** - Monospace font
3. **Description** - Line clamped
4. **Type** - Badge (blue/green/orange/cyan/grape/violet/indigo)
5. **Total Qty** - Scaled by buildQuantity with [unit]
6. **In Stock** - Color badge (green/orange/red) with [unit]
7. **On Order** - Blue badge if > 0 with [unit]
8. **Building** - Cyan badge if > 0
9. **Allocated** - Yellow badge if > 0 with [unit]
10. **Available** - Color badge (green/orange/red) based on requirement
11. **Shortfall** - Red badge or green checkmark (uses toggles)
12. **Supplier** - Default supplier name

**Sort Logic Location**: `filteredAndSortedData` useMemo hook (lines ~180-260)

---

## Common Modification Patterns

### Adding a New Column
1. Update `BomItem` interface in `Panel.tsx`
2. Add field to enrichment in `views.py` (backend)
3. Add column definition to `columns` array
4. Add sort case in `switch` statement
5. Update CSV export headers and data mapping
6. Update `columns` dependency array

### Modifying Calculations
1. **Shortfall**: Update render function in shortfall column + sort logic
2. **Stock levels**: Modify enrichment in `views.py`
3. **Quantities**: Check `deduplicate_and_sum()` in `bom_traversal.py`

### Changing Filters
1. Update `filteredAndSortedData` useMemo hook
2. Ensure dependency array includes all state variables used
3. Update filter UI components if needed

---

## Build & Deployment

### Local Development
```bash
# Frontend hot reload
npm run dev

# Build frontend
npm run build

# Build Python package
python -m build
```

### Deployment (via toolkit scripts)
```powershell
# Build + Deploy in one step
.\scripts\Deploy-Plugin.ps1 -Plugin FlatBOMGenerator -Server staging

# Build only
.\scripts\Build-Plugin.ps1 -Plugin FlatBOMGenerator
```

### Build Output
- Frontend: Compiles to `flat_bom_generator/static/Panel.js`
- Python: Creates `.whl` file in `dist/`

---

## Testing Checklist

**Backend:**
- [ ] Circular BOM references handled gracefully
- [ ] Duplicate parts aggregated correctly
- [ ] Leaf-part filtering (no assemblies unless purchaseable)
- [ ] Stock calculations (allocated, available) accurate

**Frontend:**
- [ ] All columns sortable
- [ ] Search filters IPN and Part Name
- [ ] Checkboxes affect shortfall calculation
- [ ] Build quantity multiplies all requirements
- [ ] Stats panel counts update dynamically
- [ ] CSV export includes all fields
- [ ] Pagination includes "All" option and works correctly
- [ ] Component column displays full_name instead of part_name
- [ ] Unit display [unit] appears on Total Qty, In Stock, Allocated, and On Order columns
- [ ] IMP Processed counter displays in statistics panel

**Integration:**
- [ ] Panel appears on assembly part pages
- [ ] Generate button triggers API call
- [ ] Refresh button reloads data
- [ ] Loading states display correctly
- [ ] Error handling shows user-friendly messages

---

## Known Patterns & Conventions

### InvenTree Integration
- Plugin panels use `InvenTreePluginContext` for part data
- Part ID from: `context?.id || context?.instance?.pk`
- API calls via: `context.api.get()`

### React Patterns
- Mantine UI components for all UI elements
- `useMemo` for expensive computations (filtering, sorting)
- Color scheme: green (good), orange (warning), red (critical), blue (info), cyan (building), yellow (allocated)

### Python Patterns
- Django ORM with `select_related()` for performance
- Logger: `logger = logging.getLogger('inventree')`
- Always handle `Part.DoesNotExist` exceptions

---

## File Change Impact Map

| Change This... | May Require Updating... |
|----------------|-------------------------|
| BomItem interface | views.py enrichment, columns array, CSV export |
| Shortfall calculation | Shortfall column render, sort logic, "Need to Order" stat |
| New state variable | Dependency arrays in useMemo hooks |
| API response structure | TypeScript interfaces, error handling |
| BOM traversal logic | Unit tests, documentation |
| Stock calculations | Backend views.py, frontend calculations |

---

## Performance Considerations

- **Backend**: Use `select_related()` to prefetch related models (default_supplier)
- **Frontend**: `useMemo` for filtering/sorting large datasets
- **Pagination**: Defaults to 50 items per page, adjustable
- **Search**: Only searches IPN and Part Name (not description) for speed

---

## Version Information

- **InvenTree**: Compatible with stable branch API
- **React**: 18.x
- **Mantine**: 7.x
- **DataTable**: mantine-datatable 8.2.0
- **Python**: 3.8+
- **Django**: Via InvenTree version

---

## Quick Command Reference

```bash
# Install dependencies
npm install

# TypeScript check
npm run tsc

# Build for production
npm run build

# Format code
npx biome format --write .
```

---

## Troubleshooting

**"Column not sorting"**: Add accessor case to switch statement in sort logic

**"Checkbox not affecting calculation"**: Check dependency arrays and calculation functions

**"API returning wrong data"**: Verify enrichment in views.py and field names match BomItem interface

**"Build fails"**: Check TypeScript errors with `npm run tsc`, ensure all imports exist

**"Frontend changes not showing"**: Run `npm run build` then rebuild plugin package

---

## Documentation Maintenance

### Keeping Documentation Current

This plugin has three documentation files that must stay synchronized with code:

1. **README.md** - User-facing feature documentation
2. **COPILOT-GUIDE.md** - This file, developer/AI reference
3. **TEST-PLAN.md** - Test cases and verification procedures

### When to Update Documentation

Update documentation immediately when you change:

#### UI Changes
- [ ] Column names, headers, or labels → Update README Table Columns section
- [ ] Pagination options → Update README and this file's state variables
- [ ] Statistics panel counters → Update README Usage section
- [ ] Data display formats (e.g., adding units) → Update README and examples

#### Data/API Changes
- [ ] BomItem interface fields → Update this file's interface definition
- [ ] API response structure → Update README API section and this file
- [ ] New query parameters → Update README API docs
- [ ] Field name changes → Update all documentation examples

#### Code Structure Changes
- [ ] Component state variables → Update this file's State Variables section
- [ ] Column definitions → Update this file's DataTable section
- [ ] New utility functions → Add to this file's Key Files section

### Documentation Update Checklist

After making code changes, verify:

- [ ] **README.md**
  - [ ] Features list is accurate
  - [ ] Table columns match UI
  - [ ] API examples work
  - [ ] Usage instructions are current
  - [ ] Note if screenshots are outdated

- [ ] **COPILOT-GUIDE.md** (this file)
  - [ ] Interfaces match code
  - [ ] State variables are accurate
  - [ ] Column descriptions are current
  - [ ] Modification patterns still work

- [ ] **TEST-PLAN.md**
  - [ ] New features have test cases
  - [ ] UI checklist includes new elements
  - [ ] Manual verification steps are complete

### Quick Documentation Audit

Run this mental checklist periodically:

1. Open README.md → Does the table column description match the UI?
2. Check "Table Columns" section → Are all columns listed and accurate?
3. Review API response example → Does it match current backend?
4. Check COPILOT-GUIDE interfaces → Do they match Panel.tsx?
5. Review TEST-PLAN UI checklist → Does it cover current features?

### Documentation Verification Schedule

**After Every Feature Addition:**
- Update relevant sections immediately

**Before Staging Deployment:**
- Quick audit of all three files

**Before Production Deployment:**
- Full documentation review

**Monthly (for Mature Plugins):**
- Comprehensive documentation verification

### Handling Documentation Debt

If you skip documentation updates during development:

1. **Mark Sections**: Add `<!-- NEEDS UPDATE: [reason] -->` comments
2. **Create List**: Document what needs updating in commit message
3. **Schedule Review**: Allocate time before next deployment
4. **Prioritize User Docs**: README.md updates are most critical

**Example Comment:**
```markdown
<!-- NEEDS UPDATE: Column changed from "Part" to "Component" on 2025-12-10 -->
| **Part** | Part name with thumbnail |
```

---

*Last Updated: December 10, 2025*
*Documentation Maintenance Section Added: December 10, 2025*
