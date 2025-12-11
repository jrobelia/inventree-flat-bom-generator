# Flat BOM Generator

InvenTree plugin that flattens nested bill of materials into a single-level view of purchaseable components with automatic quantity aggregation.

## What This Plugin Adds

InvenTree's built-in BOM view shows the hierarchical structure. This plugin **flattens** that hierarchy into a purchasing-focused view by:

### Core Functionality

- **Automatic Leaf-Part Extraction**: Traverses the entire BOM tree and extracts only the purchaseable leaf components (Fab Parts, Commercial Parts, Purchaseable Assemblies), filtering out intermediate assemblies
- **Quantity Deduplication**: When a part appears multiple times in different branches of the BOM, automatically aggregates the total quantity needed
- **Flexible Shortfall Planning**: Toggle between optimistic (ignore allocations) and realistic (account for allocated stock) planning modes
- **On-Order Awareness**: Choose whether to include incoming purchase orders in your shortfall calculations

### User Interface

- **Single-Page View**: See all purchaseable components in one table instead of navigating through BOM levels
- **Interactive Controls**: Adjust build quantity and instantly see scaled requirements across all parts
- **Planning Toggles**: Switch between planning scenarios (with/without allocations, with/without on-order) in real-time
- **CSV Export**: Export the complete flat BOM with all calculated quantities for purchasing workflows

### Why This Matters

When planning a build, you typically need to answer: "What parts do I need to order?" InvenTree's hierarchical BOM view requires manual traversal and calculation. This plugin automates that process by:

1. Traversing multi-level BOMs automatically
2. Aggregating duplicate parts across branches
3. Calculating cumulative quantities through the hierarchy
4. Presenting a single, actionable purchasing list

## Installation

### From PyPI (Recommended)

```bash
pip install inventree-flat-bom-generator
```

### From Source

```bash
git clone https://github.com/yourusername/inventree-flat-bom-generator.git
cd inventree-flat-bom-generator
pip install -e .
```

### InvenTree Plugin Manager

1. Navigate to **Settings → Plugins**
2. Search for "Flat BOM Generator"  
3. Click **Install**
4. Enable the plugin and restart InvenTree

## Usage

### Interactive UI Panel

The plugin adds a "Flat BOM Viewer" panel to assembly part pages:

1. **Navigate** to any assembly part in InvenTree
2. **Click** "Generate Flat BOM" to analyze the complete hierarchy
3. **Adjust** build quantity to see scaled requirements
4. **Toggle** allocation and on-order checkboxes to customize shortfall calculation
5. **Search** and filter the results table
6. **Export** to CSV for further analysis or purchasing

### Controls

**Build Quantity**
- Set the number of units you plan to build
- All quantities scale automatically

**Include Allocations in Shortfall** (Checkbox)
- ✅ Checked: Shortfall based on available stock (total - allocations) - *Realistic view*
- ☐ Unchecked: Shortfall based on total stock - *Optimistic view*

**Include On Order in Shortfall** (Checkbox)  
- ✅ Checked: Incoming stock reduces shortfall - *Standard planning*
- ☐ Unchecked: Ignore incoming stock - *Conservative planning*

### Statistics Panel

- **Total Parts**: Number of unique purchaseable components
- **IMP Processed**: Number of Internally Manufactured Parts (IMPs) processed during BOM traversal
- **Out of Stock**: Parts with zero inventory
- **On Order**: Parts with incoming purchase orders
- **Need to Order**: Parts with shortfall (respects checkbox settings)

### Table Columns

| Column | Description |
|--------|-------------|
| **Component** | Full part name with thumbnail image (clickable link) |
| **IPN** | Internal Part Number |
| **Description** | Part description |
| **Type** | Fab Part (blue), Coml Part (green), IMP (cyan), Purchaseable Assembly (orange), or Unknown (gray) |
| **Total Qty** | Required quantity for build (scales with build quantity) with [unit] |
| **In Stock** | Total inventory (green if sufficient, orange if partial, red if none) with [unit] |
| **Allocated** | Stock reserved for builds and sales orders with [unit] (dimmed when checkbox unchecked) |
| **On Order** | Incoming stock from purchase orders with [unit] (dimmed when checkbox unchecked) |
| **Shortfall** | Deficit to fulfill build (respects allocation and on-order checkboxes) |

All columns are **sortable** and the table is **paginated** (10/25/50/100/All per page).

## API Endpoint

### Get Flat BOM

```
GET /api/plugin/flat-bom-generator/flat-bom/{part_id}/
```

**Query Parameters:**
- `max_depth` (optional): Maximum BOM traversal depth

**Response:**
```json
{
  "part_id": 123,
  "part_name": "Main Assembly",
  "ipn": "ASM-001",
  "total_unique_parts": 45,
  "total_imps_processed": 12,
  "bom_items": [
    {
      "part_id": 456,
      "ipn": "FAB-100",
      "part_name": "Fabricated Bracket",
      "full_name": "Bracket, Mounting, Steel - FAB-100",
      "description": "Steel mounting bracket",
      "part_type": "Fab Part",
      "total_qty": 2.0,
      "unit": "pcs",
      "is_assembly": false,
      "purchaseable": true,
      "has_default_supplier": true,
      "in_stock": 50.0,
      "allocated": 10.0,
      "available": 40.0,
      "on_order": 100.0,
      "building": 0.0,
      "default_supplier_name": "Acme Manufacturing",
      "thumbnail": "/media/part_images/fab-100_thumbnail.jpg",
      "link": "/part/456/"
    }
  ]
}
```

## How It Works

### BOM Traversal Algorithm

The plugin uses a battle-tested recursive traversal with the `visited.copy()` pattern:

1. **Traverse**: Build complete BOM tree with cumulative quantities
   - Uses `visited.copy()` to allow same part in different branches
   - Detects and prevents circular references
   - Calculates cumulative quantities through multiplication

2. **Filter**: Extract only leaf parts (purchaseable components)
   - Fab Parts: Fabricated, non-assembly parts
   - Coml Parts: Commercial, non-assembly parts  
   - Purchaseable Assemblies: Assemblies with default suppliers (treated as purchaseable units)

3. **Deduplicate**: Sum quantities for parts appearing multiple times
   - Groups by part_id
   - Aggregates cumulative quantities
   - Preserves metadata

### Stock Calculations

**Total Stock** = Physical inventory in InvenTree

**Allocated** = `allocation_count()` - Stock reserved for:
- Build orders (in production)
- Sales orders (promised to customers)

**Available** = Total Stock - Allocated

**Shortfall** = Total Required - Stock Used - (On Order if enabled)
- Where Stock Used = Available (if allocations enabled) or Total (if disabled)
- `level`: Depth in the BOM tree (0 = top level)
- `parent_ipn`: IPN of the parent part
- `cumulative_qty`: Total quantity needed for one unit of the top assembly

