# Warnings & Errors Roadmap

## Implemented
- ✅ **Unit Mismatch** - BOM notes specify different unit than part's native unit

## Planned

### High Priority
- **Missing Stock** - Part has 0 stock and 0 on order (cannot build)
- **No Supplier** - Part is purchaseable but has no default supplier
- **Inactive Part** - Part in BOM is marked inactive

### Medium Priority
- **Deprecated Part** - Part has `deprecated` flag set
- **Missing Parameter** - Expected parameters (e.g., length, resistance) not set
- **Substitute Available** - Part has defined substitutes with better stock

### Low Priority
- **Price Alert** - Part price exceeds threshold or missing
- **Lead Time Warning** - Supplier lead time exceeds build schedule
- **Minimum Order Quantity** - Stock insufficient for MOQ

## Implementation Notes

All warnings should:
1. Be collected during enrichment in `views.py`
2. Include: `type`, `part_id`, `part_name`, `message`
3. Be non-blocking (don't stop BOM generation)
4. Display in persistent alert + toast notification
