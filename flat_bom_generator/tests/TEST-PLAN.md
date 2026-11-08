# FlatBOMGenerator - Test Plan

**Last Updated**: November 7, 2026  
**Test Count**: 346 backend tests (181 unit + 165 integration); frontend Vitest + Playwright run in the suite  
**Test Quality**: Grade B+ (85% Grade A tests, 92% estimated coverage)  
**Status**: All priorities complete, all critical gaps closed

---

## Overview

This document covers **testing strategy, execution, and improvement priorities** for the FlatBOMGenerator plugin.

**Related Documents:**
- [ARCHITECTURE.md](../../docs/reference/ARCHITECTURE.md) - Plugin architecture and API reference
- [DEPLOYMENT-WORKFLOW.md](../../docs/reference/DEPLOYMENT-WORKFLOW.md) - Deployment checklist
- [TEST-WRITING-METHODOLOGY.md](../../docs/archive/TEST-WRITING-METHODOLOGY.md) - Code-first validation case study (archived, non-authoritative)
- Planned work lives in [GitHub issues](https://github.com/jrobelia/inventree-flat-bom-generator/issues)

---

## Test Execution

### Quick Start

```powershell
# Unit tests (fast, no InvenTree required)
.\scripts\Test-Plugin.ps1 -Plugin "FlatBOMGenerator" -Unit

# Integration tests (requires InvenTree dev environment)
.\scripts\Test-Plugin.ps1 -Plugin "FlatBOMGenerator" -Integration

# All tests
.\scripts\Test-Plugin.ps1 -Plugin "FlatBOMGenerator" -All
```

### Unit Tests

**Location:** `flat_bom_generator/tests/*.py`  
**Purpose:** Test individual functions in isolation, no database required

**Files:** (181 tests total)
- `test_categorization.py` (32 tests) - Display-label classification (labels only, never expansion)
- `test_serializers.py` (57 tests) - DRF serializer validation
- `test_views.py` (14 tests) - View structure and helper functions
- `test_cut_list.py` (21 tests) - Cut-list aggregation (piece_count x multiplier, length-unit dimensionality)
- `test_merged_row_scalars.py` (9 tests) - Merged-row per-line scalars null on disagreement (ruling R-025)
- `test_assembly_no_children.py` (27 tests) - Expansion matrix + warning flag logic
- `test_shortfall_calculation.py` (13 tests) - Frontend calculations
- `test_max_depth_warnings.py` (8 tests) - Flag prioritization

**Characteristics:**
- Fast execution (< 1 second total)
- No external dependencies
- Test pure functions and serializers
- Can run without InvenTree dev environment

**Run from plugin directory:**
```bash
cd plugins/FlatBOMGenerator
& ".venv\Scripts\Activate.ps1"
python -m unittest flat_bom_generator.tests.test_categorization -v
```

### Integration Tests

**Location:** `flat_bom_generator/tests/integration/*.py`  
**Purpose:** Test with real InvenTree Part/BomItem/Stock models

**Files:** (165 tests total)
- `test_internal_supplier_expansion.py` (11 tests) - Expansion matrix arms incl. sourced-TLA roots (fixture: `internal_supplier_expansion.yaml`)
- `test_upstream_bom_semantics.py` (15 tests) - piece_count, inherited lines, effective consumable, merged-row scalar nulls (fixture: `upstream_bom_semantics.yaml`)
- `test_get_bom_items.py` (15 tests) - BOM item fetching and supplier lookup
- `test_plugin_core.py` (15 tests) - Plugin registration, URLs, panels
- `test_error_scenarios.py` (14 tests) - Error handling paths
- `test_view_function.py` (18 tests) - FlatBOMView endpoint testing
- `test_complex_bom_structures.py` (13 tests) - Multi-path/deep/wide BOM fixtures
- `test_views_integration.py` (12 tests) - BOM traversal workflow
- `test_query_parameters.py` (10 tests) - max_depth and query params
- `test_plugin_settings.py` (9 tests) - Settings loading
- `test_warning_generation.py` (7 tests) - Warning aggregation (fixture: `warning_scenarios.yaml`)
- `test_view_settings_loading.py` (6 tests) - Settings/query-param plumbing
- `test_bom_traversal_integration.py` (5 tests) - Core function integration
- `test_circular_references.py` (5 tests) - Circular BOM detection
- `test_view_permissions.py` (4 tests) - Role permission dispatch
- `test_substitute_enrichment.py` (4 tests) - Substitute part enrichment
- `test_stock_enrichment.py` (2 tests) - Stock field enrichment

**Characteristics:**
- Slower execution (2-5 seconds)
- Requires InvenTree dev environment
- Creates test database records
- Tests full workflow with Django models

**Prerequisites:**
1. Run `.\scripts\Setup-InvenTreeDev.ps1` (one-time setup)
2. Run `.\scripts\Link-PluginToDev.ps1 -Plugin "FlatBOMGenerator"` (creates Junction AND pip installs)
3. Activate plugin in InvenTree admin panel (Active=True)

**Run from toolkit root:**
```powershell
.\scripts\Test-Plugin.ps1 -Plugin "FlatBOMGenerator" -Integration
```

---

## Test Framework

**InvenTree Test Framework:**
- Inherits from Django's `TestCase`
- Uses `InvenTree.unit_test` module
- Test classes: `InvenTreeTestCase`, `InvenTreeAPITestCase`

**Virtual Environment:**
- Django and djangorestframework installed in `.venv`
- Activate before running: `& ".venv\Scripts\Activate.ps1"`
- Serializer tests require Django environment

**Environment Variables:**
```powershell
$env:INVENTREE_PLUGINS_ENABLED = "True"
$env:INVENTREE_PLUGIN_TESTING = "True"
$env:INVENTREE_PLUGIN_TESTING_SETUP = "True"
```

---

## API Endpoint Testing Strategy

### The Problem

~~**InvenTree does NOT support plugin URL testing via Django test client.**~~

**Corrected September 2026:** plugin URL testing IS possible on InvenTree 1.5.x —
enable `ENABLE_PLUGINS_URL`, call `registry.reload_plugins()`, then
`self.client.get('/plugin/<slug>/<path>/')` (upstream precedent:
`plugin/samples/integration/test_sample.py::test_view`). The 404s seen
historically were because plugin endpoints weren't registered under the test
registry. See `docs/reference/PLUGIN-TESTING.md` in the toolkit repo.

### The Solution

**Test business logic directly, not via HTTP** — still the approach this suite
uses; the HTTP-level route above is available if endpoint/middleware coverage
is ever needed.

#### What We CAN Test (Integration Tests)

**1. View Functions Directly:**
```python
from flat_bom_generator.views import FlatBOMView
from django.test import RequestFactory

def test_view_with_valid_part(self):
    factory = RequestFactory()
    request = factory.get('/fake-url')
    view = FlatBOMView()
    response = view.get(request, part_id=self.part.pk)
    self.assertEqual(response.status_code, 200)
```

**2. Business Logic Functions:**
```python
from flat_bom_generator.bom_traversal import get_flat_bom

def test_get_flat_bom_with_real_parts(self):
    result, imp_count, warnings, max_depth = get_flat_bom(self.part.pk)
    self.assertIsInstance(result, list)
    self.assertGreater(len(result), 0)
```

**3. Serializers with Real Data:**
```python
from flat_bom_generator.serializers import FlatBOMItemSerializer

def test_serializer_validates_real_part(self):
    serializer = FlatBOMItemSerializer(data=test_data)
    self.assertTrue(serializer.is_valid())
```

#### What We Do Not Currently Test via HTTP

- End-to-end HTTP requests through Django's URL resolver — possible since
  InvenTree 1.5.x via `ENABLE_PLUGINS_URL` + `registry.reload_plugins()`
  + `self.client.get('/plugin/<slug>/<path>/')`; not currently exercised.
  View-level dispatch *is* covered: `test_view_permissions.py` drives
  `FlatBOMView.as_view()` through DRF `dispatch()` with `APIRequestFactory`
  + `force_authenticate`, asserting 200 (`bom.view`), 403 (no roles),
  403 (`part.view` only), and 401 (anonymous). Endpoint permissions no
  longer need manual verification on a running server.
- Convention: any test mocking `flat_bom_generator.views.*` must re-import
  `FlatBOMView` inside `setUp` — plugin registry reloads purge
  `flat_bom_generator.*` from `sys.modules`, so a collection-time import
  leaves the view bound to the stale module while the mock patches the
  fresh one (see `test_stock_enrichment.py`, `test_view_settings_loading.py`).

**Reference:** Integration testing setup docs live in the `inventree-plugin-ai-toolkit` repo under `docs/reference/` (outside this checkout).

---

## Test Improvement Priorities

### ✅ Priority 1: Plugin Settings & Configuration (COMPLETE)
**Time Invested:** 2 hours | **Tests Added:** 31 (17 later removed in ticket #6)

**What Was Tested:**
- `get_category_mappings()` with real plugin settings (8 tests)
  - Category descendants via `category.get_descendants(include_self=True)`
  - Multiple categories configured
  - Invalid category IDs (graceful degradation)
  - Empty/None settings

- Plugin settings configuration edge cases (6 tests)

**Removed in ticket #6:** the `get_internal_supplier_ids()` extraction tests (9) and `_extract_id_from_value()` type-handling tests (8) were deleted with the functions and supplier-ID settings they covered - internal detection now reads the primary `SupplierPart`'s `is_internal` flag.

**Status:** Passing

---

### ✅ Priority 2: Error Scenarios (COMPLETE)
**Time Invested:** 1.5 hours | **Tests Added:** 26 tests

**What Was Tested:**
- Database exceptions (4 tests)
  - `Part.DoesNotExist` when part_id invalid
  - Non-assembly parts return 400 "Part is not an assembly"
  - Category deletion handled gracefully
  
- Invalid query parameters (4 tests)
  - Non-integer max_depth returns 400
  - Negative/zero part_id returns 404
  - Float max_depth handled
  
- Empty/None plugin settings (10 tests)
  - No categories/suppliers configured
  - Empty string settings
  - Mixed valid/invalid IDs
  
- Logging and exception handling (8 tests)
  - Invalid IDs log warnings and continue
  - Deleted categories logged
  - String validation errors logged

**Status:** All 26 tests passing, committed January 10, 2026

---

### ✅ Priority 3: Warning Generation (COMPLETE)
**Time Invested:** 9 hours total (3 hours initial research + 6 hours fixture implementation) | **Tests Added:** 8 integration tests

**Status:** ✅ **100% COVERAGE ACHIEVED** - Fixture breakthrough closed gap!

**Journey to Completion:**

**Initial Attempt (January 10):**
- InvenTree's `Part.check_add_to_bom()` validation blocked creating test scenarios
- Accepted 85% coverage gap (38 component tests, no view integration tests)

**Breakthrough (January 11-12):**
- Fixture-based approach from Priority 4 enabled reopening Priority 3
- Programmatic fixture loading bypasses InvenTree validation: `call_command('loaddata', absolute_path)`
- Created warning_scenarios.yaml (383 lines, 5 scenarios covering all 4 warning types)
- Created test_warning_generation.py (304 lines, 8 integration tests)

**Tests Created:**
1. test_inactive_part_warning_generated - Validates inactive_part warning
2. test_assembly_no_children_warning_generated - Validates empty assembly warning
3. test_unit_mismatch_warning_generated - Validates conflicting units warning
4. test_multiple_warnings_aggregated_correctly - Validates 3+ warnings together
5. test_no_warnings_for_clean_bom - Validates clean BOM (no warnings)
6. test_warning_serialization_structure - Validates BOMWarningSerializer fields
7. test_warnings_included_in_response_structure - Validates metadata.warnings structure
8. test_references_combined_across_paths - SKIPPED (reference aggregation, future feature)

**Coverage Achievement:**
- **Before:** 85% (38 component tests: serializers + flags + helpers)
- **After:** 100% (46 tests: 38 components + 8 view integration)
- **Gap Closed:** View-level warning aggregation (views.py lines 334-421)

**Fixture Debugging Journey (6 test runs):**
1. PartCategory '_icon' field fixed
2. Part obsolete fields removed (responsible, default_location, default_supplier)
3. Part MPPT fields added (tree_id, level, lft, rght)
4. BomItem obsolete fields removed (overage, checksum, inherited, optional, consumable, allow_variants)
5. Fixture loaded! Tests executed (API structure mismatch found)
6. ✅ All 8 tests passing (warnings in metadata.warnings, not top-level)

**Key Learning:** Programmatic fixture loading pattern documented for future plugin development

---

### ✅ Priority 4: Complex BOM Structures (COMPLETE - Fixture-Based Approach)
**Time Invested:** 6 hours (initial attempts + fixture breakthrough + YAML debugging) | **Tests Created:** 17 tests (16 passing, 1 skipped)

**Purpose:** Validate BOM traversal with complex real-world scenarios beyond simple 3-level BOMs.

**BREAKTHROUGH:** Discovered programmatic fixture loading pattern that bypasses InvenTree's `Part.check_add_to_bom()` validation!

**Scenario 1: Same Part Multiple Paths** ✅ WORKING (4/5 tests passing)
**Status:** ✅ **Fixture-based approach successful** - Tests validate `visited.copy()` pattern

**Problem Encountered:** InvenTree `Part.check_add_to_bom()` validation rejects dynamic BOM creation in tests.

**Solution Discovered:** Use Django fixtures with programmatic loading!
- Fixtures bypass validation (pre-validated data)
- Programmatic loading required for plugins: `call_command('loaddata', absolute_path, verbosity=0)`
- Standard `fixtures = ['name']` doesn't work (plugins not in INSTALLED_APPS)
- Path calculation: 4 levels up from test file to plugin root + 'fixtures/complex_bom.yaml'

**Implementation:**
- Created `fixtures/complex_bom.yaml` (693 lines) with all 4 scenarios
- 3 PartCategories, 37 Parts, 36 BomItems with proper MPPT fields
- Module docstring in test file documents the pattern for future use

**Tests Created:**
- **SamePartMultiplePathsTests** (4 tests) - ✅ 3 passing, 1 skipped
  - test_same_part_appears_via_multiple_paths ✅
  - test_quantity_aggregation_across_paths ✅ (2×4 + 3×2 = 14)
  - test_no_circular_reference_warning ✅
  - test_references_combined_across_paths ⏭️ SKIPPED (feature not implemented)
- **SamePartDifferentQuantitiesTests** (1 test) - ✅ PASSING
  - test_quantities_sum_from_three_paths ✅ (10+5+3=18)

**Fixture Data (pk 9001-9015):**
- Main Assembly (9001) → Sub A (9002, qty=2) → Screw (9004, qty=4)
- Main Assembly (9001) → Sub B (9003, qty=3) → Screw (9004, qty=2)
- Electronic Assembly (9010) → 3 Modules → Resistor (shared part)
- MPPT fields: tree_id, level, lft, rght on all categories
- validated: true on all BomItems

**Status:** ✅ COMPLETE - Validates `visited.copy()` pattern with real Django models  
**File:** `test_complex_bom_structures.py` (371 lines, comprehensive docstring)

**Scenario 2: Quantity Aggregation (Partial)** ✅ WORKING (1/1 test passing)
**Status:** ✅ Tests sum across 3 paths but missing true Deep BOM fixtures

**Tests:**
- test_quantities_sum_from_three_paths ✅ (Electronic Assembly → 3 Modules → Resistor)

**Note:** Current fixtures (pk 9010-9015) test quantity aggregation but not deep nesting (5+ levels). To fully complete Scenario 2, would need fixtures for 5-7 level nested BOM without max_depth parameter.

---

**Scenario 3: Wide BOM (20 direct children)** ✅ COMPLETE (4/4 tests passing)
**Status:** ✅ Fixture-based tests validate performance and correctness

**Tests:**
- test_wide_bom_has_20_children ✅ (20 unique capacitors)
- test_wide_bom_quantities ✅ (all qty=2)
- test_wide_bom_no_warnings ✅ (clean BOM)
- test_wide_bom_performance ✅ (< 2 seconds)

**Fixture Data (pk 9020-9040):**
- Power Supply Board (9020) with 20 direct children
- 20 unique capacitors: 100uF-1000uF electrolytic, 10nF-220nF ceramic, 1uF-10uF film, 22uF-100uF tantalum, 220uF-1000uF polymer
- Each capacitor qty=2, references C1-C40
- Tests API response size and frontend rendering performance

---

**Scenario 4: max_depth Limit Behavior** ✅ COMPLETE (4/4 tests passing)
**Status:** ✅ Validates depth limiting and max_depth_reached return value

**Tests:**
- test_no_max_depth_reaches_leaf ✅ (reaches depth 6 resistor)
- test_max_depth_3_stops_early ✅ (stops at level 3)
- test_max_depth_5_stops_before_leaf ✅ (stops at level 5)
- test_max_depth_10_reaches_leaf ✅ (depth 6 < limit 10)

**Fixture Data (pk 9050-9056):**
- Linear chain: System → Subsystem → Module → Board → Section → Component → Resistor (7 levels)
- Tests max_depth parameter behavior at different thresholds
- Validates that get_flat_bom returns max_depth_reached (integer, not boolean flag)

**Learning:** get_flat_bom() returns `(flat_bom, imp_count, warnings, max_depth_reached)` where max_depth_reached is the actual depth traversed (integer), not a boolean flag.

---

## Critical Gaps Closure (Complete)

**Status:** ✅ All 6 critical gaps closed on January 12, 2026

### ✅ Closed Gaps

**Gap #1: get_bom_items() Function (CLOSED)**
- 22 integration tests for BOM fetching logic
- Tests BOM fetching, empty BOMs, optional items, validated/substitutes
- Tests select_related optimization and error handling
- Commit: 6f18581 (January 12, 2026)

**Gap #2: Circular Reference Detection (CLOSED)**
- 5 integration tests for circular reference handling
- Test ABCA cycle detection and error dict structure
- Validate error nodes are skipped in leaf extraction
- Commit: 6bc3345 (January 12, 2026)

**Gap #3: Plugin Core Methods (CLOSED)**
- 15 integration tests for setup_urls() and get_ui_panels()
- Test URL registration, UI panel logic, error handling
- Test panel dict structure validation
- Commit: e14049f (January 12, 2026)

**Gap #4: Query Parameter Validation (CLOSED)**
- 11 integration tests for max_depth parameter handling
- Test string to int conversion, plugin setting fallback
- Test query param overrides, BOM traversal limiting
- Commit: 521c4de (January 12, 2026)

**Gap #5: View Settings Loading (CLOSED)**
- 6 integration tests for FlatBOMView settings loading
- Test double-patch mocking pattern for plugin registry
- Verify query parameters reach get_flat_bom and retired settings kwargs are absent
- Commit: ab90c00 (January 12, 2026)

**Gap #6: Stock Enrichment Error Handling (CLOSED)**
- 2 integration tests for race condition handling
- Found and fixed production bug (Part.DoesNotExist crash)
- Test partial enrichment with missing parts
- Commit: e1c6d6b (January 12, 2026)

---

## Remaining Test Gaps (Minor, Deferred)

**Status:** No deferred gaps as of November 2026

The former "CtL integration" gap is obsolete - the cut-to-length mechanism was removed in ticket #6. Internal-fab expansion and cut lists now carry fixture-backed integration coverage (`internal_supplier_expansion.yaml` + `test_internal_supplier_expansion.py`), including the sourced-TLA root arms pinned per ruling R-015.

---

## Test Quality Standards

### What Makes a Good Test

**✅ Good Test Characteristics:**
- Tests actual behavior, not implementation details
- Clear, descriptive name explains what it's testing
- Independent (doesn't depend on other tests)
- Covers edge cases (None, empty, zeros, negatives)
- Makes specific assertions (not just `> 0`)
- Uses controlled test data (not external files)
- Fast execution (< 1 second per test)

**❌ Test Anti-Patterns to Avoid:**
- Magic numbers with no explanation
- Duplicate calculation logic instead of importing actual code
- Tests that depend on external data files
- Tests that validate stub functions instead of real code
- Tests that make vague assertions (`assertGreater(x, 0)`)
- Tests that depend on test execution order

### Code-First Methodology

**Before writing/improving tests:**
1. Read the actual production code
2. Understand what it does (trace execution path)
3. Identify edge cases and branches
4. Write tests that validate actual behavior
5. Look for dead code and incorrect fallbacks

**See:** [TEST-WRITING-METHODOLOGY.md](../../docs/archive/TEST-WRITING-METHODOLOGY.md) for detailed guide (archived, non-authoritative)

---

## Manual UI Verification

**Run this 10-minute checklist after each deployment:**

### Basic Functionality
- [ ] Panel appears on part detail page
- [ ] "Generate Flat BOM" button loads table
- [ ] Component column shows full_name (not just part_name)
- [ ] Units display [unit] notation on relevant columns

### Interactive Features
- [ ] Pagination (10/25/50/100/All) works correctly
- [ ] "All" option displays entire table without pagination
- [ ] Column sorting works (click headers)
- [ ] Search box filters rows
- [ ] Checkboxes toggle shortfall values

### Statistics Panel
- [ ] "Total Unique Parts" count accurate
- [ ] "IMP Processed" count accurate
- [ ] Statistics update when checkboxes change

### CSV Export
- [ ] Export button downloads CSV
- [ ] All columns present in CSV
- [ ] Units and shortfall values correct

### Error Handling
- [ ] No errors in browser console (F12)
- [ ] Invalid part handled gracefully
- [ ] Loading indicator shows during generation

---

## Adding New Tests

**Test Structure Template:**
```python
from InvenTree.unit_test import InvenTreeTestCase
from part.models import Part, PartCategory

class MyFeatureTests(InvenTreeTestCase):
    """Tests for MyFeature functionality."""
    
    @classmethod
    def setUpTestData(cls):
        """Create test data once for all tests."""
        super().setUpTestData()
        
        cls.test_cat = PartCategory.objects.create(name='TestCategory')
        cls.test_part = Part.objects.create(
            name='TestPart',
            category=cls.test_cat,
            active=True,
            purchaseable=True
        )
    
    def test_my_feature(self):
        """Test that my feature works correctly."""
        # Arrange - setup is done in setUpTestData
        
        # Act - call your function
        result = my_function(self.test_part)
        
        # Assert - verify results
        self.assertEqual(result, expected_value)
        self.assertTrue(result > 0)
```

**Test Naming Convention:**
- `test_<what_it_does>_<scenario>`
- Example: `test_categorize_part_as_fab_when_in_fabrication_category`

---

## CI/CD Considerations

**Current State:** Manual test execution before deployment

**When to Consider CI:**
- ✅ Test suite comprehensive (150+ tests including integration)
- ✅ Tests consistently pass locally
- ✅ Deploying multiple times per week
- ❌ Multiple developers contributing (solo development)
- ❌ Manual testing becoming friction point (works fine now)

**Recommendation:** Continue manual testing until:
1. Integration test gaps filled (Priorities 1-4)
2. Deploying more frequently (weekly+)
3. Manual workflow becomes burdensome

**Lightweight Options When Ready:**
1. **Pre-commit Hook** (5 min setup) - Run tests before git commit
2. **GitHub Actions** (30 min setup) - Run tests on every push
3. **Scheduled Testing** (1 hour setup) - Nightly test runs with email on failure

**See:** Section 11 in old TEST-PLAN.md for detailed CI/CD considerations

---

## Test Execution Log

| Date | Type | Results | Notes |
|------|------|---------|-------|
| 2025-12-10 | Unit: Shortfall | ✅ 4/4 Pass | Initial checkbox scenarios |
| 2025-12-14 | Unit: Serializers | ✅ 23/23 Pass | Found 2 bugs (note, images) |
| 2025-12-18 | Unit: Internal Fab | ✅ 14/14 Pass | Rewritten, upgraded to High quality |
| 2026-01-09 | Unit: All Files | ✅ 164/164 Pass | Validated with code-first methodology |
| 2026-01-09 | Integration: Priority 1 | ✅ 31/31 Pass | Plugin settings tests |
| 2026-01-10 | Integration: Priority 2 | ✅ 26/26 Pass | Error scenarios tests (found 1 bug) |
| 2026-01-10 | Integration: Priority 3 | ⚠️ GAP ACCEPTED | 85% coverage via components, view integration blocked |
| 2026-01-10 | Integration: Priority 4 | ⚠️ SCENARIO 1 SKIPPED | 5 tests created, blocked by InvenTree validation |
| 2026-01-11 | Integration: Priority 4 | ✅ BREAKTHROUGH | Fixture-based approach, 693-line YAML, all scenarios working |
| 2026-01-11 | Integration: Priority 4 | ✅ 16/17 PASS | Scenarios 1-4 complete (1 skipped: reference aggregation) |
| 2026-01-12 | Integration: Priority 3 | ✅ REOPENED | Using fixture approach to close 15% gap |
| 2026-01-12 | Integration: Priority 3 | ✅ 8/8 PASS | warning_scenarios.yaml (383 lines), all warning types tested! |
| 2026-01-12 | Test Count Update | 📊 151 PASSING | 60 unit + 91 integration (8 warning + 22 get_bom_items + 61 other) |
| 2026-01-12 | Gap #1: get_bom_items | ✅ 22/22 PASS | Comprehensive BOM fetching tests, select_related optimization |
| 2026-01-12 | Gap #2: Circular Refs | ✅ 5/5 PASS | ABCA cycle detection with fixture |
| 2026-01-12 | Gap #3: Plugin Core | ✅ 15/15 PASS | setup_urls and get_ui_panels coverage |
| 2026-01-12 | Gap #4: Query Params | ✅ 11/11 PASS | max_depth parameter validation and integration |
| 2026-01-12 | Gap #5: View Settings | ✅ 6/6 PASS | Double-patch mocking for settings loading |
| 2026-01-12 | Gap #6: Stock Enrichment | ✅ 2/2 PASS + 🐛 BUG FIXED | Production bug found/fixed (Part.DoesNotExist) |

**Current Test Count:** 340 backend tests  
**Breakdown:** 177 unit + 163 integration  
**All Critical Gaps Closed:** Gaps #1-#6 complete (61 tests added)  
**Priorities 1-4 Complete:** 100% coverage achieved via fixture-based integration tests  
**Production Bug Fixed:** Part.DoesNotExist crash in stock enrichment

---

## References

**Toolkit Testing Documentation:**
- Dev environment setup docs live in the `inventree-plugin-ai-toolkit` repo under `docs/reference/` (outside this checkout)

**Plugin Documentation:**
- [ARCHITECTURE.md](../../docs/reference/ARCHITECTURE.md) - Plugin architecture and API reference
- [DEPLOYMENT-WORKFLOW.md](../../docs/reference/DEPLOYMENT-WORKFLOW.md) - Deployment checklist
- [TEST-WRITING-METHODOLOGY.md](../../docs/archive/TEST-WRITING-METHODOLOGY.md) - Code-first validation (archived, non-authoritative)
- Planned work lives in [GitHub issues](https://github.com/jrobelia/inventree-flat-bom-generator/issues)

**External Resources:**
- [InvenTree Plugin Testing](https://docs.inventree.org/en/latest/plugins/test/)
- [Django TestCase](https://docs.djangoproject.com/en/stable/topics/testing/)
- [Python unittest](https://docs.python.org/3/library/unittest.html)

---

_Last updated: November 7, 2026_
