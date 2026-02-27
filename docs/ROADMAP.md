# FlatBOMGenerator - Plugin Improvement Roadmap

> **Status:** v0.11.53 on `main` -- substitute parts + checkbox UX complete, deployed to staging  
> **Last Updated:** February 27, 2026

---

## Current Status (v0.11.53 on `main`)

### ✅ Major Accomplishments
- **Substitute Parts** - Backend enrichment, frontend display with generic child row system, 22 tests (13 unit + 4 integration + 5 data-processing)
- **Checkbox UX** - "Show Substitutes" hidden when setting off, disabled with tooltip when no substitutes exist; 10 tests
- **Test Infrastructure** - 74 frontend tests (Vitest) + 164+ backend tests, Vitest conventions documented
- **Code Quality** - Removed 96 lines dead code, fixed 3 incorrect fallbacks, 1 production bug
- **Frontend Architecture** - Panel.tsx: 1250 → 306 lines (68% reduction) via component extraction
- **Settings UI** - Moved from admin to frontend with progressive disclosure pattern
- **Optional/Consumable Parts** - Smart flag aggregation, visual badges, priority sorting
- **Warning System** - 4 warning types with integration test coverage
- **DRF Serializers** - All API responses use proper serialization

**See [Completed Work Archive](#completed-work-archive) for detailed phase history.**

### 🎯 Next Steps
1. **Mixed Flag Handling** -- same part with different optional/consumable flags loses info during deduplication (HIGH, 2-3 hours)
2. **Child Row Visual Consistency** -- CtL, substitute, and mixed-flag child rows need a coherent look that feels InvenTree-native (MEDIUM, 2-4 hours)
3. **UI Overhaul: Control Bar** -- too many checkboxes; evaluate dropdown vs other pattern, resolve hide/disable UX for CtL and substitute rows (MEDIUM, 1-2 hours)
4. **Pre-Generation Info Panel** -- explain plugin-specific features (substitutes, CtL, mixed flags) before user hits Generate (LOW, 1-2 hours)
5. Replace "All" rows-per-page option with 500 / 1000 to match InvenTree (LOW, 0.5 hours)
6. InvenTree export integration (replace custom CSV) (LOW, 4-6 hours)

---

## Planned Features

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
key = (part_id, optional, consumable, cut_length)
```

**Properties that could create separate line items:**
1. `optional` - Can be omitted to save cost
2. `consumable` - Not in final product (solder paste, etc.)
3. `note` (CtL only) - Already handled via cutlist breakdown
4. `reference` - Combines correctly ("R1, R2, R3")
5. `inherited` - Ignore (doesn't affect purchasing)

Note: `allow_variants` is excluded from the key -- variant support is out of scope (see below).

**Implementation Options:**
- **Option A**: Separate top-level rows (OA-00012 [Optional] Qty: 3, OA-00012 [Required] Qty: 2)
- **Option B**: Parent/child pattern like cutlist (expandable breakdown)
- **Option C**: Current + warning badge ("⚠️ Mixed flags")

**Recommendation:** Start with Option A (simpler), evolve to Option B later

**Impact on Future Features:**
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

### UI Overhaul: Control Bar (1-2 hours, MEDIUM PRIORITY)
**Problem:** The ControlBar has grown to 4+ checkboxes and will keep growing as features are added (mixed flags, future filters). It feels cluttered and inconsistent with the rest of InvenTree.

**Open Question:** What is the right UI pattern?
- **Option A -- Dropdown menu** (like column visibility): all filters behind a single button with a filter funnel icon. Clean, scalable, already has a precedent in this plugin.
- **Option B -- Collapsible panel**: filters in a panel that expands below the toolbar. More visible but takes vertical space.
- **Option C -- Toolbar redesign**: group related controls visually (e.g., display options vs build margin options).

**Current checkboxes to rethink:**
- Show Cutlist Rows (should hide/disable when no CtL parts -- see cutlist checkbox item)
- Show Substitutes (already has hide/disable logic)
- Include Allocations in Build Margin
- Include On Order in Build Margin

**Decision needed:** Pick the UI pattern before implementing. Dropdown (Option A) is the simplest starting point.

**Note:** This item subsumes and replaces the earlier "Consolidate Filter Checkboxes" plan.

### UX Polish: Cutlist Checkbox (0.5-1 hour, LOW PRIORITY)
**Current:** "Show Cutlist Rows" checkbox is always enabled regardless of whether the BOM contains any cut-to-length parts.  
**Goal:** Apply the same hide/disable pattern used for the Substitutes checkbox.

**Complication -- CtL parts come from a setting, not just data:**
- The "Show Substitutes" checkbox can be hidden when the setting is off.
- For CtL, there is no equivalent plugin setting today -- CtL detection is implicit (parts with a length-based unit and a `note` field).
- Options:
  1. **Data-driven only:** detect `hasCutlistRows` from response data and disable/hide purely based on that (simplest, no setting change needed)
  2. **Add a plugin setting:** introduce an explicit `ENABLE_CUTLIST` toggle in the settings panel so users can hide CtL rows at a higher level, then mirror the Substitutes pattern exactly
- Option 2 gives users more control and is consistent with how Substitutes work. May be the right solution if CtL is something not all users want.

**Data-driven implementation (Option 1):**
```typescript
const hasCutlistRows = useMemo(() =>
  bomData?.bom_items?.some(item => item.cutlist_breakdown?.length > 0) || false
, [bomData]);
```
Then apply same hide/disable/tooltip logic as `substituteCheckboxState.ts`.

### UX Polish: Rows-Per-Page Control (0.5 hours, LOW PRIORITY)
**Current:** Table pagination offers 25 / 50 / 100 / **All**  
**Problem:** "All" loads every row with no cap -- slow on large BOMs and inconsistent with the rest of InvenTree

**Goal:** Match InvenTree's standard pagination values: 25 / 50 / 100 / **500 / 1000**

**Implementation:**
- Find the `DataTable` (or equivalent) `recordsPerPageOptions` prop in `Panel.tsx` or the table component
- Replace the `"all"` entry with `500` and `1000`
- No API changes needed -- data is already fully loaded client-side

### Child Row Visual Consistency (2-4 hours, MEDIUM PRIORITY)
**Problem:** The plugin currently has three types of child/extra rows, each styled independently:
- **Cut-to-length child rows** -- grey/neutral theme, `↳` symbol
- **Substitute child rows** -- blue theme, `↳` symbol, "Substitute" badge
- **Mixed flag rows (planned)** -- no style decided yet

These have grown organically and will diverge further as Mixed Flag Handling adds a third type. They need a coherent system that:
1. Makes all child row types feel visually similar to each other (same indentation, same `↳` symbol scale, same cell padding)
2. Makes each type **distinctly identifiable** (colour, badge, or icon -- not just row colour)
3. Feels closer to native InvenTree table patterns (InvenTree uses subtle row shading and tag-style badges)

**Open Questions:**
- Should all child row types share one colour with a distinguishing badge? Or keep distinct colours?
- What does InvenTree use for grouped/child rows in its own tables? Study the source and match the pattern.
- Does the `↳` symbol need to indent further for deeper nesting?

**Dependencies:**
- Mixed Flag Handling (defines what a third child type looks like)
- UI Overhaul (control bar changes may affect row visibility toggles)

**Approach:** Research InvenTree's table row patterns first, then design a unified child row spec before touching any CSS/classes.

---

### Pre-Generation Information Panel (1-2 hours, LOW PRIORITY)
**Problem:** Users land on a blank panel with only a "Generate" button and no explanation of what the plugin does differently from InvenTree's built-in BOM view.

**Features that are non-obvious to new users:**
- Recursive flattening (all levels, not just immediate children)
- Substitute parts display and the setting required to enable it
- Cut-to-length child rows and how length units trigger them
- Mixed flag handling (when implemented)
- Stock columns: what "allocated", "on order", and "build margin" mean
- Warning badges and what triggers them
- CSV export format differences

**Goal:** Add a help/info section that is visible before generation and collapsible after. Should feel like the InvenTree "information" panels used elsewhere (subtle card, not a modal).

**Options:**
- **Collapsible info card** above the Generate button -- visible on first load, user can collapse it
- **"?" icon linking to README** -- minimal, but takes users out of the plugin
- **Tooltip-per-feature** -- adds context at point of use rather than upfront

**Recommendation:** Collapsible info card (collapses after first generation, state persisted in `localStorage`).

---

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

### Phase 9: Substitute Parts (Jan 23 - Feb 27, 2026)
- `SubstitutePartSerializer` with DRF pattern (16 fields, 9 unit tests)
- Backend enrichment: `BomItemSubstitute` query, stock data, unit-mismatch warnings
- Generic child row system: `is_child_row` / `child_row_type` / `parent_row_part_id` (replaces `is_cut_list_child`)
- Frontend: blue-themed substitute rows, badge, dark mode, auto-show on generation
- 4 integration tests for enrichment logic
- Checkbox UX: hidden when setting off, disabled with tooltip when no substitutes in BOM data
- 10 unit tests for checkbox state logic (`substituteCheckboxState.ts`)
- 5 data-processing tests for substitute flattening and grouping (`bomDataProcessing.test.ts`)
- CSV export for substitute rows: deliberately skipped (low value)
- Merged to `main` at v0.11.53

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
- [TEST-WRITING-METHODOLOGY.md](archive/TEST-WRITING-METHODOLOGY.md) - Code-first validation approach (archive)

**Architecture:**
- [ARCHITECTURE.md](ARCHITECTURE.md) - Plugin architecture, API reference, patterns
- [decisions.md](decisions.md) - Non-obvious technical choices and rationale

**Warnings:**
- [WARNINGS-ROADMAP.md](WARNINGS-ROADMAP.md) - Warning system expansion ideas
- [ARCHITECTURE-WARNINGS.md](reference/ARCHITECTURE-WARNINGS.md) - Warning system implementation patterns

**Deployment:**
- [DEPLOYMENT-WORKFLOW.md](reference/DEPLOYMENT-WORKFLOW.md) - Deployment checklist and testing workflow

---

_Last updated: February 27, 2026_
