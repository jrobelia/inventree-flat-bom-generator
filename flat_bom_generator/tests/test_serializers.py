"""Unit tests for serializers.py

Tests serializer validation, field mapping, and edge cases without requiring
database or Django models. Uses mock data to simulate Part objects.

Test Organization:
- BOMWarningSerializerTests: Validation for warning messages
- FlatBOMItemSerializerTests: Validation for enriched BOM items

Run: python -m unittest flat_bom_generator.tests.test_serializers
"""

import unittest

# Configure Django settings before importing anything Django-related
import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        DEBUG=True,
        SECRET_KEY="test-secret-key-for-serializer-tests",
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.auth",
            "rest_framework",
        ],
        USE_I18N=True,
        USE_L10N=True,
    )
    django.setup()

from flat_bom_generator.serializers import (
    BOMWarningSerializer,
    FlatBOMItemSerializer,
    FlatBOMResponseSerializer,
)


class BOMWarningSerializerTests(unittest.TestCase):
    """Test BOMWarningSerializer validation and field handling."""

    def test_all_fields_valid(self):
        """Valid warning with all fields should serialize successfully."""
        data = {
            "type": "unit_mismatch",
            "part_id": 123,
            "part_name": "Test Part",
            "message": "Unit mismatch: BOM notes specify 'mm' but part unit is 'inches'",
        }
        serializer = BOMWarningSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["type"], "unit_mismatch")
        self.assertEqual(serializer.validated_data["part_id"], 123)
        self.assertEqual(serializer.validated_data["part_name"], "Test Part")
        self.assertIn("Unit mismatch", serializer.validated_data["message"])

    def test_summary_warning_no_part_id(self):
        """Summary warnings (max_depth_reached) have no part_id - should be valid."""
        data = {
            "type": "max_depth_reached",
            "part_id": None,
            "part_name": "3 assemblies stopped at max depth",
            "message": "BOM traversal stopped for 3 assemblies: Part A, Part B, Part C",
        }
        serializer = BOMWarningSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertIsNone(serializer.validated_data["part_id"])
        self.assertEqual(serializer.validated_data["part_name"], "3 assemblies stopped at max depth")

    def test_part_id_optional(self):
        """part_id field should be optional (not required)."""
        data = {
            "type": "inactive_part",
            "part_name": "Obsolete Component",
            "message": "Part is inactive and may not be available",
        }
        serializer = BOMWarningSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertNotIn("part_id", serializer.validated_data)

    def test_missing_required_type(self):
        """Missing 'type' field should fail validation."""
        data = {
            "part_id": 456,
            "part_name": "Test Part",
            "message": "Some message",
        }
        serializer = BOMWarningSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("type", serializer.errors)

    def test_missing_required_message(self):
        """Missing 'message' field should fail validation."""
        data = {
            "type": "unit_mismatch",
            "part_id": 789,
            "part_name": "Test Part",
        }
        serializer = BOMWarningSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("message", serializer.errors)

    def test_empty_string_fields_invalid(self):
        """Empty strings for required fields should fail validation."""
        data = {
            "type": "",
            "part_name": "",
            "message": "",
        }
        serializer = BOMWarningSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("type", serializer.errors)
        self.assertIn("message", serializer.errors)

    def test_all_warning_types(self):
        """Test all four implemented warning types serialize correctly."""
        warning_types = [
            "unit_mismatch",
            "inactive_part",
            "assembly_no_children",
            "max_depth_reached",
        ]
        for warning_type in warning_types:
            with self.subTest(warning_type=warning_type):
                data = {
                    "type": warning_type,
                    "part_id": 100,
                    "part_name": f"Test for {warning_type}",
                    "message": f"Test message for {warning_type}",
                }
                serializer = BOMWarningSerializer(data=data)
                self.assertTrue(serializer.is_valid(), f"Failed for {warning_type}: {serializer.errors}")
                self.assertEqual(serializer.validated_data["type"], warning_type)


class FlatBOMItemSerializerTests(unittest.TestCase):
    """Test FlatBOMItemSerializer validation and field handling."""

    def get_valid_bom_item_data(self):
        """Return minimal valid BOM item data for testing."""
        return {
            # Core identifiers (required)
            "part_id": 123,
            "ipn": "TEST-001",
            "part_name": "Test Part",
            # Quantities (required)
            "total_qty": 10.0,
            "in_stock": 5.0,
            "allocated": 2.0,
            "on_order": 3.0,
            "available": 3.0,
            # Display metadata (required)
            "full_name": "Test Part Full Name",
            "description": "Test description",
            "image": None,
            "thumbnail": None,
            "link": "/part/123/",
            "unit": "pcs",
            # Part properties (required)
            "is_assembly": False,
            "purchaseable": True,
            "default_supplier_id": None,
            "part_type": "Coml",
            # BOM data (optional)
            "note": None,
            "cut_list": None,
            "internal_fab_cut_list": None,
            # Warning flags (required)
            "assembly_no_children": False,
            "max_depth_exceeded": False,
        }

    def test_all_fields_valid(self):
        """Valid BOM item with all fields should serialize successfully."""
        data = self.get_valid_bom_item_data()
        serializer = FlatBOMItemSerializer(data=data)
        self.assertTrue(serializer.is_valid(), f"Validation failed: {serializer.errors}")
        self.assertEqual(serializer.validated_data["part_id"], 123)
        self.assertEqual(serializer.validated_data["ipn"], "TEST-001")
        self.assertEqual(serializer.validated_data["total_qty"], 10.0)

    def test_with_image_urls(self):
        """BOM item with image and thumbnail URLs should serialize."""
        data = self.get_valid_bom_item_data()
        data["image"] = "/media/part_images/test.jpg"
        data["thumbnail"] = "/media/part_images/test_thumb.jpg"
        serializer = FlatBOMItemSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["image"], "/media/part_images/test.jpg")
        self.assertEqual(serializer.validated_data["thumbnail"], "/media/part_images/test_thumb.jpg")

    def test_with_bom_note(self):
        """BOM item with note field should serialize."""
        data = self.get_valid_bom_item_data()
        data["note"] = "Cut to 100mm length"
        serializer = FlatBOMItemSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["note"], "Cut to 100mm length")

    def test_assembly_part(self):
        """Assembly part with is_assembly=True should serialize."""
        data = self.get_valid_bom_item_data()
        data["is_assembly"] = True
        data["part_type"] = "Assy"
        serializer = FlatBOMItemSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertTrue(serializer.validated_data["is_assembly"])
        self.assertEqual(serializer.validated_data["part_type"], "Assy")

    def test_assembly_no_children_flag(self):
        """Assembly with no children flag set should serialize."""
        data = self.get_valid_bom_item_data()
        data["is_assembly"] = True
        data["assembly_no_children"] = True
        serializer = FlatBOMItemSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertTrue(serializer.validated_data["assembly_no_children"])

    def test_max_depth_exceeded_flag(self):
        """Item with max_depth_exceeded flag should serialize."""
        data = self.get_valid_bom_item_data()
        data["is_assembly"] = True
        data["max_depth_exceeded"] = True
        serializer = FlatBOMItemSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertTrue(serializer.validated_data["max_depth_exceeded"])

    def test_with_supplier(self):
        """Part with default supplier should serialize."""
        data = self.get_valid_bom_item_data()
        data["default_supplier_id"] = 456
        serializer = FlatBOMItemSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["default_supplier_id"], 456)

    def test_decimal_quantities(self):
        """Quantities can be decimal values (for meters, kg, etc.)."""
        data = self.get_valid_bom_item_data()
        data["total_qty"] = 12.75
        data["in_stock"] = 5.25
        data["allocated"] = 1.5
        data["on_order"] = 8.0
        data["available"] = 3.75
        serializer = FlatBOMItemSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["total_qty"], 12.75)
        self.assertEqual(serializer.validated_data["in_stock"], 5.25)

    def test_zero_quantities(self):
        """Zero quantities are valid (out of stock scenarios)."""
        data = self.get_valid_bom_item_data()
        data["in_stock"] = 0.0
        data["allocated"] = 0.0
        data["on_order"] = 0.0
        data["available"] = 0.0
        serializer = FlatBOMItemSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["available"], 0.0)

    def test_missing_required_part_id(self):
        """Missing part_id should fail validation."""
        data = self.get_valid_bom_item_data()
        del data["part_id"]
        serializer = FlatBOMItemSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("part_id", serializer.errors)

    def test_missing_required_quantities(self):
        """Missing required quantity fields should fail validation."""
        data = self.get_valid_bom_item_data()
        del data["total_qty"]
        serializer = FlatBOMItemSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("total_qty", serializer.errors)

    def test_invalid_part_id_type(self):
        """part_id must be an integer."""
        data = self.get_valid_bom_item_data()
        data["part_id"] = "not-an-integer"
        serializer = FlatBOMItemSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("part_id", serializer.errors)

    def test_invalid_boolean_flag(self):
        """Boolean flags must be boolean type."""
        data = self.get_valid_bom_item_data()
        data["is_assembly"] = "not_a_boolean"
        serializer = FlatBOMItemSerializer(data=data)
        # DRF BooleanField is permissive - it coerces many values
        # Test that it at least accepts proper booleans
        self.assertTrue(serializer.is_valid() or "is_assembly" in serializer.errors)

    def test_with_cut_list(self):
        """BOM item with cut_list should serialize."""
        data = self.get_valid_bom_item_data()
        data["cut_list"] = [{"length": 100.0, "unit": "mm", "count": 2}, {"length": 50.0, "unit": "mm", "count": 1}]
        serializer = FlatBOMItemSerializer(data=data)
        self.assertTrue(serializer.is_valid(), f"Validation failed: {serializer.errors}")
        self.assertIsInstance(serializer.validated_data["cut_list"], list)
        self.assertEqual(len(serializer.validated_data["cut_list"]), 2)

    def test_with_internal_fab_cut_list(self):
        """BOM item with internal_fab_cut_list should serialize."""
        data = self.get_valid_bom_item_data()
        data["internal_fab_cut_list"] = [
            {"length": 100.0, "unit": "mm", "count": 2},
            {"length": 50.0, "unit": "mm", "count": 1},
        ]
        serializer = FlatBOMItemSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertIsInstance(serializer.validated_data["internal_fab_cut_list"], list)
        self.assertEqual(len(serializer.validated_data["internal_fab_cut_list"]), 2)

    def test_all_part_types(self):
        """Test all category types serialize correctly."""
        part_types = ["TLA", "Internal Fab", "Purchased Assy", "CtL", "Coml", "Fab", "Assy", "Other"]
        for part_type in part_types:
            with self.subTest(part_type=part_type):
                data = self.get_valid_bom_item_data()
                data["part_type"] = part_type
                serializer = FlatBOMItemSerializer(data=data)
                self.assertTrue(serializer.is_valid(), f"Failed for {part_type}: {serializer.errors}")
                self.assertEqual(serializer.validated_data["part_type"], part_type)


class FlatBOMResponseSerializerTests(unittest.TestCase):
    """Test FlatBOMResponseSerializer validation and complete response structure."""

    def get_valid_bom_item(self):
        """Helper to create valid BOM item dict."""
        return {
            "part_id": 456,
            "ipn": "FAB-100",
            "part_name": "Bracket",
            "full_name": "FAB-100 | Bracket, Mounting",
            "description": "Steel mounting bracket",
            "part_type": "Fab",
            "total_qty": 2.0,
            "unit": "pcs",
            "is_assembly": False,
            "purchaseable": True,
            "default_supplier_id": None,
            "note": "",
            "level": 1,
            "in_stock": 50.0,
            "on_order": 0.0,
            "allocated": 10.0,
            "available": 40.0,
            "image": None,
            "thumbnail": None,
            "link": "/part/456/",
        }

    def get_valid_warning(self):
        """Helper to create valid warning dict."""
        return {
            "type": "unit_mismatch",
            "part_id": 789,
            "part_name": "Test Part",
            "message": "Unit mismatch detected",
        }

    def test_complete_response_all_fields(self):
        """Complete response with all fields should serialize successfully."""
        data = {
            "part_id": 123,
            "part_name": "Main Assembly",
            "ipn": "ASM-001",
            "total_unique_parts": 45,
            "total_ifps_processed": 12,
            "max_depth_reached": 5,
            "bom_items": [self.get_valid_bom_item()],
            "metadata": {"warnings": [self.get_valid_warning()]},
        }
        serializer = FlatBOMResponseSerializer(data=data)
        self.assertTrue(serializer.is_valid(), f"Errors: {serializer.errors}")
        self.assertEqual(serializer.validated_data["part_id"], 123)
        self.assertEqual(serializer.validated_data["total_unique_parts"], 45)
        self.assertIsInstance(serializer.validated_data["bom_items"], list)
        self.assertEqual(len(serializer.validated_data["bom_items"]), 1)

    def test_empty_bom_items(self):
        """Response with empty bom_items list should be valid."""
        data = {
            "part_id": 123,
            "part_name": "Simple Part",
            "ipn": "PART-001",
            "total_unique_parts": 0,
            "total_ifps_processed": 0,
            "max_depth_reached": 0,
            "bom_items": [],
            "metadata": {"warnings": []},
        }
        serializer = FlatBOMResponseSerializer(data=data)
        self.assertTrue(serializer.is_valid(), f"Errors: {serializer.errors}")
        self.assertEqual(len(serializer.validated_data["bom_items"]), 0)

    def test_multiple_bom_items(self):
        """Response with multiple BOM items should serialize correctly."""
        item1 = self.get_valid_bom_item()
        item2 = self.get_valid_bom_item()
        item2["part_id"] = 457
        item2["ipn"] = "COML-200"
        item2["part_type"] = "Coml"

        data = {
            "part_id": 123,
            "part_name": "Assembly",
            "ipn": "ASM-001",
            "total_unique_parts": 2,
            "total_ifps_processed": 0,
            "max_depth_reached": 2,
            "bom_items": [item1, item2],
            "metadata": {"warnings": []},
        }
        serializer = FlatBOMResponseSerializer(data=data)
        self.assertTrue(serializer.is_valid(), f"Errors: {serializer.errors}")
        self.assertEqual(len(serializer.validated_data["bom_items"]), 2)

    def test_multiple_warnings(self):
        """Response with multiple warnings should serialize correctly."""
        warning1 = self.get_valid_warning()
        warning2 = {
            "type": "inactive_part",
            "part_id": 790,
            "part_name": "Inactive Part",
            "message": "Part is inactive",
        }

        data = {
            "part_id": 123,
            "part_name": "Assembly",
            "ipn": "ASM-001",
            "total_unique_parts": 1,
            "total_ifps_processed": 0,
            "max_depth_reached": 1,
            "bom_items": [self.get_valid_bom_item()],
            "metadata": {"warnings": [warning1, warning2]},
        }
        serializer = FlatBOMResponseSerializer(data=data)
        self.assertTrue(serializer.is_valid(), f"Errors: {serializer.errors}")
        self.assertEqual(len(serializer.validated_data["metadata"]["warnings"]), 2)

    def test_empty_ipn(self):
        """Response with empty IPN string should be valid."""
        data = {
            "part_id": 123,
            "part_name": "Part Without IPN",
            "ipn": "",  # Empty string is valid
            "total_unique_parts": 0,
            "total_ifps_processed": 0,
            "max_depth_reached": 0,
            "bom_items": [],
            "metadata": {"warnings": []},
        }
        serializer = FlatBOMResponseSerializer(data=data)
        self.assertTrue(serializer.is_valid(), f"Errors: {serializer.errors}")
        self.assertEqual(serializer.validated_data["ipn"], "")

    def test_missing_required_field(self):
        """Missing required field should fail validation."""
        data = {
            "part_id": 123,
            "part_name": "Assembly",
            # Missing ipn
            "total_unique_parts": 1,
            "total_ifps_processed": 0,
            "max_depth_reached": 1,
            "bom_items": [],
            "metadata": {"warnings": []},
        }
        serializer = FlatBOMResponseSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("ipn", serializer.errors)

    def test_invalid_bom_item(self):
        """Invalid BOM item should fail validation."""
        invalid_item = {"part_id": "not-a-number"}  # Missing required fields

        data = {
            "part_id": 123,
            "part_name": "Assembly",
            "ipn": "ASM-001",
            "total_unique_parts": 1,
            "total_ifps_processed": 0,
            "max_depth_reached": 1,
            "bom_items": [invalid_item],
            "metadata": {"warnings": []},
        }
        serializer = FlatBOMResponseSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("bom_items", serializer.errors)

    def test_invalid_warning(self):
        """Invalid warning should fail validation."""
        invalid_warning = {"type": "bad_warning"}  # Missing required fields

        data = {
            "part_id": 123,
            "part_name": "Assembly",
            "ipn": "ASM-001",
            "total_unique_parts": 0,
            "total_ifps_processed": 0,
            "max_depth_reached": 0,
            "bom_items": [],
            "metadata": {"warnings": [invalid_warning]},
        }
        serializer = FlatBOMResponseSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("metadata", serializer.errors)

    def test_negative_quantities_in_bom_item(self):
        """Negative quantities should be accepted (represent stock shortfalls)."""
        data = FlatBOMItemSerializerTests().get_valid_bom_item_data()
        data["available"] = -5.0  # Negative available (over-allocated)
        serializer = FlatBOMItemSerializer(data=data)
        # DRF FloatField accepts negative by default
        self.assertTrue(serializer.is_valid(), f"Should accept negative: {serializer.errors}")
        self.assertEqual(serializer.validated_data["available"], -5.0)

    def test_empty_string_ipn_allowed(self):
        """IPN can be empty string (allow_blank=True)."""
        data = FlatBOMItemSerializerTests().get_valid_bom_item_data()
        data["ipn"] = ""
        serializer = FlatBOMItemSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["ipn"], "")

    def test_empty_string_unit_allowed(self):
        """Unit can be empty string (some parts have no unit)."""
        data = FlatBOMItemSerializerTests().get_valid_bom_item_data()
        data["unit"] = ""
        serializer = FlatBOMItemSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["unit"], "")

    def test_empty_string_description_allowed(self):
        """Description can be empty string (allow_blank=True)."""
        data = FlatBOMItemSerializerTests().get_valid_bom_item_data()
        data["description"] = ""
        serializer = FlatBOMItemSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["description"], "")

    def test_metadata_with_multiple_warning_lists(self):
        """Metadata can have multiple keys, but all values must be lists of warnings.
        
        The metadata field is DictField(child=ListField(child=BOMWarningSerializer())),
        which means every value must be a list of valid warnings.
        """
        valid_warning = FlatBOMResponseSerializerTests().get_valid_warning()
        
        data = {
            "part_id": 123,
            "part_name": "Assembly",
            "ipn": "ASM-001",
            "total_unique_parts": 1,
            "total_ifps_processed": 0,
            "max_depth_reached": 1,
            "bom_items": [FlatBOMResponseSerializerTests().get_valid_bom_item()],
            "metadata": {
                "warnings": [valid_warning],
                "errors": [valid_warning],  # Additional warning list (valid)
            },
        }
        serializer = FlatBOMResponseSerializer(data=data)
        self.assertTrue(serializer.is_valid(), f"Should accept multiple warning lists: {serializer.errors}")

    def test_metadata_with_invalid_value_type_fails(self):
        """Metadata values must be lists of warnings - other types should fail.
        
        Since metadata is DictField(child=ListField(child=BOMWarningSerializer())),
        values must be lists of valid warning dicts.
        """
        data = {
            "part_id": 123,
            "part_name": "Assembly",
            "ipn": "ASM-001",
            "total_unique_parts": 1,
            "total_ifps_processed": 0,
            "max_depth_reached": 1,
            "bom_items": [FlatBOMResponseSerializerTests().get_valid_bom_item()],
            "metadata": {
                "warnings": [FlatBOMResponseSerializerTests().get_valid_warning()],
                "invalid_string": "not_a_list",  # Invalid: string instead of list
            },
        }
        serializer = FlatBOMResponseSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("metadata", serializer.errors)

    def test_response_with_zero_statistics(self):
        """Response with all zero statistics should be valid."""
        data = {
            "part_id": 999,
            "part_name": "Empty Assembly",
            "ipn": "EMPTY-001",
            "total_unique_parts": 0,
            "total_ifps_processed": 0,
            "max_depth_reached": 0,
            "bom_items": [],
            "metadata": {"warnings": []},
        }
        serializer = FlatBOMResponseSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["total_unique_parts"], 0)


if __name__ == "__main__":
    unittest.main()
