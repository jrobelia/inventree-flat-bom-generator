# Warning System Architecture

**Date**: December 15, 2025  
**Purpose**: Document the design patterns learned while implementing BOM error warnings

---

## Problem Statement

When implementing warnings for BOM generation errors, we encountered a classic problem:
- Assemblies stopped by `max_depth` setting had NO children (expected)
- Assemblies with NO BOM items defined also had NO children (error)
- Both triggered the same detection logic, causing **duplicate warnings**

**Initial Result**: 65 warnings (most duplicates) instead of ~4 meaningful warnings.

---

## Architecture Lesson: Flag Prioritization

### The Issue
Data can have **multiple states** that trigger different warnings:
```python
assembly_with_no_children = is_assembly and len(children) == 0
```

This is TRUE for:
1. Assembly stopped at max_depth (expected behavior)
2. Assembly with no BOM defined (error condition)

### The Solution: Prioritized Flags
```python
if tree.get("is_assembly") and not children:
    # Priority: If stopped by max_depth, don't flag as BOM error
    assembly_no_children_flag = not max_depth_exceeded
```

**Key Principle**: When one condition **explains** another, prioritize the explanation.

---

## Architecture Lesson: Summary vs Per-Item Warnings

### The Issue
Generating warnings during iteration creates **per-item noise**:
```python
for item in flat_bom:
    if item.get("max_depth_exceeded"):
        warnings.append(...)  # 30+ warnings for same root cause!
```

### The Solution: Pre-Check Summary Warnings
```python
# BEFORE iterating, check for systemic issues
parts_at_max_depth = [item for item in flat_bom if item.get("max_depth_exceeded")]
if parts_at_max_depth:
    warnings.append({
        "type": "max_depth_reached",
        "message": f"... {len(parts_at_max_depth)} assemblies not expanded..."
    })

# Then iterate for per-item checks
for item in flat_bom:
    if item.get("assembly_no_children"):  # Only genuine BOM errors
        warnings.append(...)
```

**Key Principle**: Systemic issues → Summary warning. Individual issues → Per-item warning.

---

## Data Flow: Flag Lifecycle

Understanding how data flows through the pipeline is critical:

### 1. **Flag Creation** (bom_traversal.py - `traverse_bom()`)
```python
if max_depth is not None and level >= max_depth:
    skip_bom_expansion = True
    max_depth_hit = True

if max_depth_hit and is_assembly:
    node["max_depth_exceeded"] = True  # ← FLAG CREATED
```

### 2. **Flag Propagation** (bom_traversal.py - `get_leaf_parts_only()`)
```python
leaves.append({
    "part_id": tree["part_id"],
    "max_depth_exceeded": tree.get("max_depth_exceeded", False),  # ← COPIED
    "assembly_no_children": not max_depth_exceeded,  # ← DERIVED
})
```

### 3. **Flag Preservation** (bom_traversal.py - `deduplicate_and_sum()`)
```python
# CRITICAL: Must explicitly copy flags to part_info and result rows
part_info[key] = {
    "part_id": part_id,
    "max_depth_exceeded": leaf.get("max_depth_exceeded", False),  # ← PRESERVED
    "assembly_no_children": leaf.get("assembly_no_children", False),  # ← PRESERVED
}

row = {
    "part_id": part_info[key]["part_id"],
    "max_depth_exceeded": part_info[key].get("max_depth_exceeded", False),  # ← INCLUDED
    "assembly_no_children": part_info[key].get("assembly_no_children", False),  # ← INCLUDED
}
```

### 4. **Flag Consumption** (views.py - enrichment)
```python
# Summary check BEFORE loop
parts_at_max_depth = [item for item in flat_bom if item.get("max_depth_exceeded")]
if parts_at_max_depth:
    warnings.append(...)  # ONE warning

# Per-item check DURING loop
for item in flat_bom:
    if item.get("assembly_no_children"):  # Only genuine errors
        warnings.append(...)  # Multiple warnings OK
```

---

## Common Pitfall: Lost Flags

**Problem**: Flags disappeared during deduplication!

**Root Cause**: When building dictionaries from existing data, only explicitly copied fields survive:
```python
# ❌ WRONG - flags lost!
row = {
    "part_id": part_info[key]["part_id"],
    "ipn": part_info[key]["ipn"],
    # ... max_depth_exceeded NOT copied → lost!
}

# ✅ CORRECT - flags preserved
row = {
    "part_id": part_info[key]["part_id"],
    "ipn": part_info[key]["ipn"],
    "max_depth_exceeded": part_info[key].get("max_depth_exceeded", False),  # ← EXPLICIT
}
```

**Lesson**: In data transformation pipelines, **explicitly copy all needed fields**. Don't rely on object spreading or inheritance.

---

## Testing Strategy

### Unit Test Structure
Test the **decision logic** separately from the **data pipeline**:

```python
def test_flag_logic():
    """Test: Assembly stopped by max_depth should NOT be flagged as no_children"""
    tree = {
        "is_assembly": True,
        "children": [],
        "max_depth_exceeded": True
    }
    
    # Decision logic from get_leaf_parts_only()
    if tree.get("is_assembly") and not tree.get("children"):
        assembly_no_children_flag = not tree.get("max_depth_exceeded")
    
    assert not assembly_no_children_flag  # Should NOT flag
```

**Why Separate Tests?**
- Logic tests are **fast** (no database/mocks)
- Logic tests **document the rules**
- Integration tests verify pipeline but are slower

---

## Summary: Key Architectural Patterns

1. **Flag Prioritization**: Use conditionals to prevent overlapping warnings
   ```python
   flag = condition_to_warn and not higher_priority_condition
   ```

2. **Summary Warnings**: Check collections before iterating
   ```python
   if any(item.get("flag") for item in collection):
       warnings.append(summary_warning)
   ```

3. **Explicit Field Propagation**: Always copy flags through transformations
   ```python
   result = {**source, "flag": source.get("flag", default)}
   ```

4. **Test Decision Logic**: Unit test the rules, integration test the pipeline
   ```python
   # Unit: Does this combination produce correct flag?
   # Integration: Does flag survive through pipeline?
   ```

5. **Data Flow Documentation**: Track flag lifecycle through codebase
   ```
   CREATE → PROPAGATE → PRESERVE → CONSUME
   ```

---

## Outcome

**Before**: 65 warnings (mostly duplicates)  
**After**: ~5 warnings (all meaningful)

- ✅ 1 summary warning for max_depth (covers 30+ assemblies)
- ✅ 1 warning for genuine empty assembly (OAStg-00001)
- ✅ 2 unit mismatch warnings (CtL part)  
- ✅ 1 inactive part warning

**Code Quality**: 4 new unit tests, all passing, documenting the decision logic.

---

**Architectural Takeaway**: Complex systems need **flag prioritization** and **summary aggregation** to avoid overwhelming users with redundant information. Test the decision rules separately from the data pipeline.
