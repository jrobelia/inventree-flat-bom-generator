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
└── static/                  # Compiled frontend assets

frontend/
├── src/
│   ├── Panel.tsx           # Main React component
│   ├── locale.tsx          # i18n setup
│   └── vite-env.d.ts       # TypeScript definitions
├── package.json            # Frontend dependencies
└── vite.config.ts          # Build configuration
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
recordsPerPage: number          // Pagination size
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
1. **Part** - Thumbnail + clickable name
2. **IPN** - Monospace font
3. **Description** - Line clamped
4. **Type** - Badge (blue/green/orange)
5. **Total Qty** - Scaled by buildQuantity
6. **In Stock** - Color badge (green/orange/red)
7. **On Order** - Blue badge if > 0
8. **Building** - Cyan badge if > 0
9. **Allocated** - Yellow badge if > 0
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

*Last Updated: December 2025*
