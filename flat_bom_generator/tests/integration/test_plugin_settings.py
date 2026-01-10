"""Integration tests for plugin settings functions.

Tests get_category_mappings(), get_internal_supplier_ids(), and related
helper functions with real InvenTree database models.
"""

from InvenTree.unit_test import InvenTreeTestCase
from company.models import Company
from part.models import Part, PartCategory

from flat_bom_generator.views import (
    _extract_id_from_value,
    get_category_mappings,
    get_internal_supplier_ids,
)


class MockPlugin:
    """Mock plugin for testing settings retrieval."""

    def __init__(self, settings_dict=None):
        """Initialize mock plugin with settings dictionary."""
        self.settings = settings_dict or {}

    def get_setting(self, key, default=None):
        """Mock get_setting method."""
        return self.settings.get(key, default)


class ExtractIdFromValueTests(InvenTreeTestCase):
    """Test _extract_id_from_value() helper function."""

    def test_extract_id_from_integer(self):
        """Test extracting ID from integer value."""
        result = _extract_id_from_value(123, "TEST_SETTING")
        self.assertEqual(result, 123)

    def test_extract_id_from_valid_string(self):
        """Test extracting ID from valid string."""
        result = _extract_id_from_value("456", "TEST_SETTING")
        self.assertEqual(result, 456)

    def test_extract_id_from_invalid_string(self):
        """Test extracting ID from invalid string returns None."""
        result = _extract_id_from_value("not_a_number", "TEST_SETTING")
        self.assertIsNone(result)

    def test_extract_id_from_object_with_pk(self):
        """Test extracting ID from object with pk attribute."""
        obj = type("MockObj", (), {"pk": 789})()
        result = _extract_id_from_value(obj, "TEST_SETTING")
        self.assertEqual(result, 789)

    def test_extract_id_from_object_with_id(self):
        """Test extracting ID from object with id attribute."""
        obj = type("MockObj", (), {"id": 999})()
        result = _extract_id_from_value(obj, "TEST_SETTING")
        self.assertEqual(result, 999)

    def test_extract_id_from_none(self):
        """Test extracting ID from None returns None."""
        result = _extract_id_from_value(None, "TEST_SETTING")
        self.assertIsNone(result)

    def test_extract_id_from_empty_string(self):
        """Test extracting ID from empty string returns None."""
        result = _extract_id_from_value("", "TEST_SETTING")
        self.assertIsNone(result)

    def test_extract_id_from_invalid_object(self):
        """Test extracting ID from object without pk/id returns None."""
        obj = type("MockObj", (), {"value": 123})()
        result = _extract_id_from_value(obj, "TEST_SETTING")
        self.assertIsNone(result)


class GetInternalSupplierIdsTests(InvenTreeTestCase):
    """Test get_internal_supplier_ids() function."""

    @classmethod
    def setUpTestData(cls):
        """Create test suppliers."""
        super().setUpTestData()

        cls.supplier1 = Company.objects.create(
            name="Internal Supplier 1",
            is_supplier=True,
            is_manufacturer=False,
        )
        cls.supplier2 = Company.objects.create(
            name="Internal Supplier 2",
            is_supplier=True,
            is_manufacturer=False,
        )
        cls.supplier3 = Company.objects.create(
            name="Internal Supplier 3",
            is_supplier=True,
            is_manufacturer=False,
        )

    def test_get_single_primary_supplier(self):
        """Test retrieving single primary supplier."""
        plugin = MockPlugin({
            "PRIMARY_INTERNAL_SUPPLIER": self.supplier1.pk,
            "ADDITIONAL_INTERNAL_SUPPLIERS": "",
        })
        result = get_internal_supplier_ids(plugin)
        self.assertEqual(result, [self.supplier1.pk])

    def test_get_primary_and_additional_suppliers(self):
        """Test retrieving primary and additional suppliers."""
        plugin = MockPlugin({
            "PRIMARY_INTERNAL_SUPPLIER": self.supplier1.pk,
            "ADDITIONAL_INTERNAL_SUPPLIERS": f"{self.supplier2.pk},{self.supplier3.pk}",
        })
        result = get_internal_supplier_ids(plugin)
        expected = sorted([self.supplier1.pk, self.supplier2.pk, self.supplier3.pk])
        self.assertEqual(result, expected)

    def test_get_additional_suppliers_only(self):
        """Test retrieving only additional suppliers (no primary)."""
        plugin = MockPlugin({
            "PRIMARY_INTERNAL_SUPPLIER": None,
            "ADDITIONAL_INTERNAL_SUPPLIERS": f"{self.supplier2.pk},{self.supplier3.pk}",
        })
        result = get_internal_supplier_ids(plugin)
        expected = sorted([self.supplier2.pk, self.supplier3.pk])
        self.assertEqual(result, expected)

    def test_get_suppliers_with_whitespace(self):
        """Test parsing additional suppliers with whitespace."""
        plugin = MockPlugin({
            "PRIMARY_INTERNAL_SUPPLIER": self.supplier1.pk,
            "ADDITIONAL_INTERNAL_SUPPLIERS": f" {self.supplier2.pk} , {self.supplier3.pk} ",
        })
        result = get_internal_supplier_ids(plugin)
        expected = sorted([self.supplier1.pk, self.supplier2.pk, self.supplier3.pk])
        self.assertEqual(result, expected)

    def test_get_suppliers_with_duplicates(self):
        """Test deduplication of duplicate supplier IDs."""
        plugin = MockPlugin({
            "PRIMARY_INTERNAL_SUPPLIER": self.supplier1.pk,
            "ADDITIONAL_INTERNAL_SUPPLIERS": f"{self.supplier1.pk},{self.supplier2.pk}",
        })
        result = get_internal_supplier_ids(plugin)
        # Should deduplicate supplier1
        expected = sorted([self.supplier1.pk, self.supplier2.pk])
        self.assertEqual(result, expected)

    def test_get_suppliers_with_invalid_id(self):
        """Test handling of invalid supplier ID (not in database)."""
        invalid_id = 99999
        plugin = MockPlugin({
            "PRIMARY_INTERNAL_SUPPLIER": invalid_id,
            "ADDITIONAL_INTERNAL_SUPPLIERS": str(self.supplier2.pk),
        })
        result = get_internal_supplier_ids(plugin)
        # Should only include supplier2 (valid ID)
        self.assertEqual(result, [self.supplier2.pk])

    def test_get_suppliers_with_invalid_string(self):
        """Test handling of invalid string in additional suppliers."""
        plugin = MockPlugin({
            "PRIMARY_INTERNAL_SUPPLIER": self.supplier1.pk,
            "ADDITIONAL_INTERNAL_SUPPLIERS": f"{self.supplier2.pk},not_a_number,{self.supplier3.pk}",
        })
        result = get_internal_supplier_ids(plugin)
        # Should skip invalid string
        expected = sorted([self.supplier1.pk, self.supplier2.pk, self.supplier3.pk])
        self.assertEqual(result, expected)

    def test_get_suppliers_with_empty_settings(self):
        """Test with empty supplier settings."""
        plugin = MockPlugin({
            "PRIMARY_INTERNAL_SUPPLIER": None,
            "ADDITIONAL_INTERNAL_SUPPLIERS": "",
        })
        result = get_internal_supplier_ids(plugin)
        self.assertEqual(result, [])

    def test_get_suppliers_with_none_plugin(self):
        """Test with None plugin (test environment)."""
        result = get_internal_supplier_ids(None)
        self.assertEqual(result, [])


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
        cls.ctl_parent = PartCategory.objects.create(
            name="Cut-to-Length",
            description="Parent cut-to-length category",
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
            "CUT_TO_LENGTH_CATEGORY": None,
        })
        result = get_category_mappings(plugin)
        self.assertIn("fabrication", result)
        self.assertEqual(result["fabrication"], [self.coml_parent.pk])

    def test_get_category_with_descendants(self):
        """Test retrieving category includes all descendants."""
        plugin = MockPlugin({
            "FABRICATION_CATEGORY": self.fab_parent.pk,
            "COMMERCIAL_CATEGORY": None,
            "CUT_TO_LENGTH_CATEGORY": None,
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
            "CUT_TO_LENGTH_CATEGORY": self.ctl_parent.pk,
        })
        result = get_category_mappings(plugin)
        self.assertIn("fabrication", result)
        self.assertIn("commercial", result)
        self.assertIn("cut_to_length", result)
        # Fabrication has descendants
        self.assertEqual(len(result["fabrication"]), 4)
        # Commercial and CTL have no descendants
        self.assertEqual(result["commercial"], [self.coml_parent.pk])
        self.assertEqual(result["cut_to_length"], [self.ctl_parent.pk])

    def test_get_category_with_invalid_id(self):
        """Test handling of invalid category ID (not in database)."""
        invalid_id = 99999
        plugin = MockPlugin({
            "FABRICATION_CATEGORY": invalid_id,
            "COMMERCIAL_CATEGORY": self.coml_parent.pk,
            "CUT_TO_LENGTH_CATEGORY": None,
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
            "CUT_TO_LENGTH_CATEGORY": None,
        })
        result = get_category_mappings(plugin)
        self.assertIn("fabrication", result)
        self.assertEqual(len(result["fabrication"]), 4)

    def test_get_category_with_invalid_string(self):
        """Test handling of invalid string category ID."""
        plugin = MockPlugin({
            "FABRICATION_CATEGORY": "not_a_number",
            "COMMERCIAL_CATEGORY": self.coml_parent.pk,
            "CUT_TO_LENGTH_CATEGORY": None,
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
            "CUT_TO_LENGTH_CATEGORY": None,
        })
        result = get_category_mappings(plugin)
        self.assertIn("fabrication", result)
        self.assertEqual(len(result["fabrication"]), 4)

    def test_get_category_with_empty_settings(self):
        """Test with no categories configured."""
        plugin = MockPlugin({
            "FABRICATION_CATEGORY": None,
            "COMMERCIAL_CATEGORY": None,
            "CUT_TO_LENGTH_CATEGORY": None,
        })
        result = get_category_mappings(plugin)
        self.assertEqual(result, {})

    def test_get_category_with_none_plugin(self):
        """Test with None plugin (test environment)."""
        result = get_category_mappings(None)
        self.assertEqual(result, {})
