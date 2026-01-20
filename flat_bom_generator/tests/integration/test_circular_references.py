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
        """traverse_bom should raise ValueError on circular reference."""
        from flat_bom_generator.bom_traversal import traverse_bom

        # Should raise ValueError when circular reference detected
        # The cycle: A (level 0) → B (level 1) → C (level 2) → A (ERROR - already visited)
        with self.assertRaises(ValueError) as context:
            traverse_bom(self.part_a)
        
        # Verify error message is clear and actionable
        error_msg = str(context.exception)
        self.assertIn('CRITICAL', error_msg)
        self.assertIn('Circular BOM reference detected', error_msg)
        self.assertIn('CIRC-A', error_msg)  # Part IPN from fixture
        self.assertIn(str(self.part_a.pk), error_msg)
        self.assertIn('database integrity may be compromised', error_msg)

    def test_circular_reference_error_message_structure(self):
        """ValueError message should contain all required information."""
        from flat_bom_generator.bom_traversal import traverse_bom

        # Should raise ValueError with detailed message
        with self.assertRaises(ValueError) as context:
            traverse_bom(self.part_a)
        
        error_msg = str(context.exception)
        
        # Verify error message contains critical information
        self.assertIn('CRITICAL', error_msg)
        self.assertIn('Circular BOM reference detected', error_msg)
        self.assertIn('CIRC-A', error_msg)  # Part IPN from fixture
        self.assertIn(str(self.part_a.pk), error_msg)  # Part ID
        self.assertIn('level 3', error_msg)  # Level where circular ref detected
        self.assertIn('database integrity may be compromised', error_msg)

    def test_error_nodes_cannot_exist(self):
        """Error nodes no longer exist - circular refs raise ValueError."""
        from flat_bom_generator.bom_traversal import traverse_bom

        # This test documents behavior change from error dict to exception
        # Error nodes can no longer exist in BOM tree because traverse_bom
        # raises ValueError immediately when circular reference detected
        
        with self.assertRaises(ValueError) as context:
            traverse_bom(self.part_a)
        
        # Verify it's a circular reference error
        self.assertIn('Circular BOM reference', str(context.exception))

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

    def test_circular_reference_raises_not_logs(self):
        """Circular reference detection raises ValueError, not just logging."""
        from flat_bom_generator.bom_traversal import traverse_bom
        import logging
        from io import StringIO

        # Capture log output
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setLevel(logging.ERROR)
        logger = logging.getLogger('inventree')
        logger.addHandler(handler)

        try:
            # Should raise ValueError (fail-loud, not silent logging)
            with self.assertRaises(ValueError) as context:
                traverse_bom(self.part_a)
            
            # Verify it's the circular reference error
            self.assertIn('Circular BOM reference', str(context.exception))
            
            # Note: get_flat_bom() catches this exception and logs it as ERROR
            # but traverse_bom() itself raises the exception immediately

        finally:
            logger.removeHandler(handler)
