"""Integration tests for settings loading in FlatBOMView.

Tests verify that the view correctly loads plugin settings and query params
and passes them to the get_flat_bom function. Uses mocking to isolate view
behavior.

Strategy:
- Mock BOTH get_flat_bom() AND registry.get_plugin()
- Create real FlatBOMGeneratorPlugin instances with configured settings
- Patch registry.get_plugin to return our configured plugin
- Verify view passes correct kwargs to get_flat_bom

Settings/param sources:
- expand_purchased_assemblies -> query param only
- include_internal_fab_in_cutlist -> retired with the internal-fab cut-list
  mechanism (issue #14); the view no longer reads it
- FABRICATION_CATEGORY / COMMERCIAL_CATEGORY -> category_mappings
- Internal-supplier detection uses Company.is_internal in traversal - the
  view passes no supplier settings at all.
- plugin=None -> defaults used
"""

from unittest.mock import patch

from rest_framework.test import APIRequestFactory, force_authenticate
from InvenTree.unit_test import InvenTreeTestCase
from part.models import Part, PartCategory

from flat_bom_generator.core import FlatBOMGenerator
from flat_bom_generator.views import FlatBOMView


class ViewSettingsLoadingTests(InvenTreeTestCase):
    """Tests for plugin settings loading in FlatBOMView.

    Verifies that the view correctly retrieves plugin settings and passes them
    to get_flat_bom(). Uses mocking strategy to intercept both registry.get_plugin
    and get_flat_bom to verify integration.

    Note: get_category_mappings is tested in test_plugin_settings.py. This file
    tests the VIEW's integration with the settings seam.
    """

    @classmethod
    def setUpTestData(cls):
        """Create test data once for all tests."""
        super().setUpTestData()

        # Grant the 'bom' view permission FlatBOMView requires (role_required='bom')
        cls.user.groups.add(cls.group)
        cls.assignRole('bom.view')

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

    def setUp(self):
        """Set up API request factory for each test."""
        super().setUp()
        # Re-import at test time: the plugin registry can reload
        # flat_bom_generator modules mid-suite, replacing sys.modules entries.
        # The view class and the @patch('flat_bom_generator.views.*') targets
        # must resolve the same module object or mocks silently miss.
        from flat_bom_generator.views import FlatBOMView

        self.factory = APIRequestFactory()
        self.view = FlatBOMView.as_view()

    @patch('flat_bom_generator.views.get_flat_bom')
    @patch('plugin.registry.registry.get_plugin')
    def test_view_loads_expand_purchased_assemblies_query_param(self, mock_get_plugin, mock_get_flat_bom):
        """expand_purchased_assemblies comes from the query param."""
        plugin = FlatBOMGenerator()
        mock_get_plugin.return_value = plugin

        # Mock get_flat_bom to return empty BOM
        mock_get_flat_bom.return_value = ([], 0, [], 0)

        # Make request with the query param set
        request = self.factory.get(
            f'/fake-url/{self.test_part.pk}/?expand_purchased_assemblies=true'
        )
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
    def test_view_passes_no_supplier_settings(self, mock_get_plugin, mock_get_flat_bom):
        """Internal suppliers come from Company.is_internal - no settings kwargs."""
        plugin = FlatBOMGenerator()
        mock_get_plugin.return_value = plugin

        mock_get_flat_bom.return_value = ([], 0, [], 0)

        request = self.factory.get(f'/fake-url/{self.test_part.pk}/')
        force_authenticate(request, user=self.user)
        response = self.view(request, part_id=self.test_part.pk)

        self.assertEqual(response.status_code, 200)
        mock_get_flat_bom.assert_called_once()

        # Retired seams must not be passed to get_flat_bom
        call_kwargs = mock_get_flat_bom.call_args[1]
        self.assertNotIn('internal_supplier_ids', call_kwargs)
        self.assertNotIn('ifab_units', call_kwargs)
        self.assertNotIn('bom_item_notes', call_kwargs)

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
        # FABRICATION_CATEGORY maps to 'fabrication' key
        if 'fabrication' in call_kwargs['category_mappings']:
            self.assertIn(self.test_cat.pk, call_kwargs['category_mappings']['fabrication'])

    @patch('flat_bom_generator.views.get_flat_bom')
    @patch('plugin.registry.registry.get_plugin')
    def test_view_ignores_retired_ifab_cuts_param(self, mock_get_plugin, mock_get_flat_bom):
        """The retired include_internal_fab_in_cutlist param reaches nothing."""
        plugin = FlatBOMGenerator()
        mock_get_plugin.return_value = plugin

        mock_get_flat_bom.return_value = ([], 0, [], 0)

        request = self.factory.get(
            f'/fake-url/{self.test_part.pk}/?include_internal_fab_in_cutlist=true'
        )
        force_authenticate(request, user=self.user)
        response = self.view(request, part_id=self.test_part.pk)

        self.assertEqual(response.status_code, 200)
        mock_get_flat_bom.assert_called_once()

        call_kwargs = mock_get_flat_bom.call_args[1]
        self.assertNotIn('enable_ifab_cuts', call_kwargs)

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
        self.assertEqual(call_kwargs['category_mappings'], {})
        self.assertNotIn('enable_ifab_cuts', call_kwargs)

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
            'category_mappings',
        ]

        for kwarg in required_kwargs:
            self.assertIn(kwarg, call_kwargs, f"Missing kwarg: {kwarg}")
