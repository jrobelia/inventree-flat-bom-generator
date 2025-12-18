# FlatBOMGenerator Refactor & Optimization Plan

> **Status:** 80% complete - Serializers done, integration tests working, internal fab tests rewritten  
> **For History:** See [REFAC-HISTORY.md](REFAC-HISTORY.md) for completed work logs  
> **Last Updated:** December 18, 2025

---

## Current Status (December 18, 2025)

### ✅ Completed
- Serializer refactoring (Phases 1-3) - Ready for deployment
- View layer integration tests (14 tests passing)
- BOM traversal integration tests (~13 tests passing)
- Warning system (4 types implemented)
- Test quality framework established
- DRF APIView testing pattern documented
- **Internal fab tests rewritten** (11 tests, test actual code not stubs)
- **Code cleanup** (removed 45 lines dead code, 2 incorrect fallback paths)
- **ValueError on unit mismatch** (fail fast on data corruption)
- **Code-first test methodology documented** (TEST-WRITING-METHODOLOGY.md)

### ⏸️ Pending Deployment
- Phase 3 FlatBOMResponseSerializer (committed but not deployed)
- Internal fab test improvements (committed, not deployed)
- Dead code removal (committed, not deployed)

### 🔴 Critical Priorities
1. Deploy Phase 3 serializers + internal fab improvements (30-45 min)
2. ~~Fix skipped test (test_piece_qty_times_count_rollup)~~ - ✅ COMPLETE
3. ~~Rewrite internal fab tests (remove stub functions)~~ - ✅ COMPLETE

### 📊 Test Metrics
- **Total Tests:** 121 unit tests (all passing)
- **Quality Grade:** B+ (internal fab tests upgraded from Low to High quality)
- **Test Validation:** 1/13 files validated with code-first methodology (8%)
- **Backend Status:** ⚠️ NOT SOLID - only test_internal_fab_cutlist.py fully validated
- **Coverage:** View layer + core BOM traversal + internal fab cut lists tested
- **Recent Wins:** Found/removed 2 incorrect cumulative_qty fallbacks, discovered dead code paths

---

## Key Lessons Learned

### What Works
1. **Test-first workflow** - Caught 2 bugs immediately
2. **Incremental phases** - Small, verifiable changes
3. **Production validation** - Deploy → Test → Verify cycle
4. **Integration test pattern discovery** - Major toolkit win

### What to Avoid
1. ❌ Skipping deployment after code changes
2. ❌ Assuming "tests pass" = "code works in production"
3. ❌ Creating code without checking for existing solutions
4. ❌ Moving fast without explaining approach

### Core Principle
> "Deploy and validate each phase. Don't stack unverified changes."

---

---

## Test Organization

### Unit Tests (`flat_bom_generator/tests/*.py`)
**Purpose:** Test individual functions in isolation, no database required (mostly)

**Files:**
- `test_categorization.py` - Pure function tests (39 tests)
- `test_serializers.py` - DRF serializer validation (31 tests)  
- `test_shortfall_calculation.py` - Frontend calculation logic (21 tests)
- `test_assembly_no_children.py` - Warning flag logic (5 tests)
- `test_max_depth_warnings.py` - Flag prioritization (5 tests)
- `test_cut_to_length_aggregation.py` - Aggregation logic (1 test)
- `test_internal_fab_cutlist.py` - ⚠️ **Low quality** - uses stub functions (10 tests)
- `test_internal_fab_cut_rollup.py` - ⚠️ **1 skipped test** (1 test)
- `test_full_bom_part_13.py` - ⚠️ **Magic numbers** (1 test)
- `test_views.py` - ⚠️ **Unclear purpose** (investigate)

**Run:** `.\scripts\Test-Plugin.ps1 -Plugin "FlatBOMGenerator" -Unit`

### Integration Tests (`flat_bom_generator/tests/integration/*.py`)
**Purpose:** Test with real InvenTree Part/BomItem/Stock models

**Files:**
- `test_view_function.py` - FlatBOMView endpoint (14 tests)
  - Response structure, HTTP codes, error handling
  - Stock enrichment, statistics, warnings
- `test_views_integration.py` - BOM traversal workflow (7+ tests)
  - Leaf part filtering, quantity aggregation
  - Deduplication, serializer validation
  - Stock calculations, categorization
- `test_bom_traversal_integration.py` - Core functions (6+ tests)
  - get_flat_bom(), deduplicate_and_sum()
  - Part stock properties, categorization

**Run:** `.\scripts\Test-Plugin.ps1 -Plugin "FlatBOMGenerator" -Integration`

### How to Tell Which is Which
1. **Location**: Unit tests in `tests/`, integration tests in `tests/integration/`
2. **Imports**: Integration tests import `InvenTreeTestCase`, use Part/BomItem models
3. **Setup**: Integration tests have `setUpTestData()` creating test database records
4. **Run time**: Unit tests fast (< 1 sec), integration tests slower (2-5 sec)

---

## Practical Advice for Testing & Refactoring

1. **Start Small and Isolate Changes**
  - Refactor one small section at a time (e.g., a single function or component).
  - After each change, run your tests to confirm nothing broke.

2. **Follow Test-First Workflow**
  - See [TEST-PLAN.md](../flat_bom_generator/tests/TEST-PLAN.md) for complete test-first workflow
  - Check if tests exist → Evaluate quality → Improve/Create → Refactor → Verify

3. **Write Tests Before and After Refactoring**
  - If a function isn't tested, write a simple test for its current behavior before changing it.
  - After refactoring, make sure the test still passes.

4. **Use Descriptive Test Names**
  - Name tests after what they check, e.g., `test_flatten_bom_handles_duplicates`.

4. **Focus on “Pure” Functions First**
  - Functions that don’t depend on external state (like database or network) are easiest to test and refactor.

5. **Don’t Aim for Perfection**
  - Incremental improvement is better than a big rewrite. It’s okay if your first tests are basic.

6. **Use Assertions Effectively**
  - Assert expected outputs, but also check for error cases and edge conditions.

7. **Keep Tests Close to Code**
  - Place test files in a `tests/` folder next to the code they cover.

8. **Learn by Example**
  - Look at existing tests in your project or in open-source plugins for patterns.

9. **Use Version Control**
  - Commit after every small, working change. This makes it easy to revert if something breaks.

10. **Ask for Feedback**
   - Don’t hesitate to ask for code reviews or advice as you go.

---

## Goals & Priorities

### Refactoring Goals
- Achieve a semi-professional, maintainable codebase
- Reduce file/component complexity (especially Panel.tsx)
- Improve separation of concerns and code readability
- Adopt modern React/TypeScript patterns (hooks, context, modularization)
- Ensure backend logic is clear, testable, and efficient
- Maintain or improve test coverage

### Priority Additions

**1. InvenTree Export Plugin System** (Medium Priority)
- **Current**: Custom CSV export in Panel.tsx with manual column handling  
- **Target**: Integrate with InvenTree's DataExportMixin for standardized exports
- **Why**: Built-in support for multiple formats (CSV, JSON, XLSX), automatic encoding/escaping
- **Status**: Not started, defer until backend 100% stable

**2. Warning System Expansion** (Low Priority)
- **Current**: 4 warning types implemented (unit_mismatch, inactive_part, assembly_no_children, max_depth_exceeded)
- **Target**: See [WARNINGS-ROADMAP.md](WARNINGS-ROADMAP.md) for additional planned warnings
- **Status**: Core warnings working, expansion deferred

**3. Frontend Refactoring** (Low Priority)
- **Current**: Panel.tsx is 800+ lines with inline logic
- **Target**: Break into components, extract hooks, improve state management
- **Status**: Defer until backend tests comprehensive and stable

---

## Refined Priorities (Post-Integration Testing)

### ~~Priority 1: Test Quality Improvements~~ ✅ COMPLETE (Dec 18, 2025)
**Critical for safety net before major refactoring**

1. ~~**Deploy Phase 3 Serializers**~~ - ⏸️ Ready to deploy
   - Serializers implemented and tested
   - Pending: Build → Deploy → Test on staging → Verify API response
   
2. ~~**Fix Skipped Test**~~ - ✅ COMPLETE
   - Was: `test_piece_qty_times_count_rollup` skipped
   - Now: All 12 internal fab tests passing
   - Discovered tests were testing stub functions, not real code

3. ~~**Rewrite Internal Fab Tests**~~ - ✅ COMPLETE (Dec 18)
   - Removed stub `get_cut_list_for_row()` function
   - Tests now validate actual `deduplicate_and_sum()` behavior
   - Created code-first test methodology (documented in TEST-WRITING-METHODOLOGY.md)
   - Found and removed 45 lines of dead code
   - Added ValueError for unit mismatch (fail fast on data corruption)
   - All 11 tests passing, quality upgraded from Low → High

### Priority 2: Test Validation (12-18 hours)
**PREREQUISITE for frontend refactoring - validate ALL tests with code-first methodology**

**Current Status:** 1/13 files validated (test_internal_fab_cutlist.py)
**Goal:** Validate all 13 test files to ensure tests match actual code behavior

**Validation Plan** (see TEST-WRITING-METHODOLOGY.md):
1. **test_categorization.py** (18 tests, 2-3 hours)
   - Walk through category hierarchy logic
   - Verify supplier detection works as coded
   - Check edge cases for overlapping categories

2. **test_shortfall_calculation.py** (21 tests, 2-3 hours)
   - Trace through actual calculation in Panel.tsx
   - Remove duplicated logic, import actual function
   - Verify all 4 checkbox combinations match UI behavior

3. **test_assembly_no_children.py** (4 tests, 1 hour)
   - Trace through get_leaf_parts_only() function
   - Verify flag propagation through pipeline

4. **test_max_depth_warnings.py** (5 tests, 1 hour)
   - Walk through flag prioritization logic
   - Remove duplicated logic, call actual functions

5. **test_cut_to_length_aggregation.py** (1 test, 2 hours)
   - Expand to 5-10 tests covering edge cases
   - Walk through CtL aggregation logic

6. **test_full_bom_part_13.py** (3 tests, 1 hour)
   - Understand what "9 unique parts from 10 rows" means
   - Either add clear documentation OR delete if redundant

7. **test_internal_fab_cut_rollup.py** (22 tests, 1 hour)
   - Fix skipped test or document why skipped
   - Validate remaining tests

8. **Integration tests** (3 files, 3-4 hours)
   - test_view_function.py (14 tests)
   - test_views_integration.py (7+ tests)
   - test_bom_traversal_integration.py (6+ tests)

**Why This Matters:**
- Dec 18 validation found 51 lines of dead code and 2 incorrect fallbacks
- Tests passing ≠ tests validating correct behavior
- Cannot safely refactor frontend without backend confidence

### Priority 3: Frontend Panel.tsx Refactoring (8-12 hours)
**BLOCKED until Priority 2 complete - all tests validated**

- Break into components: DataTable, StatisticsPanel, FilterControls
- Extract custom hooks: useFlatBOM, useBuildQuantity, useFilters
- Implement React Context for shared state
- Add PropTypes/TypeScript interfaces
- Write component tests (React Testing Library)

### Priority 4: Export System & Warning Expansion (7-11 hours)
**Nice-to-have improvements after frontend stable**

- Integrate InvenTree DataExportMixin (4-6 hours)
- Expand warning system with 3-5 new types (3-5 hours)

### Priority 5: Code Cleanup (Ongoing)
**Continuous improvement as tests are validated**
**Remove dead code, outdated comments, and improve clarity**

**Dead Code Hunting:**
1. **Search for unused functions** - Functions defined but never called
   - Use `grep_search` to find function definitions
   - Search for function name + `(` to find calls
   - If no calls found (except definition), likely dead code
   - Example: `internal_fab_cut_breakdown` was defined but never called (removed Dec 18)

2. **Look for unreachable code paths**
   - `if/elif/else` where condition can never be true
   - `try/except` that can never fail
   - Code after `return` or `raise` statements
   - Example: Internal fab without cut_length path (line 272 always sets it)

3. **Find duplicate logic**
   - Same calculation in multiple places
   - Copy-pasted functions with slight variations
   - Consider: Extract to shared utility function

4. **Check for outdated fallbacks**
   - `try/except` blocks that shouldn't be needed
   - `.get()` with defaults that are never used
   - Conditional checks for cases that can't occur
   - Example: `piece_count_inc = leaf.get("quantity") or 1` always returns 1

**Comment Cleanup:**
1. **Remove "what" comments** - Code explains itself
   ```python
   # ❌ BAD
   # Increment counter
   count += 1
   
   # ✅ GOOD (no comment needed)
   count += 1
   ```

2. **Keep "why" comments** - Explain decisions
   ```python
   # ✅ GOOD
   # Use cut_length instead of cumulative_qty for internal fab parts
   # because each leaf represents one BOM occurrence
   totals[key] += cut_length
   ```

3. **Remove outdated comments**
   - Comments referencing removed code
   - Comments contradicting current behavior
   - TODOs that were completed
   - Example: "Only include if unit matches" when code now throws error

4. **Update stale docstrings**
   - Function signature changed but docstring didn't
   - Parameters added/removed
   - Return value changed
   - Behavior changed

**Verbose Comment Audit:**
1. **Test file headers** - Should be concise summary, not essay
   - Current behavior (1-2 paragraphs)
   - Critical discoveries (bullet list)
   - How understanding was established (brief)

2. **Function docstrings** - Focus on contract, not implementation
   ```python
   # ❌ TOO VERBOSE
   def deduplicate_and_sum(leaves):
       """
       This function takes a list of leaf parts and processes them
       by iterating through each one and checking if it's a CtL part
       or an internal fab part or a regular part and then it aggregates
       them based on part_id and also creates cut lists if needed...
       (5 more paragraphs)
       """
   
   # ✅ CONCISE
   def deduplicate_and_sum(leaves):
       """
       Aggregate leaf parts by part_id, creating cut lists where applicable.
       
       Args:
           leaves: List of leaf part dicts from BOM traversal
           
       Returns:
           List of aggregated parts with total_qty and optional cut lists
       """
   ```

3. **Inline comments** - One line explaining non-obvious logic
   ```python
   # ❌ TOO VERBOSE
   # We need to check if the unit is in the allowed units set because
   # if it's not then the part shouldn't be included in the cut list
   # since we can't aggregate parts with different units together
   if unit not in allowed_ifab_units:
   
   # ✅ CONCISE
   # Same part must have same unit - mismatch indicates data corruption
   if unit not in allowed_ifab_units:
   ```

**Cleanup Checklist:**
- [ ] Search for functions defined but never called
- [ ] Look for unreachable code paths (after debugging sessions)
- [ ] Check for try/except blocks that can't fail
- [ ] Review comments explaining "what" instead of "why"
- [ ] Update docstrings to match current function signatures
- [ ] Remove TODO comments that were completed
- [ ] Condense verbose test file headers
- [ ] Remove debug logging that's no longer needed

**Tools to Use:**
```powershell
# Find function definitions
grep_search -query "def function_name" -isRegexp false

# Find function calls
grep_search -query "function_name(" -isRegexp false

# Find TODO comments
grep_search -query "TODO" -isRegexp false

# Find long docstrings (manual review)
# Look for """ followed by many lines before closing """
```

**When to Clean:**
- ✅ After completing a feature (remove debug code)
- ✅ After refactoring (remove old comments)
- ✅ When tests are comprehensive (safe to remove dead code)
- ✅ Before major refactor (clean slate to work from)

**When NOT to Clean:**
- ❌ During active debugging (keep context)
- ❌ When tests are incomplete (might not be dead code)
- ❌ Before understanding code (might remove needed fallbacks)

---

## Priority Additions
- Expand warning system with 3-5 new types (3-5 hours)

---

## Priority Additions

### Use InvenTree Export Plugin System (High Priority)
**Current**: Custom CSV export in Panel.tsx with manual column handling  
**Target**: Integrate with InvenTree's DataExportMixin for standardized exports

**Why**: InvenTree has a built-in export infrastructure that:
- Supports multiple formats (CSV, JSON, XLSX)
- Handles encoding, escaping, and formatting automatically
- Provides consistent UI/UX with rest of InvenTree
- Allows server-side generation (no client memory limits)

**Implementation**:
1. Add `DataExportMixin` to plugin class
2. Register flat BOM export endpoint
3. Replace frontend "Export CSV" button with InvenTree's export dialog
4. Remove custom `escapeCsvField` and export logic from Panel.tsx

**Reference**: See how standard BOM export works in InvenTree source
- Document all major changes and rationale

## Step 1: Code Review
- Review frontend (Panel.tsx, related components, hooks, API logic)
- Review backend (core.py, bom_traversal.py, views.py, categorization.py)
- Identify:
  - Long files/components (over 300 lines)
  - Repeated or tightly coupled logic
  - Unclear responsibilities or “God objects”
  - Outdated patterns or tech debt
  - Missing/unclear documentation

## Step 2: Outline Refactor Targets
- List pain points and desired outcomes for each major file/module
- Example (Panel.tsx):
  - Split into smaller presentational and container components
  - Move API/data logic to custom hooks
  - Extract table logic, summary, and controls into separate files
  - Add/clarify prop and state types
- Example (bom_traversal.py):
  - Clarify function responsibilities
  - Add docstrings and type hints
  - Split large functions if needed
- Example (serializers.py):
  - Replace manual dictionary construction in views.py
  - Create serializers for BOM items, warnings, and responses
  - Improve type safety and maintainability
  - Separate data transformation from business logic

## Step 3: Plan Refactor Steps
- For each target area:
  - Define what to split, move, or rewrite
  - Choose new structure/pattern (e.g., hooks, context, services)
  - Plan how to test and validate after each step
- Prioritize high-impact, low-risk changes first
- Commit after each logical step

## Step 4: Incremental Refactor & Test
- Refactor one area at a time
- Run tests and check UI after each change
- Document changes in code and this plan
- **Watch for warning opportunities**: As you refactor, identify:
  - BOM structure issues that could cause incorrect output
  - Plugin settings that could be misconfigured
  - Data transformations where user input could cause errors
  - Edge cases in algorithms that need user awareness
  - Add warnings for plugin-specific issues only (not general InvenTree concerns)

## Step 5: Final Review & Documentation
- Review for code clarity, maintainability, and test coverage
- Update README and developer docs
- Summarize lessons learned and future improvement ideas

---
---

## Testing Strategy

**Documentation**:
- [DEPLOYMENT-WORKFLOW.md](DEPLOYMENT-WORKFLOW.md) - **Deployment checklist and phase-based testing workflow**
- [TEST-PLAN.md](../flat_bom_generator/tests/TEST-PLAN.md) - Test execution, strategy, and test-first workflow
- [TEST-QUALITY-REVIEW.md](TEST-QUALITY-REVIEW.md) - Quality analysis and improvement roadmap
- **Toolkit Testing Docs** (in toolkit root):
  - `docs/toolkit/TESTING-STRATEGY.md` - Unit vs integration testing strategy
  - `docs/toolkit/INVENTREE-DEV-SETUP.md` - InvenTree dev environment setup
  - `docs/toolkit/INTEGRATION-TESTING-SUMMARY.md` - What we built, quick start

**Test-First Workflow**:
1. Check if tests exist for code you're refactoring
2. Evaluate test quality (coverage, thoroughness, accuracy)
3. Improve/create tests BEFORE refactoring (unit AND integration)
4. Refactor code
5. Verify tests still pass

**Integration Testing Setup** (one-time):
```powershell
.\scripts\Setup-InvenTreeDev.ps1
.\scripts\Link-PluginToDev.ps1 -Plugin "FlatBOMGenerator"
```

**Run Tests**:
```powershell
# Unit tests (fast, no database)
.\scripts\Test-Plugin.ps1 -Plugin "FlatBOMGenerator" -Unit

# Integration tests (requires InvenTree dev setup)
.\scripts\Test-Plugin.ps1 -Plugin "FlatBOMGenerator" -Integration

# All tests
.\scripts\Test-Plugin.ps1 -Plugin "FlatBOMGenerator" -All
```

---

## Next Steps & Recommendations

**See detailed quality analysis:**
- [INTEGRATION-TEST-REVIEW.md](INTEGRATION-TEST-REVIEW.md) - Integration test quality assessment (B+ grade)
- [TEST-QUALITY-REVIEW.md](TEST-QUALITY-REVIEW.md) - Complete unit test quality analysis

**Immediate Actions:**
1. **Deploy Phase 3 serializers** - Complete the refactoring cycle
2. **Fix skipped test** - Resolve `test_piece_qty_times_count_rollup`
3. **Rewrite internal fab tests** - Remove stub functions, test real code

**Future Improvements:**
- Frontend Panel.tsx refactoring (defer until backend stable)
- InvenTree DataExportMixin integration (optimization, not critical)
- Warning system expansion (nice-to-have)

---

_Last updated: December 17, 2025_
- Removed unused ASSEMBLY_CATEGORY setting
- Learned: Start with pure functions, test before refactoring

**2025-12-15**: Warning system implementation (v0.9.2)
- Implemented 4 warning types with flag propagation
- Fixed assembly_no_children bug
- Created ARCHITECTURE-WARNINGS.md documenting patterns
- Reduced warning noise from 65 to 5 through prioritization
- Added 82 passing tests (1 skipped)

**2025-12-15 Evening**: Serializer refactoring Phase 2 (v0.9.2)
- **Phase 2 Complete**: Implemented FlatBOMItemSerializer (24 fields)
- Replaced manual dict construction in views.py
- Created 23 comprehensive serializer tests
- **Found 2 bugs through testing**: note field requirements, image URL field types
- **Production validated**: Deployed to staging, tested with 117 BOM items
- Created TEST-QUALITY-REVIEW.md identifying critical test gaps
- Established test-first workflow guidelines

**Key Insights Learned**:
- Test-first approach catches bugs immediately
- 106 passing tests don't guarantee refactored code works
- Test quality matters as much as test quantity
- Views.py completely untested despite refactoring
- Django REST Framework available in InvenTree (no dependency issues)

**Current Status**: Phase 2 complete, ready for Phase 3

---

## Serializer Refactoring Plan

### Goal
Replace manual dictionary construction in views.py with Django REST Framework serializers to improve:
- Code maintainability and readability
- Type safety and validation
- Separation of concerns (data transformation vs business logic)
- Testability

### Current Pain Points

**In views.py (lines 325-430):**
```python
# Manual dictionary construction - repetitive and error-prone
enriched_item = {
    **item,
    "full_name": part_obj.full_name if hasattr(part_obj, "full_name") else part_obj.name,
    "image": part_obj.image.url if part_obj.image else None,
    "thumbnail": part_obj.image.thumbnail.url if part_obj.image else None,
    # ... 10+ more fields manually mapped
}
```

**Issues:**
- Repetitive `if hasattr()` and `if x else None` checks
- Hard to test data transformation logic
- Manual field mapping is error-prone
- No type validation
- Violates DRY (Don't Repeat Yourself)
- Business logic mixed with data serialization

### Proposed Serializers

#### 1. `BOMWarningSerializer`
**Purpose**: Serialize warning messages with consistent structure

**Fields:**
- `type` (CharField) - Warning category (unit_mismatch, inactive_part, etc.)
- `part_id` (IntegerField, optional) - Associated part ID
- `part_name` (CharField, optional) - Human-readable part name
- `message` (CharField) - User-facing warning text

**Benefit**: Consistent warning format, easy to add new warning types

#### 2. `FlatBOMItemSerializer`
**Purpose**: Serialize enriched BOM item data for frontend

**Fields:**
- All fields from `flat_bom` traversal output
- Part model fields: `full_name`, `image`, `thumbnail`, `units`
- Stock fields: `in_stock`, `on_order`, `allocated`, `available`
- Navigation: `link` to part detail page

**Methods:**
- `get_full_name()` - Handle full_name fallback logic
- `get_image()` - Safe URL extraction with None handling
- `get_thumbnail()` - Safe thumbnail URL extraction

**Benefit**: All field mapping logic in one place, easy to test

#### 3. `FlatBOMResponseSerializer`
**Purpose**: Wrap complete API response structure

**Fields:**
- `part_id` (IntegerField) - Root part ID
- `part_name` (CharField) - Root part name
- `ipn` (CharField) - Root part IPN
- `bom_items` (List[FlatBOMItemSerializer]) - Flattened BOM
- `metadata` (Dict) - Counters and stats
  - `total_unique_parts`
  - `total_ifps_processed`
  - `max_depth_reached`
  - `warnings` (List[BOMWarningSerializer])

**Benefit**: Single source of truth for API contract, auto-generates API docs

### Implementation Plan

**Phase 1: Create Serializers (No Breaking Changes)**
1. Create `BOMWarningSerializer` in serializers.py
2. Create `FlatBOMItemSerializer` in serializers.py
3. Create `FlatBOMResponseSerializer` in serializers.py
4. Add docstrings explaining each field
5. Run tests to ensure no regressions

**Phase 2: Refactor views.py to Use Serializers**
1. Replace manual warning dict construction with `BOMWarningSerializer`
2. Replace enriched_item dict construction with `FlatBOMItemSerializer`
3. Replace Response() dict with `FlatBOMResponseSerializer`
4. Remove redundant field mapping code
5. Run tests and verify API output unchanged

**Phase 3: Add Serializer Tests**
1. Test `BOMWarningSerializer` with various warning types
2. Test `FlatBOMItemSerializer` with Part objects
3. Test edge cases: missing images, None values, empty fields
4. Test `FlatBOMResponseSerializer` integration

**Phase 4: Documentation**
1. Update PLUGIN-CONTEXT.md with serializer architecture
2. Document serializer patterns learned
3. Add to refactor plan progress log

### When to Do This

**Good time to implement:**
- After current warning system is stable
- Before adding new API endpoints
- When we need to modify API response structure
- As part of views.py refactoring

**Dependencies:**
- None - can be done incrementally
- Serializers work alongside existing code during transition

### Learning Opportunities

This refactor teaches:
- Django REST Framework serializer patterns
- Separation of concerns in API design
- How to write testable data transformation code
- Industry-standard API development practices

---

## Known Issues & Next Steps

**See [TEST-QUALITY-REVIEW.md](TEST-QUALITY-REVIEW.md) for detailed analysis.**

**Critical Priorities** (from test quality review):
- 🔴 Add views.py integration tests (2-3 hours) - Test view function directly (NOT via HTTP - InvenTree doesn't support plugin URL testing)
- 🔴 Fix or remove skipped test (test_piece_qty_times_count_rollup)
- 🔴 Rewrite test_internal_fab_cutlist.py (tests stub functions, not real code)
- 🟡 Add core BOM traversal tests (get_flat_bom, deduplicate_and_sum)
- 🟡 Expand cut-to-length test coverage

**Current Test Status**: 106 tests (105 passing, 1 skipped)

**⚠️ CRITICAL LEARNING** (Dec 16, 2025): InvenTree does NOT support plugin URL testing via Django test client. Plugin URLs return 404 in tests. 

**How to test API endpoints**: See [TEST-PLAN.md](../../flat_bom_generator/tests/TEST-PLAN.md) → API Endpoint Testing Strategy section for detailed patterns:
- Call view functions directly with RequestFactory (not via HTTP)
- Test business logic functions with real Part/BOM models
- Manual testing for HTTP layer (UI, API client)

Also see [TESTING-STRATEGY.md](../../../../docs/toolkit/TESTING-STRATEGY.md) for toolkit-level integration testing philosophy.

---

**Final Tips:**
- Ask for advice or code review at any step
- Don't try to do everything at once—small, tested steps are best
- Use this plan as a living document: update as you go
- **Always check test quality, not just test count**
- **Write tests for what you're refactoring, not just what's easy to test**

---

_Last updated: 2025-12-17_
