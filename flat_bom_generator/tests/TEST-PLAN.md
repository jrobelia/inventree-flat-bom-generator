# FlatBOMGenerator Plugin - Test Plan

## Overview

This test plan provides a **lightweight testing approach** for the FlatBOMGenerator plugin. The focus is on:

- **10-15 minute manual UI verification** - Quick smoke test checklist for deployment
- **Minimal unit tests** - Only critical logic (shortfall calculation)
- **No CI/CD complexity** - Manual test execution as needed

## Test Framework

InvenTree plugins use **Django's TestCase** from `InvenTree.unit_test` module. Tests should inherit from:

- `InvenTreeTestCase` - For basic unit tests
- `InvenTreeAPITestCase` - For API endpoint tests

**Test Execution**:
```bash
# From toolkit root - use automated script
.\scripts\Test-Plugin.ps1 -Plugin "FlatBOMGenerator"

# Or manually with InvenTree invoke command (if in InvenTree dev environment)
invoke dev.test -r flat_bom_generator.tests.test_shortfall_calculation

# Or fallback to Python unittest
python -m unittest flat_bom_generator.tests.test_shortfall_calculation -v
```

**Environment Setup**:
```powershell
$env:INVENTREE_PLUGINS_ENABLED = "True"
$env:INVENTREE_PLUGIN_TESTING = "True"
$env:INVENTREE_PLUGIN_TESTING_SETUP = "True"
```

See [InvenTree Plugin Testing Documentation](https://docs.inventree.org/en/latest/plugins/test/)

---

## 1. Unit Tests

### 1.1 Shortfall Calculation Tests

**File**: `flat_bom_generator/tests/test_shortfall_calculation.py`

**Status**: ✅ Implemented

**Purpose**: Verify the 4 shortfall calculation scenarios based on checkbox combinations.

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

### 1.2 Future Unit Tests (Optional)

**Status**: 📋 Low Priority

Only implement if issues are discovered in production:

- **BOM Traversal** - Test circular reference detection, quantity calculations
- **Part Categorization** - Test FAB/COML/IMP detection logic
- **Deduplication** - Test quantity aggregation for duplicate parts

*Note: Core BOM logic is well-tested through manual usage. Unit tests are optional.*

---

## 2. Manual UI Verification (10 minutes)

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

## 3. Test Data Setup

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

## 4. Before Production Deployment

Run this final checklist:

- [ ] ✅ Shortfall calculation tests pass (4/4)
- [ ] ✅ UI smoke test completed (10 min checklist above)
- [ ] ✅ Staging environment tested manually with real data
- [ ] ✅ No critical errors in browser console or server logs
- [ ] ✅ Performance acceptable (< 10 seconds for typical BOMs)
- [ ] ✅ README.md and COPILOT-GUIDE.md documentation up to date

---

## 5. Known Limitations

1. **Very Large BOMs** (1000+ unique parts) may take 30+ seconds to process
2. **Circular References** are detected and logged, but not automatically resolved
3. **Test Coverage** is minimal by design - only critical shortfall logic has automated tests

---

## 6. Test Execution Log

| Date | Test Type | Results | Notes |
|------|-----------|---------|-------|
| 2025-12-10 | Unit: Shortfall Calc | ✅ 4/4 Pass | All 4 checkbox scenarios working |
| 2025-12-10 | Manual: UI Smoke Test | ✅ Pass | All features working on staging |
| | | | |

---

## 7. Running Tests

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

## 8. Adding New Tests

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

---

## References

- **InvenTree Plugin Testing**: https://docs.inventree.org/en/latest/plugins/test/
- **Django TestCase**: https://docs.djangoproject.com/en/stable/topics/testing/
- **Python unittest**: https://docs.python.org/3/library/unittest.html
- **Test Automation Script**: `scripts/Test-Plugin.ps1`
