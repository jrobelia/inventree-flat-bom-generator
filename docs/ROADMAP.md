# FlatBOMGenerator - Plugin Improvement Roadmap

> **Status:** Testing complete (151 tests, 92% coverage) - Ready for feature work  
> **Last Updated:** January 15, 2026

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

### 🚧 Remaining Test Gaps (Minor, Deferred)
Very low-risk gaps deferred until issues arise:
- CtL features integration (edge cases already tested in unit tests)

### 🎯 Next Milestone
**Feature Development Phase** - Establish clean architecture, then add features:
1. Frontend refactoring (clean foundation before adding features)
2. Optional/substitute parts support (build on clean architecture)
3. Variant parts support (determine usage patterns first)
4. InvenTree export integration (backend-only, can do anytime)

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

---

## Key Lessons Learned

### What Works
1. **Fixture-based testing** - Programmatic loading bypasses InvenTree validation
2. **Code-first validation** - Read actual code before writing tests (found 96 lines dead code)
3. **Test-first workflow** - Caught bugs during serializer refactoring
4. **Incremental phases** - Small verifiable changes prevent stacking unverified work
5. **Production validation** - Deploy → Test in UI → Verify catches integration issues

### What to Avoid
1. ❌ Skipping deployment after code changes
2. ❌ Assuming "tests pass" = "code works in production"
3. ❌ Creating code without checking existing solutions
4. ❌ Accepting test gaps too quickly

### Core Principle
> "Test what you refactor, not just what's easy. Use fixtures when Django validation blocks test creation."

---

## Planned Improvements (Next 1-3 Months)

### Frontend Refactoring (16-24 hours, HIGH PRIORITY)
**Goal:** Improve maintainability and establish clean architecture before adding new features

**Status:** ✅ **PLANNED - Comprehensive guide complete**

**Current State:**
- Panel.tsx is **1240 lines** with inline logic (55% larger than originally estimated 800+)
- All state management in single component
- ~400 lines of column definitions inline
- No component extraction
- No custom hooks
- Violates React best practices (components should be <300 lines)

**Why Now:**
- Backend is solid (312 tests passing, all gaps closed, 92% coverage)
- Adding features to 1240-line file will make it worse
- Refactoring gets harder as file grows
- **Blocks optional/substitute parts feature** (needs clean architecture)
- Industry best practice: clean code before new features

**Implementation Plan:**
- **Complete Guide:** [FRONTEND-REFACTORING-GUIDE.md](FRONTEND-REFACTORING-GUIDE.md)
- **5 Phases:** Extract types → Extract hooks → Extract components → Optimize → Test
- **Target:** Panel.tsx: 1240 → 240 lines (80% reduction)
- **Result:** 20+ focused, testable modules

**Updated Estimate:** 16-24 hours (increased from 8-12 due to actual file size)

**Benefits:**
- Panel.tsx under 300 lines (target achieved)
- All logic testable in isolation
- Proper memoization and performance optimization
- Clean foundation for optional/substitute/variant features
- Easier for AI agents to work with (smaller files, clearer structure)
- 30-40% faster feature development after refactoring

**ROI:** Refactoring time recovered after 2-3 new features

**Do First:** Complete refactoring before adding optional/substitute parts

**Reference:** See [FRONTEND-REFACTORING-GUIDE.md](FRONTEND-REFACTORING-GUIDE.md) for step-by-step implementation plan with code examples

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

### Warning System Expansion (3-5 hours, LOW PRIORITY)
**Goal:** Add more warning types for better user guidance

**Current Warnings:** (4 types implemented)
- `unit_mismatch` - Cut-to-length parts with inconsistent units
- `inactive_part` - Parts marked inactive in InvenTree
- `assembly_no_children` - Assemblies without BOM items
- `max_depth_exceeded` - BOM traversal stopped by depth limit

**Proposed New Warnings:** (See [WARNINGS-ROADMAP.md](WARNINGS-ROADMAP.md))
- Missing supplier - Parts without default supplier
- Zero stock - Parts with no inventory and no incoming POs
- Obsolete parts - Parts marked for discontinuation
- Long lead time - Parts with >30 day lead time
- BOM conflicts - Duplicate parts with different quantities

**Implementation:**
- Add warning type to serializer enum
- Implement detection logic in views.py
- Add i18n translations
- Update UI to display new warnings

**Status:** Core warning infrastructure complete, expansion deferred

---

### Optional Parts & Substitute Parts Support (6-10 hours, MEDIUM PRIORITY)
**Goal:** Integrate InvenTree's optional and substitute part features into flat BOM display

**InvenTree Native Features:**
InvenTree has built-in support for both features:
- **Optional Parts**: Boolean `optional` field on BomItem (parts that can be excluded from builds)
- **Substitute Parts**: `BomItemSubstitute` model linking alternative parts to BOM items
  - Multiple substitutes per BOM item allowed
  - Substitute stock included in availability calculations
  - Can be allocated during build orders

**Current Plugin Behavior:**
- Flattens BOM without considering `optional` flag
- Does not include substitute parts in flat view
- Does not show which parts have substitutes available
- Stock calculations don't account for substitute availability

**Design Decisions:**

**Substitute Parts = Cutlist Pattern:**
- Treat substitutes like cutlist rows (additional rows tied to parent part)
- Reuse existing cutlist infrastructure (already handles multiple rows per part)
- Display substitute part names (not arrows like cutlist)
- Each substitute gets its own row with full stock data
- **Sorting behavior**: Only parent parts participate in sort; substitutes stay grouped below parent
- When sorted, substitutes move with their parent (never separated)

**UI Controls Refactoring:**
- Move settings from plugin config to checkboxes near "Generate" button
- Better UX: controls where you need them
- Checkboxes to add:
  - "Include Optional Parts" (default: unchecked - user decides)
  - "Include Substitute Parts" (default: unchecked)
  - "Include Allocations" (existing - move from separate location)
  - "Include On Order" (existing - move from separate location)

**Optional Parts = Badge with Filtering:**
- Orange "Optional" badge in dedicated "Flags" column
- "Flags" column can show: [Optional], [Substitute], or both badges
- Italic text styling for optional part rows
- Controlled by "Include Optional Parts" checkbox
- When excluded, optional parts don't appear in table or shortfall calculations
- Sortable column: sorts by flag presence (flagged parts grouped together)

**Proposed Changes:**

1. **Optional Parts Display** (2-3 hours)
   - Add `optional` field to BomItem data retrieval
   - Add "Flags" column with badge (orange for optional, sortable)
   - Italic text styling for optional part rows
   - Filter controlled by "Include Optional Parts" checkbox
   - When excluded: remove from table, exclude from shortfall/stats calculations

2. **Substitute Parts Integration** (3-4 hours)
   - Query `BomItemSubstitute` relationships during BOM enrichment
   - Create additional rows per substitute (like cutlist breakdown)
   - Display: "[Substitute] Part Name" in Component column
   - Show "[Substitute]" badge in Flags column
   - Each substitute row shows individual stock, allocated, on order, shortfall
   - Controlled by "Include Substitute Parts" checkbox near Generate button
   - Substitutes stay grouped with parent during sorting (don't sort independently)

3. **UI Controls Consolidation** (2-3 hours)
   - Group checkboxes near "Generate Flat BOM" button
   - Move existing "Include Allocations" and "Include On Order" from current location
   - Add "Include Optional Parts" checkbox
   - Add "Include Substitute Parts" checkbox
   - Cleaner interface: all generation options in one place
   - Add "Flags" column to table (13th column, sortable by flag presence)

**Implementation Notes:**
- Substitutes leverage `deduplicate_and_sum()` cutlist pattern
- Each substitute is a separate dict entry (like cutlist items)
- Stock calculations per substitute (not aggregated)
- User can see which substitute has best availability

**Backend Changes:**
- Update `views.py` to query `BomItemSubstitute` relationships
- Mark items with `optional` flag in enrichment
- Create substitute rows (similar to cutlist row generation)
- Add parent grouping logic to keep substitutes attached during sorting
- No changes to `bom_traversal.py` needed (substitutes are post-flatten enrichment)

**Testing Requirements:**
- Unit tests: optional flag display logic
- Integration tests: BomItemSubstitute relationships with fixture data
- UI verification: badges, checkbox controls, substitute rows

**Benefits:**
- Reuses proven cutlist infrastructure
- Better UX: controls consolidated near Generate button
- Clear visibility: see each substitute's individual stock
- Simple optional indicator (no complex filtering)
- Helps identify which substitute to use based on availability

**Updated Time Estimate:** 7-10 hours (increased from 6-9 due to optional column + filtering)

**Open Questions:**
1. Should substitute stock count toward shortfall calculation? (Probably no - show each separately)
2. Sort order: Primary part first, then substitutes alphabetically?
3. Should "Total Unique Parts" count include substitutes? (Probably no - they're alternatives)
4. Default state: Include optional parts ON or OFF?

**Defer Until:** Gather user feedback on checkbox placement and default behavior

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

## Future Ideas (Exploratory)

### Warning System Expansion (3-5 hours, LOW PRIORITY)
**Goal:** Add more warning types for better user guidance

**Current Warnings:** (4 types implemented)
- `unit_mismatch` - Cut-to-length parts with inconsistent units
- `inactive_part` - Parts marked inactive in InvenTree
- `assembly_no_children` - Assemblies without BOM items
- `max_depth_exceeded` - BOM traversal stopped by depth limit

**Proposed New Warnings:** (See [WARNINGS-ROADMAP.md](WARNINGS-ROADMAP.md))
- Missing supplier - Parts without default supplier
- Zero stock - Parts with no inventory and no incoming POs
- Obsolete parts - Parts marked for discontinuation
- Long lead time - Parts with >30 day lead time
- BOM conflicts - Duplicate parts with different quantities

**Implementation:**
- Add warning type to serializer enum
- Implement detection logic in views.py
- Add i18n translations
- Update UI to display new warnings

**Defer Until:** User feedback indicates value

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
