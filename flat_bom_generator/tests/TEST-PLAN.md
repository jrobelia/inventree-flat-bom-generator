# FlatBOMGenerator Plugin - Test Plan

**Last Updated**: December 15, 2025  
**Test Count**: 106 tests (105 passing, 1 skipped)  
**Overall Grade**: C+ (good foundation, significant gaps)

## Overview

This test plan documents the **current test suite** and **testing strategy** for the FlatBOMGenerator plugin:

- **106 automated unit tests** (105 passing, 1 skipped)
- **14 integration tests created** (framework working, URL registration issue)
- **Test-first workflow** - Check/create/improve tests BEFORE refactoring
- **Test quality evaluation** - Assess coverage, thoroughness, accuracy before changes
- **10-15 minute manual UI verification** - Quick smoke test checklist for deployment
- **Manual test execution** - Currently no CI/CD (see Section 11 for post-refactor considerations)

**Key Documents**:
- **TEST-QUALITY-REVIEW.md** - Comprehensive analysis of all 106 tests with improvement roadmap
- **REFAC-PANEL-PLAN.md** - Serializer refactoring plan with test-first guidelines
- **Integration Testing Status**: See toolkit docs:
  - `docs/toolkit/INVENTREE-DEV-SETUP.md` - InvenTree dev environment setup
  - `docs/toolkit/INTEGRATION-TESTING-SETUP-SUMMARY.md` - Current status and known issues

## Test Framework

InvenTree plugins use **Django's TestCase** from `InvenTree.unit_test` module. Tests should inherit from:

- `InvenTreeTestCase` - For basic unit tests
- `InvenTreeAPITestCase` - For API endpoint tests

**Virtual Environment:**
- Django and djangorestframework are installed in `.venv`
- Always activate `.venv` before running tests: `& ".venv\Scripts\Activate.ps1"`
- Test serializers require Django environment (configured in test file)

**Test Execution**:
```bash
# UNIT TESTS (Fast, no InvenTree required)
# From plugin directory with venv activated (RECOMMENDED)
cd plugins/FlatBOMGenerator
& ".venv\Scripts\Activate.ps1"
python -m unittest flat_bom_generator.tests.test_shortfall_calculation -v

# From toolkit root - use automated script
.\scripts\Test-Plugin.ps1 -Plugin "FlatBOMGenerator" -Unit

# INTEGRATION TESTS (Requires InvenTree dev environment + plugin installed)
# Prerequisites:
#   1. Run Setup-InvenTreeDev.ps1 (one-time)
#   2. Run Link-PluginToDev.ps1 (creates Junction AND pip installs plugin)
#   3. Activate plugin in InvenTree admin panel (Active=True)

# From toolkit root
.\scripts\Test-Plugin.ps1 -Plugin "FlatBOMGenerator" -Integration

# Or manually with InvenTree invoke command (if in InvenTree dev environment)
# (Note: invoke has PTY issues on Windows, use Test-Plugin.ps1 script instead)
cd inventree-dev\InvenTree
invoke dev.test -r FlatBOMGenerator.flat_bom_generator.tests.integration
```

**Critical**: Integration tests require plugin to be:
1. **Linked** via Junction (file access)
2. **Installed** via `pip install -e .` (entry point registration)
3. **Activated** in InvenTree admin panel (Active=True in database)

See `docs/toolkit/INTEGRATION-TESTING-SUMMARY.md` → "What We Learned" for details.

**Integration Testing Status**:
- ✅ **Framework Working**: 14 tests discovered and executed
- ✅ **URL Registration Fixed**: Plugin requires `pip install -e .` in InvenTree venv (not just Junction)
- **Setup**: Run `Link-PluginToDev.ps1` which creates Junction AND pip installs plugin
- **Details**: See `docs/toolkit/INTEGRATION-TESTING-SETUP-SUMMARY.md` → "What We Learned" section

**Environment Setup**:
```powershell
$env:INVENTREE_PLUGINS_ENABLED = "True"
$env:INVENTREE_PLUGIN_TESTING = "True"
$env:INVENTREE_PLUGIN_TESTING_SETUP = "True"
```

See [InvenTree Plugin Testing Documentation](https://docs.inventree.org/en/latest/plugins/test/)

---

## 1. Current Test Suite (106 Tests)

### 1.1 Test Files Overview

| File | Tests | Status | Quality | Purpose |
|------|-------|--------|---------|---------|
| `test_serializers.py` | 23 | ✅ Pass | ⭐⭐⭐ High | Validate DRF serializers for API responses |
| `test_shortfall_calculation.py` | 21 | ✅ Pass | ⭐⭐⭐ High | Test 4 checkbox scenarios + edge cases |
| `test_categorization.py` | 18 | ✅ Pass | ⭐⭐⭐ High | Test FAB/COML/IMP detection logic |
| `test_assembly_no_children.py` | 4 | ✅ Pass | ⭐⭐ Medium | Verify assemblies without children are included |
| `test_max_depth_warnings.py` | 5 | ✅ Pass | ⭐⭐ Medium | Test max_depth flag propagation |
| `test_cut_to_length_aggregation.py` | 1 | ✅ Pass | ⭐⭐ Medium | Test cut-to-length aggregation (needs expansion) |
| `test_internal_fab_cutlist.py` | 9 | ✅ Pass | ⭐ Low | **Tests stub functions, not real code** |
| `test_full_bom_part_13.py` | 3 | ✅ Pass | ⭐ Low | Magic numbers, unexplained expectations |
| `test_internal_fab_cut_rollup.py` | 22 | ⚠️ Skipped | ⭐ Low | **1 test skipped for months** |

**Summary**: 62 high-quality tests, 10 medium-quality, 12 low-quality (need rewrite), 1 skipped (needs investigation)

---

### 1.2 Critical Coverage Gaps

**IDENTIFIED**: December 15, 2025 (see TEST-QUALITY-REVIEW.md for details)

🔴 **CRITICAL - NO TESTS**:
- **views.py API endpoint** - ZERO tests for `FlatBOMAPIView.get()` (just refactored with serializers!)
- **Core BOM traversal** - `get_flat_bom()` and `deduplicate_and_sum()` untested
- **Error conditions** - No tests for missing part_id, database errors, validation failures

🟡 **HIGH PRIORITY - Weak Coverage**:
- **Cut-to-length** - Only 1 test, missing edge cases
- **Internal fab** - Tests use stub functions instead of real code
- **Full BOM test** - Magic numbers without explanation
- **Skipped test** - Needs investigation and fix

---

### 1.3 Test Quality Standards

**Test-First Workflow** (per REFAC-PANEL-PLAN.md guidelines):
1. ✅ Check if tests exist for code you're refactoring
2. ✅ Evaluate test quality (coverage, thoroughness, accuracy, up-to-date)
3. ✅ Improve/create tests BEFORE refactoring
4. ✅ Refactor code
5. ✅ Verify tests still pass

**Quality Criteria** (what makes a good test):
- **Coverage**: Tests validate what you claim to test (not stub functions)
- **Thoroughness**: Edge cases, error conditions, boundary values covered
- **Accuracy**: Tests actual behavior, not implementation details
- **Clarity**: Test names and assertions explain what's being validated
- **Maintainability**: No magic numbers, external file dependencies, or duplicated production logic
- **Isolation**: Tests don't depend on each other or external state

---

## 2. Detailed Test Documentation

### 2.1 Serializer Tests (test_serializers.py)

**File**: `flat_bom_generator/tests/test_serializers.py`  
**Status**: ✅ Implemented (23 tests, all passing)  
**Quality**: ⭐⭐⭐ High - Comprehensive validation of all fields, edge cases, error conditions

#### BOMWarningSerializer Tests (7 tests)

Tests validation of warning messages returned in API responses:
- `test_valid_warning_all_fields()` - All 4 warning types with full data
- `test_warning_types()` - Each warning type individually
- `test_required_fields()` - Validates required vs optional fields
- `test_optional_fields_omitted()` - Tests None/null values
- `test_summary_warning()` - Tests warnings without specific part_id
- `test_invalid_data_missing_fields()` - Tests validation errors
- `test_empty_strings_rejected()` - Tests empty string validation

#### FlatBOMItemSerializer Tests (16 tests)

Tests validation of enriched BOM item data in API responses:
- `test_valid_item_all_fields()` - All 24 fields with complete data
- `test_part_types()` - All 8 part_type categories
- `test_required_fields_only()` - Minimal required data
- `test_optional_fields_none()` - Tests None/null handling
- `test_quantity_types()` - Zero, decimal, integer quantities
- `test_unit_field()` - Unit notation handling
- `test_shortfall_calculation()` - Negative and positive shortfalls
- `test_cut_list_data()` - Optional cut_list field
- `test_internal_fab_cut_list()` - Optional internal_fab field
- `test_image_fields()` - Relative URL handling (CharField, not URLField)
- `test_note_field()` - Optional notes (allow_blank, allow_null)
- `test_invalid_missing_required()` - Validation errors
- `test_invalid_wrong_types()` - Type validation

**Bug Fixes Discovered Through Tests**:
1. `note` field was `required=True` → Changed to `required=False, allow_null=True, allow_blank=True`
2. `image` and `thumbnail` were `URLField` → Changed to `CharField` (for relative URLs like `/media/...`)

---

### 2.2 Shortfall Calculation Tests (test_shortfall_calculation.py)

**File**: `flat_bom_generator/tests/test_shortfall_calculation.py`  
**Status**: ✅ Implemented (21 tests, all passing)  
**Quality**: ⭐⭐⭐ High - Comprehensive edge case coverage

**Purpose**: Verify the 4 shortfall calculation scenarios based on checkbox combinations + edge cases.

**Note**: Tests duplicate production calculation logic (should import actual functions instead).

#### Test Scenarios

| Scenario | Include Allocations | Include On Order | Formula | Status |
|----------|-------------------|------------------|---------|--------|
| 1 | ❌ No | ❌ No | `max(0, required - in_stock)` | ✅ Pass |
| 2 | ✅ Yes | ❌ No | `max(0, required - (in_stock - allocated))` | ✅ Pass |
| 3 | ❌ No | ✅ Yes | `max(0, required - (in_stock + on_order))` | ✅ Pass |
| 4 | ✅ Yes | ✅ Yes | `max(0, required - (in_stock - allocated + on_order))` | ✅ Pass |

**Test Cases**:
- `test_scenario_1_neither_checked()` - Optimistic view (neither box checked)
- `test_scenario_2_allocations_only()` - Realistic view of available stock
- `test_scenario_3_on_order_only()` - Assume incoming stock helps
- `test_scenario_4_both_checked()` - Full realistic planning

---

### 2.3 Other Test Files

**Categorization Tests** (test_categorization.py) - 18 tests, ⭐⭐⭐ High Quality
- Tests FAB/COML/IMP part category detection based on category path
- Comprehensive edge case coverage

**Assembly Tests** (test_assembly_no_children.py) - 4 tests, ⭐⭐ Medium Quality  
- Verifies assemblies without children are included in flat BOM
- Tests both "Assembly" and "Part Assembly" category types
- Needs: Reduce duplicate tree structure creation

**Max Depth Warnings** (test_max_depth_warnings.py) - 5 tests, ⭐⭐ Medium Quality
- Tests max_depth warning flag propagation to child parts
- Needs: Test actual view behavior, not just duplicated logic

**Cut-to-Length** (test_cut_to_length_aggregation.py) - 1 test, ⭐⭐ Medium Quality
- Tests basic cut-to-length aggregation
- **Needs expansion**: Add 5-10 tests for edge cases (zero quantities, unit conversion, missing units)

**Internal Fab Cutlist** (test_internal_fab_cutlist.py) - 9 tests, ⭐ Low Quality
- **CRITICAL ISSUE**: Tests stub functions, not real production code
- Uses external CSV files (brittle, hard to understand)
- **Action Required**: Rewrite to test actual `get_flat_bom()` behavior

**Full BOM Part 13** (test_full_bom_part_13.py) - 3 tests, ⭐ Low Quality
- Tests with magic number (expects 9 unique parts, no explanation)
- **Action Required**: Delete or rewrite with clear expected values

**Internal Fab Cut Rollup** (test_internal_fab_cut_rollup.py) - 22 tests, ⭐ Low Quality
- **1 test skipped** (`test_piece_qty_times_count_rollup`) for months
- **Action Required**: Investigate and fix or remove

---

## 3. Test Improvement Roadmap

**See TEST-QUALITY-REVIEW.md for complete analysis**

### 3.1 Critical Priority (Do First)

🔴 **Add Views Integration Tests** (2-3 hours)
- Test `FlatBOMAPIView.get()` with mock data
- Verify response structure matches API contract
- Test error conditions (missing part_id, invalid data)
- Test with checkbox combinations
- **Status**: NOT STARTED - views.py has ZERO tests!

🔴 **Fix or Remove Skipped Test** (1 hour)
- Investigate `test_piece_qty_times_count_rollup`
- Determine if feature incomplete or test wrong
- Fix or delete with explanation

🔴 **Rewrite Internal Fab Tests** (2-3 hours)
- Remove stub functions
- Test actual `get_flat_bom()` behavior
- Use controlled test data, not external CSVs

---

### 3.2 High Priority (Do Soon)

🟡 **Add Core BOM Traversal Tests** (3-4 hours)
- Test `get_flat_bom()` with various BOM structures
- Test `deduplicate_and_sum()` with duplicate parts
- Test circular reference detection
- Test quantity calculations through multiple levels

🟡 **Expand Cut-to-Length Tests** (1-2 hours)
- Add edge cases: zero quantities, unit conversion, missing units
- Test different unit combinations
- Test error conditions

🟡 **Fix Full BOM Part 13 Test** (30 minutes)
- Add clear comments explaining expected values
- Or delete if redundant with other tests

---

### 3.3 Medium Priority (Future)

🟢 **Add Error Condition Tests** (2 hours)
- Test database query failures
- Test missing required data
- Test malformed BOM structures

🟢 **Improve Shortfall/Max Depth Tests** (1 hour)
- Import actual calculation functions instead of duplicating logic
- Test functions in isolation

🟢 **Performance Tests** (optional)
- Large BOM stress testing (1000+ parts)
- Measure response times

---

## 4. Manual UI Verification (10 minutes)

Run this checklist after each deployment to staging/production:

### Basic Functionality
- [ ] **Load Plugin**: Panel appears on part detail page
- [ ] **Generate Flat BOM**: Click "Generate Flat BOM" button, table loads
- [ ] **Component Column**: Shows full_name (e.g., "Electronics / Resistors / 10k Resistor")
- [ ] **Units Display**: In Stock/Allocated/On Order show `[unit]` notation

### Interactive Features  
- [ ] **Pagination**: 10/25/50/100/All options work correctly
- [ ] **"All" Pagination**: Displays entire table without pagination
- [ ] **Sorting**: Click column headers to sort (ascending/descending)
- [ ] **Search**: Search box filters rows correctly
- [ ] **Checkboxes**: Include Allocations/On Order toggle shortfall values

### Statistics Panel
- [ ] **Total Unique Parts**: Count is accurate
- [ ] **IMP Processed**: Count is accurate (label shows "IMP Processed", not "Total IMP Processed")
- [ ] **Updates**: Statistics update when checkboxes change

### CSV Export
- [ ] **Export Button**: Downloads CSV file
- [ ] **CSV Content**: All columns present (Component, IPN, Category, Total Qty, Unit, In Stock, Allocated, On Order, Shortfall)
- [ ] **CSV Formatting**: Units included, shortfall values correct

### Error Handling
- [ ] **No Errors**: Browser console (F12) shows no red errors
- [ ] **Invalid Part**: Gracefully handles parts with no BOM
- [ ] **Loading State**: Shows loading indicator during generation

---

## 5. Test Data Setup

### Minimal Test Hierarchy

Create minimal test data in InvenTree staging:

```
TLA-001 (Top Level Assembly)
├── IMP-001 (Internal Make Part) × 2
│   ├── FAB-001 (Fabricated Part) × 4
│   └── COML-001 (Commercial Part) × 2
└── COML-002 (Commercial Part) × 10
```

### Test Stock Levels

| Part | In Stock | Allocated | On Order | Notes |
|------|----------|-----------|----------|-------|
| FAB-001 | 50 | 10 | 100 | Should show sufficient stock |
| COML-001 | 100 | 20 | 0 | Should show sufficient stock |
| COML-002 | 5 | 0 | 200 | Shortfall without "On Order" |
| IMP-001 | 10 | 2 | 0 | Parent assembly (not a leaf) |

**Expected Behavior** (Building 1× TLA-001):
- **Include Allocations ❌, Include On Order ❌**: COML-002 shows 5 shortfall (need 10, have 5)
- **Include Allocations ✅, Include On Order ❌**: All parts sufficient
- **Include Allocations ❌, Include On Order ✅**: All parts sufficient (COML-002: 5 + 200 = 205)
- **Include Allocations ✅, Include On Order ✅**: All parts sufficient

---

## 6. Before Production Deployment

Run this final checklist:

- [ ] ✅ All automated tests pass (106/106, no skipped tests)
- [ ] ✅ Critical gaps addressed (views tests, core traversal tests added)
- [ ] ✅ UI smoke test completed (10 min checklist above)
- [ ] ✅ Staging environment tested manually with real data
- [ ] ✅ No critical errors in browser console or server logs
- [ ] ✅ Performance acceptable (< 10 seconds for typical BOMs)
- [ ] ✅ README.md and COPILOT-GUIDE.md documentation up to date

**Current Status** (December 15, 2025):
- 105/106 tests passing (1 skipped - needs investigation)
- Critical gaps identified but NOT yet addressed (views, core traversal)
- NOT ready for production until views tests are added

---

## 7. Known Limitations

1. **Very Large BOMs** (1000+ unique parts) may take 30+ seconds to process
2. **Circular References** are detected and logged, but not automatically resolved
3. **Test Coverage** has significant gaps (views, core traversal) - see TEST-QUALITY-REVIEW.md
4. **Some Tests Use Stub Functions** - test_internal_fab_cutlist.py needs rewrite
5. **One Test Skipped** - test_piece_qty_times_count_rollup needs investigation

---

## 8. Test Execution Log

| Date | Test Type | Results | Notes |
|------|-----------|---------|-------|
| 2025-12-10 | Unit: Shortfall Calc | ✅ 4/4 Pass | Initial 4 checkbox scenarios |
| 2025-12-10 | Manual: UI Smoke Test | ✅ Pass | All features working on staging |
| 2025-12-14 | Unit: Serializers | ✅ 23/23 Pass | Found 2 bugs (note field, image URLs) |
| 2025-12-15 | All Tests | ✅ 105 Pass, ⚠️ 1 Skip | Total 106 tests, 1 skipped |
| 2025-12-15 | Test Quality Review | 📋 Complete | Identified critical gaps (views, core) |

---

## 9. Running Tests

### Automated Test Execution (Recommended)

```powershell
# From toolkit root - runs all tests in plugin
.\scripts\Test-Plugin.ps1 -Plugin "FlatBOMGenerator"

# With detailed output
.\scripts\Test-Plugin.ps1 -Plugin "FlatBOMGenerator" -Verbose

# Run specific test class
.\scripts\Test-Plugin.ps1 -Plugin "FlatBOMGenerator" -TestPath "flat_bom_generator.tests.test_shortfall_calculation.ShortfallCalculationTests"
```

The `Test-Plugin.ps1` script:
- Sets required environment variables automatically
- Discovers test files in `flat_bom_generator/tests/`
- Runs tests with proper InvenTree test framework
- Reports results with colored output

### Manual Test Execution

```powershell
# Set environment variables
$env:INVENTREE_PLUGINS_ENABLED = "True"
$env:INVENTREE_PLUGIN_TESTING = "True"
$env:INVENTREE_PLUGIN_TESTING_SETUP = "True"

# Run with Python unittest
cd plugins\FlatBOMGenerator
python -m unittest flat_bom_generator.tests.test_shortfall_calculation -v
```

### InvenTree Invoke (if in InvenTree dev environment)

```bash
# Run specific test class
invoke dev.test -r flat_bom_generator.tests.test_shortfall_calculation.ShortfallCalculationTests

# Run all tests in module
invoke dev.test -r flat_bom_generator.tests.test_shortfall_calculation
```

---

## 10. Adding New Tests

When adding new unit tests, follow InvenTree plugin testing patterns:

```python
# Example test structure
from InvenTree.unit_test import InvenTreeTestCase
from part.models import Part, PartCategory

class MyFeatureTests(InvenTreeTestCase):
    """Tests for MyFeature functionality."""
    
    @classmethod
    def setUpTestData(cls):
        """Create test data once for all tests."""
        super().setUpTestData()
        
        # Create test parts, categories, etc.
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

**Key Points**:
- Inherit from `InvenTreeTestCase` or `InvenTreeAPITestCase`
- Use Django ORM to create test data (creates temporary test database)
- Use `setUpTestData()` for data that doesn't change between tests
- Use standard `unittest` assertions
- Follow test-first workflow (see REFAC-PANEL-PLAN.md guidelines)

**Test Quality Checklist**:
- [ ] Tests validate actual behavior, not implementation details
- [ ] Tests cover edge cases and error conditions
- [ ] Tests use clear, descriptive names
- [ ] Tests have no magic numbers (explain expected values)
- [ ] Tests don't duplicate production code
- [ ] Tests don't depend on external files (use controlled test data)
- [ ] Tests make specific assertions (not just `assertGreater(x, 0)`)
- [ ] Tests are isolated (don't depend on each other)

---

## 11. CI/CD Considerations (Post-Refactor)

### Current State (December 2025)
- **106 automated tests** - No longer "minimal testing"
- **Manual execution** - Run tests locally before deployment
- **Manual deployment** - Copy plugin to server via `Deploy-Plugin.ps1`
- **No CI pipeline** - Simple, works for part-time development

### When to Consider CI/CD

**Recommended Timing**: After serializer refactoring complete (Phase 3 done) AND critical test gaps filled (views, core traversal)

**Signs You're Ready for CI**:
- ✅ Test suite is comprehensive (150+ tests including views, core, error conditions)
- ✅ Tests consistently pass locally
- ✅ Deploying multiple times per week
- ✅ Multiple developers contributing (not just solo development)
- ✅ Manual test execution becomes friction point

**Signs You Should Wait**:
- ❌ Test suite still has critical gaps (views, core traversal)
- ❌ Tests are unreliable (flaky, skipped tests)
- ❌ Deploying infrequently (once per month)
- ❌ Solo development with good local workflow
- ❌ CI setup complexity outweighs benefit

### Lightweight CI Options

**Option 1: GitHub Actions (Free for public repos)**
- Runs on every commit/PR
- Simple YAML configuration
- No server maintenance
- Good for open source plugins

**Option 2: Pre-commit Hooks (Simplest)**
- Run tests automatically before git commit
- Catches issues before they're pushed
- No external service needed
- 5-minute setup

**Option 3: Scheduled Testing**
- Run tests nightly via scheduled task
- Email results if failures detected
- Minimal setup complexity
- Good for stability monitoring

### Recommended Approach: Start Small

**Phase 1** (5 minutes) - Pre-commit Hook:
```bash
# .git/hooks/pre-commit
#!/bin/bash
cd plugins/FlatBOMGenerator
python -m unittest discover -s flat_bom_generator/tests
```

**Phase 2** (30 minutes) - GitHub Actions (when ready):
```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - run: pip install djangorestframework django
      - run: python -m unittest discover -s flat_bom_generator/tests
```

**Phase 3** (1-2 hours) - Full CI/CD:
- Automated deployment to staging on merge to `main`
- Automated deployment to production on tag/release
- Slack/email notifications on failures

### Decision Framework

Ask yourself:
1. **Pain Level**: Is manual testing becoming tedious? (If no, wait)
2. **Test Confidence**: Do tests reliably catch issues? (Need views/core tests first)
3. **Deployment Frequency**: Deploying weekly or more? (If monthly, CI overkill)
4. **Time Investment**: Worth 1-2 hours setup + learning curve? (Prefer simplicity)

**Current Recommendation**: 
- **Now**: Continue manual testing (works fine, tests still being improved)
- **After refactor complete + test gaps filled**: Consider pre-commit hook (5 min setup, big benefit)
- **If deploying frequently (weekly+)**: Consider GitHub Actions (30 min setup)
- **If staying solo + part-time**: Manual testing is perfectly valid

---

## References

**Plugin-Specific Documentation:**
- **Test Quality Review**: `docs/internal/TEST-QUALITY-REVIEW.md` - Complete analysis of all tests
- **Refactoring Guidelines**: `docs/internal/REFAC-PANEL-PLAN.md` - Test-first workflow

**Toolkit Testing Documentation** (in toolkit root):
- **[docs/toolkit/TESTING-STRATEGY.md](../../../../../docs/toolkit/TESTING-STRATEGY.md)** - Unit vs integration testing philosophy
- **[docs/toolkit/INVENTREE-DEV-SETUP.md](../../../../../docs/toolkit/INVENTREE-DEV-SETUP.md)** - InvenTree dev environment setup guide
- **[docs/toolkit/INTEGRATION-TESTING-SUMMARY.md](../../../../../docs/toolkit/INTEGRATION-TESTING-SUMMARY.md)** - What we built, quick start

**External Resources:**
- **InvenTree Plugin Testing**: https://docs.inventree.org/en/latest/plugins/test/
- **Django TestCase**: https://docs.djangoproject.com/en/stable/topics/testing/
- **Python unittest**: https://docs.python.org/3/library/unittest.html
- **Test Automation Script**: `scripts/Test-Plugin.ps1`
- **GitHub Actions**: https://docs.github.com/en/actions
- **Pre-commit Framework**: https://pre-commit.com/
