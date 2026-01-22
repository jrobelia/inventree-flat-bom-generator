# FlatBOMGenerator - Plugin Improvement Roadmap

> **Status:** Optional/Consumable Parts Complete - Ready for Production Deployment  
> **Last Updated:** January 22, 2026

---

## Current Status (v0.11.23)

### ✅ Major Accomplishments
- **Test Infrastructure** - 151 tests (60 unit + 91 integration), Grade B+ quality, 92% coverage
- **Code Quality** - Removed 96 lines dead code, fixed 3 incorrect fallbacks, 1 production bug
- **Frontend Architecture** - Panel.tsx: 1250 → 306 lines (68% reduction) via component extraction
- **Settings UI** - Moved from admin to frontend with progressive disclosure pattern
- **Optional/Consumable Parts** - Smart flag aggregation, visual badges, priority sorting
- **Warning System** - 4 warning types with integration test coverage
- **DRF Serializers** - All API responses use proper serialization

**See [Completed Work Archive](#completed-work-archive) for detailed phase history.**

### 🎯 Next Steps
1. Check box UX polish (disable when no cutlist parts)
2. Substitute parts support (show alternatives with individual stock)
3. Variant parts support (aggregate variant stock)
4. InvenTree export integration (replace custom CSV)

---

## Planned Features

### Substitute Parts Support (3-4 hours, HIGH PRIORITY)
**Goal:** Display substitute parts as expandable child rows with individual stock

**Design Pattern:** Reuse cutlist infrastructure (proven pattern)
- Treat substitutes like cutlist breakdown (additional rows per parent)
- Show "[Substitute] Part Name" with badge in Flags column
- Each substitute shows its own stock, allocated, on order, shortfall
- Group substitutes with parent during sorting

**Implementation:**
- Query `BomItemSubstitute` relationships during enrichment
- Create substitute rows (similar to cutlist generation)
- Add "Include Substitute Parts" checkbox (default: unchecked)

**Benefits:**
- See which substitute has best availability at a glance
- Reuses proven cutlist pattern (less risk)

### Mixed Flag Handling (2-3 hours, HIGH PRIORITY)
**Goal:** Properly handle parts with different BOM line item properties

**Problem:** Current deduplication groups only by `part_id`, losing distinction when same part has mixed properties:
- Example: 5× OA-00012 (3 optional, 2 required) → Shows as "Qty: 5" with no flags
- Information lost: User can't see 3 are optional (could be omitted)

**Root Cause:** Deduplication key is too simple:
```python
# Current (v0.11.23)
grouped_parts[item["part_id"]].append(item)
```

**Solution:** Separate line items by distinguishing properties:
```python
# Proposed deduplication key
key = (part_id, optional, consumable, allow_variants, cut_length)
```

**Properties that could create separate line items:**
1. `optional` - Can be omitted to save cost
2. `consumable` - Not in final product (solder paste, etc.)
3. `allow_variants` - Changes stock calculation (variant_stock vs in_stock)
4. `note` (CtL only) - Already handled via cutlist breakdown
5. `reference` - Combines correctly ("R1, R2, R3")
6. `inherited` - Ignore (doesn't affect purchasing)

**Implementation Options:**
- **Option A**: Separate top-level rows (OA-00012 [Optional] Qty: 3, OA-00012 [Required] Qty: 2)
- **Option B**: Parent/child pattern like cutlist (expandable breakdown)
- **Option C**: Current + warning badge ("⚠️ Mixed flags")

**Recommendation:** Start with Option A (simpler), evolve to Option B later

**Impact on Future Features:**
- Variant support must handle `allow_variants` flag differently per row
- Substitute parts are different part_ids (no conflict)

**Status:** Not in production, document for when needed


### Variant Parts Support (2-10 hours, MEDIUM PRIORITY)
**Goal:** Integrate InvenTree's variant/template part system into flat BOM display

**InvenTree Variant System:**
- Template parts (`is_template=True`) with variant children (`variant_of` relationship)
- Stock exists on variants, not templates
- `allow_variants` BomItem flag allows any variant to fulfill requirement
- Parts have `variant_stock` (total across all variants) vs `in_stock` (specific part only)

**Current Plugin Behavior:**
- Ignores variant relationships entirely
- Shows template parts with zero stock (real stock on variants)
- Does not respect `allow_variants` flag
- Stock calculations use `in_stock` only (excludes variant stock)

**Implementation Options:**

**Option 1: Variant Stock Visibility** (2-3 hours, LOW RISK)
- Add `variant_stock` column to table (shows stock across all variants)
- Add "Has Variants" badge indicator
- No behavioral changes, just additional visibility
- **Recommended starting point** - quick win, foundation for future enhancements

**Option 2: Variant Expansion Mode** (6-8 hours, MEDIUM RISK)
- Add "Expand Template Parts to Variants" checkbox
- Replace template parts with individual variant rows (like cutlist pattern)
- Show each variant's stock separately
- User can see which variant has best availability
- Reuses existing cutlist infrastructure

**Option 3: Respect allow_variants Flag** (8-10 hours, HIGH COMPLEXITY)
- Track `allow_variants` flag through BOM traversal
- Stock calculations include variant_stock when flag is true
- Badge: "Variants Allowed" on affected BomItems
- Most accurate to InvenTree's build allocation logic
- **Critical**: Requires separate line items for mixed `allow_variants` (see Mixed Flag Handling)

**Proposed Approach:**
1. Start with Option 1 (variant visibility)
2. Gather user feedback on variant usage patterns
3. Implement Option 2 or 3 based on actual needs

**Testing Requirements:**
- Fixtures with template parts and variants
- Stock on variants but not templates
- BomItems with `allow_variants=True`
- Nested variant hierarchies (variant → sub-variant)

**Benefits:**
- Better visibility for parts with variant families
- Stock availability more accurately represented
- Aligns with InvenTree's build order allocation logic

**Open Questions:**
1. Are template parts common in your BOMs?
2. Do you use the `allow_variants` flag?
3. Should variant expansion be default ON or OFF?
4. Should inactive variants be included in calculations?

**Defer Until:** Determine actual variant usage patterns in production BOMs

### UX Polish: Cutlist Checkbox (0.5 hours, LOW PRIORITY)
**Current:** "Show Cutlist Rows" checkbox always enabled  
**Improvement:** Disable when no cutlist parts, update label to "(none in BOM)"

**Implementation:**
```typescript
const hasCutlistRows = useMemo(() => 
  bomData?.bom_items?.some(item => item.cutlist_breakdown?.length > 0) || false
, [bomData]);

<Checkbox
  label={hasCutlistRows ? "Show Cutlist Rows" : "Show Cutlist Rows (none in BOM)"}
  disabled={!hasCutlistRows}
  ...
/>
```

### InvenTree Export Integration (4-6 hours, MEDIUM PRIORITY)
**Goal:** Replace custom CSV export with InvenTree's DataExportMixin

**Benefits:**
- Multiple formats (CSV, JSON, XLSX)
- Automatic encoding/escaping
- Server-side generation (no memory limits)

**Defer Until:** Backend 100% stable



## Completed Work Archive

<details>
<summary><strong>Development Phases (Dec 2025 - Jan 2026)</strong></summary>

### Phase 1-2: Test Quality Foundation (Dec 18 - Jan 9, 2026)
- Code-first test methodology established
- 164 unit tests validated, 30 added to fill gaps
- Found/removed 96 lines dead code, fixed 3 incorrect fallbacks

### Phase 3: Serializer Refactoring (Dec 15-18, 2025)
- BOMWarningSerializer, FlatBOMItemSerializer, FlatBOMResponseSerializer
- 38 serializer tests, found 2 bugs

### Phase 4-5: Integration Testing (Jan 9-12, 2026)
- 91 integration tests created across 6 priority areas
- Fixture-based testing pattern (bypasses InvenTree validation)
- Found/fixed 1 production bug (Part.DoesNotExist)

### Phase 6: Frontend Refactoring (Jan 18, 2026)
- Panel.tsx: 950 → 306 lines (68% reduction)
- 5 components extracted, 5 custom hooks
- **Details:** [FRONTEND-REFACTORING-GUIDE.md](internal/archive/2026-01-frontend-refactoring/FRONTEND-REFACTORING-GUIDE.md)

### Phase 7: Settings UI (Jan 20-21, 2026)
- Moved 3 settings from admin to frontend
- Progressive disclosure pattern
- **Details:** [SETTINGS-UI-IMPLEMENTATION-PLAN.md](internal/archive/2026-01-settings-ui/SETTINGS-UI-IMPLEMENTATION-PLAN.md)

### Phase 8: Optional/Consumable Parts (Jan 22, 2026)
- Smart flag aggregation (flag=True only if ALL instances)
- Orange "Optional" badge, yellow "Consumable" badge
- Priority-based sorting
- **Known Limitation**: Mixed flags (e.g., 3 optional + 2 required of same part) lose distinction

</details>

---

## Key Lessons Learned

### What Works
1. **Fixture-based testing** - Programmatic loading bypasses InvenTree validation
2. **Code-first validation** - Read actual code before writing tests (found 96 lines dead code)
3. **Test-first workflow** - Caught bugs during serializer refactoring
4. **Incremental phases** - Small verifiable changes prevent stacking unverified work
5. **Production validation** - Deploy → Test in UI → Verify catches integration issues
6. **User diagnostic insights** - User identified `toggleable` vs `switchable` bug immediately
7. **TypeScript type extensions** - `ExtendedColumn<T>` pattern bridges runtime/compile-time gaps

### What to Avoid
1. ❌ Skipping deployment after code changes
2. ❌ Assuming "tests pass" = "code works in production"
3. ❌ Creating code without checking existing solutions
4. ❌ Accepting test gaps too quickly
5. ❌ All-at-once refactoring when user suggests incremental approach
6. ❌ Assuming library TypeScript types are complete (check runtime behavior)

### Core Principle
> "Test what you refactor, not just what's easy. Use fixtures when Django validation blocks test creation."

---

## Development Guidelines

### Test-First Approach
1. Check if tests exist for code you're refactoring
2. Evaluate test quality (coverage, thoroughness, accuracy)
3. Improve/create tests BEFORE refactoring
4. Make code changes
5. Verify tests pass
6. Deploy → Test in UI → Verify

### Code Quality Standards
- **Pure functions preferred** - Easier to test and reason about
- **Type hints required** - All functions have parameter and return types
- **Docstrings with examples** - Explain why, not what
- **Functions under 50 lines** - Extract subfunctions if longer
- **No dead code** - Remove unused imports, functions, fallbacks

### Documentation Updates
- Update docstrings when function signatures change
- Update ARCHITECTURE.md when adding/removing files
- Update this ROADMAP when priorities change
- Link related documentation (don't duplicate content)

---

## References

**Testing:**
- [TEST-PLAN.md](../flat_bom_generator/tests/TEST-PLAN.md) - Test execution, strategy, priorities
- [TEST-WRITING-METHODOLOGY.md](TEST-WRITING-METHODOLOGY.md) - Code-first validation approach

**Architecture:**
- [ARCHITECTURE.md](../ARCHITECTURE.md) - Plugin architecture, API reference, patterns

**Warnings:**
- [WARNINGS-ROADMAP.md](WARNINGS-ROADMAP.md) - Warning system expansion ideas
- [ARCHITECTURE-WARNINGS.md](ARCHITECTURE-WARNINGS.md) - Warning system implementation patterns

**Deployment:**
- [DEPLOYMENT-WORKFLOW.md](DEPLOYMENT-WORKFLOW.md) - Deployment checklist and testing workflow

---

_Last updated: January 22, 2026_
