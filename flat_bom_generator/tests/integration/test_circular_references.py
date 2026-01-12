"""Integration tests for circular reference detection in BOM traversal.

**PURPOSE**: Test that traverse_bom() detects and handles circular references correctly.

Circular references occur when:
- Part A contains Part B, and Part B contains Part A (direct cycle)
- Part A → Part B → Part C → Part A (indirect cycle)

**FIXTURE-BASED TESTING**: Uses circular_refs.yaml to bypass InvenTree validation.

InvenTree's Part.check_add_to_bom() validation prevents creating circular references
in the UI, but they could exist in imported/legacy data. These tests verify robust
error handling when circular refs are encountered.

Fixture Contents (fixtures/circular_refs.yaml):
- 3 Parts (pk 7001-7003) forming circular reference chain
- 3 BomItems (pk 70001-70003) creating A→B→C→A cycle

Prerequisites:
- InvenTree development environment set up
- Plugin installed via pip install -e .

Run:
    .\scripts\Test-Plugin.ps1 -Plugin "FlatBOMGenerator" -Integration
"""

import unittest
import os
from django.core.management import call_command
from InvenTree.unit_test import InvenTreeTestCase
from part.models import Part, PartCategory, BomItem


class CircularReferenceDetectionTests(InvenTreeTestCase):
    """Integration tests for circular reference detection using fixture data."""

    @classmethod
    def setUpTestData(cls):
        """Load fixture data once for all tests."""
        super().setUpTestData()

        # Load fixture (bypasses InvenTree validation!)
        test_dir = os.path.dirname(__file__)  # integration/
        fixtures_dir = os.path.dirname(test_dir)  # tests/
        fixture_path = os.path.join(fixtures_dir, 'fixtures', 'circular_refs.yaml')
        call_command('loaddata', fixture_path, verbosity=0)

        # Get references to fixture parts (A→B→C→A cycle)
        cls.part_a = Part.objects.get(pk=7001)  # Assembly A
        cls.part_b = Part.objects.get(pk=7002)  # Assembly B
        cls.part_c = Part.objects.get(pk=7003)  # Assembly C

    def test_traverse_bom_detects_circular_reference(self):
        """traverse_bom should detect circular reference and return error dict."""
        from flat_bom_generator.bom_traversal import traverse_bom

        # Traverse from Part A (will hit A→B→C→A cycle)
        result = traverse_bom(self.part_a)

        # Should detect circular ref when returning to Part A
        # The cycle: A (level 0) → B (level 1) → C (level 2) → A (ERROR - already visited)
        # Need to check children for error nodes
        self.assertIn('children', result)
        children_b = result['children']
        self.assertGreater(len(children_b), 0)

        # Find Part B in children
        child_b = children_b[0]
        self.assertEqual(child_b['part_id'], self.part_b.pk)

        # Check Part B's children for Part C
        self.assertIn('children', child_b)
        children_c = child_b['children']
        self.assertGreater(len(children_c), 0)

        # Find Part C in children
        child_c = children_c[0]
        self.assertEqual(child_c['part_id'], self.part_c.pk)

        # Check Part C's children for error node (circular ref to Part A)
        self.assertIn('children', child_c)
        children_a_error = child_c['children']
        self.assertGreater(len(children_a_error), 0)

        # This should be an error node (Part A visited again)
        error_node = children_a_error[0]
        self.assertIn('error', error_node)
        self.assertEqual(error_node['error'], 'circular_reference')

    def test_circular_reference_error_dict_structure(self):
        """Error dict should contain all required fields."""
        from flat_bom_generator.bom_traversal import traverse_bom

        result = traverse_bom(self.part_a)

        # Navigate to error node (A→B→C→A)
        child_b = result['children'][0]
        child_c = child_b['children'][0]
        error_node = child_c['children'][0]

        # Verify error dict structure
        self.assertEqual(error_node['error'], 'circular_reference')
        self.assertEqual(error_node['part_id'], self.part_a.pk)
        self.assertEqual(error_node['ipn'], self.part_a.IPN or '')
        self.assertEqual(error_node['part_name'], self.part_a.name)
        self.assertEqual(error_node['level'], 3)  # Level 3 (A at 0, B at 1, C at 2, A again at 3)

    def test_error_nodes_skipped_in_leaf_extraction(self):
        """get_leaf_parts_only should skip error nodes."""
        from flat_bom_generator.bom_traversal import traverse_bom, get_leaf_parts_only

        tree = traverse_bom(self.part_a)
        leaves = get_leaf_parts_only(tree)

        # Should NOT include error nodes in leaf parts
        # Error nodes don't represent real parts to purchase/build
        for leaf in leaves:
            self.assertNotIn('error', leaf, "Error nodes should not appear in leaf parts")

    def test_get_flat_bom_handles_circular_reference(self):
        """get_flat_bom should handle circular references gracefully."""
        from flat_bom_generator.bom_traversal import get_flat_bom

        # Should complete without raising exception
        result, imp_count, warnings, max_depth = get_flat_bom(self.part_a.pk)

        # Should return a list (may be empty or contain valid leaf parts)
        self.assertIsInstance(result, list)
        
        # Should not crash - result structure should be valid
        for item in result:
            self.assertIn('part_id', item)
            self.assertIn('ipn', item)

    def test_circular_reference_logged(self):
        """Circular reference detection should log warning."""
        from flat_bom_generator.bom_traversal import traverse_bom
        import logging
        from io import StringIO

        # Capture log output
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setLevel(logging.WARNING)
        logger = logging.getLogger('inventree')
        logger.addHandler(handler)

        try:
            traverse_bom(self.part_a)
            log_output = log_stream.getvalue()

            # Should log circular reference warning
            self.assertIn('Circular reference detected', log_output)
            self.assertIn(str(self.part_a.pk), log_output)

        finally:
            logger.removeHandler(handler)
