# Warnings & Errors Roadmap

**Scope:** Warnings specific to flat BOM generation, BOM structure issues, and plugin settings that affect output. We do NOT duplicate InvenTree's built-in warnings (stock levels, suppliers, etc.).

---

## Implemented ✅

### Critical - BOM Structure Issues
- ✅ **Assembly/Internal Fab with No Children** (Dec 15, 2025)
  - Severity: HIGH (data loss bug fixed)
  - Parts with `is_assembly=True` but no BOM items were disappearing
  - Now included in flat BOM with warning flag
  - 5 unit tests passing

- ✅ **Max Depth Exceeded** (Dec 15, 2025)
  - Severity: MEDIUM
  - Summary warning when BOM traversal stopped by MAX_DEPTH setting
  - Informs user that assemblies weren't fully expanded
  - Suggests increasing MAX_DEPTH setting

- ✅ **Inactive Part in BOM** (Dec 15, 2025)
  - Severity: MEDIUM-HIGH
  - Part marked inactive but still in BOM
  - May not be available for production

### Data Quality - Plugin-Specific
- ✅ **Unit Mismatch** (Dec 15, 2025)
  - Severity: MEDIUM
  - BOM notes specify different unit than part's native unit
  - Affects quantity calculations in flat BOM
  - 2 unit tests for detection logic

---

## Not Needed ❌

### Prevented by InvenTree
- ❌ **Circular BOM References** - InvenTree prevents with `check_add_to_bom()`
- ❌ **Orphaned References** - Django CASCADE deletes dependent BOM items
- ❌ **Negative Quantities** - MinValueValidator(0) prevents this

### Outside Plugin Scope
- ❌ **Missing Stock** - InvenTree has low stock warnings (not BOM structure issue)
- ❌ **No Default Supplier** - Inventory management, not BOM generation issue
- ❌ **Price Alerts** - Purchasing concern, not BOM structure
- ❌ **Lead Time Warnings** - Scheduling concern, not BOM structure
- ❌ **Minimum Order Quantity** - Purchasing concern, not BOM structure
- ❌ **Deprecated Parts** - Inventory management, not BOM generation
- ❌ **Missing Parameters** - Part definition issue, not BOM structure
- ❌ **Substitute Available** - Purchasing decision, not BOM generation

---

## Future Considerations 🔮

**Watch for During Refactoring:**
As we refactor and improve the plugin, keep an eye out for:
- BOM structure issues that affect flat BOM accuracy
- Plugin settings that could cause unexpected behavior
- Data transformations where user input could cause errors
- Edge cases in BOM traversal algorithm

**Potential Future Warnings:**
- **Invalid Cut-to-Length Notes** - CtL category parts with unparseable length notes
- **Category Mismatch** - Part in wrong category for its type (e.g., assembly in Commercial)
- **Internal Fab Without Cut List** - Internal Fab part missing required length notes

---

## Warning Design Principles

### What Makes a Good Plugin Warning?

1. **Affects Flat BOM Output** - Warning about data that impacts plugin functionality
2. **Actionable** - User can fix it by editing BOM or plugin settings
3. **Not Redundant** - InvenTree doesn't already warn about it
4. **Clear Message** - Explains the problem and suggests solution

### Warning Categories

**Critical (High Priority):**
- Data loss or missing parts in output
- BOM structure prevents correct flattening
- Plugin settings causing incorrect results

**Important (Medium Priority):**
- Data quality issues affecting calculations
- Parts that may cause production problems
- Settings that could be misconfigured

**Informational (Low Priority):**
- Edge cases handled gracefully
- Suggestions for optimization

---

## Implementation Checklist

When adding a new warning:
- [ ] Add to WARNINGS-RESEARCH.md with research notes
- [ ] Implement detection logic in appropriate file
- [ ] Use BOMWarningSerializer for consistent format
- [ ] Add unit tests for detection logic
- [ ] Update this roadmap with implementation date
- [ ] Test in staging environment
- [ ] Document in user-facing README if needed

---

_Last updated: December 15, 2025_
