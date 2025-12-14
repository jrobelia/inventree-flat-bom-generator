"""
Unit tests for categorization module.

Tests the categorization logic and helper functions that determine
how parts are categorized in the flat BOM.
"""

import unittest
from flat_bom_generator.categorization import _extract_length_from_notes


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


if __name__ == '__main__':
    unittest.main()
