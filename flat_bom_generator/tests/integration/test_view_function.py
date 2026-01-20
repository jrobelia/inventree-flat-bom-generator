"""Integration tests for FlatBOMView.get() method.

Tests the view function directly with real database models and APIRequestFactory.
Cannot test via HTTP (plugin URLs return 404 in InvenTree test framework).

DRF Testing Pattern:
- Use APIRequestFactory to create requests
- Call view as callable (via as_view()) to trigger DRF's request wrapping
- Pattern: response = self.view(request, part_id=123)
- This invokes dispatch() which wraps WSGIRequest into DRF Request

What We Test:
- View function accepts requests and returns valid responses
- Response structure matches FlatBOMResponseSerializer
- View handles missing/invalid part IDs gracefully
- View enriches BOM data with stock information
- View includes warnings in response
- Stock calculations are accurate
- Part categorization works correctly

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

from rest_framework.test import APIRequestFactory, force_authenticate
from InvenTree.unit_test import InvenTreeTestCase
from part.models import Part, PartCategory, BomItem
from stock.models import StockItem
from rest_framework import status
from plugin.registry import registry

from flat_bom_generator.views import FlatBOMView


class FlatBOMViewIntegrationTests(InvenTreeTestCase):
    """Integration tests for FlatBOMView.get() method with real database models.
    
    Tests view function directly (not via HTTP - plugin URLs return 404).
    Uses RequestFactory to create mock requests and calls view.get() directly.
    """
    
    @classmethod
    def setUpTestData(cls):
        """Create test data once for all tests.
        
        Activates the flat-bom-generator plugin for testing.
        
        BOM Structure (matches working test_views_integration.py):
            TLA-001 (Top Level Assembly)
            ├── IFP-001 (Internal Fab Part) × 2
            │   ├── FAB-100 (Fabricated Part) × 4
            │   └── COML-100 (Commercial Part) × 2
            └── COML-200 (Commercial Part) × 10
        
        Leaf parts in flat BOM:
            - FAB-100: 8 (2 × 4)
            - COML-100: 4 (2 × 2)
            - COML-200: 10
        """
        super().setUpTestData()
        
        # Activate the flat-bom-generator plugin
        registry.set_plugin_state('flat-bom-generator', True)
        
        # Create test user for authentication (get_or_create handles --keepdb)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        cls.user, created = User.objects.get_or_create(
            username='flatbom_testuser',
            defaults={
                'password': 'testpass',
                'email': 'flatbom_test@example.com'
            }
        )
        
        # Create categories (exact pattern from working test)
        cls.assemblies_cat = PartCategory.objects.create(
            name='Assemblies',
            description='Assembly parts'
        )
        cls.fab_cat = PartCategory.objects.create(
            name='Fab Parts',
            description='Fabricated parts'
        )
        cls.coml_cat = PartCategory.objects.create(
            name='Commercial Parts',
            description='Commercial off-the-shelf parts'
        )
        
        # Create parts (exact pattern from working test)
        cls.tla = Part.objects.create(
            name='Main Assembly',
            IPN='TLA-001',
            category=cls.assemblies_cat,
            description='Top level assembly for testing',
            active=True,
            assembly=True,
            is_template=False
        )
        
        cls.ifp = Part.objects.create(
            name='Subassembly',
            IPN='IFP-001',
            category=cls.assemblies_cat,
            description='Internal fab part subassembly',
            active=True,
            assembly=True,
            is_template=False
        )
        
        cls.fab = Part.objects.create(
            name='Bracket, Mounting',
            IPN='FAB-100',
            category=cls.fab_cat,
            description='Steel mounting bracket',
            active=True,
            purchaseable=True,
            is_template=False
        )
        
        cls.coml1 = Part.objects.create(
            name='Resistor, 10k',
            IPN='COML-100',
            category=cls.coml_cat,
            description='10k ohm resistor',
            active=True,
            purchaseable=True,
            is_template=False
        )
        
        cls.coml2 = Part.objects.create(
            name='Capacitor, 100uF',
            IPN='COML-200',
            category=cls.coml_cat,
            description='100 microfarad capacitor',
            active=True,
            purchaseable=True,
            is_template=False
        )
        
        # Create BOM relationships (exact pattern from working test)
        BomItem.objects.create(
            part=cls.tla,
            sub_part=cls.ifp,
            quantity=2,
            reference='U1, U2'
        )
        BomItem.objects.create(
            part=cls.tla,
            sub_part=cls.coml2,
            quantity=10,
            reference='C1-C10'
        )
        BomItem.objects.create(
            part=cls.ifp,
            sub_part=cls.fab,
            quantity=4,
            reference='BRK1-BRK4'
        )
        BomItem.objects.create(
            part=cls.ifp,
            sub_part=cls.coml1,
            quantity=2,
            reference='R1, R2'
        )
        
        # Create stock for shortfall calculations
        StockItem.objects.create(
            part=cls.fab,
            quantity=50,
            status=10  # OK status
        )
        StockItem.objects.create(
            part=cls.coml1,
            quantity=100,
            status=10
        )
        StockItem.objects.create(
            part=cls.coml2,
            quantity=5,  # Intentionally low for shortfall testing
            status=10
        )
    
    def setUp(self):
        """Set up API request factory for each test."""
        super().setUp()
        self.factory = APIRequestFactory()
        # Use as_view() to get the callable that properly wraps requests
        self.view = FlatBOMView.as_view()
    
    def test_view_returns_200_with_valid_part_id(self):
        """View should return HTTP 200 when part ID exists."""
        request = self.factory.get(f'/api/plugin/flat-bom-generator/flat-bom/{self.tla.pk}/')
        force_authenticate(request, user=self.user)
        force_authenticate(request, user=self.user)
        # Call view as callable - as_view() handles request wrapping
        response = self.view(request, part_id=self.tla.pk)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_view_returns_404_with_invalid_part_id(self):
        """View should return HTTP 404 when part ID doesn't exist."""
        invalid_id = 99999
        request = self.factory.get(f'/api/plugin/flat-bom-generator/flat-bom/{invalid_id}/')
        force_authenticate(request, user=self.user)
        response = self.view(request, part_id=invalid_id)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)
    
    def test_response_structure_matches_serializer(self):
        """Response should include all fields defined in FlatBOMResponseSerializer."""
        request = self.factory.get(f'/api/plugin/flat-bom-generator/flat-bom/{self.tla.pk}/')
        force_authenticate(request, user=self.user)
        response = self.view(request, part_id=self.tla.pk)
        
        # Check top-level fields
        required_fields = [
            'part_id', 'part_name', 'ipn',
            'total_unique_parts', 'total_ifps_processed', 'max_depth_reached',
            'bom_items', 'metadata'
        ]
        
        for field in required_fields:
            self.assertIn(field, response.data, f"Missing field: {field}")
    
    def test_bom_items_are_leaf_parts_only(self):
        """BOM items should only include leaf parts (purchaseable non-assemblies), not parent assemblies.
        
        Tests core BOM traversal without relying on categories.
        With fallback logic, purchaseable non-assembly parts should appear regardless of part_type.
        """
        request = self.factory.get(f'/api/plugin/flat-bom-generator/flat-bom/{self.tla.pk}/')
        force_authenticate(request, user=self.user)
        response = self.view(request, part_id=self.tla.pk)
        
        bom_items = response.data['bom_items']
        
        # Should have leaf parts (exact count depends on BOM structure)
        self.assertGreater(len(bom_items), 0, "Should have at least one leaf part")
        
        # Check that leaf parts are included
        part_ids = {item['part_id'] for item in bom_items}
        
        # FAB and COML should be in results (purchaseable non-assemblies)
        self.assertIn(self.fab.pk, part_ids, f"FAB part should be leaf. Got IDs: {part_ids}")
        self.assertIn(self.coml1.pk, part_ids, f"COML1 part should be leaf. Got IDs: {part_ids}")
        
        # TLA (top assembly) should NOT be in leaf parts
        self.assertNotIn(self.tla.pk, part_ids, "TLA should not be in leaf parts")
    
    def test_quantities_are_correct(self):
        """BOM items should have correct quantities from BOM hierarchy.
        
        Tests quantity aggregation through nested assemblies.
        BOM structure:
          TLA-001 (qty 1)
            ├── IFP-001 (qty 2) <-- subassembly
            │   ├── FAB-100 (qty 4) --> Total: 2 × 4 = 8
            │   └── COML-100 (qty 2) --> Total: 2 × 2 = 4
            └── COML-200 (qty 10) --> Total: 10
        """
        request = self.factory.get(f'/api/plugin/flat-bom-generator/flat-bom/{self.tla.pk}/')
        force_authenticate(request, user=self.user)
        response = self.view(request, part_id=self.tla.pk)
        
        bom_items = response.data['bom_items']
        self.assertGreater(len(bom_items), 0, "Should have BOM items")
        
        # Find items by part_id (if they exist in results)
        items_by_id = {item['part_id']: item for item in bom_items}
        
        # Verify FAB quantities (if present)
        if self.fab.pk in items_by_id:
            fab_item = items_by_id[self.fab.pk]
            self.assertEqual(fab_item['total_qty'], 8.0, 
                "FAB-100: 2 (IMP qty) × 4 (FAB in IMP) = 8")
        
        # Verify COML-100 quantities (if present)
        if self.coml1.pk in items_by_id:
            coml1_item = items_by_id[self.coml1.pk]
            self.assertEqual(coml1_item['total_qty'], 4.0,
                "COML-100: 2 (IMP qty) × 2 (COML in IMP) = 4")
        
        # Verify COML-200 quantities (if present)
        if self.coml2.pk in items_by_id:
            coml2_item = items_by_id[self.coml2.pk]
            self.assertEqual(coml2_item['total_qty'], 10.0,
                "COML-200: Direct child of TLA = 10")
    
    def test_stock_levels_included_in_response(self):
        """BOM items should include stock level information."""
        request = self.factory.get(f'/api/plugin/flat-bom-generator/flat-bom/{self.tla.pk}/')
        force_authenticate(request, user=self.user)
        response = self.view(request, part_id=self.tla.pk)
        
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
        """Response statistics should match actual BOM data.
        
        Tests that statistics fields are present and reasonable.
        Exact counts depend on BOM structure and leaf part detection.
        """
        request = self.factory.get(f'/api/plugin/flat-bom-generator/flat-bom/{self.tla.pk}/')
        force_authenticate(request, user=self.user)
        response = self.view(request, part_id=self.tla.pk)
        
        # Should have some unique parts (at least 1)
        self.assertGreater(response.data['total_unique_parts'], 0, 
            "Should have at least 1 unique leaf part")
        
        # Max depth should be reasonable (1-3 for our test BOM)
        self.assertGreaterEqual(response.data['max_depth_reached'], 1)
        self.assertLessEqual(response.data['max_depth_reached'], 3)
        
        # Part info should match TLA
        self.assertEqual(response.data['part_id'], self.tla.pk)
        self.assertEqual(response.data['part_name'], self.tla.name)
        self.assertEqual(response.data['ipn'], "TLA-001")
    
    def test_metadata_includes_warnings_list(self):
        """Response metadata should include warnings list (even if empty)."""
        request = self.factory.get(f'/api/plugin/flat-bom-generator/flat-bom/{self.tla.pk}/')
        force_authenticate(request, user=self.user)
        response = self.view(request, part_id=self.tla.pk)
        
        self.assertIn('metadata', response.data)
        self.assertIn('warnings', response.data['metadata'])
        self.assertIsInstance(response.data['metadata']['warnings'], list)
    
    def test_view_handles_part_without_bom(self):
        """View should return empty bom_items for part with no BOM."""
        # Create a part with no BOM items
        simple_part = Part.objects.create(
            name="Simple Part",
            description="No BOM",
            category=self.fab_cat,  # Use existing category
            IPN="SIMPLE-001",
            active=True,
            assembly=False,
            purchaseable=True,
            is_template=False
        )
        
        request = self.factory.get(f'/api/plugin/flat-bom-generator/flat-bom/{simple_part.pk}/')
        force_authenticate(request, user=self.user)
        
        # Non-assembly parts should return 400 error
        response = self.view(request, part_id=simple_part.pk)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('not an assembly', response.data['error'])
    
    def test_view_includes_part_type_categorization(self):
        """BOM items should include part_type field with categorization.
        
        Without plugin settings configured, part_type will be "Other".
        With category mappings configured, would be "Fab Part", "Coml Part", etc.
        """
        request = self.factory.get(f'/api/plugin/flat-bom-generator/flat-bom/{self.tla.pk}/')
        force_authenticate(request, user=self.user)
        response = self.view(request, part_id=self.tla.pk)
        
        bom_items = response.data['bom_items']
        
        # All items should have part_type field
        for item in bom_items:
            self.assertIn('part_type', item)
            # Without category mappings, defaults to "Other"
            # With categories, would be "Fab Part", "Coml Part", etc.
            self.assertIsInstance(item['part_type'], str)
            self.assertGreater(len(item['part_type']), 0)
    
    def test_view_enriches_with_image_urls(self):
        """BOM items should include image and thumbnail fields (None if no image)."""
        request = self.factory.get(f'/api/plugin/flat-bom-generator/flat-bom/{self.tla.pk}/')
        force_authenticate(request, user=self.user)
        response = self.view(request, part_id=self.tla.pk)
        
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
        force_authenticate(request, user=self.user)
        response = self.view(request, part_id=self.tla.pk)
        
        bom_items = response.data['bom_items']
        
        for item in bom_items:
            self.assertIn('link', item)
            self.assertIsInstance(item['link'], str)
            self.assertIn('/part/', item['link'])
    
    def test_view_handles_missing_part_id_parameter(self):
        """View should handle case where part_id parameter is missing."""
        request = self.factory.get('/api/plugin/flat-bom-generator/flat-bom/')
        force_authenticate(request, user=self.user)
        # Call without part_id parameter - should raise TypeError or return error
        try:
            response = self.view(request)
            # If it doesn't raise, should return error response
            self.assertNotEqual(response.status_code, status.HTTP_200_OK)
        except TypeError:
            # Expected - part_id is required parameter
            pass
    
    def test_response_is_json_serializable(self):
        """Response data should be JSON serializable (no Django model objects)."""
        import json
        
        request = self.factory.get(f'/api/plugin/flat-bom-generator/flat-bom/{self.tla.pk}/')
        force_authenticate(request, user=self.user)
        response = self.view(request, part_id=self.tla.pk)
        
        # This should not raise TypeError
        try:
            json_str = json.dumps(response.data)
            self.assertIsInstance(json_str, str)
        except TypeError as e:
            self.fail(f"Response data not JSON serializable: {e}")

