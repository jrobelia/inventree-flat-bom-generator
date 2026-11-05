"""
Unit tests for categorization module.

Tests display-label assignment (categorize_part) and the unit-mismatch
helpers. categorize_part assigns labels only - it does not decide expansion
or line-item membership; those live in bom_traversal.
"""

import unittest
from flat_bom_generator.categorization import (
    _extract_length_with_unit,
    _check_unit_mismatch,
    categorize_part,
)


class CategorizePartTests(unittest.TestCase):
    """Test categorize_part display-label assignment."""

    def test_top_level_assembly(self):
        """Top level part always returns TLA regardless of other parameters"""
        result = categorize_part(
            part_name="Top Level Part",
            is_assembly=True,
            is_top_level=True,
            default_supplier_id=5,
            supplier_is_internal=True,
            part_category_id=20,
            category_mappings={"fabrication": [20]},
        )
        self.assertEqual(result, "TLA")

    def test_internal_fab_assembly(self):
        """Assembly with internal primary supplier returns Internal Fab"""
        result = categorize_part(
            part_name="Internal Fab Part",
            is_assembly=True,
            is_top_level=False,
            default_supplier_id=10,
            supplier_is_internal=True,
        )
        self.assertEqual(result, "Internal Fab")

    def test_internal_fab_does_not_require_fabrication_category(self):
        """Internal Fab is driven by supplier.is_internal alone, not categories"""
        result = categorize_part(
            part_name="Internal Fab Part",
            is_assembly=True,
            is_top_level=False,
            default_supplier_id=10,
            supplier_is_internal=True,
            part_category_id=50,
            category_mappings={"commercial": [50]},
        )
        self.assertEqual(result, "Internal Fab")

    def test_purchased_assembly(self):
        """Assembly with external primary supplier returns Purchased Assy"""
        result = categorize_part(
            part_name="Purchased Assembly",
            is_assembly=True,
            is_top_level=False,
            default_supplier_id=20,
            supplier_is_internal=False,
            part_category_id=5,
        )
        self.assertEqual(result, "Purchased Assy")

    def test_purchased_assembly_in_fab_category(self):
        """Fab-category assembly with external supplier is Purchased Assy, not Internal Fab"""
        result = categorize_part(
            part_name="Fab Assembly External",
            is_assembly=True,
            is_top_level=False,
            default_supplier_id=99,
            supplier_is_internal=False,
            part_category_id=5,
            category_mappings={"fabrication": [5]},
        )
        self.assertEqual(result, "Purchased Assy")

    def test_assembly_no_default_supplier(self):
        """Assembly with no primary supplier returns 'Assy'."""
        result = categorize_part(
            part_name="Assembly No Supplier",
            is_assembly=True,
            is_top_level=False,
            default_supplier_id=None,
            part_category_id=5,
            category_mappings={"fabrication": [5]},
        )
        self.assertEqual(result, "Assy")

    def test_commercial_part(self):
        """Non-assembly in Commercial category returns Coml"""
        result = categorize_part(
            part_name="Screw",
            is_assembly=False,
            is_top_level=False,
            part_category_id=40,
            category_mappings={"commercial": [40, 41]},
        )
        self.assertEqual(result, "Coml")

    def test_fabrication_part(self):
        """Non-assembly in Fabrication category returns Fab"""
        result = categorize_part(
            part_name="Bracket",
            is_assembly=False,
            is_top_level=False,
            part_category_id=5,
            category_mappings={"fabrication": [5, 12]},
        )
        self.assertEqual(result, "Fab")

    def test_category_hierarchy(self):
        """Category mappings include parent and children IDs"""
        # Part in child category should match
        result = categorize_part(
            part_name="Child Part",
            is_assembly=False,
            is_top_level=False,
            part_category_id=12,  # Child category
            category_mappings={"fabrication": [5, 12, 13]},  # Parent + children
        )
        self.assertEqual(result, "Fab")

    def test_no_match_other(self):
        """Part with no matching criteria returns Other"""
        result = categorize_part(
            part_name="Unknown Part",
            is_assembly=False,
            is_top_level=False,
            part_category_id=999,
            category_mappings={"commercial": [40]},
        )
        self.assertEqual(result, "Other")

    def test_empty_defaults(self):
        """Function handles None/empty defaults gracefully"""
        result = categorize_part(
            part_name="Part",
            is_assembly=False,
            is_top_level=False,
        )
        self.assertEqual(result, "Other")

    def test_part_with_category_but_empty_mappings(self):
        """Part with category_id but empty category_mappings returns 'Other'."""
        result = categorize_part(
            part_name="Unknown Part",
            is_assembly=False,
            is_top_level=False,
            part_category_id=15,
            category_mappings={},  # Empty mappings
        )
        self.assertEqual(result, "Other")

    def test_non_assembly_label_ignores_supplier(self):
        """Non-assembly parts label from category - supplier flags are irrelevant"""
        result = categorize_part(
            part_name="Screw",
            is_assembly=False,
            is_top_level=False,
            default_supplier_id=10,
            supplier_is_internal=True,
            part_category_id=40,
            category_mappings={"commercial": [40]},
        )
        self.assertEqual(result, "Coml")


class ExtractLengthWithUnitTests(unittest.TestCase):
    """Test _extract_length_with_unit function."""

    def test_number_with_mm(self):
        """Extract value and unit: '100mm' -> {value: 100.0, unit: 'mm'}"""
        result = _extract_length_with_unit("100mm")
        self.assertEqual(result["value"], 100.0)
        self.assertEqual(result["unit"], "mm")

    def test_number_with_space_and_unit(self):
        """Extract value and unit with space: '50.5 inches' -> {value: 50.5, unit: 'inches'}"""
        result = _extract_length_with_unit("50.5 inches")
        self.assertEqual(result["value"], 50.5)
        self.assertEqual(result["unit"], "inches")

    def test_number_with_cm(self):
        """Extract centimeters: '25cm' -> {value: 25.0, unit: 'cm'}"""
        result = _extract_length_with_unit("25cm")
        self.assertEqual(result["value"], 25.0)
        self.assertEqual(result["unit"], "cm")

    def test_number_with_meters(self):
        """Extract meters: '5m' -> {value: 5.0, unit: 'm'}"""
        result = _extract_length_with_unit("5m")
        self.assertEqual(result["value"], 5.0)
        self.assertEqual(result["unit"], "m")

    def test_number_with_feet(self):
        """Extract feet: '10ft' -> {value: 10.0, unit: 'ft'}"""
        result = _extract_length_with_unit("10ft")
        self.assertEqual(result["value"], 10.0)
        self.assertEqual(result["unit"], "ft")

    def test_number_without_unit(self):
        """Number without unit: '100' -> {value: 100.0, unit: None}"""
        result = _extract_length_with_unit("100")
        self.assertEqual(result["value"], 100.0)
        self.assertIsNone(result["unit"])

    def test_text_before_number(self):
        """Handles text before number: 'Cut 12mm from stock' -> {value: 12.0, unit: 'mm'}"""
        result = _extract_length_with_unit("Cut 12mm from stock")
        self.assertEqual(result["value"], 12.0)
        self.assertEqual(result["unit"], "mm")

    def test_ignores_later_units(self):
        """Ignores units not adjacent to first number: '100mm from 12 inch stock' -> {value: 100.0, unit: 'mm'}"""
        result = _extract_length_with_unit("100mm from 12 inch stock")
        self.assertEqual(result["value"], 100.0)
        self.assertEqual(result["unit"], "mm")

    def test_case_insensitive(self):
        """Units are case-insensitive: '100MM' -> {value: 100.0, unit: 'mm'}"""
        result = _extract_length_with_unit("100MM")
        self.assertEqual(result["value"], 100.0)
        self.assertEqual(result["unit"], "mm")

    def test_plural_units(self):
        """Handles plural units: '5 millimeters' -> {value: 5.0, unit: 'millimeters'}"""
        result = _extract_length_with_unit("5 millimeters")
        self.assertEqual(result["value"], 5.0)
        self.assertEqual(result["unit"], "millimeters")

    def test_empty_string(self):
        """Empty string returns None for both: '' -> {value: None, unit: None}"""
        result = _extract_length_with_unit("")
        self.assertIsNone(result["value"])
        self.assertIsNone(result["unit"])

    def test_no_numbers(self):
        """No numbers returns None: 'No numbers here' -> {value: None, unit: None}"""
        result = _extract_length_with_unit("No numbers here")
        self.assertIsNone(result["value"])
        self.assertIsNone(result["unit"])


class CheckUnitMismatchTests(unittest.TestCase):
    """Test _check_unit_mismatch function."""

    def test_matching_units(self):
        """No warning when units match: '100mm' with part unit 'mm'"""
        result = _check_unit_mismatch("100mm", "mm")
        self.assertIsNone(result)

    def test_mismatched_units(self):
        """Warning when units mismatch: '100mm' with part unit 'inches'"""
        result = _check_unit_mismatch("100mm", "inches")
        self.assertIsNotNone(result)
        self.assertIn("mm", result)
        self.assertIn("inches", result)

    def test_no_unit_in_notes(self):
        """No warning when notes have no unit: '100' with part unit 'mm'"""
        result = _check_unit_mismatch("100", "mm")
        self.assertIsNone(result)

    def test_empty_notes(self):
        """No warning for empty notes"""
        result = _check_unit_mismatch("", "mm")
        self.assertIsNone(result)

    def test_no_part_unit(self):
        """No warning when part has no unit"""
        result = _check_unit_mismatch("100mm", None)
        self.assertIsNone(result)

    def test_case_insensitive_match(self):
        """Units match case-insensitively: '100MM' with part unit 'mm'"""
        result = _check_unit_mismatch("100MM", "mm")
        self.assertIsNone(result)

    def test_ignores_irrelevant_units(self):
        """Ignores units not near number: '100mm from 12 inch stock' with part unit 'mm'"""
        result = _check_unit_mismatch("100mm from 12 inch stock", "mm")
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
