# BOM Error Warnings Research

**Date:** December 15, 2025  
**Purpose:** Research errors that affect flat BOM generation and implement warnings

---

## Research Findings

### 1. Circular BOM References
**Question:** Does InvenTree allow circular BOM references?

**Answer:** ❌ NO - InvenTree prevents this at the database level

**Evidence:**
- InvenTree has `Part.check_add_to_bom()` method ([part/models.py:600](../reference/inventree-source/src/backend/InvenTree/part/models.py))
- Validates before saving BOM items ([part/models.py:4598](../reference/inventree-source/src/backend/InvenTree/part/models.py))
- Checks for:
  - Same part as parent
  - Part in same variant tree as parent
  - Parent used in this part's BOM
  - Parent used in any child's BOM (recursive)

**Action:** ✅ No warning needed - InvenTree prevents this

---

### 2. Assembly/Internal Fab Parts with No Children
**Question:** If an `is_assembly` part has no children, does it appear in flat BOM?

**Answer:** 🐛 **BUG FOUND AND FIXED** - These parts silently disappear from flat BOM!

**Bug Fixed:** December 15, 2025

**Fix Applied:**
- Modified `get_leaf_parts_only()` to detect assemblies with no children
- Include them in leaves list with `assembly_no_children` flag
- Generate warning in `views.py` during enrichment
- Added 5 unit tests covering all scenarios

**Test Results:** ✅ All 5 tests passing
- `test_assembly_with_no_children_included_in_leaves`
- `test_internal_fab_with_no_children_included_in_leaves`
- `test_assembly_with_children_not_flagged`
- `test_non_assembly_leaf_not_affected`
- `test_purchased_assembly_no_children_not_flagged`

**Warning Generated:**
- Type: `assembly_no_children`
- Severity: High (data loss prevented)
- Message: "{part_type} part has no BOM items defined"

---

### 3. Invalid Quantities (Negative/Zero)
**Question:** Can negative or zero quantities be entered in BOM items?

**Answer:** ⚠️ ZERO allowed, negative NOT allowed

**Evidence:**
- `BomItem.quantity` field has `validators=[MinValueValidator(0)]` ([part/models.py:4410](../reference/inventree-source/src/backend/InvenTree/part/models.py))
- Zero quantity IS allowed (validator is >=0, not >0)
- Negative quantities blocked at database level

**Implications:**
- Zero quantity BOM items can exist (might be placeholders or optional items)
- For CtL parts, notes field is free text - invalid lengths COULD be entered
- Unit mismatch warnings already catch problematic CtL notes

**Action:** ⚠️ Consider warning for zero-quantity BOM items (low priority)

---

### 4. Max Depth Exceeded
**Question:** Should we warn if BOM traversal hits max_depth before reaching leaf parts?

**Answer:** ✅ YES - This is a good warning

**Current Behavior:**
- `max_depth` parameter limits traversal ([bom_traversal.py:220](flat_bom_generator/bom_traversal.py))
- When hit, `skip_bom_expansion = True` and children not explored
- Node returned as-is, but assemblies at max depth might not be true "leaf" parts

**Warning Needed:**
- Type: `max_depth_exceeded`
- Severity: Medium (incomplete BOM - may be missing sub-parts)
- Message: "BOM traversal stopped at max depth {depth} for part {part_name}"
- Trigger: When `skip_bom_expansion` is True due to max_depth AND part is assembly with children

**Implementation:**
- Track when max_depth causes early termination
- Return list of affected part IDs/names
- Display warning in UI

---

### 5. Orphaned References
**Question:** Can BOM reference a part that no longer exists?

**Answer:** ❌ NO - Django CASCADE prevents this

**Evidence:**
- `BomItem.part` ForeignKey has `on_delete=models.CASCADE` ([part/models.py:4386](../reference/inventree-source/src/backend/InvenTree/part/models.py))
- `BomItem.sub_part` ForeignKey has `on_delete=models.CASCADE` ([part/models.py:4396](../reference/inventree-source/src/backend/InvenTree/part/models.py))
- If a Part is deleted, all BOM items referencing it are automatically deleted
- No orphaned references can exist

**Action:** ✅ No warning needed - Django ORM prevents this

---

### 6. Inactive Parts in BOM
**Question:** Can parts be marked inactive while still in a BOM?

**Answer:** ✅ YES - InvenTree allows this

**Evidence:**
- User confirmed: "InvenTree does allow a part to be marked inactive while it is a member of a BOM"
- This can cause confusion when generating production BOMs

**Warning Needed:**
- Type: `inactive_part`
- Severity: Medium-High (may not be available for production)
- Message: "Part {part_name} is marked inactive"
- Trigger: Check `part_obj.active` field during enrichment

**Implementation:**
In `views.py` enrichment loop:
```python
if not part_obj.active:
    warnings.append({
        "type": "inactive_part",
        "part_id": item["part_id"],
        "part_name": part_full_name,
        "message": "Part is marked inactive and may not be available",
    })
```

---

## Warnings Summary

### ✅ Completed

1. **Unit Mismatch** (December 15, 2025)
   - Severity: MEDIUM
   - Working in production
   - Detects BOM notes unit vs part unit mismatch

2. **Assembly/Internal Fab with No Children** (December 15, 2025) 🐛
   - Severity: HIGH (bug fix)
   - Bug fixed + warning added
   - 5 unit tests passing

### 🔨 To Implement (Priority Order)

1. **Inactive Part in BOM** ✅
   - Severity: MEDIUM-HIGH
   - Check `part_obj.active` field in views.py
   - User confirmed: InvenTree allows this

2. **Max Depth Exceeded** ✅
   - Severity: MEDIUM
   - Track during traversal
   - Warn when assemblies stopped at depth limit

### ❌ Not Needed

- **Circular BOM** - InvenTree prevents with `check_add_to_bom()`
- **Orphaned References** - Django CASCADE deletes BOM items
- **Negative Quantities** - MinValueValidator(0) prevents this

### ⚠️ Low Priority / Optional

- **Zero Quantity BOM Items** - Allowed by InvenTree (might be intentional)

---

## Next Steps

1. ✅ ~~Research remaining items~~ **COMPLETE**
2. ✅ ~~Fix assembly-no-children bug~~ **COMPLETE**
3. 🔨 **Implement inactive part warning** (NEXT)
4. 🔨 Implement max depth exceeded warning
5. 📝 Update WARNINGS-ROADMAP.md with implementation status
6. 🧪 Add integration tests for warning UI display

---

_Last updated: 2025-12-15_
