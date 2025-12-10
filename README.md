# Flat BOM Generator

InvenTree plugin that provides an advanced flat bill of materials viewer with intelligent stock tracking, allocation awareness, and production planning capabilities.

## Features

### 📊 Smart BOM Analysis
- **Leaf-Part Filtering**: Automatically identifies and displays only purchaseable components (Fab Parts, Commercial Parts, and Purchaseable Assemblies)
- **Quantity Deduplication**: Aggregates duplicate parts across the BOM hierarchy with accurate cumulative quantities
- **Part Categorization**: Distinguishes between fabricated parts, commercial parts, and purchaseable assemblies
- **Circular Reference Detection**: Safely handles circular BOM references without infinite loops

### 📦 Stock Intelligence
- **Real-Time Stock Levels**: Shows current inventory with color-coded indicators
- **Allocation Tracking**: Displays stock allocated to build orders and sales orders
- **Available Stock**: Calculates truly available stock (total - allocations)
- **On Order Quantities**: Shows incoming stock from purchase orders
- **Building Quantities**: Tracks parts currently in production

### 🎯 Production Planning
- **Build Quantity Multiplier**: Calculate requirements for any build quantity
- **Flexible Shortfall Calculation**: 
  - Toggle allocations: Use total stock (optimistic) or available stock (realistic)
  - Toggle on-order: Include or exclude incoming stock from shortfall
- **Need to Order Counter**: Instantly see how many parts require purchasing

### 🎨 Modern UI
- **DataTable Interface**: Sortable, filterable, paginated table using Mantine DataTable
- **Search Functionality**: Filter by IPN or part name
- **Visual Indicators**: Color-coded badges for stock levels and part types
- **Statistics Dashboard**: Quick overview of total parts, out of stock, on order, and need to order
- **Part Thumbnails**: Visual identification with inline images
- **Responsive Design**: Works on desktop and mobile

### 📤 Export Capabilities
- **CSV Export**: Download complete BOM with all calculated quantities
- **Includes All Fields**: IPN, name, description, quantities, stock levels, allocations, shortfalls, and suppliers

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
| **Type** | Fab Part (blue), Coml Part (green), or Purchaseable Assembly (orange) |
| **Total Qty** | Required quantity for build (scales with build quantity) with [unit] |
| **In Stock** | Total inventory (green if sufficient, orange if partial, red if none) with [unit] |
| **On Order** | Incoming stock from purchase orders with [unit] |
| **Building** | Stock currently in production |
| **Allocated** | Stock reserved for builds and sales orders with [unit] |
| **Available** | Truly available stock (In Stock - Allocated) |
| **Shortfall** | Deficit to fulfill build (respects checkboxes) |
| **Supplier** | Default supplier name |

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

## Development

Based on battle-tested BOM traversal code from the [OA-Inventree-Cost-Analysis-Plugin](https://github.com/jrobelia/OA-Inventree-Cost-Analysis-Plugin).

