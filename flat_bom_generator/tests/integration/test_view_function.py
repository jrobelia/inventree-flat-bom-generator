"""Integration tests for FlatBOMView.get() method.

Tests the view function directly with real database models and RequestFactory.
Cannot test via HTTP (plugin URLs return 404 in InvenTree test framework).

What We Test:
- View function accepts requests and returns valid responses
- Response structure matches FlatBOMResponseSerializer
- View handles missing/invalid part IDs gracefully
- View enriches BOM data with stock information
- View includes warnings in response

Prerequisites:
- InvenTree development environment must be set up
- Plugin must be installed: pip install -e .

Setup:
    .\scripts\Setup-InvenTreeDev.ps1
    .\scripts\Link-PluginToDev.ps1 -Plugin "FlatBOMGenerator"

Run:
    .\scripts\Test-Plugin.ps1 -Plugin "FlatBOMGenerator" -Integration
    
    Or manually:
    cd inventree-dev\InvenTree
    & .venv\Scripts\Activate.ps1
    invoke dev.test -r FlatBOMGenerator.flat_bom_generator.tests.integration.test_view_function -v

See: docs/toolkit/INVENTREE-DEV-SETUP.md for complete setup guide
See: docs/toolkit/TESTING-STRATEGY.md for API endpoint testing strategy
"""

from django.test import RequestFactory
from InvenTree.unit_test import InvenTreeTestCase
from part.models import Part, PartCategory, BomItem
from stock.models import StockItem
from rest_framework import status

from flat_bom_generator.views import FlatBOMView


class FlatBOMViewIntegrationTests(InvenTreeTestCase):
    """Integration tests for FlatBOMView.get() method with real database models.
    
    Tests view function directly (not via HTTP - plugin URLs return 404).
    Uses RequestFactory to create mock requests and calls view.get() directly.
    """
    
    @classmethod
    def setUpTestData(cls):
        """Create test data once for all tests.
        
        BOM Structure:
            TLA-001 (Top Level Assembly) - 1 unit
            ├── FAB-001 (Fabricated Part) - 2 units
            └── COML-001 (Commercial Part) - 5 units
        """
        super().setUpTestData()
        
        # Create categories
        cls.fab_category = PartCategory.objects.create(
            name="Fabricated",
            description="Fabricated parts",
            pathstring="Fabricated"
        )
        
        cls.coml_category = PartCategory.objects.create(
            name="Commercial",
            description="Commercial parts",
            pathstring="Commercial"
        )
        
        cls.assy_category = PartCategory.objects.create(
            name="Assembly",
            description="Assembly parts",
            pathstring="Assembly"
        )
        
        # Create parts
        cls.tla = Part.objects.create(
            name="Top Level Assembly",
            description="Test assembly",
            category=cls.assy_category,
            IPN="TLA-001",
            active=True,
            assembly=True,
            purchaseable=False,
            units="pcs",
            is_template=False
        )
        
        cls.fab_part = Part.objects.create(
            name="Fabricated Bracket",
            description="Steel bracket",
            category=cls.fab_category,
            IPN="FAB-001",
            active=True,
            assembly=False,
            purchaseable=True,
            units="pcs",
            is_template=False
        )
        
        cls.coml_part = Part.objects.create(
            name="Commercial Resistor",
            description="10k resistor",
            category=cls.coml_category,
            IPN="COML-001",
            active=True,
            assembly=False,
            purchaseable=True,
            units="pcs",
            is_template=False
        )
        
        # Create BOM structure
        BomItem.objects.create(
            part=cls.tla,
            sub_part=cls.fab_part,
            quantity=2,
            reference="BRK1, BRK2"
        )
        
        BomItem.objects.create(
            part=cls.tla,
            sub_part=cls.coml_part,
            quantity=5,
            reference="R1-R5"
        )
        
        # Create stock for testing stock calculations
        StockItem.objects.create(
            part=cls.fab_part,
            quantity=100
        )
        
        StockItem.objects.create(
            part=cls.coml_part,
            quantity=50
        )
    
    def setUp(self):
        """Set up request factory for each test."""
        super().setUp()
        self.factory = RequestFactory()
        self.view = FlatBOMView()
    
    def test_view_returns_200_with_valid_part_id(self):
        """View should return HTTP 200 when part ID exists."""
        request = self.factory.get(f'/api/plugin/flat-bom-generator/flat-bom/{self.tla.pk}/')
        response = self.view.get(request, part_id=self.tla.pk)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_view_returns_404_with_invalid_part_id(self):
        """View should return HTTP 404 when part ID doesn't exist."""
        invalid_id = 99999
        request = self.factory.get(f'/api/plugin/flat-bom-generator/flat-bom/{invalid_id}/')
        response = self.view.get(request, part_id=invalid_id)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)
    
    def test_response_structure_matches_serializer(self):
        """Response should include all fields defined in FlatBOMResponseSerializer."""
        request = self.factory.get(f'/api/plugin/flat-bom-generator/flat-bom/{self.tla.pk}/')
        response = self.view.get(request, part_id=self.tla.pk)
        
        # Check top-level fields
        required_fields = [
            'part_id', 'part_name', 'ipn',
            'total_unique_parts', 'total_ifps_processed', 'max_depth_reached',
            'bom_items', 'metadata'
        ]
        
        for field in required_fields:
            self.assertIn(field, response.data, f"Missing field: {field}")
    
    def test_bom_items_are_leaf_parts_only(self):
        """BOM items should only include leaf parts (FAB, COML), not assemblies."""
        request = self.factory.get(f'/api/plugin/flat-bom-generator/flat-bom/{self.tla.pk}/')
        response = self.view.get(request, part_id=self.tla.pk)
        
        bom_items = response.data['bom_items']
        self.assertEqual(len(bom_items), 2, "Should have 2 leaf parts")
        
        # Check that items are leaf parts
        part_ids = {item['part_id'] for item in bom_items}
        self.assertIn(self.fab_part.pk, part_ids)
        self.assertIn(self.coml_part.pk, part_ids)
        self.assertNotIn(self.tla.pk, part_ids, "TLA should not be in leaf parts")
    
    def test_quantities_are_correct(self):
        """BOM items should have correct quantities from BOM hierarchy."""
        request = self.factory.get(f'/api/plugin/flat-bom-generator/flat-bom/{self.tla.pk}/')
        response = self.view.get(request, part_id=self.tla.pk)
        
        bom_items = response.data['bom_items']
        
        # Find items by part_id
        fab_item = next(item for item in bom_items if item['part_id'] == self.fab_part.pk)
        coml_item = next(item for item in bom_items if item['part_id'] == self.coml_part.pk)
        
        self.assertEqual(fab_item['total_qty'], 2.0, "FAB part should need 2 units")
        self.assertEqual(coml_item['total_qty'], 5.0, "COML part should need 5 units")
    
    def test_stock_levels_included_in_response(self):
        """BOM items should include stock level information."""
        request = self.factory.get(f'/api/plugin/flat-bom-generator/flat-bom/{self.tla.pk}/')
        response = self.view.get(request, part_id=self.tla.pk)
        
        bom_items = response.data['bom_items']
        
        for item in bom_items:
            # Check stock fields exist
            self.assertIn('in_stock', item)
            self.assertIn('on_order', item)
            self.assertIn('allocated', item)
            self.assertIn('available', item)
            
            # Stock values should be numeric
            self.assertIsInstance(item['in_stock'], (int, float))
            self.assertIsInstance(item['available'], (int, float))
    
    def test_statistics_are_accurate(self):
        """Response statistics should match actual BOM data."""
        request = self.factory.get(f'/api/plugin/flat-bom-generator/flat-bom/{self.tla.pk}/')
        response = self.view.get(request, part_id=self.tla.pk)
        
        # Should have 2 unique parts (FAB and COML)
        self.assertEqual(response.data['total_unique_parts'], 2)
        
        # Max depth should be 1 (TLA -> leaf parts)
        self.assertEqual(response.data['max_depth_reached'], 1)
        
        # Part info should match TLA
        self.assertEqual(response.data['part_id'], self.tla.pk)
        self.assertEqual(response.data['part_name'], self.tla.name)
        self.assertEqual(response.data['ipn'], "TLA-001")
    
    def test_metadata_includes_warnings_list(self):
        """Response metadata should include warnings list (even if empty)."""
        request = self.factory.get(f'/api/plugin/flat-bom-generator/flat-bom/{self.tla.pk}/')
        response = self.view.get(request, part_id=self.tla.pk)
        
        self.assertIn('metadata', response.data)
        self.assertIn('warnings', response.data['metadata'])
        self.assertIsInstance(response.data['metadata']['warnings'], list)
    
    def test_view_handles_part_without_bom(self):
        """View should return empty bom_items for part with no BOM."""
        # Create a part with no BOM items
        simple_part = Part.objects.create(
            name="Simple Part",
            description="No BOM",
            category=self.fab_category,
            IPN="SIMPLE-001",
            active=True,
            assembly=False,
            purchaseable=True
        )
        
        request = self.factory.get(f'/api/plugin/flat-bom-generator/flat-bom/{simple_part.pk}/')
        response = self.view.get(request, part_id=simple_part.pk)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['bom_items']), 0)
        self.assertEqual(response.data['total_unique_parts'], 0)
    
    def test_view_includes_part_type_categorization(self):
        """BOM items should include part_type field with categorization."""
        request = self.factory.get(f'/api/plugin/flat-bom-generator/flat-bom/{self.tla.pk}/')
        response = self.view.get(request, part_id=self.tla.pk)
        
        bom_items = response.data['bom_items']
        
        # Find items by category
        fab_item = next(item for item in bom_items if item['part_id'] == self.fab_part.pk)
        coml_item = next(item for item in bom_items if item['part_id'] == self.coml_part.pk)
        
        # Check part_type is set
        self.assertIn('part_type', fab_item)
        self.assertIn('part_type', coml_item)
        
        # Part types should be reasonable (Fab or Coml)
        self.assertIn(fab_item['part_type'], ['Fab', 'Fab Part', 'Coml', 'Coml Part'])
        self.assertIn(coml_item['part_type'], ['Fab', 'Fab Part', 'Coml', 'Coml Part'])
    
    def test_view_enriches_with_image_urls(self):
        """BOM items should include image and thumbnail fields (None if no image)."""
        request = self.factory.get(f'/api/plugin/flat-bom-generator/flat-bom/{self.tla.pk}/')
        response = self.view.get(request, part_id=self.tla.pk)
        
        bom_items = response.data['bom_items']
        
        for item in bom_items:
            self.assertIn('image', item)
            self.assertIn('thumbnail', item)
            # Should be None or a string URL
            self.assertTrue(item['image'] is None or isinstance(item['image'], str))
            self.assertTrue(item['thumbnail'] is None or isinstance(item['thumbnail'], str))
    
    def test_view_includes_link_to_part_detail(self):
        """BOM items should include link field pointing to part detail page."""
        request = self.factory.get(f'/api/plugin/flat-bom-generator/flat-bom/{self.tla.pk}/')
        response = self.view.get(request, part_id=self.tla.pk)
        
        bom_items = response.data['bom_items']
        
        for item in bom_items:
            self.assertIn('link', item)
            self.assertIsInstance(item['link'], str)
            self.assertIn('/part/', item['link'])
    
    def test_view_handles_missing_part_id_parameter(self):
        """View should handle case where part_id parameter is missing."""
        request = self.factory.get('/api/plugin/flat-bom-generator/flat-bom/')
        # Call without part_id parameter - should raise TypeError or return error
        try:
            response = self.view.get(request)
            # If it doesn't raise, should return error response
            self.assertNotEqual(response.status_code, status.HTTP_200_OK)
        except TypeError:
            # Expected - part_id is required parameter
            pass
    
    def test_response_is_json_serializable(self):
        """Response data should be JSON serializable (no Django model objects)."""
        import json
        
        request = self.factory.get(f'/api/plugin/flat-bom-generator/flat-bom/{self.tla.pk}/')
        response = self.view.get(request, part_id=self.tla.pk)
        
        # This should not raise TypeError
        try:
            json_str = json.dumps(response.data)
            self.assertIsInstance(json_str, str)
        except TypeError as e:
            self.fail(f"Response data not JSON serializable: {e}")
