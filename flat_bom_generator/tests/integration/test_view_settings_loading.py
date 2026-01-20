"""Integration tests for plugin settings loading in FlatBOMView.

Tests verify that the view correctly loads plugin settings and passes them to
the get_flat_bom function. Uses mocking to isolate view behavior.

Strategy:
- Mock BOTH get_flat_bom() AND registry.get_plugin() 
- Create real FlatBOMGeneratorPlugin instances with configured settings
- Patch registry.get_plugin to return our configured plugin
- Verify view passes correct settings to get_flat_bom

Settings tested:
- SHOW_PURCHASED_ASSEMBLIES → expand_purchased_assemblies
- PRIMARY_INTERNAL_SUPPLIER → internal_supplier_ids
- FABRICATION_CATEGORY → category_mappings
- plugin=None → defaults used
"""

from unittest.mock import patch

from rest_framework.test import APIRequestFactory, force_authenticate
from InvenTree.unit_test import InvenTreeTestCase
from part.models import Part, PartCategory
from company.models import Company

from flat_bom_generator.core import FlatBOMGenerator
from flat_bom_generator.views import FlatBOMView


class ViewSettingsLoadingTests(InvenTreeTestCase):
    """Tests for plugin settings loading in FlatBOMView.
    
    Verifies that the view correctly retrieves plugin settings and passes them
    to get_flat_bom(). Uses mocking strategy to intercept both registry.get_plugin
    and get_flat_bom to verify integration.
    
    Note: Helper functions (get_internal_supplier_ids, get_category_mappings) are
    already tested in test_plugin_settings.py (31 tests). This file tests the VIEW's
    integration with those helpers.
    """
    
    @classmethod
    def setUpTestData(cls):
        """Create test data once for all tests."""
        super().setUpTestData()
        
        # Create test category
        cls.test_cat = PartCategory.objects.create(name='TestCategory')
        
        # Create test assembly part
        cls.test_part = Part.objects.create(
            name='Test Assembly',
            IPN='TEST-001',
            category=cls.test_cat,
            active=True,
            assembly=True,
            is_template=False
        )
        
        # Create test company for supplier tests
        cls.test_company = Company.objects.create(
            name='Test Supplier',
            is_supplier=True
        )
    
    def setUp(self):
        """Set up API request factory for each test."""
        super().setUp()
        self.factory = APIRequestFactory()
        self.view = FlatBOMView.as_view()
    
    @patch('flat_bom_generator.views.get_flat_bom')
    @patch('plugin.registry.registry.get_plugin')
    def test_view_loads_expand_purchased_assemblies_setting(self, mock_get_plugin, mock_get_flat_bom):
        """View should load SHOW_PURCHASED_ASSEMBLIES setting and pass to get_flat_bom."""
        # Create plugin with setting configured
        plugin = FlatBOMGenerator()
        plugin.set_setting('SHOW_PURCHASED_ASSEMBLIES', True)
        mock_get_plugin.return_value = plugin
        
        # Mock get_flat_bom to return empty BOM
        mock_get_flat_bom.return_value = ([], 0, [], 0)
        
        # Make request
        request = self.factory.get(f'/fake-url/{self.test_part.pk}/')
        force_authenticate(request, user=self.user)
        response = self.view(request, part_id=self.test_part.pk)
        
        # Verify success
        self.assertEqual(response.status_code, 200)
        mock_get_flat_bom.assert_called_once()
        
        # Check expand_purchased_assemblies argument
        call_kwargs = mock_get_flat_bom.call_args[1]
        self.assertEqual(call_kwargs['expand_purchased_assemblies'], True)
    
    @patch('flat_bom_generator.views.get_flat_bom')
    @patch('plugin.registry.registry.get_plugin')
    def test_view_loads_internal_supplier_ids(self, mock_get_plugin, mock_get_flat_bom):
        """View should load supplier settings via get_internal_supplier_ids."""
        # Create plugin with setting configured
        plugin = FlatBOMGenerator()
        plugin.set_setting('PRIMARY_INTERNAL_SUPPLIER', self.test_company.pk)
        mock_get_plugin.return_value = plugin
        
        # Mock get_flat_bom to return empty BOM
        mock_get_flat_bom.return_value = ([], 0, [], 0)
        
        # Make request
        request = self.factory.get(f'/fake-url/{self.test_part.pk}/')
        force_authenticate(request, user=self.user)
        response = self.view(request, part_id=self.test_part.pk)
        
        # Verify success
        self.assertEqual(response.status_code, 200)
        mock_get_flat_bom.assert_called_once()
        
        # Check internal_supplier_ids argument
        call_kwargs = mock_get_flat_bom.call_args[1]
        self.assertIn(self.test_company.pk, call_kwargs['internal_supplier_ids'])
    
    @patch('flat_bom_generator.views.get_flat_bom')
    @patch('plugin.registry.registry.get_plugin')
    def test_view_loads_category_mappings(self, mock_get_plugin, mock_get_flat_bom):
        """View should load category settings via get_category_mappings."""
        # Create plugin with setting configured
        plugin = FlatBOMGenerator()
        plugin.set_setting('FABRICATION_CATEGORY', self.test_cat.pk)
        mock_get_plugin.return_value = plugin
        
        # Mock get_flat_bom to return empty BOM
        mock_get_flat_bom.return_value = ([], 0, [], 0)
        
        # Make request
        request = self.factory.get(f'/fake-url/{self.test_part.pk}/')
        force_authenticate(request, user=self.user)
        response = self.view(request, part_id=self.test_part.pk)
        
        # Verify success
        self.assertEqual(response.status_code, 200)
        mock_get_flat_bom.assert_called_once()
        
        # Check category_mappings argument
        call_kwargs = mock_get_flat_bom.call_args[1]
        self.assertIsInstance(call_kwargs['category_mappings'], dict)
        # FABRICATION_CATEGORY maps to 'fab' key
        if 'fab' in call_kwargs['category_mappings']:
            self.assertIn(self.test_cat.pk, call_kwargs['category_mappings']['fab'])
    
    @patch('flat_bom_generator.views.get_flat_bom')
    @patch('plugin.registry.registry.get_plugin')
    def test_view_loads_ifab_units_setting(self, mock_get_plugin, mock_get_flat_bom):
        """View should load INTERNAL_FAB_CUT_UNITS and parse CSV correctly."""
        # Create plugin with CSV units (with spaces to test strip())
        plugin = FlatBOMGenerator()
        plugin.set_setting('INTERNAL_FAB_CUT_UNITS', 'mm, in, ft')
        mock_get_plugin.return_value = plugin
        
        # Mock get_flat_bom to return empty BOM
        mock_get_flat_bom.return_value = ([], 0, [], 0)
        
        # Make request
        request = self.factory.get(f'/fake-url/{self.test_part.pk}/')
        force_authenticate(request, user=self.user)
        response = self.view(request, part_id=self.test_part.pk)
        
        # Verify success
        self.assertEqual(response.status_code, 200)
        mock_get_flat_bom.assert_called_once()
        
        # Check ifab_units argument is parsed correctly as set
        call_kwargs = mock_get_flat_bom.call_args[1]
        self.assertIsInstance(call_kwargs['ifab_units'], set)
        self.assertEqual(call_kwargs['ifab_units'], {'mm', 'in', 'ft'})
    
    @patch('flat_bom_generator.views.get_flat_bom')
    @patch('plugin.registry.registry.get_plugin')
    def test_view_defaults_when_plugin_not_found(self, mock_get_plugin, mock_get_flat_bom):
        """View should use defaults when plugin is not in registry."""
        # Mock registry to return None (plugin not found)
        mock_get_plugin.return_value = None
        
        # Mock get_flat_bom to return empty BOM
        mock_get_flat_bom.return_value = ([], 0, [], 0)
        
        # Make request
        request = self.factory.get(f'/fake-url/{self.test_part.pk}/')
        force_authenticate(request, user=self.user)
        response = self.view(request, part_id=self.test_part.pk)
        
        # Verify success
        self.assertEqual(response.status_code, 200)
        mock_get_flat_bom.assert_called_once()
        
        # Check default values
        call_kwargs = mock_get_flat_bom.call_args[1]
        self.assertEqual(call_kwargs['expand_purchased_assemblies'], False)
        self.assertEqual(call_kwargs['internal_supplier_ids'], [])
        self.assertEqual(call_kwargs['category_mappings'], {})
        self.assertEqual(call_kwargs['enable_ifab_cuts'], False)
    
    @patch('flat_bom_generator.views.get_flat_bom')
    @patch('plugin.registry.registry.get_plugin')
    def test_view_passes_all_settings_to_get_flat_bom(self, mock_get_plugin, mock_get_flat_bom):
        """View should pass all loaded settings to get_flat_bom function."""
        # Create plugin (settings not critical for this test)
        plugin = FlatBOMGenerator()
        mock_get_plugin.return_value = plugin
        
        # Mock get_flat_bom to return empty BOM
        mock_get_flat_bom.return_value = ([], 0, [], 0)
        
        # Make request
        request = self.factory.get(f'/fake-url/{self.test_part.pk}/')
        force_authenticate(request, user=self.user)
        response = self.view(request, part_id=self.test_part.pk)
        
        # Verify success
        self.assertEqual(response.status_code, 200)
        mock_get_flat_bom.assert_called_once()
        
        # Check all required kwargs are present
        call_kwargs = mock_get_flat_bom.call_args[1]
        required_kwargs = [
            'max_depth',
            'expand_purchased_assemblies',
            'internal_supplier_ids',
            'category_mappings',
            'enable_ifab_cuts',
            'ifab_units'
        ]
        
        for kwarg in required_kwargs:
            self.assertIn(kwarg, call_kwargs, f"Missing kwarg: {kwarg}")
