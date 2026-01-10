# FlatBOMGenerator - Test Plan

**Last Updated**: January 9, 2026  
**Test Count**: 195 tests (164 unit + 31 integration)  
**Overall Grade**: A- (excellent unit tests, integration needs gap filling)

---

## Overview

This document covers **testing strategy, execution, and improvement priorities** for the FlatBOMGenerator plugin.

**Related Documents:**
- [ROADMAP.md](../../docs/ROADMAP.md) - Plugin improvement plan and architecture
- [TEST-WRITING-METHODOLOGY.md](../../docs/TEST-WRITING-METHODOLOGY.md) - Code-first validation approach
- [ARCHITECTURE.md](../../ARCHITECTURE.md) - Plugin architecture and API reference

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

**Files:** (164 tests total)
- `test_categorization.py` (50 tests) - Part type classification
- `test_serializers.py` (38 tests) - DRF serializer validation
- `test_views.py` (16 tests) - View structure and helper functions
- `test_internal_fab_cutlist.py` (14 tests) - Internal fab cut lists
- `test_assembly_no_children.py` (15 tests) - Warning flag logic
- `test_shortfall_calculation.py` (13 tests) - Frontend calculations
- `test_max_depth_warnings.py` (8 tests) - Flag prioritization
- `test_cut_to_length_aggregation.py` (8 tests) - CtL aggregation
- `test_full_bom_part_13.py` (deleted) - Zero value test
- `test_internal_fab_cut_rollup.py` (merged) - Consolidated into cutlist tests

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

**Files:** (31 tests total)
- `test_view_function.py` (14 tests) - FlatBOMView endpoint testing
- `test_views_integration.py` (12 tests) - BOM traversal workflow
- `test_bom_traversal_integration.py` (5 tests) - Core function integration

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

**InvenTree does NOT support plugin URL testing via Django test client.**

Plugin URLs return 404 in tests because plugin endpoints aren't registered in test environment.

### The Solution

**Test business logic directly, not via HTTP.**

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

#### What We CANNOT Test (Requires Manual Testing)

- ❌ HTTP requests to `/api/plugin/flat-bom-generator/flat-bom/{id}/`
- ❌ URL routing and middleware
- ❌ Authentication/permissions on plugin endpoints
- ✅ **Manual Test Instead:** Use InvenTree UI or API client (Postman/curl) on running server

**Reference:** See [toolkit/TESTING-STRATEGY.md](../../../../docs/toolkit/TESTING-STRATEGY.md) for complete integration testing philosophy.

---

## Test Improvement Priorities

### Current Coverage

**What's Well Tested:**
- ✅ Serializers (38 tests) - All fields, validation, edge cases
- ✅ Categorization (50 tests) - All functions, all part types
- ✅ Warning flags (23 tests) - Flag logic and propagation
- ✅ View structure (16 tests) - Helper functions, imports, contracts
- ✅ Cut-to-length (22 tests) - Aggregation and internal fab
- ✅ Stock calculations (13 tests) - Shortfall formulas

**What's Missing (Integration Test Gaps):**

### 🔴 Priority 1: Plugin Settings & Configuration (0 tests, HIGH RISK)
**Estimated Time:** 2-3 hours for 5-7 tests

**What to Test:**
- `get_category_mappings()` with real plugin settings
  - Category descendants via `category.get_descendants(include_self=True)`
  - Multiple categories configured
  - Invalid category IDs (graceful degradation)
  
- `get_internal_supplier_ids()` extraction
  - Settings with comma-separated IDs
  - Settings with single ID
  - Empty/None settings
  
- `_extract_id_from_value()` type handling
  - Integer values
  - String values
  - Objects with `.pk` attribute
  - Objects with `.id` attribute
  - None values
  
- MAX_DEPTH setting from plugin
  - Default value used
  - Query parameter override
  - Invalid values handled

**Why Critical:** Settings misconfiguration breaks core functionality silently

---

### 🔴 Priority 2: Error Scenarios (0 tests, MEDIUM RISK)
**Estimated Time:** 1 hour for 3-4 tests

**What to Test:**
- Database exceptions
  - `Part.DoesNotExist` when part_id invalid
  - `PartCategory.DoesNotExist` when category deleted
  
- Invalid query parameters
  - Non-integer max_depth
  - Negative part_id
  - Missing required parameters
  
- Empty/None plugin settings
  - No categories configured
  - No internal suppliers configured
  - Graceful fallback behavior

**Why Important:** Users should see helpful error messages, not stack traces

---

### 🟡 Priority 3: Warning Generation (0 tests for actual generation, MEDIUM PRIORITY)
**Estimated Time:** 1.5 hours for 4-5 tests

**What to Test:**
- Unit mismatch warnings
  - Create CtL parts with different units
  - Verify warning in API response metadata
  
- Inactive part warnings
  - Create inactive Part objects
  - Verify warning generated
  
- Assembly no children warnings
  - Create assembly with no BOM items
  - Verify assembly_no_children flag
  - Verify NOT flagged when max_depth stopped it
  
- Max depth exceeded warnings
  - Create very deep BOM (depth > 10)
  - Verify max_depth_exceeded flag
  - Verify summary warning message

**Why Valuable:** Warnings guide users to BOM issues they should fix

---

### 🟡 Priority 4: Complex BOM Structures (minimal coverage, MEDIUM PRIORITY)
**Estimated Time:** 1.5 hours for 3-4 tests

**What to Test:**
- Multi-level assemblies (depth > 2)
  - Quantity multiplication through levels
  - Correct aggregation at each level
  
- Duplicate parts at different BOM levels
  - Same part in level 1 and level 3
  - Quantities correctly summed
  
- Mixed leaf types in single BOM
  - Fab + Coml + CtL + Purchased Assembly
  - All types correctly categorized
  
- Internal Fab assemblies with children
  - cut_length propagates correctly
  - Children not lost in traversal

**Why Useful:** Real-world BOMs are complex, need confidence they work

---

### 🟢 Priority 5-7: Deferred (Lower Priority)

**Priority 5: Cut-to-Length Features** (0 integration tests)
- CtL parts with length extraction from notes
- Unit mismatch detection with actual InvenTree units
- enable_ifab_cuts plugin setting effect

**Priority 6: Query Parameters** (1 test only)
- max_depth query parameter override
- Invalid query parameter handling

**Priority 7: Edge Cases** (0 tests)
- Very deep BOMs (depth > 10)
- Very wide BOMs (100+ children)
- Parts with no category/supplier

**Defer Until:** After Priorities 1-4 complete, evaluate if needed

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

**See:** [TEST-WRITING-METHODOLOGY.md](../../docs/TEST-WRITING-METHODOLOGY.md) for detailed guide

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
| 2026-01-09 | Integration: All | ✅ 31/31 Pass | Fixed 4 broken tests |

---

## References

**Toolkit Testing Documentation:**
- [TESTING-STRATEGY.md](../../../../docs/toolkit/TESTING-STRATEGY.md) - Unit vs integration philosophy
- [INVENTREE-DEV-SETUP.md](../../../../docs/toolkit/INVENTREE-DEV-SETUP.md) - Dev environment setup
- [INTEGRATION-TESTING-SUMMARY.md](../../../../docs/toolkit/INTEGRATION-TESTING-SUMMARY.md) - What we built

**Plugin Documentation:**
- [ROADMAP.md](../../docs/ROADMAP.md) - Plugin improvement plan
- [TEST-WRITING-METHODOLOGY.md](../../docs/TEST-WRITING-METHODOLOGY.md) - Code-first validation
- [DEPLOYMENT-WORKFLOW.md](../../docs/DEPLOYMENT-WORKFLOW.md) - Deployment checklist

**External Resources:**
- [InvenTree Plugin Testing](https://docs.inventree.org/en/latest/plugins/test/)
- [Django TestCase](https://docs.djangoproject.com/en/stable/topics/testing/)
- [Python unittest](https://docs.python.org/3/library/unittest.html)

---

_Last updated: January 9, 2026_
