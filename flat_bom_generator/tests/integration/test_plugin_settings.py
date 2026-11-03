"""Integration tests for plugin settings functions.

Tests get_category_mappings() with real InvenTree database models.
Internal-supplier detection uses Company.is_internal directly - it is
covered by the traversal/expansion tests, not a settings helper.
"""

from InvenTree.unit_test import InvenTreeTestCase
from part.models import PartCategory

from flat_bom_generator.views import get_category_mappings


class MockPlugin:
    """Mock plugin for testing settings retrieval."""

    def __init__(self, settings_dict=None):
        """Initialize mock plugin with settings dictionary."""
        self.settings = settings_dict or {}

    def get_setting(self, key, cache=False, backup_value=None):
        """Mock get_setting method (mirrors SettingsMixin signature)."""
        return self.settings.get(key, backup_value)




class GetCategoryMappingsTests(InvenTreeTestCase):
    """Test get_category_mappings() function."""

    @classmethod
    def setUpTestData(cls):
        """Create test categories with hierarchy."""
        super().setUpTestData()

        # Create parent categories
        cls.fab_parent = PartCategory.objects.create(
            name="Fabrication",
            description="Parent fabrication category",
        )
        cls.coml_parent = PartCategory.objects.create(
            name="Commercial",
            description="Parent commercial category",
        )

        # Create child categories under fabrication
        cls.fab_child1 = PartCategory.objects.create(
            name="Fabrication Child 1",
            parent=cls.fab_parent,
        )
        cls.fab_child2 = PartCategory.objects.create(
            name="Fabrication Child 2",
            parent=cls.fab_parent,
        )

        # Create grandchild under fab_child1
        cls.fab_grandchild = PartCategory.objects.create(
            name="Fabrication Grandchild",
            parent=cls.fab_child1,
        )

    def test_get_single_category_no_children(self):
        """Test retrieving category with no children."""
        plugin = MockPlugin({
            "FABRICATION_CATEGORY": self.coml_parent.pk,
            "COMMERCIAL_CATEGORY": None,
        })
        result = get_category_mappings(plugin)
        self.assertIn("fabrication", result)
        self.assertEqual(result["fabrication"], [self.coml_parent.pk])

    def test_get_category_with_descendants(self):
        """Test retrieving category includes all descendants."""
        plugin = MockPlugin({
            "FABRICATION_CATEGORY": self.fab_parent.pk,
            "COMMERCIAL_CATEGORY": None,
        })
        result = get_category_mappings(plugin)
        self.assertIn("fabrication", result)
        # Should include parent + 2 children + 1 grandchild = 4 total
        self.assertEqual(len(result["fabrication"]), 4)
        self.assertIn(self.fab_parent.pk, result["fabrication"])
        self.assertIn(self.fab_child1.pk, result["fabrication"])
        self.assertIn(self.fab_child2.pk, result["fabrication"])
        self.assertIn(self.fab_grandchild.pk, result["fabrication"])

    def test_get_multiple_categories(self):
        """Test retrieving multiple category types."""
        plugin = MockPlugin({
            "FABRICATION_CATEGORY": self.fab_parent.pk,
            "COMMERCIAL_CATEGORY": self.coml_parent.pk,
        })
        result = get_category_mappings(plugin)
        self.assertIn("fabrication", result)
        self.assertIn("commercial", result)
        # Fabrication has descendants
        self.assertEqual(len(result["fabrication"]), 4)
        # Commercial has no descendants
        self.assertEqual(result["commercial"], [self.coml_parent.pk])

    def test_get_category_with_invalid_id(self):
        """Test handling of invalid category ID (not in database)."""
        invalid_id = 99999
        plugin = MockPlugin({
            "FABRICATION_CATEGORY": invalid_id,
            "COMMERCIAL_CATEGORY": self.coml_parent.pk,
        })
        result = get_category_mappings(plugin)
        # Should skip fabrication (invalid) and only include commercial
        self.assertNotIn("fabrication", result)
        self.assertIn("commercial", result)
        self.assertEqual(result["commercial"], [self.coml_parent.pk])

    def test_get_category_with_string_id(self):
        """Test retrieving category with string ID."""
        plugin = MockPlugin({
            "FABRICATION_CATEGORY": str(self.fab_parent.pk),
            "COMMERCIAL_CATEGORY": None,
        })
        result = get_category_mappings(plugin)
        self.assertIn("fabrication", result)
        self.assertEqual(len(result["fabrication"]), 4)

    def test_get_category_with_invalid_string(self):
        """Test handling of invalid string category ID."""
        plugin = MockPlugin({
            "FABRICATION_CATEGORY": "not_a_number",
            "COMMERCIAL_CATEGORY": self.coml_parent.pk,
        })
        result = get_category_mappings(plugin)
        # Should skip fabrication (invalid string)
        self.assertNotIn("fabrication", result)
        self.assertIn("commercial", result)

    def test_get_category_with_object(self):
        """Test retrieving category with object (has pk attribute)."""
        plugin = MockPlugin({
            "FABRICATION_CATEGORY": self.fab_parent,
            "COMMERCIAL_CATEGORY": None,
        })
        result = get_category_mappings(plugin)
        self.assertIn("fabrication", result)
        self.assertEqual(len(result["fabrication"]), 4)

    def test_get_category_with_empty_settings(self):
        """Test with no categories configured."""
        plugin = MockPlugin({
            "FABRICATION_CATEGORY": None,
            "COMMERCIAL_CATEGORY": None,
        })
        result = get_category_mappings(plugin)
        self.assertEqual(result, {})

    def test_get_category_with_none_plugin(self):
        """Test with None plugin (test environment)."""
        result = get_category_mappings(None)
        self.assertEqual(result, {})
