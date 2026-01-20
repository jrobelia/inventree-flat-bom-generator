"""Integration tests for Priority 4: Complex BOM Structures.

Tests BOM traversal with complex real-world scenarios:
- Same part appearing via multiple paths
- Deep BOMs (5+ levels)
- Wide BOMs (many children)
- max_depth limit behavior

Scenario 1: Same Part Multiple Paths
Tests the critical visited.copy() pattern that allows the same part
to appear in different branches of the BOM tree.

Implementation Note:
Uses fixture-based testing (complex_bom.yaml) instead of dynamic part creation.
InvenTree's MPTT validation makes it difficult to create nested assemblies dynamically,
but fixtures with explicit tree_id values bypass this limitation.

Prerequisites:
- InvenTree development environment
- Plugin installed via: pip install -e .

Run:
    .\scripts\Test-Plugin.ps1 -Plugin "FlatBOMGenerator" -Integration
"""

import os
import unittest
from django.core.management import call_command
from InvenTree.unit_test import InvenTreeTestCase
from part.models import Part
from plugin.registry import registry

from flat_bom_generator.bom_traversal import get_flat_bom


class SamePartMultiplePathsTests(InvenTreeTestCase):
    """Test same part appearing via multiple paths in BOM.
    
    BOM Structure:
        Main Assembly (qty=1)
        ├── Subassembly A (qty=2)
        │   └── Screw M3x10 (qty=4)  ← Same part
        └── Subassembly B (qty=3)
            └── Screw M3x10 (qty=2)  ← Same part
    
    Expected Result:
        Screw M3x10 total = (2 × 4) + (3 × 2) = 8 + 6 = 14
    """
    
    @classmethod
    def setUpTestData(cls):
        """Load test data from fixture programmatically.
        
        Django's fixture loader doesn't discover plugin fixtures automatically,
        so we load them with an absolute path using call_command.
        """
        super().setUpTestData()
        
        # Load fixture data programmatically with absolute path
        # Path: tests/integration/test_complex_bom_structures.py -> ../../fixtures/complex_bom.yaml
        # Go up 2 levels to tests/, then into fixtures/
        fixture_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'fixtures',
            'complex_bom.yaml'
        )
        call_command('loaddata', fixture_path, verbosity=0)
        
        # Activate plugin
        registry.set_plugin_state('flat-bom-generator', True)
        
        # Get parts from fixture by PK
        cls.main_assy = Part.objects.get(pk=9001)
        cls.sub_a = Part.objects.get(pk=9002)
        cls.sub_b = Part.objects.get(pk=9003)
        cls.screw = Part.objects.get(pk=9004)
    
    def test_same_part_appears_via_multiple_paths(self):
        """Same part in different branches should appear correctly."""
        result, imp_count, warnings, max_depth = get_flat_bom(self.main_assy.pk)
        
        # Should have exactly 1 unique part (the screw) in flat BOM
        self.assertEqual(len(result), 1, "Should have 1 unique leaf part")
        
        screw_entry = result[0]
        self.assertEqual(screw_entry['part_id'], self.screw.pk, "Should be the screw part")
        self.assertEqual(screw_entry['ipn'], 'HW-SCREW-M3-10', "Should have correct IPN")
    
    def test_quantity_aggregation_across_paths(self):
        """Quantities should aggregate correctly: (2×4) + (3×2) = 14."""
        result, imp_count, warnings, max_depth = get_flat_bom(self.main_assy.pk)
        
        screw_entry = result[0]
        
        # Expected: Sub A contributes 2×4=8, Sub B contributes 3×2=6, total=14
        self.assertEqual(
            screw_entry['total_qty'], 14.0,
            "Total quantity should be (2×4) + (3×2) = 14"
        )
    
    def test_no_circular_reference_warning(self):
        """Same part in different paths should NOT trigger circular reference."""
        result, imp_count, warnings, max_depth = get_flat_bom(self.main_assy.pk)
        
        # Should have no warnings (same part via different paths is valid)
        self.assertEqual(len(warnings), 0, "Should have no circular reference warnings")
    
    def test_references_combined_across_paths(self):
        """Reference designators from both paths should be combined.
        
        When the same part appears via multiple BOM paths, reference designators
        from all paths are aggregated into a single comma-separated string.
        """
        result, imp_count, warnings, max_depth = get_flat_bom(self.main_assy.pk)
        
        screw_entry = result[0]
        reference = screw_entry.get('reference', '')
        
        # Should contain references from both Sub A and Sub B
        # Fixture uses J1, J2, J3, J4 for Sub A and J5, J6 for Sub B
        self.assertIn('J1', reference, "Should include references from Sub A")
        self.assertIn('J5', reference, "Should include references from Sub B")


class SamePartDifferentQuantitiesTests(InvenTreeTestCase):
    """Test same part with different quantities in different branches.
    
    BOM Structure:
        Electronic Assembly
        ├── Module A → Resistor 10k (qty=10)
        ├── Module B → Resistor 10k (qty=5)
        └── Module C → Resistor 10k (qty=3)
    
    Expected Result:
        Resistor 10k total = 10 + 5 + 3 = 18
    """
    
    @classmethod
    def setUpTestData(cls):
        """Load test data from fixture programmatically.
        
        Django's fixture loader doesn't discover plugin fixtures automatically,
        so we load them with an absolute path using call_command.
        """
        super().setUpTestData()
        
        # Load fixture data programmatically with absolute path
        # Path: tests/integration/test_complex_bom_structures.py -> ../../fixtures/complex_bom.yaml
        # Go up 2 levels to tests/, then into fixtures/
        fixture_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'fixtures',
            'complex_bom.yaml'
        )
        call_command('loaddata', fixture_path, verbosity=0)
        
        # Activate plugin
        registry.set_plugin_state('flat-bom-generator', True)
        
        # Get parts from fixture by PK
        cls.assy = Part.objects.get(pk=9010)
        cls.module_a = Part.objects.get(pk=9011)
        cls.module_b = Part.objects.get(pk=9012)
        cls.module_c = Part.objects.get(pk=9013)
        cls.resistor = Part.objects.get(pk=9014)
    
    def test_quantities_sum_from_three_paths(self):
        """Quantities from 3 different paths should sum correctly."""
        result, imp_count, warnings, max_depth = get_flat_bom(self.assy.pk)
        
        self.assertEqual(len(result), 1, "Should have 1 unique part")
        
        resistor_entry = result[0]
        self.assertEqual(resistor_entry['part_id'], self.resistor.pk)
        self.assertEqual(
            resistor_entry['total_qty'], 18.0,
            "Total should be 10 + 5 + 3 = 18"
        )

# Scenario 3: Wide BOM (20 direct children)
class WideBOMTests(InvenTreeTestCase):
    """Test wide BOM with many direct children.
    
    BOM Structure:
        Power Supply Board
        ├── Capacitor 100uF (qty=2)
        ├── Capacitor 220uF (qty=2)
        ├── Capacitor 470uF (qty=2)
        ├── ... (17 more capacitors)
        └── Capacitor 220nF (qty=2)
    
    Total: 20 direct children (40 total capacitors)
    
    Expected Results:
        - 20 unique parts in flat BOM
        - API response handles many items
        - All parts are leaf parts (purchaseable)
    """
    
    @classmethod
    def setUpTestData(cls):
        """Load test data from fixture programmatically."""
        super().setUpTestData()
        
        # Load fixture data programmatically with absolute path
        fixture_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'fixtures',
            'complex_bom.yaml'
        )
        call_command('loaddata', fixture_path, verbosity=0)
        
        # Activate plugin
        registry.set_plugin_state('flat-bom-generator', True)
        
        # Get parts from fixture by PK
        cls.power_supply = Part.objects.get(pk=9020)
        cls.first_cap = Part.objects.get(pk=9021)  # 100uF
        cls.last_cap = Part.objects.get(pk=9040)   # 220nF
    
    def test_wide_bom_has_20_children(self):
        """Wide BOM should have 20 unique leaf parts."""
        result, imp_count, warnings, max_depth = get_flat_bom(self.power_supply.pk)
        
        # Should have exactly 20 unique capacitors
        self.assertEqual(len(result), 20, "Should have 20 unique capacitors")
        
        # All should be leaf parts (non-assembly, purchaseable)
        for item in result:
            part = Part.objects.get(pk=item['part_id'])
            self.assertFalse(part.assembly, f"Part {item['ipn']} should not be assembly")
            self.assertTrue(part.purchaseable, f"Part {item['ipn']} should be purchaseable")
    
    def test_wide_bom_quantities(self):
        """All capacitors should have quantity 2."""
        result, imp_count, warnings, max_depth = get_flat_bom(self.power_supply.pk)
        
        # Each capacitor appears once with qty=2
        for item in result:
            self.assertEqual(item['total_qty'], 2.0, f"Part {item['ipn']} should have qty=2")
    
    def test_wide_bom_no_warnings(self):
        """Wide BOM should not generate warnings."""
        result, imp_count, warnings, max_depth = get_flat_bom(self.power_supply.pk)
        
        self.assertEqual(len(warnings), 0, "Should have no warnings")
    
    def test_wide_bom_performance(self):
        """Wide BOM should complete in reasonable time."""
        import time
        
        start = time.time()
        result, imp_count, warnings, max_depth = get_flat_bom(self.power_supply.pk)
        elapsed = time.time() - start
        
        # Should complete in under 2 seconds (generous limit)
        self.assertLess(elapsed, 2.0, f"Wide BOM took {elapsed:.2f}s (limit: 2s)")


# Scenario 4: max_depth Behavior (7-level linear chain)
class MaxDepthBehaviorTests(InvenTreeTestCase):
    """Test max_depth parameter behavior with deep BOM.
    
    BOM Structure:
        System Level 0 (depth 0)
        └── Subsystem Level 1 (depth 1)
            └── Module Level 2 (depth 2)
                └── Board Level 3 (depth 3)
                    └── Section Level 4 (depth 4)
                        └── Component Level 5 (depth 5)
                            └── Resistor Level 6 (depth 6, leaf)
    
    Total Depth: 7 levels (0-6)
    
    Tests:
        - With max_depth=3, should stop at Level 3
        - With max_depth=5, should reach Level 5 but not 6
        - With max_depth=None, should reach leaf at Level 6
    """
    
    @classmethod
    def setUpTestData(cls):
        """Load test data from fixture programmatically."""
        super().setUpTestData()
        
        # Load fixture data programmatically with absolute path
        fixture_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'fixtures',
            'complex_bom.yaml'
        )
        call_command('loaddata', fixture_path, verbosity=0)
        
        # Activate plugin
        registry.set_plugin_state('flat-bom-generator', True)
        
        # Get parts from fixture by PK
        cls.level_0 = Part.objects.get(pk=9050)
        cls.level_3 = Part.objects.get(pk=9053)
        cls.level_5 = Part.objects.get(pk=9055)
        cls.level_6_leaf = Part.objects.get(pk=9056)
    
    def test_no_max_depth_reaches_leaf(self):
        """Without max_depth limit, should reach leaf part at level 6."""
        result, imp_count, warnings, max_depth_reached = get_flat_bom(self.level_0.pk)
        
        # Should have exactly 1 leaf part (resistor at level 6)
        self.assertEqual(len(result), 1, "Should reach leaf part")
        
        leaf = result[0]
        self.assertEqual(leaf['part_id'], self.level_6_leaf.pk, "Should be level 6 resistor")
        self.assertEqual(leaf['ipn'], 'RES-10K-0.25W', "Should match fixture IPN")
    
    def test_max_depth_3_stops_early(self):
        """With max_depth=3, should stop at level 3 and set flag."""
        result, imp_count, warnings, max_depth_reached = get_flat_bom(self.level_0.pk, max_depth=3)
        
        # Should have reached level 3
        self.assertEqual(max_depth_reached, 3, "Should have reached depth 3")
    
    def test_max_depth_5_stops_before_leaf(self):
        """With max_depth=5, should reach level 5 but not leaf at level 6."""
        result, imp_count, warnings, max_depth_reached = get_flat_bom(self.level_0.pk, max_depth=5)
        
        # Should have reached level 5
        self.assertEqual(max_depth_reached, 5, "Should have reached depth 5")
    
    def test_max_depth_10_reaches_leaf(self):
        """With max_depth=10 (higher than BOM depth), should reach leaf."""
        result, imp_count, warnings, max_depth_reached = get_flat_bom(self.level_0.pk, max_depth=10)
        
        # Should reach leaf normally
        self.assertEqual(len(result), 1, "Should reach leaf part")
        self.assertEqual(max_depth_reached, 6, "Should have traversed to depth 6")
        
        leaf = result[0]
        self.assertEqual(leaf['part_id'], self.level_6_leaf.pk)
