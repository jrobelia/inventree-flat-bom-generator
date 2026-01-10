# FlatBOMGenerator - Plugin Improvement Roadmap

> **Status:** 90% complete - Backend solid, ready for feature expansion  
> **Last Updated:** January 9, 2026

---

## Current Status

### ✅ Completed Work
- **Serializer Refactoring** (Phases 1-3) - DRF serializers for all API responses
- **Warning System** - 4 warning types (unit_mismatch, inactive_part, assembly_no_children, max_depth_exceeded)
- **Test Infrastructure** - 195 tests (164 unit + 31 integration), all passing, grade A-
- **Code Quality** - Removed 96 lines dead code, fixed 3 incorrect fallbacks
- **Documentation** - Code-first methodology, testing patterns, API reference

### 🔴 Current Priorities

**1. Deploy Serializer Refactoring** (30-45 min)
- Phase 3 FlatBOMResponseSerializer ready for production
- All tests passing, validated on staging
- Action: Build → Deploy → Verify API response format

**2. Integration Test Coverage** (6-8 hours)
- 7 critical gaps identified (see [TEST-PLAN.md](../flat_bom_generator/tests/TEST-PLAN.md))
- High priority: Plugin settings, error scenarios
- Medium priority: Warning generation, complex BOMs
- Recommended: 15-20 new tests across top 4 priorities

**3. Frontend Polish** (2-3 hours)
- Fix any UI issues from serializer deployment
- Performance testing with large BOMs (100+ parts)
- Browser compatibility verification

---

## Key Lessons Learned

### What Works
1. **Test-first workflow** - Caught 2 bugs during serializer refactoring
2. **Incremental phases** - Small, verifiable changes prevent stacking unverified work
3. **Production validation** - Deploy → Test in UI → Verify cycle catches integration issues
4. **Code-first methodology** - Reading actual code before writing tests found 96 lines dead code

### What to Avoid
1. ❌ Skipping deployment after code changes
2. ❌ Assuming "tests pass" = "code works in production"
3. ❌ Creating code without checking existing solutions
4. ❌ Moving fast without explaining approach

### Core Principle
> "Deploy and validate each phase. Don't stack unverified changes."

---

## Architecture Overview

### Backend (Python/Django)
- **Django REST Framework** - Serializers for API responses (Phases 1-3 complete)
- **Plugin System** - Settings, URL routes, UI integration
- **Core Algorithms** - BOM traversal, deduplication, categorization
- **Warning System** - 4 types with flag propagation

### Frontend (React/TypeScript)
- **React 19** with TypeScript
- **Mantine 8** UI components
- **Vite 6** build tooling
- **Lingui** i18n for translations
- **mantine-datatable** for BOM display

### Testing
- **195 tests** - 164 unit (pure functions, fast) + 31 integration (Django models, slower)
- **Grade A-** - Unit tests excellent, integration coverage good with known gaps
- **Methodology** - Code-first validation, test-first refactoring
- **Details** - See [TEST-PLAN.md](../flat_bom_generator/tests/TEST-PLAN.md)

---

## Future Improvements

### Frontend Refactoring (8-12 hours, LOW PRIORITY)
**Goal:** Improve maintainability and component reusability

**Current State:**
- Panel.tsx is 800+ lines with inline logic
- All state management in single component
- Tightly coupled data fetching and display

**Proposed Changes:**
1. **Extract Components** (4-6 hours)
   - `DataTableComponent` - BOM table with pagination
   - `StatisticsPanel` - Part counts and shortfall summary
   - `FilterControls` - Search, checkboxes, build quantity
   
2. **Custom Hooks** (2-3 hours)
   - `useFlatBOM()` - API call and data caching
   - `useBuildQuantity()` - Build multiplier state
   - `useFilters()` - Search and checkbox state
   
3. **React Context** (2-3 hours)
   - Shared state for filters and build quantity
   - Avoid prop drilling through component tree

**Blocked Until:** Backend integration test gaps filled (confidence in API stability)

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

## Plugin Feature Ideas (Future Exploration)

### Multi-Level BOM Analysis
- Show BOM at each level (not just flat)
- Toggle between flat and hierarchical view
- Visualize BOM tree structure

### Cost Analysis
- Calculate total BOM cost
- Show cost breakdown by part type
- Track cost changes over time

### Make vs Buy Analysis
- Compare internal fabrication vs purchase cost
- Lead time comparison
- Supplier reliability scoring

### BOM Comparison
- Compare BOMs between part revisions
- Highlight added/removed/changed items
- Show quantity differences

**Note:** These are ideas for discussion, not committed work. Evaluate value vs complexity before implementing.

---

## Completed Refactoring Phases

### Phase 1: Test Quality Foundation (Dec 18, 2025)
- Fixed skipped test (merged test_piece_qty_times_count_rollup into internal fab tests)
- Rewrote internal fab tests (removed stub functions, 14 tests validate actual code)
- Established code-first test methodology
- Found/removed 45 lines dead code, fixed 2 incorrect fallbacks

### Phase 2: Test Validation (Jan 9, 2026)
- Validated 164 unit tests with code-first methodology
- Added 30 new tests to fill coverage gaps
- Fixed 4 broken integration tests
- Comprehensive gap analysis (7 priorities identified)
- Found/removed additional 51 lines dead code

### Phase 3: Serializer Refactoring (Dec 15-18, 2025)
- Phase 1: BOMWarningSerializer (4 fields)
- Phase 2: FlatBOMItemSerializer (24 fields)
- Phase 3: FlatBOMResponseSerializer (8 fields)
- Created 38 comprehensive serializer tests
- Found 2 bugs through testing (note field, image URLs)
- **Status:** Ready for production deployment

---

## Development Workflow

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

## Next Steps

**Immediate (This Week):**
1. Deploy Phase 3 serializers to production
2. Verify API response format in UI
3. Run performance test with large BOM (100+ parts)

**Short Term (Next 2 Weeks):**
1. Add plugin settings integration tests (5-7 tests)
2. Add error scenario integration tests (3-4 tests)
3. Document any deployment issues

**Medium Term (Next Month):**
1. Fill remaining integration test gaps
2. Consider frontend refactoring (if backend stable)
3. Evaluate export system integration

**Long Term (Future):**
- Warning system expansion (if user feedback indicates value)
- Frontend component extraction (if code becomes hard to maintain)
- Feature exploration (cost analysis, BOM comparison)

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

_Last updated: January 9, 2026_
