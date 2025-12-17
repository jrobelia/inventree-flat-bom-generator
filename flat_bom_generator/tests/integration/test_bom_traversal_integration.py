"""Integration tests for BOM traversal with real InvenTree models.

These tests verify that BOM traversal functions work correctly with real database models.
They DON'T test exact categorization (that's for unit tests), but DO test:
- Functions accept real Part/BOM objects without errors
- Quantity calculations are correct
- Deduplication works
- Stock lookups work

Prerequisites:
- InvenTree development environment set up
- Plugin installed via pip install -e .

Run:
    .\scripts\Test-Plugin.ps1 -Plugin "FlatBOMGenerator" -Integration
"""

from InvenTree.unit_test import InvenTreeTestCase
from part.models import Part, PartCategory, BomItem


class BOMTraversalIntegrationTests(InvenTreeTestCase):
    """Integration tests for BOM traversal functions with real models."""
    
    def test_get_flat_bom_accepts_part_id_and_returns_tuple(self):
        """get_flat_bom should accept part ID and return 4-tuple."""
        from flat_bom_generator.bom_traversal import get_flat_bom
        from part.models import Part, PartCategory
        
        # Create simple part (no BOM needed for this test)
        cat = PartCategory.objects.create(name='Test Category')
        part = Part.objects.create(
            name='Test Part',
            IPN='TST-001',
            category=cat,
            active=True,
            assembly=True,
            is_template=False
        )
        
        # Should not raise exception, should return 4-tuple
        result = get_flat_bom(part.pk)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 4)
        
        # Unpack tuple
        flat_bom, imp_count, warnings, max_depth = result
        self.assertIsInstance(flat_bom, list)
        self.assertIsInstance(imp_count, int)
        self.assertIsInstance(warnings, list)
        self.assertIsInstance(max_depth, int)
    
    def test_deduplicate_and_sum_works_with_dict_list(self):
        """deduplicate_and_sum should handle list of dicts."""
        from flat_bom_generator.bom_traversal import deduplicate_and_sum
        
        # deduplicate_and_sum expects cumulative_qty (from traversal), not total_qty
        input_data = [
            {'part_id': 1, 'cumulative_qty': 5, 'reference': 'R1', 'part_type': 'Other'},
            {'part_id': 1, 'cumulative_qty': 3, 'reference': 'R2', 'part_type': 'Other'},
        ]
        
        result = deduplicate_and_sum(input_data)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['total_qty'], 8)  # Renamed to total_qty in output
    
    def test_part_stock_properties_work(self):
        """Part stock properties should return numeric values."""
        from part.models import Part, PartCategory
        
        cat = PartCategory.objects.create(name='Test Category')
        part = Part.objects.create(
            name='Test Part',
            IPN='TST-002',
            category=cat,
            active=True,
            purchaseable=True
        )
        
        # These should all return numeric values without errors
        stock_value = part.total_stock
        self.assertIsInstance(float(stock_value), float)
        
        available = part.available_stock
        self.assertIsInstance(float(available), float)
        
        allocated = part.allocation_count()
        self.assertIsInstance(float(allocated), float)
    
    def test_serializers_validate_with_real_part_data(self):
        """Serializers should validate data from real Part objects."""
        from flat_bom_generator.serializers import BOMWarningSerializer, FlatBOMItemSerializer
        from part.models import Part, PartCategory
        
        cat = PartCategory.objects.create(name='Test Category')
        part = Part.objects.create(
            name='Test Part',
            IPN='TST-003',
            category=cat,
            active=True,
            purchaseable=True
        )
        
        # Test BOMWarningSerializer
        warning_data = {
            'type': 'unit_mismatch',
            'part_id': part.pk,
            'part_name': part.name,
            'message': 'Test warning'
        }
        serializer = BOMWarningSerializer(data=warning_data)
        self.assertTrue(serializer.is_valid(), f"Errors: {serializer.errors}")
        
        # Test FlatBOMItemSerializer with all required fields
        item_data = {
            'part_id': part.pk,
            'ipn': part.IPN,
            'part_name': part.name,
            'full_name': part.name,  # Required
            'description': part.description or '',  # Required
            'total_qty': 5.0,
            'unit': part.units or '',  # Required
            'part_type': 'Other',
            'is_assembly': part.assembly,  # Required
            'purchaseable': part.purchaseable,  # Required
            'in_stock': 0.0,
            'allocated': 0.0,
            'available': 0.0,
            'on_order': 0.0,
            'link': f'/part/{part.pk}/',  # Required
        }
        serializer = FlatBOMItemSerializer(data=item_data)
        self.assertTrue(serializer.is_valid(), f"Errors: {serializer.errors}")


class CategoryIntegrationTests(InvenTreeTestCase):
    """Integration tests for categorization logic with real categories."""
    
    @classmethod
    def setUpTestData(cls):
        """Create test categories."""
        super().setUpTestData()
        
        cls.fab_cat = PartCategory.objects.create(name='Fabrication')
        cls.coml_cat = PartCategory.objects.create(name='Commercial')
    
    def test_categorize_part_accepts_real_category_id(self):
        """categorize_part should accept real category IDs."""
        from flat_bom_generator.categorization import categorize_part
        
        # Should not raise exception
        result = categorize_part(
            "Test Part",
            is_assembly=False,
            is_top_level=False,
            default_supplier_id=None,
            internal_supplier_ids=[],
            part_category_id=self.fab_cat.pk,
            category_mappings={'fabrication': [self.fab_cat.pk]},
            bom_item_notes=None
        )
        
        self.assertIsInstance(result, str)
        self.assertEqual(result, "Fab")  # categorize_part returns "Fab", not "Fab Part"
