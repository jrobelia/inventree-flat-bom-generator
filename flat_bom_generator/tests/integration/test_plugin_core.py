"""Integration tests for FlatBOMGenerator plugin core functionality.

These tests validate the plugin's core methods that handle URL registration
and UI panel configuration. Tests use the InvenTree test framework to create
real Django models and test plugin integration.

Code-First Validation:
- setup_urls() (core.py lines 95-103)
  - Returns list with one Django path object
  - URL pattern: "flat-bom/<int:part_id>/"
  - View: FlatBOMView.as_view()
  - Name: "flat-bom"

- get_ui_panels() (core.py lines 110-142)
  - Returns empty list for non-part targets
  - Returns empty list when no part_id in context
  - Returns empty list when part doesn't exist (Part.DoesNotExist)
  - Returns empty list when part is not an assembly
  - Returns panel dict for assemblies with proper structure:
    * key: "flat-bom-viewer-panel"
    * title: "Flat BOM Viewer"
    * description: "View flattened bill of materials..."
    * icon: "ti:list-tree:outline"
    * source: plugin static file path

Test Strategy:
- Unit-style tests for setup_urls() (no database needed)
- Integration tests for get_ui_panels() (requires Part model)
- Edge case coverage: invalid part_id, non-existent part, non-assembly part
- Validates actual plugin behavior, not implementation details
"""

from django.urls import path
from InvenTree.unit_test import InvenTreeTestCase
from part.models import Part, PartCategory

from flat_bom_generator.core import FlatBOMGenerator


class SetupUrlsTests(InvenTreeTestCase):
    """Tests for FlatBOMGenerator.setup_urls() method.
    
    Validates URL configuration returned by the plugin. This method
    doesn't require database access as it just returns URL patterns.
    """

    def setUp(self):
        """Create plugin instance for testing."""
        self.plugin = FlatBOMGenerator()

    def test_setup_urls_returns_list(self):
        """setup_urls() should return a list of URL patterns."""
        urls = self.plugin.setup_urls()
        self.assertIsInstance(urls, list)

    def test_setup_urls_returns_one_url(self):
        """setup_urls() should return exactly one URL pattern."""
        urls = self.plugin.setup_urls()
        self.assertEqual(len(urls), 1)

    def test_url_pattern_is_path_object(self):
        """URL pattern should be a Django path object."""
        urls = self.plugin.setup_urls()
        # Django path objects don't have a specific type check,
        # but they should have pattern and name attributes
        url_pattern = urls[0]
        self.assertTrue(hasattr(url_pattern, 'pattern'))
        self.assertTrue(hasattr(url_pattern, 'name'))

    def test_url_pattern_name(self):
        """URL pattern should be named 'flat-bom'."""
        urls = self.plugin.setup_urls()
        self.assertEqual(urls[0].name, 'flat-bom')

    def test_url_pattern_string(self):
        """URL pattern should match expected structure."""
        urls = self.plugin.setup_urls()
        pattern_str = str(urls[0].pattern)
        # Pattern should accept part_id as integer
        self.assertIn('flat-bom', pattern_str)
        self.assertIn('part_id', pattern_str)


class GetUiPanelsTests(InvenTreeTestCase):
    """Tests for FlatBOMGenerator.get_ui_panels() method.
    
    Validates UI panel configuration for different contexts. Tests
    use real Part models to ensure plugin behaves correctly in
    production scenarios.
    """

    @classmethod
    def setUpTestData(cls):
        """Create test data once for all tests."""
        super().setUpTestData()

        # Create test category
        cls.test_cat = PartCategory.objects.create(
            name='TestCategory',
            description='Test category for plugin core tests'
        )

        # Create non-assembly part
        cls.non_assembly_part = Part.objects.create(
            name='Non-Assembly Part',
            category=cls.test_cat,
            description='Part that is not an assembly',
            active=True,
            assembly=False
        )

        # Create assembly part
        cls.assembly_part = Part.objects.create(
            name='Assembly Part',
            category=cls.test_cat,
            description='Part that is an assembly',
            active=True,
            assembly=True
        )

    def setUp(self):
        """Create plugin instance for each test."""
        self.plugin = FlatBOMGenerator()

    def test_returns_empty_list_for_non_part_target(self):
        """get_ui_panels() should return empty list when target_model is not 'part'."""
        context = {
            'target_model': 'stockitem',
            'target_id': 123
        }
        panels = self.plugin.get_ui_panels(request=None, context=context)
        self.assertEqual(panels, [])

    def test_returns_empty_list_when_no_part_id(self):
        """get_ui_panels() should return empty list when part_id is missing."""
        context = {
            'target_model': 'part'
            # No target_id provided
        }
        panels = self.plugin.get_ui_panels(request=None, context=context)
        self.assertEqual(panels, [])

    def test_returns_empty_list_for_nonexistent_part(self):
        """get_ui_panels() should handle Part.DoesNotExist gracefully."""
        context = {
            'target_model': 'part',
            'target_id': 999999  # Non-existent part ID
        }
        panels = self.plugin.get_ui_panels(request=None, context=context)
        self.assertEqual(panels, [])

    def test_returns_empty_list_for_non_assembly_part(self):
        """get_ui_panels() should not show panel for non-assembly parts."""
        context = {
            'target_model': 'part',
            'target_id': self.non_assembly_part.pk
        }
        panels = self.plugin.get_ui_panels(request=None, context=context)
        self.assertEqual(panels, [])

    def test_returns_panel_for_assembly_part(self):
        """get_ui_panels() should return panel for assembly parts."""
        context = {
            'target_model': 'part',
            'target_id': self.assembly_part.pk
        }
        panels = self.plugin.get_ui_panels(request=None, context=context)
        
        # Should return list with one panel
        self.assertEqual(len(panels), 1)
        
        # Validate panel structure
        panel = panels[0]
        self.assertIsInstance(panel, dict)

    def test_panel_has_correct_key(self):
        """Panel should have key 'flat-bom-viewer-panel'."""
        context = {
            'target_model': 'part',
            'target_id': self.assembly_part.pk
        }
        panels = self.plugin.get_ui_panels(request=None, context=context)
        panel = panels[0]
        self.assertEqual(panel['key'], 'flat-bom-viewer-panel')

    def test_panel_has_correct_title(self):
        """Panel should have title 'Flat BOM Viewer'."""
        context = {
            'target_model': 'part',
            'target_id': self.assembly_part.pk
        }
        panels = self.plugin.get_ui_panels(request=None, context=context)
        panel = panels[0]
        self.assertEqual(panel['title'], 'Flat BOM Viewer')

    def test_panel_has_description(self):
        """Panel should have description about flattened BOM."""
        context = {
            'target_model': 'part',
            'target_id': self.assembly_part.pk
        }
        panels = self.plugin.get_ui_panels(request=None, context=context)
        panel = panels[0]
        self.assertIn('description', panel)
        self.assertIn('flattened bill of materials', panel['description'])

    def test_panel_has_icon(self):
        """Panel should have icon 'ti:list-tree:outline'."""
        context = {
            'target_model': 'part',
            'target_id': self.assembly_part.pk
        }
        panels = self.plugin.get_ui_panels(request=None, context=context)
        panel = panels[0]
        self.assertEqual(panel['icon'], 'ti:list-tree:outline')

    def test_panel_has_source(self):
        """Panel should have source pointing to plugin static file."""
        context = {
            'target_model': 'part',
            'target_id': self.assembly_part.pk
        }
        panels = self.plugin.get_ui_panels(request=None, context=context)
        panel = panels[0]
        self.assertIn('source', panel)
        # Source should reference Panel.js and the render function
        self.assertIn('Panel.js', panel['source'])
        self.assertIn('renderFlatBOMGeneratorPanel', panel['source'])
