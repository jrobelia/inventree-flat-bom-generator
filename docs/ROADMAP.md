# FlatBOMGenerator - Plugin Improvement Roadmap

> **Status:** Optional/Consumable Parts Complete - Ready for Production Deployment  
> **Last Updated:** January 22, 2026

---

## Project Status

### ✅ What's Been Completed
- **DRF Serializers** - All API responses use Django REST Framework serializers
- **Warning System** - 4 warning types with full integration test coverage
- **Test Infrastructure** - 151 tests (60 unit + 91 integration), Grade B+ quality, 92% coverage
- **Test Priorities 1-4** - Plugin settings (31 tests), error scenarios (26 tests), warning generation (8 tests), complex BOMs (17 tests), get_bom_items (22 tests)
- **Critical Gaps Closed** - Circular refs (5 tests), plugin core (15 tests), query params (11 tests), view settings (6 tests), stock enrichment (2 tests)
- **Code Quality** - Removed 96 lines dead code, fixed 3 incorrect fallbacks, found/fixed 1 production bug (Part.DoesNotExist)
- **Fixture Breakthrough** - Programmatic fixture loading pattern established
- **Frontend Refactoring (Phase 3)** - Extracted components from Panel.tsx: 950 → 306 lines (68% reduction) → [Archived Guide](internal/archive/2026-01-frontend-refactoring/FRONTEND-REFACTORING-GUIDE.md)
- **Settings UI Implementation** - Moved settings from admin to frontend with progressive disclosure (v0.11.6-v0.11.18) → [Archived Plan](internal/archive/2026-01-settings-ui/SETTINGS-UI-IMPLEMENTATION-PLAN.md)
- **Optional/Consumable Parts** - Flag display, sorting, and smart aggregation logic (v0.11.23)

### 🚧 Remaining Test Gaps (Minor, Deferred)
Very low-risk gaps deferred until issues arise:
- CtL features integration (edge cases already tested in unit tests)

### 🎯 Next Milestone
**Production Deployment** - Ready to deploy v0.11.23 to production:
1. ✅ Settings UI implementation complete
2. ✅ Optional/consumable parts support complete
3. ✅ Merged feature/optional-parts to main
4. 📋 Create release tag v0.11.23
5. 📋 Deploy to production server
6. Substitute parts support (after production validation)
7. Variant parts support (determine usage patterns first)
8. InvenTree export integration (backend-only, can do anytime)

---

## Completed Refactoring Phases

### Phase 1: Test Quality Foundation (Dec 18, 2025)
- Established code-first test methodology
- Rewrote internal fab tests (14 tests, removed stub functions)
- Fixed skipped test, found 45 lines dead code

### Phase 2: Test Validation (Jan 9, 2026)
- Validated 164 unit tests with code-first methodology
- Added 30 tests to fill coverage gaps
- Fixed 4 broken integration tests, found 51 lines dead code

### Phase 3: Serializer Refactoring (Dec 15-18, 2025)
- Implemented BOMWarningSerializer, FlatBOMItemSerializer, FlatBOMResponseSerializer
- Created 38 serializer tests
- Found 2 bugs (note field, image URLs)

### Phase 4: Integration Test Priorities (Jan 9-12, 2026)
- Priority 1: Plugin settings & configuration (31 tests)
- Priority 2: Error scenarios (26 tests, found 1 bug)
- Priority 3: Warning generation (8 tests, fixture-based approach)
- Priority 4: Complex BOM structures (17 tests, programmatic fixture loading)

### Phase 5: Critical Gaps Closure (Jan 12, 2026)
- Gap #1: get_bom_items() function (22 tests for BOM fetching logic)
- Gap #2: Circular reference detection (5 tests with fixture)
- Gap #3: Plugin core methods (15 tests for setup_urls, get_ui_panels)
- Gap #4: Query parameter validation (11 tests for max_depth)
- Gap #5: View settings loading (6 tests with double-patch mocking)
- Gap #6: Stock enrichment errors (2 tests, found/fixed production bug)

### Phase 6: Frontend Refactoring Phase 3 (Jan 18, 2026)
- Completed all 5 steps of Phase 3 component extraction
- Panel.tsx reduced: 950 → 306 lines (68% reduction)
- Current: 396 lines (with Settings UI added in Phase 7)
- Extracted components: ErrorAlert, WarningsAlert, StatisticsPanel, ControlBar, bomTableColumns
- Created ExtendedColumn<T> type workaround for mantine-datatable TypeScript gap
- Fixed critical bug: DataTable requires `switchable` property (not `toggleable`) for column visibility
- Removed 6 unused imports from Panel.tsx
- All changes deployed and tested on staging server

**Critical Discovery:** `toggleable` vs `switchable` property name
- DataTable crashes with "can't access property 'filter', R is undefined" when using wrong property
- TypeScript doesn't include `switchable` in DataTableColumn type definition (runtime-only property)
- Solution: Created `type ExtendedColumn<T> = DataTableColumn<T> & { switchable?: boolean };`

### Phase 7: Settings UI Implementation (Jan 20-21, 2026) ✅ COMPLETE
- Moved 3 settings from admin panel to frontend UI with localStorage persistence
- Added "Show Cutlist Rows" frontend filter to ControlBar
- Implemented progressive disclosure (settings panel → drawer after first generation)
- Added visual clarity enhancements (info icon, better spacing, section header)
- Simplified progressive disclosure pattern (removed hasGeneratedOnce tracking)
- All changes tested and verified on staging server (v0.11.6-v0.11.18)

**📁 Archived:** [SETTINGS-UI-IMPLEMENTATION-PLAN.md](internal/archive/2026-01-settings-ui/SETTINGS-UI-IMPLEMENTATION-PLAN.md)

### Phase 8: Optional/Consumable Parts (Jan 22, 2026) ✅ COMPLETE
- Added `optional` and `consumable` boolean fields to BomItem interface
- Backend: Extract flags from BomItem model in `get_bom_items()`
- Backend: Propagate flags through `traverse_bom()` and `get_leaf_parts_only()`
- Backend: Smart aggregation in `deduplicate_and_sum()` - flag=True only if ALL instances have flag
- Serializer: Added `optional` and `consumable` fields to FlatBOMItemSerializer
- Frontend: New "Flags" column with orange "Optional" and yellow "Consumable" badges
- Frontend: Tooltips explain flag meaning
- Frontend: Sorting by flag priority (optional+consumable > optional > consumable > none)
- All changes tested and merged to main (v0.11.23)

**Key Implementation:**
- Aggregation logic: Part marked optional/consumable only if it appears that way in ALL BOM paths
- Example: If part appears 3 times (2 optional, 1 required) → final flag = False (not all optional)
- Sorting: Score-based (optional=2, consumable=1, total score determines order)

**📁 Archived:** [SETTINGS-UI-IMPLEMENTATION-PLAN.md](internal/archive/2026-01-settings-ui/SETTINGS-UI-IMPLEMENTATION-PLAN.md)

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

## Planned Improvements (Next 1-3 Months)

### Frontend Refactoring (16-24 hours, HIGH PRIORITY)
**Goal:** Improve maintainability and establish clean architecture before adding new features

**Status:** ✅ **COMPLETE - Phase 3 refactoring done January 18, 2026**

**📁 See:** [FRONTEND-REFACTORING-GUIDE.md](internal/archive/2026-01-frontend-refactoring/FRONTEND-REFACTORING-GUIDE.md) (archived)

**Original State (pre-refactoring):**
- Panel.tsx was 950 lines with inline logic
- All state management in single component
- ~400 lines of column definitions inline
- No component extraction
- No custom hooks

**Current State (post-refactoring + Settings UI):**
- Panel.tsx is 396 lines (58% smaller than original 950)
- Component extraction complete (5 components)
- Custom hooks extracted (5 hooks)
- Clean architecture established

**Why It Was Done:**
- Backend was solid (312 tests passing, all gaps closed, 92% coverage)
- Adding features to 950-line file would have made it worse
- Established clean architecture before Settings UI feature
- Now ready for optional/substitute parts features

**What Was Completed:**
- **Guide Used:** [FRONTEND-REFACTORING-GUIDE.md](FRONTEND-REFACTORING-GUIDE.md)
- **5 Steps Executed:** Extract types → Extract hooks → Extract components (5 components)
- **Result:** Panel.tsx: 950 → 306 lines (68% reduction)
- **Current:** 396 lines (after Settings UI added)
- **Outcome:** 10+ focused, testable modules

**Time Invested:** Approximately 8-12 hours across Phase 6

**Benefits Achieved:**
- ✅ Panel.tsx under 400 lines (even with Settings UI added)
- ✅ All logic testable in isolation
- ✅ Proper memoization and performance optimization
- ✅ Clean foundation for optional/substitute/variant features
- ✅ Easier for AI agents to work with (smaller files, clearer structure)
- ✅ Settings UI feature implemented quickly on clean architecture

**ROI:** Refactoring investment already paying off - Settings UI took 3-5 hours vs estimated 8-10 hours on monolithic file

**📁 Archived:** [FRONTEND-REFACTORING-GUIDE.md](internal/archive/2026-01-frontend-refactoring/FRONTEND-REFACTORING-GUIDE.md) (4500 lines)

---

### ✅ Settings UI/UX Improvement (COMPLETE - v0.11.6-v0.11.18)
**Goal:** Move plugin settings from admin panel to panel UI for better user experience

**📁 See:** [SETTINGS-UI-IMPLEMENTATION-PLAN.md](internal/archive/2026-01-settings-ui/SETTINGS-UI-IMPLEMENTATION-PLAN.md) (archived)

**Implementation Complete:**
- ✅ Moved 3 backend settings to frontend with localStorage persistence
  - Maximum Traversal Depth (NumberInput)
  - Expand Purchased Assemblies (Switch)
  - Include Internal Fab Parts in Cutlist (Switch with dynamic units label)
- ✅ Added "Show Cutlist Rows" frontend filter (Checkbox in ControlBar)
- ✅ Implemented progressive disclosure (settings panel before first generation, drawer after)
- ✅ Added visual clarity enhancements:
  - Info icon in Alert box
  - Increased spacing (gap='lg')
  - "GENERATION SETTINGS" section header
  - Refined button sizing to match InvenTree standards
- ✅ All changes tested and verified on staging server

**Benefits Achieved:**
- ✅ Better UX: Change settings without leaving panel
- ✅ Per-session settings: Experiment without affecting other users
- ✅ InvenTree consistency: Uses toggle switches and drawer pattern
- ✅ Faster workflow: No page navigation required
- ✅ Progressive disclosure: Show complexity only when needed
- ✅ Guided first use: Settings prominent before first generation
- ✅ Clean data focus: Settings collapse after first generation

**Deployment Status:** Ready for production

---

### Settings UI/UX Improvement (3-5 hours, COMPLETED)
**Goal:** Move plugin settings from admin panel to panel UI for better user experience

**InvenTree Pattern Analysis:**
InvenTree uses **different patterns for different purposes**:
- **Filters** → Side drawer (`Drawer` component, slides in from right, must be closed)
- **Column visibility** → Menu dropdown (`Menu` component, closes on blur)
- **Build quantity** → Always visible (NumberInput in header)

InvenTree's BomTable:
- Filters passed to backend via API params (e.g., `available_stock=true`)
- Filters trigger automatic table refresh when applied
- Column visibility is quick toggle (no refresh needed)

**Recommendation:** Use **Drawer** (slide-out panel) for settings, matching InvenTree's filter pattern

**Current State:**
- Settings are in InvenTree plugin configuration page (admin panel)
- Users must leave the panel, navigate to settings, change value, return to panel, regenerate
- Uses checkboxes (not consistent with InvenTree's toggle switches in newer UI)
- Settings are plugin-wide, not per-session

**Proposed Changes:**
Move these settings from plugin config to panel UI:

1. **Maximum Traversal Depth** (number input)
   - Currently: Plugin setting (global)
   - Proposed: Number input in settings panel (per-session)
   - Default: Keep plugin setting as default value
   - Behavior: Auto-refresh on change (InvenTree pattern)

2. **Expand Purchased Assemblies** (Switch)
   - Currently: Plugin setting checkbox
   - Proposed: Switch in settings panel
   - Default: Plugin setting value
   - Behavior: Auto-refresh on change

3. **Include Internal Fab Parts in Cutlist** (Switch)
   - Currently: Plugin setting checkbox ("Enable Internal Fab Cut Breakdown")
   - Proposed: Switch in settings drawer with dynamic units label
   - Label: "Include Ifab in Cutlist (mm, in, cm)" - units from CUTLIST_UNITS_FOR_INTERNAL_FAB setting
   - Default: Plugin setting value
   - Behavior: Auto-refresh on change (triggers backend processing)

**Always Visible Controls (ControlBar - Immediate Frontend Filters):**
- **Build Quantity** (NumberInput) - Multiplies requirements
- **Include Allocations** (Checkbox) - Use available vs total stock
- **Include On Order** (Checkbox) - Include incoming in shortfall
- **Show Cutlist Rows** (NEW - Checkbox) - Show/hide BOTH Native CtL and Internal Fab cutlist child rows

**UI Layout Strategy (Progressive Disclosure + InvenTree Pattern):**

**Before First Generation (Settings Prominent):**
```
┌─────────────────────────────────────────────────────────────┐
│ 📋 Generation Settings                                       │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ Max Depth: [10 ▼]                                      │   │
│ │ ☑️ Expand Purchased Assemblies                         │   │
│ │ ☑️ Include Ifab in Cutlist (mm, in, cm)               │   │
│ │                                                         │   │
│ │ [Apply Settings]  [Reset to Defaults]                  │   │
│ └───────────────────────────────────────────────────────┘   │
│                                                              │
│ [Generate Flat BOM]                                         │
└─────────────────────────────────────────────────────────────┘
```
*Settings visible in Paper component to guide first-time configuration*

**After First Generation (Clean Data Focus):**
```
┌───────────────────────────────────────────────────────────────┐
│ [Build Qty: 5] [☑️ Allocations] [☑️ On Order] [☑️ Cutlists] │
│ [⚙️●] [⋮ Columns] [Export ▼]                                 │
│   ↑                                                           │
│  Settings drawer (blue if custom)                            │
└───────────────────────────────────────────────────────────────┘
```
*Settings collapse to icon, cutlist toggle moves to ControlBar (immediate effect)*

**Settings Drawer (Slides from Right):**
```
                    ┌──────────────────────────────────┐
                    │ ✕  Generation Settings            │
                    ├──────────────────────────────────┤
                    │                                   │
                    │ Backend Settings                  │
                    │ (triggers auto-refresh on Apply)  │
                    │ ───────────────────────────────   │
                    │ Max Depth: [10 ▼]                │
                    │ ☑️ Expand Assemblies              │
                    │ ☑️ Include Ifab in Cutlist        │
                    │    (mm, in, cm)                   │
                    │                                   │
                    │ [Apply]  [Reset to Defaults]      │
                    │                                   │
                    └──────────────────────────────────┘
```
*Note: Units (mm, in, cm) loaded from CUTLIST_UNITS_FOR_INTERNAL_FAB plugin setting*

**Design Patterns:**
- **Progressive Disclosure**: Show settings panel initially, hide after first generation (collapse to gear icon)
- **Drawer Component**: Mantine `Drawer` slides from right (InvenTree standard for filters)
- **Auto-Refresh on Apply**: Backend settings (Max Depth, Expand Assemblies, Include Ifab) trigger automatic BOM regeneration when "Apply" clicked
- **Immediate Frontend Filters**: ControlBar toggles (Allocations, On Order, Cutlists) filter table without refresh
- **Dynamic Labels**: Include Ifab setting shows units from plugin config (e.g., "mm, in, cm")
- **Visual Indicators**: Blue gear icon when settings differ from defaults
- **Persistent State**: Store in localStorage which view to show (expanded panel vs. drawer icon)
- **Must Close Drawer**: User clicks Apply/Close to dismiss (standard drawer behavior)
- **Frequency-Based Grouping**: Frequently-toggled controls (Build Qty, Allocations, On Order, Cutlists) always visible; rarely-changed backend settings in drawer

**Benefits:**
- ✅ **Guided first use**: Settings prominent before first generation (discoverability)
- ✅ **Clean data focus**: Settings collapse after first generation (less clutter)
- ✅ **Visual feedback**: Blue dot indicator shows custom settings active
- ✅ **Better UX**: Change settings without leaving panel
- ✅ **Per-session settings**: Experiment without affecting other users
- ✅ **InvenTree consistency**: Use toggle switches instead of checkboxes
- ✅ **Faster workflow**: No page navigation required
- ✅ **Progressive disclosure**: Show complexity only when needed

**Implementation:**

1. **Frontend State Management** (1.5-2 hours)
   - Add state variables for 4 new settings
   - Add `settingsDrawerOpen` state (true before first generation, false after)
   - Add `hasCustomSettings` computed value (compare to defaults)
   - Load defaults from plugin settings (via API or context)
   - Store in localStorage: settings values + drawer expansion state

2. **Backend Parameter Handling** (1-2 hours)
   - Accept optional query parameters: `max_depth`, `expand_assemblies`, `enable_cuts`, `include_cutlist`
   - Override plugin settings with query param values
   - Maintain backward compatibility (defaults from plugin settings)

3. **UI Component Updates** (1.5-2 hours)
   - Create `SettingsPanel` component (expanded Paper view before first generation)
   - Create `SettingsDrawer` component (Mantine Drawer, slides from right)
   - Add settings icon to ControlBar with indicator badge
   - Implement "Apply Settings" button (triggers auto-refresh for backend settings)
   - Use Mantine `Switch` components (toggle style)
   - Add "Reset to Defaults" button in drawer

4. **UX State Transitions** (0.5 hours)
   - Show settings panel before first generation
   - Collapse to icon after first successful BOM generation
   - Drawer opens when clicking gear icon
   - Apply button closes drawer and triggers refresh (if backend settings changed)
   - Frontend filters (Include Cut Parts) apply immediately without closing drawer
   - Persist drawer open/closed state in localStorage

**Testing Requirements:**
- ✅ Settings panel visible on initial load (before first generation)
- ✅ Settings collapse to drawer after first successful generation
- ✅ Gear icon shows blue color/badge when settings differ from defaults
- ✅ Drawer opens/closes correctly when clicking gear icon
- ✅ "Apply Settings" button triggers refresh for backend settings
- ✅ Frontend filters (Include Cut Parts) work immediately without refresh
- ✅ Toggles correctly override plugin settings
- ✅ localStorage persists user preferences + drawer state
- ✅ Query params passed correctly to backend
- ✅ "Reset to Defaults" button works
- ✅ Drawer slides from right (InvenTree pattern)
- ✅ Frontend tests for state management

**Backward Compatibility:**
- Plugin settings remain as defaults
- API accepts both old and new parameter names
- No breaking changes to existing functionality

**Open Questions:**
1. Should Drawer stay open while toggling frontend filters (Include Cut Parts)?
   - **Recommendation**: YES - allows experimenting with display options
2. Should "Apply" button behavior differ for backend vs frontend settings?
   - **Recommendation**: Apply closes drawer only if backend settings changed (triggers refresh)
3. Should plugin settings continue as global defaults after UI implementation?
   - **Recommendation**: YES - good fallback for users who prefer admin configuration

**Defer Until:** Frontend refactoring complete (need clean ControlBar architecture)

---

### UX Polish: Cutlist Checkbox State (0.5 hours, LOW PRIORITY)
**Goal:** Improve cutlist checkbox UX when no cutlist parts present

**Current Behavior:**
- "Show Cutlist Rows" checkbox always enabled
- When no cutlist parts in BOM, checkbox has no effect (nothing to show/hide)
- No visual indication that checkbox is irrelevant

**Proposed Changes:**
1. Disable checkbox when `bomData` contains zero cutlist rows
2. Update label to indicate why disabled: "Show Cutlist Rows (none in BOM)"
3. Grey out checkbox with Mantine `disabled` prop

**Implementation:**
```typescript
// In ControlBar component
const hasCutlistRows = useMemo(() => {
  return bomData?.bom_items?.some(item => 
    item.cutlist_breakdown && item.cutlist_breakdown.length > 0
  ) || false;
}, [bomData]);

<Checkbox
  label={hasCutlistRows ? "Show Cutlist Rows" : "Show Cutlist Rows (none in BOM)"}
  checked={showCutlistRows}
  onChange={(e) => setShowCutlistRows(e.currentTarget.checked)}
  disabled={!hasCutlistRows}
/>
```

**Benefits:**
- Clearer UX - users understand when cutlist feature is inactive
- Prevents confusion about non-functional checkbox
- Follows accessibility best practices (disabled state for unavailable actions)

**Testing:**
- Verify disabled state when BOM has no cutlist parts
- Verify enabled state when cutlist parts present
- Check label text updates correctly

**Defer Until:** After optional/substitute parts feature complete (may affect cutlist detection logic)

---

### InvenTree Export Integration (4-6 hours, MEDIUM PRIORITY)
**Goal:** Replace custom CSV export with InvenTree's built-in export system

**Current State:**
- Custom CSV export in Panel.tsx
- Manual field escaping and formatting
- Only supports CSV format

**Proposed Changes:**
1. Add `DataExportMixin` to plugin class
2. Register flat BOM export endpoint
3. Replace frontend "Export CSV" button with InvenTree's export dialog
4. Remove custom `escapeCsvField` logic

**Benefits:**
- Multiple formats supported (CSV, JSON, XLSX)
- Automatic encoding and escaping
- Consistent UI/UX with rest of InvenTree
- Server-side generation (no client memory limits)

**Reference:** See InvenTree source for standard BOM export implementation

**Defer Until:** Backend 100% stable with comprehensive tests

---
**Goal:** Replace custom CSV export with InvenTree's built-in export system

**Current State:**
- Custom CSV export in Panel.tsx
- Manual field escaping and formatting
- Only supports CSV format

**Proposed Changes:**
1. Add `DataExportMixin` to plugin class
2. Register flat BOM export endpoint
3. Replace frontend "Export CSV" button with InvenTree's export dialog
4. Remove custom `escapeCsvField` logic

**Benefits:**
- Multiple formats supported (CSV, JSON, XLSX)
- Automatic encoding and escaping
- Consistent UI/UX with rest of InvenTree
- Server-side generation (no client memory limits)

**Reference:** See InvenTree source for standard BOM export implementation

**Defer Until:** Backend 100% stable with comprehensive tests

---

### Substitute Parts Support (MEDIUM PRIORITY)
**Goal:** Display InvenTree's substitute parts with individual stock visibility

**InvenTree Feature:**
- `BomItemSubstitute` model linking alternative parts to BOM items
- Multiple substitutes per BOM item allowed
- Substitute stock included in InvenTree's availability calculations
- Can be allocated during build orders

**Current Plugin Behavior:**
- Does not include substitute parts in flat view
- Does not show which parts have substitutes available
- Stock calculations don't account for substitute availability

**Design Decision: Substitute Parts = Cutlist Pattern**
- Treat substitutes like cutlist rows (additional rows tied to parent part)
- Reuse existing cutlist infrastructure (already handles multiple rows per part)
- Display substitute part names (not arrows like cutlist)
- Each substitute gets its own row with full stock data
- **Sorting behavior**: Only parent parts participate in sort; substitutes stay grouped below parent

**Proposed Changes:**

1. **Substitute Parts Integration**
   - Query `BomItemSubstitute` relationships during BOM enrichment
   - Create additional rows per substitute (like cutlist breakdown)
   - Display: "[Substitute] Part Name" in Component column
   - Show "[Substitute]" badge in Flags column
   - Each substitute row shows individual stock, allocated, on order, shortfall

2. **Substitute Parts Filtering**
   - Add "Include Substitute Parts" checkbox (default: unchecked)
   - When excluded: show only primary parts
   - When included: expand to show substitute alternatives
   - Substitutes stay grouped with parent during sorting (don't sort independently)

**Backend Changes:**
- Update `views.py` to query `BomItemSubstitute` relationships
- Create substitute rows (similar to cutlist row generation)
- Add parent grouping logic to keep substitutes attached during sorting
- No changes to `bom_traversal.py` needed (substitutes are post-flatten enrichment)

**Implementation Notes:**
- Substitutes leverage `deduplicate_and_sum()` cutlist pattern
- Each substitute is a separate dict entry (like cutlist items)
- Stock calculations per substitute (not aggregated)
- User can see which substitute has best availability

**Testing Requirements:**
- Integration tests: BomItemSubstitute relationships with fixture data
- UI verification: substitute rows, checkbox controls, grouping behavior

**Benefits:**
- Reuses proven cutlist infrastructure
- Clear visibility: see each substitute's individual stock
- Helps identify which substitute to use based on availability
- No complex aggregation logic needed

**Open Questions:**
1. Should substitute stock count toward shortfall calculation? (Probably no - show each separately)
2. Sort order: Primary part first, then substitutes alphabetically?
3. Should "Total Unique Parts" count include substitutes? (Probably no - they're alternatives)

**Defer Until:** Gather user feedback on default behavior

---

### Variant Parts Support (2-10 hours, PRIORITY TBD)
**Goal:** Integrate InvenTree's variant/template part system into flat BOM display

**InvenTree Variant System:**
- Template parts (`is_template=True`) with variant children (`variant_of` relationship)
- Stock exists on variants, not templates
- `allow_variants` BomItem flag allows any variant to fulfill requirement
- Parts have `variant_stock` (total across all variants) vs `in_stock` (specific part only)
- Stock items can be converted between variants via API

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
- Stock calculations include variant stock when flag is true
- Badge: "Variants Allowed" on affected BomItems
- Most accurate to InvenTree's build allocation logic

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

_Last updated: January 15, 2026_
