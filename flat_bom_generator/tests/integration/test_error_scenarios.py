"""
Integration tests for error scenarios in FlatBOMGenerator.

Tests database exceptions, invalid query parameters, and graceful degradation
when plugin settings are missing or invalid.

Code-first validated: January 10, 2026
"""

import logging
from unittest.mock import Mock

from company.models import Company
from InvenTree.unit_test import InvenTreeTestCase
from part.models import Part, PartCategory
from rest_framework import status
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from flat_bom_generator.views import (
    FlatBOMView,
    get_category_mappings,
    get_internal_supplier_ids,
)


class DatabaseExceptionTests(InvenTreeTestCase):
    """Test error handling for database exceptions."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.factory = APIRequestFactory()
        self.view = FlatBOMView()

    def test_part_does_not_exist(self):
        """Test response when part_id doesn't exist in database."""
        # Part ID 999999 should not exist
        django_request = self.factory.get("/fake-url/999999/")
        django_request.user = self.user
        request = Request(django_request)
        self.view.request = request

        response = self.view.get(request, part_id=999999)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["error"], "Part not found")

    def test_part_is_not_assembly(self):
        """Test response when part exists but is not an assembly."""
        # Create a non-assembly part
        part = Part.objects.create(
            name="Non-Assembly Part",
            description="Test part",
            assembly=False,  # Not an assembly
            active=True,
        )

        django_request = self.factory.get(f"/fake-url/{part.pk}/")
        django_request.user = self.user
        request = Request(django_request)
        self.view.request = request

        response = self.view.get(request, part_id=part.pk)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Part is not an assembly")

    def test_invalid_category_id_in_get_category_mappings(self):
        """Test that invalid category IDs are handled gracefully."""
        # Create mock plugin with invalid category ID
        mock_plugin = Mock()
        mock_plugin.get_setting.side_effect = lambda key, default=None: {
            "FABRICATION_CATEGORY": 999999,  # Non-existent category
            "COMMERCIAL_CATEGORY": None,
            "CUT_TO_LENGTH_CATEGORY": None,
        }.get(key, default)

        # Should not raise exception, should log warning and skip
        result = get_category_mappings(mock_plugin)

        # Should return empty mappings (invalid category skipped)
        self.assertEqual(result, {})

    def test_deleted_category_in_get_category_mappings(self):
        """Test graceful handling when category is deleted after configuration."""
        # Create a category, configure it, then delete it
        category = PartCategory.objects.create(name="Test Category")
        category_id = category.pk
        category.delete()

        # Create mock plugin with deleted category ID
        mock_plugin = Mock()
        mock_plugin.get_setting.side_effect = lambda key, default=None: {
            "FABRICATION_CATEGORY": category_id,
            "COMMERCIAL_CATEGORY": None,
            "CUT_TO_LENGTH_CATEGORY": None,
        }.get(key, default)

        # Should not raise exception
        result = get_category_mappings(mock_plugin)

        # Should return empty mappings
        self.assertEqual(result, {})


class InvalidQueryParameterTests(InvenTreeTestCase):
    """Test error handling for invalid query parameters."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.factory = APIRequestFactory()
        self.view = FlatBOMView()

        # Create a test assembly
        self.assembly = Part.objects.create(
            name="Test Assembly", description="Test assembly", assembly=True, active=True
        )

    def test_non_integer_max_depth(self):
        """Test that non-integer max_depth returns 400 error."""
        django_request = self.factory.get(f"/fake-url/{self.assembly.pk}/?max_depth=invalid")
        django_request.user = self.user
        request = Request(django_request)
        self.view.request = request

        response = self.view.get(request, part_id=self.assembly.pk)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Invalid max_depth parameter")

    def test_float_max_depth(self):
        """Test that float max_depth returns 400 error."""
        django_request = self.factory.get(f"/fake-url/{self.assembly.pk}/?max_depth=3.5")
        django_request.user = self.user
        request = Request(django_request)
        self.view.request = request

        response = self.view.get(request, part_id=self.assembly.pk)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Invalid max_depth parameter")

    def test_negative_part_id(self):
        """Test that negative part_id returns 404 (doesn't exist)."""
        django_request = self.factory.get("/fake-url/-1/")
        django_request.user = self.user
        request = Request(django_request)
        self.view.request = request

        response = self.view.get(request, part_id=-1)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["error"], "Part not found")

    def test_zero_part_id(self):
        """Test that part_id=0 returns 404 (doesn't exist)."""
        django_request = self.factory.get("/fake-url/0/")
        django_request.user = self.user
        request = Request(django_request)
        self.view.request = request

        response = self.view.get(request, part_id=0)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["error"], "Part not found")


class EmptyPluginSettingsTests(InvenTreeTestCase):
    """Test graceful degradation when plugin settings are empty or None."""

    def test_get_internal_supplier_ids_with_none_plugin(self):
        """Test that None plugin returns empty list."""
        result = get_internal_supplier_ids(None)

        self.assertEqual(result, [])
        self.assertIsInstance(result, list)

    def test_get_internal_supplier_ids_with_no_settings(self):
        """Test that empty settings return empty list."""
        mock_plugin = Mock()
        mock_plugin.get_setting.return_value = None

        result = get_internal_supplier_ids(mock_plugin)

        self.assertEqual(result, [])

    def test_get_internal_supplier_ids_with_empty_string(self):
        """Test that empty string settings return empty list."""
        mock_plugin = Mock()
        mock_plugin.get_setting.side_effect = lambda key, default=None: {
            "PRIMARY_INTERNAL_SUPPLIER": "",
            "ADDITIONAL_INTERNAL_SUPPLIERS": "",
        }.get(key, default)

        result = get_internal_supplier_ids(mock_plugin)

        self.assertEqual(result, [])

    def test_get_internal_supplier_ids_with_invalid_company_ids(self):
        """Test that invalid company IDs are filtered out."""
        mock_plugin = Mock()
        mock_plugin.get_setting.side_effect = lambda key, default=None: {
            "PRIMARY_INTERNAL_SUPPLIER": 999999,  # Non-existent
            "ADDITIONAL_INTERNAL_SUPPLIERS": "999998,999997",  # Also non-existent
        }.get(key, default)

        result = get_internal_supplier_ids(mock_plugin)

        # Should validate against database and return empty list
        self.assertEqual(result, [])

    def test_get_internal_supplier_ids_mixed_valid_invalid(self):
        """Test that only valid IDs are returned when mixed with invalid."""
        # Create one valid company
        company = Company.objects.create(name="Test Company", is_supplier=True)

        mock_plugin = Mock()
        mock_plugin.get_setting.side_effect = lambda key, default=None: {
            "PRIMARY_INTERNAL_SUPPLIER": company.pk,  # Valid
            "ADDITIONAL_INTERNAL_SUPPLIERS": f"{company.pk},999999",  # Valid + Invalid
        }.get(key, default)

        result = get_internal_supplier_ids(mock_plugin)

        # Should return only the valid company ID (deduplicated)
        self.assertEqual(result, [company.pk])

    def test_get_category_mappings_with_none_plugin(self):
        """Test that None plugin returns empty dict."""
        result = get_category_mappings(None)

        self.assertEqual(result, {})
        self.assertIsInstance(result, dict)

    def test_get_category_mappings_with_no_settings(self):
        """Test that empty settings return empty dict."""
        mock_plugin = Mock()
        mock_plugin.get_setting.return_value = None

        result = get_category_mappings(mock_plugin)

        self.assertEqual(result, {})

    def test_get_category_mappings_with_empty_string_settings(self):
        """Test that empty string settings return empty dict."""
        mock_plugin = Mock()
        mock_plugin.get_setting.side_effect = lambda key, default=None: {
            "FABRICATION_CATEGORY": "",
            "COMMERCIAL_CATEGORY": "",
            "CUT_TO_LENGTH_CATEGORY": "",
        }.get(key, default)

        result = get_category_mappings(mock_plugin)

        self.assertEqual(result, {})

    def test_get_category_mappings_partially_configured(self):
        """Test that only configured categories are returned."""
        # Create one category
        category = PartCategory.objects.create(name="Test Category")

        mock_plugin = Mock()
        mock_plugin.get_setting.side_effect = lambda key, default=None: {
            "FABRICATION_CATEGORY": category.pk,  # Configured
            "COMMERCIAL_CATEGORY": None,  # Not configured
            "CUT_TO_LENGTH_CATEGORY": "",  # Empty string
        }.get(key, default)

        result = get_category_mappings(mock_plugin)

        # Should return only fabrication mapping
        self.assertIn("fabrication", result)
        self.assertNotIn("commercial", result)
        self.assertNotIn("cut_to_length", result)
        self.assertEqual(result["fabrication"], [category.pk])


class LoggingAndExceptionHandlingTests(InvenTreeTestCase):
    """Test that errors are logged appropriately without breaking functionality."""

    def setUp(self):
        """Set up test data and logging capture."""
        super().setUp()
        # Capture log output
        self.logger = logging.getLogger("inventree")

    def test_invalid_string_supplier_id_logs_warning(self):
        """Test that invalid string supplier ID logs warning."""
        mock_plugin = Mock()
        mock_plugin.get_setting.side_effect = lambda key, default=None: {
            "PRIMARY_INTERNAL_SUPPLIER": "not_a_number",
            "ADDITIONAL_INTERNAL_SUPPLIERS": "",
        }.get(key, default)

        with self.assertLogs("inventree", level="WARNING") as cm:
            result = get_internal_supplier_ids(mock_plugin)

        # Should return empty list
        self.assertEqual(result, [])

        # Should have logged warning
        self.assertTrue(
            any(
                "has invalid string value" in message and "not_a_number" in message
                for message in cm.output
            ),
            f"Expected warning about 'not_a_number' not found in logs: {cm.output}",
        )

    def test_invalid_string_category_id_logs_warning(self):
        """Test that invalid string category ID logs warning and continues."""
        mock_plugin = Mock()
        mock_plugin.get_setting.side_effect = lambda key, default=None: {
            "FABRICATION_CATEGORY": "invalid_id",
            "COMMERCIAL_CATEGORY": None,
            "CUT_TO_LENGTH_CATEGORY": None,
        }.get(key, default)

        with self.assertLogs("inventree", level="WARNING") as cm:
            result = get_category_mappings(mock_plugin)

        # Should return empty dict (invalid category skipped)
        self.assertEqual(result, {})

        # Should have logged warning
        self.assertTrue(
            any(
                "has invalid string value" in message and "invalid_id" in message
                for message in cm.output
            ),
            f"Expected warning about 'invalid_id' not found in logs: {cm.output}",
        )

    def test_deleted_category_logs_warning(self):
        """Test that deleted category logs warning message and continues."""
        # Create and delete a category
        category = PartCategory.objects.create(name="Test Category")
        category_id = category.pk
        category.delete()

        mock_plugin = Mock()
        mock_plugin.get_setting.side_effect = lambda key, default=None: {
            "FABRICATION_CATEGORY": category_id,
            "COMMERCIAL_CATEGORY": None,
            "CUT_TO_LENGTH_CATEGORY": None,
        }.get(key, default)

        with self.assertLogs("inventree", level="WARNING") as cm:
            result = get_category_mappings(mock_plugin)

        # Should return empty dict
        self.assertEqual(result, {})

        # Should have logged warning about category not existing
        self.assertTrue(
            any("does not exist" in message and str(category_id) in message for message in cm.output),
            f"Expected warning about category {category_id} not existing not found in logs: {cm.output}",
        )
