# Flat BOM Generator for InvenTree

**Version:** 0.9.2 | **InvenTree:** 1.1.6+

> Personal project for automated flat BOM generation. Currently in testing phase and undergoing refactoring to improve code quality. Feedback and bug reports welcome!

InvenTree plugin that flattens nested bill of materials into a single-level view of purchaseable components with automatic quantity aggregation.  This is the first of three plugins I would like to develop to enhance InvenTree's manufacturing planning capabilities for assemblies with many layers of nesting sub-assemblies.  They create actionable but temporary lists that can be used for manufacturing and purchasing purposes.  This plugin focuses on generating a flat BOM for high level planning and purchasing purposes based on an assembly BOM.  The other two plugins would focus on semi-automated BO and PO generation based on a top level Build Order, possibly using project based part allocation.

## What This Plugin Adds

InvenTree's built-in BOM view shows the hierarchical structure. This plugin **flattens** that hierarchy into a purchasing-focused view by:

### Core Functionality

- **Automatic Leaf-Part Extraction**: Traverses the entire BOM tree and extracts only the purchaseable leaf components (Fab Parts, Commercial Parts, Purchaseable Assemblies), filtering out intermediate assemblies
- **Quantity Deduplication**: When a part appears multiple times in different branches of the BOM, automatically aggregates the total quantity needed
- **Flexible Build Margin Planning**: Toggle between optimistic (ignore allocations) and realistic (account for allocated stock) planning modes
- **On-Order Awareness**: Choose whether to include incoming purchase orders in your Build Margin calculations

### Warning System

The plugin automatically detects and flags potential BOM issues:

- **Unit Mismatch Detection**: Flags when parts at the same BOM level use different units (e.g., mixing "pcs" and "grams")
- **Inactive Part Detection**: Warns when BOM contains inactive parts that may not be orderable
- **Assembly Without Children**: Identifies assemblies marked as assemblies but with no BOM items defined
- **Max Depth Exceeded**: Alerts when BOM traversal hits the configured depth limit (prevents infinite loops)

Warnings appear in a summary panel and help identify data quality issues before manufacturing.

### User Interface

- **Single-Page View**: See all purchaseable components in one table instead of navigating through BOM levels
- **Interactive Controls**: Adjust build quantity and instantly see scaled requirements across all parts
- **Planning Toggles**: Switch between planning scenarios (with/without allocations, with/without on-order) in real-time
- **CSV Export**: Export the complete flat BOM with all calculated quantities for purchasing workflows

*Screenshot: Main panel view with controls and BOM table*  
![FlatBOMGenerator panel showing generate button, controls, statistics panel, and full BOM table](imgs/flat-bom-panel-overview.png)

### Why This Matters

When planning a build, you typically need to answer: "What parts do I need to order?" InvenTree's hierarchical BOM view requires manual traversal and calculation. This plugin automates that process by:

1. Traversing multi-level BOMs automatically
2. Aggregating duplicate parts across branches
3. Calculating cumulative quantities through the hierarchy
4. Presenting a single, actionable purchasing list

### Performance Note

**Each generation request performs a complete recursive BOM traversal with no caching.** For large assemblies (1000+ parts, 10+ levels deep), this can take several seconds. The plugin:
- Traverses every part in the BOM hierarchy from scratch
- Calculates cumulative quantities through all levels
- Filters and deduplicates results

Consider using the optional `max_depth` parameter for very deep BOMs to limit traversal depth if appropriate.

## Installation

### Option 1: Install from Git (Recommended for Production)

**For Docker:**
```bash
# Add to your InvenTree data/plugins.txt file:
git+https://github.com/jrobelia/inventree-flat-bom-generator.git

# Then restart InvenTree
docker-compose restart
```

**For Bare Metal:**
```bash
# Install directly via pip
pip install git+https://github.com/jrobelia/inventree-flat-bom-generator.git

# Then restart InvenTree
```

**Enable the plugin:**
- Navigate to **Settings → Plugins** in InvenTree
- Find "Flat BOM Generator" in the list
- Toggle to enable and restart InvenTree

### Option 2: Development Installation (Editable Mode)

**For Docker:**

1. **On your Docker host**, navigate to your InvenTree installation directory:
   ```bash
   cd /path/to/inventree  # Directory containing docker-compose.yml
   ```

2. **Clone into the plugins directory:**
   ```bash
   git clone https://github.com/jrobelia/inventree-flat-bom-generator.git data/plugins/inventree-flat-bom-generator
   ```

3. **Install in editable mode:**
   ```bash
   docker-compose exec inventree-server pip install -e /home/inventree/data/plugins/inventree-flat-bom-generator
   ```

4. **Restart InvenTree:**
   ```bash
   docker-compose restart
   ```

**For Bare Metal:**

1. **Navigate to the InvenTree data directory:**
   ```bash
   cd /path/to/inventree/data  # Your InvenTree data folder
   ```

2. **Clone and install:**
   ```bash
   git clone https://github.com/jrobelia/inventree-flat-bom-generator.git plugins/inventree-flat-bom-generator
   cd plugins/inventree-flat-bom-generator
   pip install -e .
   ```

3. **Restart InvenTree**

**Enable the plugin:**
- Navigate to **Settings → Plugins** in InvenTree
- Find "Flat BOM Generator" in the list  
- Toggle to enable and restart InvenTree

## Configuration

After enabling the plugin, configure it in **Settings → Plugins → Flat BOM Generator**:

### Plugin Settings

| Setting | Description | Default |
|---------|-------------|---------|
| **Maximum Traversal Depth** | Maximum depth to traverse BOM hierarchy. Set to 0 for unlimited depth. Use positive values (e.g., 5) to limit traversal for very deep BOMs and improve performance. | `0` (unlimited) |
| **Expand Purchased Assemblies** | When enabled, expands the BOM for assemblies that have a default supplier (normally treated as purchaseable units). Useful to see internal components of purchased sub-assemblies. | `False` |
| **Primary Internal Supplier** | Your primary internal manufacturing company/supplier. Parts with this supplier will be categorized as Internal Fab and automatically expanded during traversal. | None |
| **Additional Internal Suppliers** | Comma-separated list of additional internal supplier IDs (e.g., "5,12"). Parts with these suppliers are also treated as internal. Leave empty if you only have one internal supplier. | Empty |
| **Fabrication Category** | InvenTree category for fabricated parts. Parts in this category (or child categories) will be classified as Fab or Internal Fab. Required for proper categorization. | None |
| **Commercial Category** | InvenTree category for commercial/COTS parts. Parts in this category (or child categories) will be classified as Coml. Required for proper categorization. | None |
| **Assembly Category** | InvenTree category for assemblies. Used to identify assembly parts. Optional - assemblies are also identified by the `is_assembly` flag. | None |
| **Cut-to-Length Category** | InvenTree category for cut-to-length raw materials (wire, bar stock, etc.). Parts in this category with length in BOM notes will be classified as CtL. Optional but recommended if you use cut-to-length parts. | None |
| **Enable Internal Fab Cuts** | When enabled, parts categorized as Internal Fab with cut-to-length data will have their cuts aggregated and displayed. | `False` |
| **Internal Fab Cut Units** | Unit to use for internal fab cut list aggregation (e.g., "mm", "inch", "cm"). Only applies when Enable Internal Fab Cuts is enabled. | `mm` |

**Part Type Categorization:**
- Parts are automatically categorized based on these settings
- **Fab Part** (blue badge): In Fabrication category, non-assembly
- **Coml Part** (green badge): In Commercial category, non-assembly  
- **Internal Fab** (cyan badge): Assembly in Fabrication category with internal default supplier, will be expanded to show components
- **Purchaseable Assembly** (orange badge): Assembly with external default supplier, treated as purchaseable unit
- **Unknown** (gray badge): Doesn't match any category (common if categories not configured)
- **Standard Assemblies**: Assembly without default supplier, not categorized because they are expanded during traversal and not displayed in the final flat BOM

## Part Categorization Reference

The plugin uses the following logic to categorize parts and determine whether they appear in the flat BOM:

| Part Type | Category | is_assembly | default_supplier | supplier source | Appears in Flat BOM | Description |
|-----------|----------|-------------|------------------|-----------------|---------------------|-------------|
| **Coml** | Commercial | FALSE | any/none | any | ✅ YES | Off-the-shelf parts you buy but didn't design |
| **Internal Fab** | Fabricated | TRUE | required | internal | ❌ NO (expands) | CNC, 3D print, cut pieces - BOM must contain materials part is made from |
| **CtL** | Fabricated → Cut to Length | FALSE | any/none | any | ✅ YES | Wire, bar stock, etc. - Length stored in BOM line item note field |
| **Fab** | Fabricated | FALSE | any/none | any | ✅ YES | Machining, PCB - Standard part made externally from a drawing |
| **Assy** | Assembly | TRUE | none/internal | internal | ❌ NO (expands) | Standard assembly done in-house |
| **Purchased Assy** | Assembly | TRUE | required | external | ✅ YES | PCBA, wire harness, etc. - Purchased complete with external supplier |

### Understanding Default Suppliers

**Critical Concept:** Default suppliers determine how assemblies are treated during BOM traversal.

**Why This Matters:**
- **External Default Supplier** → Assembly appears in flat BOM as a purchaseable unit (Purchased Assy)
- **Internal Default Supplier** → Assembly is expanded, showing its component parts (Internal Fab)
- **No Default Supplier** → Assembly is expanded, showing its component parts (Standard Assy)

**Example Scenarios:**

1. **PCBA with External Supplier**: A circuit board assembled by a contract manufacturer
   - `is_assembly` = TRUE
   - `default_supplier` = "ACME PCB Assembly Co"
   - **Result**: Appears in flat BOM as "Purchased Assy", BOM is NOT expanded
   - **Why**: You purchase it complete, don't need to buy individual resistors/capacitors

2. **Internal Fabrication Assembly**: A CNC machined part made in-house
   - `is_assembly` = TRUE  
   - `default_supplier` = Your internal supplier company
   - **Result**: Does NOT appear in flat BOM, BOM IS expanded
   - **Why**: Plugin shows raw materials needed (bar stock, etc.), not the fabricated part itself

3. **Standard Assembly**: A sub-assembly built in-house
   - `is_assembly` = TRUE
   - `default_supplier` = None
   - **Result**: Does NOT appear in flat BOM, BOM IS expanded
   - **Why**: Plugin shows component parts you need to order, not the sub-assembly

**Configuration Tip:** Set default suppliers correctly to control BOM traversal behavior. This is more important than category configuration for assemblies.

### Category Configuration Behavior

**When all categories are configured:**
- Plugin uses InvenTree category structure to classify parts
- Supports hierarchical categories (parent + all child categories)
- Non-assembly parts: Classified as Coml, Fab, or CtL based on their category
- Assembly parts: Classified based on default supplier (Purchased Assy, Internal Fab, or Assy)

**When categories are NOT configured:**
- **Assemblies still work**: Purchased Assy and Internal Fab rely on `is_assembly` flag and default supplier, not categories
- **Non-assemblies become "Other"**: Without category mappings, non-assembly parts cannot be classified as Coml, Fab, or CtL
- **Result**: Only assemblies with suppliers will be correctly filtered; non-assemblies may all appear as "Other"
- **Recommendation**: Configure at minimum the Fabricated and Commercial categories for proper classification

**Partial configuration scenarios:**

| Categories Configured | What Works | What Doesn't |
|----------------------|------------|--------------|
| None | Purchased Assy, Internal Fab identification | Coml, Fab, CtL classification (all → "Other") |
| Fabricated only | Fab, Internal Fab, assemblies | Coml, CtL (→ "Other") |
| Commercial only | Coml, assemblies | Fab, CtL (→ "Other") |
| Fabricated + Commercial | Most parts classified correctly | CtL (→ treated as Fab) |
| All four categories | ✅ Full classification | None |

**Note:** The "Other" category means the plugin cannot determine the part type from available data. These parts will still appear in the flat BOM if they are leaf parts (non-assemblies without child BOMs).

## Usage

### Interactive UI Panel

The plugin adds a "Flat BOM Viewer" panel to assembly part pages:

1. **Navigate** to any assembly part in InvenTree
2. **Click** "Generate Flat BOM" to analyze the complete hierarchy
3. **Adjust** build quantity to see scaled requirements
4. **Toggle** allocation and on-order checkboxes to customize Build Margin calculation
5. **Search** and filter the results table
6. **Export** to CSV for further analysis or purchasing

### Controls

**Build Quantity**
- Set the number of units you plan to build
- All quantities scale automatically

**Include Allocations in Build Margin** (Checkbox)
- ✅ Checked: Build Margin based on available stock (total - allocations) - *Realistic view*
- ☐ Unchecked: Build Margin based on total stock - *Optimistic view*

**Include On Order in Build Margin** (Checkbox)  
- ✅ Checked: Incoming stock increases Build Margin - *Standard planning*
- ☐ Unchecked: Ignore incoming stock - *Conservative planning*

*Screenshot: Build quantity input and checkbox controls*  
![Build quantity multiplier and checkbox controls for customizing calculations](imgs/build-controls.png)

### Statistics Panel

- **Total Parts**: Number of unique purchaseable components
- **Internal Fab Processed**: Number of Internal Fabricated Part assemblies expanded during BOM traversal
- **Out of Stock**: Parts with zero inventory
- **On Order**: Parts with incoming purchase orders
- **Need to Order**: Parts with Build Margin deficit (respects checkbox settings)

*Screenshot: Statistics panel with counters*  
![Statistics panel displaying Total Unique Parts, Internal Fab Processed, and Need to Order counters](imgs/statistics-panel.png)

### Table Columns

| Column | Description |
|--------|-------------|
| **Component** | Full part name with IPN prefix and variant (includes thumbnail image, clickable link) |
| **IPN** | Internal Part Number |
| **Description** | Part description |
| **Type** | Color-coded badge: Coml (green), Fab (blue), CtL (teal), Purchased Assy (orange), Internal Fab (cyan), Assy (violet), TLA (grape), Other (gray) |
| **Total Qty** | Required quantity for build (scales with build quantity) with [unit] |
| **In Stock** | Total inventory (green if sufficient, orange if partial, red if none) with [unit] |
| **On Order** | Incoming stock from purchase orders with [unit] (dimmed when checkbox unchecked) |
| **Building** | Stock currently in production builds (cyan badge if > 0) |
| **Allocated** | Stock reserved for builds and sales orders with [unit] (dimmed when checkbox unchecked) |
| **Available** | Stock available after subtracting allocations (green if sufficient, orange if partial, red if none) |
| **Build Margin** | Balance after build (negative red badge if deficit, positive green badge if surplus; respects allocation and on-order checkboxes) |

All columns are **sortable** and the table is **paginated** (10/25/50/100/All per page).

*Screenshot: BOM table showing all columns with various part types and stock levels*  
![Full data table showing sortable columns, color-coded badges, and stock level indicators](imgs/data-table-view.png)

## API Endpoint

### Get Flat BOM

```
GET /api/plugin/flat-bom-generator/flat-bom/{part_id}/
```

**Performance Warning:** Each API call performs a complete recursive BOM traversal with no caching. For large assemblies, response times can be several seconds.

**Query Parameters:**
- `max_depth` (optional): Maximum BOM traversal depth (recommended for very deep BOMs to improve performance)

**Response:**
```json
{
  "part_id": 123,
  "part_name": "Main Assembly",
  "ipn": "ASM-001",
  "total_unique_parts": 45,
  "total_ifps_processed": 12,
  "bom_items": [
    {
      "part_id": 456,
      "ipn": "FAB-100",
      "part_name": "Bracket, Mounting, Steel",
      "full_name": "FAB-100 | Bracket, Mounting, Steel | A ",
      "description": "Steel mounting bracket",
      "part_type": "Fab",
      "total_qty": 2.0,
      "unit": "pcs",
      "is_assembly": false,
      "purchaseable": true,
      "default_supplier_id": 789,
      "reference": "U1, U2",
      "note": "",
      "level": 1,
      "in_stock": 50.0,
      "on_order": 100.0,
      "allocated": 10.0,
      "available": 40.0,
      "image": "/media/part_images/fab-100.jpg",
      "thumbnail": "/media/part_images/fab-100_thumbnail.jpg",
      "link": "/part/456/"
    }
  ]
}
```

## How It Works

### BOM Traversal Algorithm

The plugin uses a recursive traversal with the `visited.copy()` pattern:

1. **Traverse**: Build complete BOM tree with cumulative quantities
   - Uses `visited.copy()` to allow same part in different branches
   - Detects and prevents circular references
   - Calculates cumulative quantities through multiplication

2. **Filter**: Extract only leaf parts (purchaseable components)
   - Coml: Commercial/COTS parts (non-assembly in Commercial category)
   - Fab: Fabricated parts (non-assembly in Fabrication category)
   - CtL: Cut-to-length materials (non-assembly in Cut-to-Length category with length in BOM notes)
   - Purchased Assy: Assemblies with external default supplier (purchased complete)

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

**Build Margin** = Stock Used + (On Order if enabled) - Total Required
- Where Stock Used = Available (if allocations enabled) or Total Stock (if disabled)
- Negative value indicates deficit (need to order)
- Positive value indicates surplus (extra stock after build)

### API Response Fields

Each item in `bom_items` contains:
- `part_id`: Part database ID
- `ipn`: Internal Part Number
- `part_name`: Part name
- `full_name`: Full display name (includes variant info)
- `description`: Part description
- `part_type`: "TLA", "Coml", "Fab", "CtL", "Purchased Assy", "Internal Fab", "Assy", or "Other"
- `total_qty`: Total quantity needed through BOM hierarchy (aggregated from all BOM levels)
- `unit`: Unit of measurement (e.g., "pcs", "mm", "kg")
- `is_assembly`: Boolean - whether part is an assembly
- `purchaseable`: Boolean - whether part can be purchased
- `has_default_supplier`: Boolean - whether part has default supplier configured
- `default_supplier_id`: ID of default supplier (null if none)
- `note`: BOM item notes
- `level`: Depth in original BOM tree
- `in_stock`: Total inventory
- `on_order`: Quantity on incomplete purchase orders
- `allocated`: Stock reserved for builds/sales
- `available`: Total stock minus allocated
- `image`: Full-size image URL (null if none)
- `thumbnail`: Thumbnail image URL (null if none)
- `link`: URL to part detail page

