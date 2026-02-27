# FlatBOMGenerator - Plugin Improvement Roadmap

> **Status:** Substitute Parts feature branch -- deployed, pending staging verification  
> **Last Updated:** February 26, 2026

---

## Current Status (v0.11.47 on `feature/substitute-parts`)

### ✅ Major Accomplishments
- **Substitute Parts** - Backend enrichment, frontend display with generic child row system, 13 tests (9 unit + 4 integration)
- **Test Infrastructure** - 164+ tests (69+ unit + 95+ integration), Grade B+ quality, 92% coverage
- **Code Quality** - Removed 96 lines dead code, fixed 3 incorrect fallbacks, 1 production bug
- **Frontend Architecture** - Panel.tsx: 1250 → 306 lines (68% reduction) via component extraction
- **Settings UI** - Moved from admin to frontend with progressive disclosure pattern
- **Optional/Consumable Parts** - Smart flag aggregation, visual badges, priority sorting
- **Warning System** - 4 warning types with integration test coverage
- **DRF Serializers** - All API responses use proper serialization

**See [Completed Work Archive](#completed-work-archive) for detailed phase history.**

### 🎯 Next Steps
1. **Staging verification** -- test substitute parts feature on staging server
2. CSV export: mark substitute rows (currently skipped)
3. UX: disable "Show Substitutes" checkbox when no substitutes exist
4. **Frontend InvenTree Patterns** - Optional refactoring to align with InvenTree core patterns ([See Plan](FRONTEND-REFACTORING-PLAN.md))
5. Consolidate checkbox filters into dropdown menu (like column visibility)
6. InvenTree export integration (replace custom CSV)

---

## Planned Features

### Substitute Parts -- Finishing Touches (1-2 hours remaining)
**Status:** Core feature complete on `feature/substitute-parts` branch. Deployed, pending staging test.

**What's done:**
- `SubstitutePartSerializer` (16 fields) with 9 unit tests
- Backend enrichment in `views.py` -- queries `BomItemSubstitute`, groups by part, enriches with stock, generates unit-mismatch warnings
- `SHOW_SUBSTITUTE_PARTS` plugin setting with query param override (`?include_substitutes=true`)
- Generic child row system (`is_child_row`, `child_row_type`, `parent_row_part_id`) -- replaces old `is_cut_list_child`
- Frontend: blue-themed rows, `↳` symbol, "Substitute" badge, dark mode support
- "Show Substitutes" checkbox in ControlBar, auto-enabled on generation
- 4 integration tests in `test_substitute_enrichment.py`
- Tracking `bom_item_pk` through traversal and deduplication for correct substitute lookup

**Remaining gaps:**
- CSV export does not identify substitute rows (comment exists, logic not implemented)
- "Show Substitutes" checkbox always enabled (should disable when no subs exist)
- Zero frontend tests for substitute behavior in `bomDataProcessing.test.ts`
- Needs staging verification before merge

**See:** [Substitute Parts Implementation Plan](planning/SUBSTITUTE-PARTS-IMPLEMENTATION-PLAN.md)

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


### Variant Parts Support -- Not Planned

InvenTree's variant/template part system (template parts with `is_template=True`,
variants via `variant_of`, and `allow_variants` on BomItems) adds significant
complexity to BOM traversal, stock aggregation, and deduplication. After
evaluation, this is out of scope for the Flat BOM Generator plugin:

- Correctly respecting `allow_variants` requires per-BomItem flag tracking
  through the entire traversal and deduplication pipeline
- Mixed `allow_variants` flags on the same part create deduplication conflicts
  (see Mixed Flag Handling above)
- Variant stock aggregation interacts with every stock column and build margin
  calculation
- The effort (8-10 hours for a correct implementation) outweighs the value for
  this plugin's use case

Users who need variant-aware BOM analysis should use InvenTree's built-in BOM
view and build order system, which handles variants natively.

### UX Polish: Consolidate Filter Checkboxes (1-2 hours, MEDIUM PRIORITY)
**Goal:** Move checkbox filters from ControlBar into a dropdown menu (similar to column visibility)

**Current:** 4 checkboxes in ControlBar taking up space:
- Show Cutlist Rows
- Show Substitutes
- Include Allocations in Build Margin
- Include On Order in Build Margin

**Proposed:** Dropdown button with icon (filter funnel) containing all filters

**Benefits:**
- Cleaner UI with more horizontal space
- Scales better as more filters are added
- Consistent pattern with column visibility dropdown

**Implementation:**
- Reuse Menu component pattern from column visibility
- Keep state in Panel.tsx (no API changes needed)
- Update ControlBar.tsx to replace checkboxes with dropdown

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

### Phase 9: Substitute Parts (Jan 23 - Feb 2026)
- `SubstitutePartSerializer` with DRF pattern (16 fields, 9 unit tests)
- Backend enrichment: `BomItemSubstitute` query, stock data, unit-mismatch warnings
- Generic child row system: `is_child_row` / `child_row_type` / `parent_row_part_id` (replaces `is_cut_list_child`)
- Frontend: blue-themed substitute rows, badge, dark mode, auto-show on generation
- 4 integration tests for enrichment logic
- **Remaining:** CSV export, frontend tests, UX polish (checkbox disable)

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
- [TEST-WRITING-METHODOLOGY.md](reference/TEST-WRITING-METHODOLOGY.md) - Code-first validation approach

**Architecture:**
- [ARCHITECTURE.md](ARCHITECTURE.md) - Plugin architecture, API reference, patterns
- [decisions.md](decisions.md) - Non-obvious technical choices and rationale

**Warnings:**
- [WARNINGS-ROADMAP.md](WARNINGS-ROADMAP.md) - Warning system expansion ideas
- [ARCHITECTURE-WARNINGS.md](reference/ARCHITECTURE-WARNINGS.md) - Warning system implementation patterns

**Deployment:**
- [DEPLOYMENT-WORKFLOW.md](reference/DEPLOYMENT-WORKFLOW.md) - Deployment checklist and testing workflow

---

_Last updated: February 26, 2026_
