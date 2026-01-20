"""Integration tests for get_bom_items() function with real InvenTree models.

**FIXTURE-BASED TESTING**: Uses get_bom_items.yaml to bypass InvenTree validation.

This test file uses Django fixtures loaded via call_command('loaddata') to bypass
InvenTree's Part.check_add_to_bom() validation which blocks dynamic BOM creation.

Fixture Contents (fixtures/get_bom_items.yaml):
- 1 PartCategory (pk 8001)
- 1 Company/Supplier (pk 8001)
- 6 Parts (pk 8001-8006): 1 assembly, 1 empty assembly, 4 components
- 1 SupplierPart (pk 8001) for resistor default_supplier
- 4 BomItems (pk 80001-80004) with various attributes for testing

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
from company.models import Company, SupplierPart


class GetBomItemsTests(InvenTreeTestCase):
    """Integration tests for get_bom_items() function using fixture data."""

    @classmethod
    def setUpTestData(cls):
        """Load fixture data once for all tests."""
        super().setUpTestData()

        # Load fixture (bypasses InvenTree validation!)
        test_dir = os.path.dirname(__file__)  # integration/
        fixtures_dir = os.path.dirname(test_dir)  # tests/
        fixture_path = os.path.join(fixtures_dir, 'fixtures', 'get_bom_items.yaml')
        call_command('loaddata', fixture_path, verbosity=0)

        # Get references to fixture parts
        cls.parent = Part.objects.get(pk=8001)  # Main Assembly
        cls.resistor = Part.objects.get(pk=8002)  # Resistor, 10k
        cls.capacitor = Part.objects.get(pk=8003)  # Capacitor, 100nF
        cls.connector = Part.objects.get(pk=8004)  # Connector, USB-C
        cls.no_ref_part = Part.objects.get(pk=8005)  # No Ref Part
        cls.empty_part = Part.objects.get(pk=8006)  # Empty Assembly
        cls.category = PartCategory.objects.get(pk=8001)
        cls.supplier = Company.objects.get(pk=8001)

    def test_get_bom_items_returns_list(self):
        """get_bom_items should return a list."""
        from flat_bom_generator.bom_traversal import get_bom_items

        result = get_bom_items(self.parent)
        self.assertIsInstance(result, list)

    def test_get_bom_items_returns_correct_count(self):
        """get_bom_items should return all BOM items for a part."""
        from flat_bom_generator.bom_traversal import get_bom_items

        result = get_bom_items(self.parent)
        self.assertEqual(len(result), 4)  # 4 BOM items in fixture

    def test_get_bom_items_includes_required_fields(self):
        """Each BOM item dict should include all required fields."""
        from flat_bom_generator.bom_traversal import get_bom_items

        result = get_bom_items(self.parent)
        self.assertGreater(len(result), 0)

        # Check first item has all required fields
        item = result[0]
        required_fields = [
            'sub_part',
            'sub_part_id',
            'quantity',
            'reference',
            'note',
            'notes',  # Alias for categorization
            'optional',
            'inherited',
            'has_default_supplier'
        ]

        for field in required_fields:
            self.assertIn(field, item, f"Missing required field: {field}")

    def test_get_bom_items_quantity_is_float(self):
        """Quantity should be converted to float."""
        from flat_bom_generator.bom_traversal import get_bom_items

        result = get_bom_items(self.parent)
        resistor_item = next(item for item in result if item['sub_part_id'] == self.resistor.pk)
        
        self.assertIsInstance(resistor_item['quantity'], float)
        self.assertEqual(resistor_item['quantity'], 10.0)

    def test_get_bom_items_reference_field(self):
        """Reference field should be populated correctly."""
        from flat_bom_generator.bom_traversal import get_bom_items

        result = get_bom_items(self.parent)
        resistor_item = next(item for item in result if item['sub_part_id'] == self.resistor.pk)
        
        self.assertEqual(resistor_item['reference'], 'R1-R10')

    def test_get_bom_items_empty_reference_becomes_empty_string(self):
        """Empty reference should be empty string, not None."""
        from flat_bom_generator.bom_traversal import get_bom_items

        # Use no_ref_part from fixture (pk 8005)
        result = get_bom_items(self.parent)
        no_ref_item = next(item for item in result if item['sub_part_id'] == self.no_ref_part.pk)
        
        self.assertEqual(no_ref_item['reference'], '')
        self.assertIsInstance(no_ref_item['reference'], str)

    def test_get_bom_items_note_field(self):
        """Note field should be populated correctly."""
        from flat_bom_generator.bom_traversal import get_bom_items

        result = get_bom_items(self.parent)
        resistor_item = next(item for item in result if item['sub_part_id'] == self.resistor.pk)
        
        self.assertEqual(resistor_item['note'], 'Standard resistor')

    def test_get_bom_items_notes_alias(self):
        """'notes' should be an alias of 'note' for categorization compatibility."""
        from flat_bom_generator.bom_traversal import get_bom_items

        result = get_bom_items(self.parent)
        resistor_item = next(item for item in result if item['sub_part_id'] == self.resistor.pk)
        
        self.assertEqual(resistor_item['notes'], resistor_item['note'])

    def test_get_bom_items_empty_note_becomes_empty_string(self):
        """Empty note should be empty string, not None."""
        from flat_bom_generator.bom_traversal import get_bom_items

        result = get_bom_items(self.parent)
        capacitor_item = next(item for item in result if item['sub_part_id'] == self.capacitor.pk)
        
        self.assertEqual(capacitor_item['note'], '')
        self.assertIsInstance(capacitor_item['note'], str)

    def test_get_bom_items_optional_flag(self):
        """Optional flag should be correct."""
        from flat_bom_generator.bom_traversal import get_bom_items

        result = get_bom_items(self.parent)
        
        # Resistor is NOT optional
        resistor_item = next(item for item in result if item['sub_part_id'] == self.resistor.pk)
        self.assertFalse(resistor_item['optional'])
        
        # Connector IS optional
        connector_item = next(item for item in result if item['sub_part_id'] == self.connector.pk)
        self.assertTrue(connector_item['optional'])

    def test_get_bom_items_inherited_flag(self):
        """Inherited flag should be correct."""
        from flat_bom_generator.bom_traversal import get_bom_items

        result = get_bom_items(self.parent)
        resistor_item = next(item for item in result if item['sub_part_id'] == self.resistor.pk)
        
        self.assertFalse(resistor_item['inherited'])

    def test_get_bom_items_has_default_supplier_true(self):
        """has_default_supplier should be True when supplier exists."""
        from flat_bom_generator.bom_traversal import get_bom_items

        result = get_bom_items(self.parent)
        resistor_item = next(item for item in result if item['sub_part_id'] == self.resistor.pk)
        
        self.assertTrue(resistor_item['has_default_supplier'])

    def test_get_bom_items_has_default_supplier_false(self):
        """has_default_supplier should be False when no supplier."""
        from flat_bom_generator.bom_traversal import get_bom_items

        result = get_bom_items(self.parent)
        capacitor_item = next(item for item in result if item['sub_part_id'] == self.capacitor.pk)
        
        self.assertFalse(capacitor_item['has_default_supplier'])

    def test_get_bom_items_sub_part_is_part_instance(self):
        """sub_part should be a Part model instance."""
        from flat_bom_generator.bom_traversal import get_bom_items

        result = get_bom_items(self.parent)
        resistor_item = next(item for item in result if item['sub_part_id'] == self.resistor.pk)
        
        self.assertIsInstance(resistor_item['sub_part'], Part)
        self.assertEqual(resistor_item['sub_part'].pk, self.resistor.pk)

    def test_get_bom_items_empty_bom_returns_empty_list(self):
        """Parts with no BOM should return empty list."""
        from flat_bom_generator.bom_traversal import get_bom_items

        # Use empty_part from fixture (pk 8006)
        result = get_bom_items(self.empty_part)
        self.assertEqual(len(result), 0)
        self.assertIsInstance(result, list)

    def test_get_bom_items_uses_select_related(self):
        """get_bom_items should use select_related for performance."""
        from flat_bom_generator.bom_traversal import get_bom_items
        from django.test.utils import CaptureQueriesContext
        from django.db import connection

        with CaptureQueriesContext(connection) as queries:
            result = get_bom_items(self.parent)
            self.assertGreater(len(result), 0)

        # Check that we're not doing N+1 queries
        # Should be ~2-3 queries max:
        # 1. Fetch BomItems with select_related
        # 2. Maybe some additional lookups
        # NOT: 1 + N queries (1 for BomItems, then N for each sub_part)
        query_count = len(queries)
        self.assertLessEqual(
            query_count,
            5,  # Allow some flexibility
            f"Too many queries ({query_count}), possible N+1 problem"
        )
