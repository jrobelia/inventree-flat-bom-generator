"""
Unit tests for categorization module.

Tests the categorization logic and helper functions that determine
how parts are categorized in the flat BOM.
"""

import unittest
from flat_bom_generator.categorization import _extract_length_from_notes, categorize_part


class ExtractLengthFromNotesTests(unittest.TestCase):
    """Test _extract_length_from_notes function."""

    def test_simple_integer(self):
        """Test simple integer value: '100' -> 100.0"""
        result = _extract_length_from_notes("100")
        self.assertEqual(result, 100.0)

    def test_integer_with_unit(self):
        """Test integer with unit: '100mm' -> 100.0"""
        result = _extract_length_from_notes("100mm")
        self.assertEqual(result, 100.0)

    def test_float_value(self):
        """Test float value: '50.5' -> 50.5"""
        result = _extract_length_from_notes("50.5")
        self.assertEqual(result, 50.5)

    def test_float_with_unit(self):
        """Test float with unit: '12.75 inches' -> 12.75"""
        result = _extract_length_from_notes("12.75 inches")
        self.assertEqual(result, 12.75)

    def test_length_prefix(self):
        """Test with 'Length:' prefix: 'Length: 50.5' -> 50.5"""
        result = _extract_length_from_notes("Length: 50.5")
        self.assertEqual(result, 50.5)

    def test_cut_to_prefix(self):
        """Test with 'Cut to' prefix: 'Cut to 12.75 inches' -> 12.75"""
        result = _extract_length_from_notes("Cut to 12.75 inches")
        self.assertEqual(result, 12.75)

    def test_decimal_without_leading_digit(self):
        """Test decimal without leading digit: '.45' -> 0.45"""
        result = _extract_length_from_notes(".45")
        self.assertEqual(result, 0.45)

    def test_empty_string(self):
        """Test empty string returns None"""
        result = _extract_length_from_notes("")
        self.assertIsNone(result)

    def test_none_input(self):
        """Test None input returns None"""
        result = _extract_length_from_notes(None)
        self.assertIsNone(result)

    def test_non_numeric_text(self):
        """Test non-numeric text returns None"""
        result = _extract_length_from_notes("No numbers here")
        self.assertIsNone(result)

    def test_only_letters_and_symbols(self):
        """Test text with only letters and symbols returns None"""
        result = _extract_length_from_notes("ABC-XYZ")
        self.assertIsNone(result)

    def test_extracts_first_number(self):
        """Test that first number is extracted when multiple numbers present"""
        result = _extract_length_from_notes("Cut 25.5mm from 100mm stock")
        self.assertEqual(result, 25.5)

    def test_whitespace_handling(self):
        """Test whitespace before/after is handled: '  100  ' -> 100.0"""
        result = _extract_length_from_notes("  100  ")
        self.assertEqual(result, 100.0)

    def test_large_number(self):
        """Test large number: '999999.99' -> 999999.99"""
        result = _extract_length_from_notes("999999.99")
        self.assertEqual(result, 999999.99)

    def test_zero(self):
        """Test zero value: '0' -> 0.0"""
        result = _extract_length_from_notes("0")
        self.assertEqual(result, 0.0)


class CategorizePartTests(unittest.TestCase):
    """Test categorize_part function."""

    def test_top_level_assembly(self):
        """Top level part always returns TLA regardless of other parameters"""
        result = categorize_part(
            part_name="Top Level Part",
            is_assembly=True,
            is_top_level=True,
            default_supplier_id=5,
            internal_supplier_ids=[10],
            part_category_id=20,
            category_mappings={"fabrication": [20]},
        )
        self.assertEqual(result, "TLA")

    def test_internal_fab_assembly(self):
        """Assembly in Fabrication category with internal supplier returns Internal Fab"""
        result = categorize_part(
            part_name="Internal Fab Part",
            is_assembly=True,
            is_top_level=False,
            default_supplier_id=10,
            internal_supplier_ids=[10, 15],
            part_category_id=5,
            category_mappings={"fabrication": [5, 12]},
        )
        self.assertEqual(result, "Internal Fab")

    def test_purchased_assembly(self):
        """Assembly with external supplier returns Purchased Assy"""
        result = categorize_part(
            part_name="Purchased Assembly",
            is_assembly=True,
            is_top_level=False,
            default_supplier_id=20,
            internal_supplier_ids=[10, 15],
            part_category_id=5,
        )
        self.assertEqual(result, "Purchased Assy")

    def test_cut_to_length_with_valid_notes(self):
        """Non-assembly in CtL category with length in notes returns CtL"""
        result = categorize_part(
            part_name="Tubing",
            is_assembly=False,
            is_top_level=False,
            part_category_id=30,
            category_mappings={"cut_to_length": [30]},
            bom_item_notes="100mm",
        )
        self.assertEqual(result, "CtL")

    def test_cut_to_length_without_valid_notes(self):
        """CtL category part without length in notes falls back to Fab"""
        result = categorize_part(
            part_name="Tubing",
            is_assembly=False,
            is_top_level=False,
            part_category_id=30,
            category_mappings={"cut_to_length": [30]},
            bom_item_notes="See drawing",
        )
        self.assertEqual(result, "Fab")

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

    def test_generic_assembly(self):
        """Assembly with no matching categories or suppliers returns Assy"""
        result = categorize_part(
            part_name="Generic Assembly",
            is_assembly=True,
            is_top_level=False,
            part_category_id=None,
        )
        self.assertEqual(result, "Assy")

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

    def test_internal_fab_requires_fabrication_category(self):
        """Internal Fab requires both internal supplier AND fabrication category"""
        # Has internal supplier but not in fabrication category
        result = categorize_part(
            part_name="Assembly",
            is_assembly=True,
            is_top_level=False,
            default_supplier_id=10,
            internal_supplier_ids=[10],
            part_category_id=50,
            category_mappings={"commercial": [50]},
        )
        # Should be Purchased Assy because it has a supplier but not in fab category
        self.assertEqual(result, "Assy")

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


if __name__ == '__main__':
    unittest.main()
