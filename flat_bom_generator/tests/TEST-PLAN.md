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

**Related Documents**:
- **[REFAC-PANEL-PLAN.md](../../docs/internal/REFAC-PANEL-PLAN.md)** - Refactoring priorities, test-first workflow, serializer refactoring status
- **[TEST-QUALITY-REVIEW.md](../../docs/internal/TEST-QUALITY-REVIEW.md)** - Detailed test quality analysis, improvement roadmap, quality checklist
- **Integration Testing Setup**: See toolkit docs:
  - `docs/toolkit/INVENTREE-DEV-SETUP.md` - InvenTree dev environment setup
  - `docs/toolkit/INTEGRATION-TESTING-SUMMARY.md` - 6-hour investigation of plugin URL limitation
  - `docs/toolkit/INTEGRATION-TESTING-SETUP-SUMMARY.md` - Current status and known issues
  - `docs/toolkit/TESTING-STRATEGY.md` - Unit vs integration testing philosophy

## Test Framework

**⚠️ CRITICAL**: InvenTree does NOT support plugin URL testing via Django test client. Plugin URLs return 404 in tests. See "API Endpoint Testing Strategy" section below.

InvenTree plugins use **Django's TestCase** from `InvenTree.unit_test` module. Tests should inherit from:

- `InvenTreeTestCase` - For basic unit tests and direct function testing
- `InvenTreeAPITestCase` - For non-plugin API endpoints (plugin URLs not accessible in tests)

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

## API Endpoint Testing Strategy

**The Problem**: InvenTree's plugin system does NOT expose plugin URLs to Django's test client. HTTP requests to plugin endpoints return 404 in tests.

**The Solution**: Test business logic directly, not via HTTP.

### What We CAN Test (Integration Tests)

1. **View Functions Directly**:
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

2. **Business Logic Functions**:
   ```python
   from flat_bom_generator.bom_traversal import get_flat_bom
   
   def test_get_flat_bom_with_real_parts(self):
       result, imp_count, warnings, max_depth = get_flat_bom(self.part.pk)
       self.assertIsInstance(result, list)
   ```

3. **Serializers with Real Data**:
   ```python
   from flat_bom_generator.serializers import FlatBOMItemSerializer
   
   def test_serializer_validates_real_part(self):
       serializer = FlatBOMItemSerializer(data=test_data)
       self.assertTrue(serializer.is_valid())
   ```

### What We CANNOT Test (Requires Manual Testing)

- ❌ HTTP requests to `/api/plugin/flat-bom-generator/flat-bom/{id}/`
- ❌ URL routing and middleware
- ❌ Authentication/permissions on plugin endpoints
- ✅ **Manual Test Instead**: Use InvenTree UI or API client (Postman/curl) on running server

**Reference**: See [TESTING-STRATEGY.md](../../../../../docs/toolkit/TESTING-STRATEGY.md) for complete integration testing guidance.

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

**For detailed test quality analysis and improvement roadmap, see [TEST-QUALITY-REVIEW.md](../../docs/internal/TEST-QUALITY-REVIEW.md)**

**Summary of Critical Gaps**:
- 🔴 **views.py** - ZERO tests for `FlatBOMAPIView.get()` endpoint logic
- 🔴 **Core BOM traversal** - `get_flat_bom()` and `deduplicate_and_sum()` untested
- 🔴 **Error conditions** - No tests for missing part_id, database errors, validation failures
- 🟡 **Cut-to-length** - Only 1 test, needs expansion (5-10 more tests)
- 🟡 **Internal fab** - Tests use stub functions instead of real code (complete rewrite needed)
- 🟡 **Skipped test** - `test_piece_qty_times_count_rollup` needs investigation

---

### 1.3 Test-First Workflow & Quality Standards

**For complete test-first workflow, see [REFAC-PANEL-PLAN.md](../../docs/internal/REFAC-PANEL-PLAN.md) → Testing section**

**For test quality checklist, see [TEST-QUALITY-REVIEW.md](../../docs/internal/TEST-QUALITY-REVIEW.md) → Test Quality Checklist section**

**Quick Reference**: Before refactoring any code:
1. Check if tests exist
2. Evaluate test quality
3. Improve/create tests FIRST
4. Refactor code
5. Verify tests pass

---

## 2. Detailed Test Documentation

**For comprehensive file-by-file test analysis, see [TEST-QUALITY-REVIEW.md](../../docs/internal/TEST-QUALITY-REVIEW.md)**

The TEST-QUALITY-REVIEW document provides:
- Detailed analysis of all 106 tests across 9 test files
- Quality ratings and what's good/bad about each test file
- Specific improvement recommendations with time estimates
- Test anti-patterns to avoid
- Complete test quality checklist

**Quick Summary of Test Files** (see TEST-QUALITY-REVIEW.md for full details):

| File | Tests | Quality | Key Issues/Notes |
|------|-------|---------|------------------|
| test_serializers.py | 23 | ⭐⭐⭐ High | Comprehensive field validation, found 2 bugs |
| test_shortfall_calculation.py | 21 | ⭐⭐⭐ High | All 4 checkbox scenarios + edge cases |
| test_categorization.py | 18 | ⭐⭐⭐ High | Pure functions well tested |
| test_assembly_no_children.py | 4 | ⭐⭐ Medium | Good but has duplicate tree structure |
| test_max_depth_warnings.py | 5 | ⭐⭐ Medium | Tests logic duplication, not actual code |
| test_cut_to_length_aggregation.py | 1 | ⭐⭐ Medium | **Needs 5-10 more tests** |
| test_internal_fab_cutlist.py | 9 | ⭐ Low | **Tests stub functions, needs rewrite** |
| test_full_bom_part_13.py | 3 | ⭐ Low | **Magic numbers, needs rewrite or delete** |
| test_internal_fab_cut_rollup.py | 22 | ⭐ Low | **1 test skipped for months** |

---

## 3. Test Improvement Roadmap

**For complete improvement roadmap with time estimates, see [TEST-QUALITY-REVIEW.md](../../docs/internal/TEST-QUALITY-REVIEW.md) → Recommendations by Priority**

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
