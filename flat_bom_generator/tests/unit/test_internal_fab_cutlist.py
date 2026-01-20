"""
Tests for internal_fab_cut_list generation in deduplicate_and_sum.

CRITICAL UNDERSTANDING (established Dec 18, 2025):
=================================================
deduplicate_and_sum has TWO separate code paths:

1. CtL (Cut-to-Length) parts with cut_length:
   - total_qty = cumulative_qty × cut_length
   - cut_list tracks: {quantity: cumulative_qty, length: cut_length}
   
2. Internal Fab parts WITH cut_length:
   - Each leaf = ONE occurrence in BOM tree
   - total_qty += cut_length for each occurrence
   - internal_fab_cut_list tracks: {piece_qty: cut_length, count: occurrences}
   - cumulative_qty is NEVER used (throws error if unit mismatch)
   
3. Regular parts (not CtL, not internal fab):
   - total_qty += cumulative_qty
   - No cut_list generated

This file tests PATH 2 (internal fab WITH cut_length).

Example for Path 2:
- 3 BOM items each need 1 piece of 35mm tubing
- 3 leaf dicts, each with cut_length=35, cumulative_qty=ignored
- total_qty = 35 + 35 + 35 = 105mm
- cut_list = [{piece_qty: 35, count: 3}]

How we established this understanding:
1. Read deduplicate_and_sum implementation (lines 505-580)
2. Traced through test_piece_qty_times_count_rollup step-by-step
3. Identified piece_count_inc always = 1 (quantity field not in leaf)
4. Discovered cumulative_qty fallback was wrong, removed it
5. Added ValueError for unit mismatch (Dec 18) - fail fast on data corruption
6. Wrote tests matching actual behavior
"""

import unittest

from flat_bom_generator.bom_traversal import deduplicate_and_sum


def create_leaf(
    part_id,
    ipn,
    part_name,
    cut_length,
    unit,
    from_internal_fab_parent=True,
    part_type="Coml",
    description="",
):
    """
    Helper to create a single leaf part occurrence for internal fab testing.
    
    Key understanding: Each leaf represents ONE occurrence in the BOM tree.
    - deduplicate_and_sum adds cut_length to total for each occurrence
    - count = number of times this cut_length appears
    - cumulative_qty is NOT used for internal fab parts with cut_length
    
    Args:
        cut_length: Length of each piece (e.g., 25.0 for 25mm pieces)
        
    The function calculates:
        total_qty = cut_length × count (number of occurrences)
        count = number of leaf entries with this cut_length
    
    Example:
        3 leaves with cut_length=35 → total_qty=105, count=3
    """
    return {
        "part_id": part_id,
        "ipn": ipn,
        "part_name": part_name,
        "description": description,
        "cumulative_qty": 0,  # Not used for internal fab with cut_length
        "cut_length": cut_length,
        "unit": unit,
        "from_internal_fab_parent": from_internal_fab_parent,
        "part_type": part_type,
        "is_assembly": False,
        "purchaseable": True,
    }


class InternalFabCutListTests(unittest.TestCase):
    """Test internal_fab_cut_list generation for parts from Internal Fab parents."""

    def test_internal_fab_with_matching_unit(self):
        """Part with from_internal_fab_parent=True and matching unit gets cut_list."""
        # One BOM occurrence: 1 piece of 25mm tubing
        # Expected: total_qty = 25mm, cut_list = [{piece_qty: 25, count: 1}]
        leaves = [
            create_leaf(123, "TEST-001", "Test Part", 25.0, "mm", description="Test part")
        ]

        deduplicate_and_sum.ifab_units = {"mm"}
        deduplicate_and_sum.enable_ifab_cuts = True
        result = deduplicate_and_sum(leaves)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["part_id"], 123)
        self.assertEqual(result[0]["total_qty"], 25.0)  # 1 occurrence × 25mm
        
        cut_list = result[0].get("internal_fab_cut_list", [])
        self.assertEqual(len(cut_list), 1)
        self.assertEqual(cut_list[0]["piece_qty"], 25.0)
        self.assertEqual(cut_list[0]["count"], 1)  # 1 occurrence

    def test_internal_fab_with_non_matching_unit(self):
        """Part with from_internal_fab_parent=True but non-matching unit is treated as regular part.
        
        This can happen when internal fab parts have incompatible units (e.g., weight vs length).
        The part should be included in BOM as regular part without cut list (no warning, no error).
        """
        leaves = [
            create_leaf(123, "TEST-001", "Test Part", 25.0, "inches")
        ]

        deduplicate_and_sum.ifab_units = {"mm"}  # Only mm allowed
        deduplicate_and_sum.enable_ifab_cuts = True
        
        # Should NOT raise error - silently treat as regular part
        result = deduplicate_and_sum(leaves)
        
        # Part should be in results with regular quantity
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["total_qty"], 25.0)
        # No cut list should be generated
        self.assertIsNone(result[0].get("internal_fab_cut_list"))

    def test_non_internal_fab_parent(self):
        """Part without from_internal_fab_parent flag gets no cut_list."""
        leaves = [
            create_leaf(123, "TEST-001", "Test Part", 25.0, "mm", from_internal_fab_parent=False)
        ]

        deduplicate_and_sum.ifab_units = {"mm"}
        deduplicate_and_sum.enable_ifab_cuts = True
        result = deduplicate_and_sum(leaves)

        self.assertEqual(len(result), 1)
        cut_list = result[0].get("internal_fab_cut_list")
        self.assertIsNone(cut_list)

    def test_internal_fab_missing_unit(self):
        """Part with from_internal_fab_parent=True but missing unit is treated as regular part.
        
        This can happen when internal fab parts have no unit defined.
        The part should be included in BOM as regular part without cut list (no warning, no error).
        """
        leaves = [
            create_leaf(123, "TEST-001", "Test Part", 25.0, None)
        ]

        deduplicate_and_sum.ifab_units = {"mm"}
        deduplicate_and_sum.enable_ifab_cuts = True
        
        # Should NOT raise error - silently treat as regular part
        result = deduplicate_and_sum(leaves)
        
        # Part should be in results with regular quantity
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["total_qty"], 25.0)
        # No cut list should be generated
        self.assertIsNone(result[0].get("internal_fab_cut_list"))


class InternalFabCutListRollupTests(unittest.TestCase):
    """Test aggregation of multiple occurrences with same/different cut_lengths."""

    def test_rollup_multiple_occurrences_same_length(self):
        """Multiple occurrences of same part with same cut_length should aggregate."""
        # 3 BOM occurrences: each needs 1 piece of 25mm tubing
        # Expected: total_qty = 75mm, cut_list = [{piece_qty: 25, count: 3}]
        leaves = [
            create_leaf(123, "TUBE-001", "Tube", 25.0, "mm", description=""),
            create_leaf(123, "TUBE-001", "Tube", 25.0, "mm", description=""),
            create_leaf(123, "TUBE-001", "Tube", 25.0, "mm", description=""),
        ]

        deduplicate_and_sum.ifab_units = {"mm"}
        deduplicate_and_sum.enable_ifab_cuts = True
        result = deduplicate_and_sum(leaves)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["total_qty"], 75.0)  # 25 + 25 + 25
        
        cut_list = result[0].get("internal_fab_cut_list", [])
        self.assertEqual(len(cut_list), 1)  # Single entry
        self.assertEqual(cut_list[0]["piece_qty"], 25.0)
        self.assertEqual(cut_list[0]["count"], 3)  # 3 occurrences

    def test_rollup_multiple_occurrences_different_lengths(self):
        """Multiple occurrences of same part with different cut_lengths create separate entries."""
        # 2 occurrences at 25mm, 2 occurrences at 50mm
        # Expected: total_qty = 150mm, cut_list has 2 entries
        leaves = [
            create_leaf(123, "TUBE-001", "Tube", 25.0, "mm", description=""),
            create_leaf(123, "TUBE-001", "Tube", 25.0, "mm", description=""),
            create_leaf(123, "TUBE-001", "Tube", 50.0, "mm", description=""),
            create_leaf(123, "TUBE-001", "Tube", 50.0, "mm", description=""),
        ]

        deduplicate_and_sum.ifab_units = {"mm"}
        deduplicate_and_sum.enable_ifab_cuts = True
        result = deduplicate_and_sum(leaves)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["total_qty"], 150.0)  # 25+25+50+50
        
        cut_list = result[0].get("internal_fab_cut_list", [])
        self.assertEqual(len(cut_list), 2)  # Two different lengths
        
        # Find each entry (order may vary)
        lengths = {item["piece_qty"]: item["count"] for item in cut_list}
        self.assertEqual(lengths[25.0], 2)
        self.assertEqual(lengths[50.0], 2)

    def test_mixed_internal_fab_and_regular_parts(self):
        """Parts with and without from_internal_fab_parent are handled correctly."""
        leaves = [
            create_leaf(123, "IFAB-001", "IFab Part", 25.0, "mm", from_internal_fab_parent=True),
            create_leaf(456, "REG-001", "Regular Part", 30.0, "mm", from_internal_fab_parent=False),
        ]

        deduplicate_and_sum.ifab_units = {"mm"}
        deduplicate_and_sum.enable_ifab_cuts = True
        result = deduplicate_and_sum(leaves)

        self.assertEqual(len(result), 2)
        
        ifab_part = next(r for r in result if r["part_id"] == 123)
        self.assertIn("internal_fab_cut_list", ifab_part)
        self.assertEqual(len(ifab_part["internal_fab_cut_list"]), 1)
        
        regular_part = next(r for r in result if r["part_id"] == 456)
        self.assertIsNone(regular_part.get("internal_fab_cut_list"))


class InternalFabCutListEdgeCasesTests(unittest.TestCase):
    """Test edge cases and special conditions."""

    def test_empty_leaves_list(self):
        """Empty leaves list returns empty result."""
        deduplicate_and_sum.ifab_units = {"mm", "in", "cm", "ft"}
        deduplicate_and_sum.enable_ifab_cuts = True
        result = deduplicate_and_sum([])
        self.assertEqual(result, [])

    def test_cut_length_none(self):
        """
        Internal fab part with cut_length=None skips internal_fab_cut_list logic.
        
        Code behavior (line 526): elif from_ifab and cut_length is not None:
        If cut_length is None, skips to else block (line 558), uses cumulative_qty only.
        """
        leaves = [
            {
                "part_id": 500,
                "ipn": "IFP-001",
                "part_name": "Internal Fab Part No Cut",
                "description": "",
                "cumulative_qty": 10.0,
                "cut_length": None,
                "unit": "mm",
                "part_type": "Coml",
                "from_internal_fab_parent": True,
                "quantity": 1,
                "is_assembly": False,
                "purchaseable": True,
            }
        ]
        deduplicate_and_sum.ifab_units = {"mm", "in", "cm", "ft"}
        deduplicate_and_sum.enable_ifab_cuts = True
        result = deduplicate_and_sum(leaves)

        row = next((r for r in result if r["part_id"] == 500), None)
        self.assertIsNotNone(row)
        # Falls through to else: totals[key] += leaf["cumulative_qty"]
        self.assertEqual(row["total_qty"], 10.0)
        # No internal_fab_cut_list since cut_length is None
        self.assertIsNone(row.get("internal_fab_cut_list"))

    def test_piece_count_greater_than_one(self):
        """
        Test piece_count_inc > 1 (leaf["quantity"] > 1).
        
        Total calculation: cut_length × piece_count_inc
        Example: 35mm × 2 = 70mm per occurrence
        """
        leaves = [
            {
                "part_id": 700,
                "ipn": "IFP-003",
                "part_name": "Multi-Count Part",
                "description": "",
                "cumulative_qty": 140.0,  # Ignored for internal fab
                "cut_length": 35.0,
                "unit": "mm",
                "part_type": "Coml",
                "from_internal_fab_parent": True,
                "quantity": 2,  # piece_count_inc = 2
                "is_assembly": False,
                "purchaseable": True,
            },
            {
                "part_id": 700,
                "ipn": "IFP-003",
                "part_name": "Multi-Count Part",
                "description": "",
                "cumulative_qty": 210.0,  # Ignored for internal fab
                "cut_length": 35.0,
                "unit": "mm",
                "part_type": "Coml",
                "from_internal_fab_parent": True,
                "quantity": 3,  # piece_count_inc = 3
                "is_assembly": False,
                "purchaseable": True,
            },
        ]
        deduplicate_and_sum.ifab_units = {"mm", "in", "cm", "ft"}
        deduplicate_and_sum.enable_ifab_cuts = True
        result = deduplicate_and_sum(leaves)

        row = next((r for r in result if r["part_id"] == 700), None)
        self.assertIsNotNone(row)
        # Total: 35×2 + 35×3 = 70 + 105 = 175
        self.assertEqual(row["total_qty"], 175.0)

        cut_list = row.get("internal_fab_cut_list", [])
        self.assertEqual(len(cut_list), 1)
        self.assertEqual(cut_list[0]["piece_qty"], 35.0)
        # Count: 2 + 3 = 5
        self.assertEqual(cut_list[0]["count"], 5)

    def test_zero_cut_length(self):
        """Part with zero cut_length still creates cut_list entry."""
        leaves = [
            create_leaf(123, "TEST-001", "Test Part", 0.0, "mm")
        ]

        deduplicate_and_sum.ifab_units = {"mm"}
        deduplicate_and_sum.enable_ifab_cuts = True
        result = deduplicate_and_sum(leaves)

        self.assertEqual(result[0]["total_qty"], 0.0)
        cut_list = result[0].get("internal_fab_cut_list", [])
        self.assertEqual(len(cut_list), 1)
        self.assertEqual(cut_list[0]["count"], 1)

    def test_fractional_cut_lengths(self):
        """Fractional cut_lengths are handled correctly."""
        # 3 occurrences of 12.5mm pieces
        leaves = [
            create_leaf(123, "TEST-001", "Test Part", 12.5, "mm"),
            create_leaf(123, "TEST-001", "Test Part", 12.5, "mm"),
            create_leaf(123, "TEST-001", "Test Part", 12.5, "mm"),
        ]

        deduplicate_and_sum.ifab_units = {"mm"}
        deduplicate_and_sum.enable_ifab_cuts = True
        result = deduplicate_and_sum(leaves)

        self.assertEqual(result[0]["total_qty"], 37.5)  # 12.5 * 3
        cut_list = result[0].get("internal_fab_cut_list", [])
        self.assertEqual(cut_list[0]["piece_qty"], 12.5)
        self.assertEqual(cut_list[0]["count"], 3)

    def test_enable_ifab_cuts_disabled(self):
        """When enable_ifab_cuts=False, no cut_list is generated."""
        leaves = [
            create_leaf(123, "TEST-001", "Test Part", 25.0, "mm")
        ]

        deduplicate_and_sum.ifab_units = {"mm"}
        deduplicate_and_sum.enable_ifab_cuts = False  # Disabled
        result = deduplicate_and_sum(leaves)

        self.assertEqual(len(result), 1)
        # When disabled, internal_fab_cut_list should not be in output
        self.assertNotIn("internal_fab_cut_list", result[0])

    def test_multiple_allowed_units(self):
        """Parts with different but allowed units both get cut_lists."""
        leaves = [
            create_leaf(123, "PART-MM", "Part in mm", 25.0, "mm"),
            create_leaf(456, "PART-IN", "Part in inches", 10.0, "in"),
        ]

        deduplicate_and_sum.ifab_units = {"mm", "in"}  # Both allowed
        deduplicate_and_sum.enable_ifab_cuts = True
        result = deduplicate_and_sum(leaves)

        self.assertEqual(len(result), 2)
        
        mm_part = next(r for r in result if r["part_id"] == 123)
        self.assertIsNotNone(mm_part.get("internal_fab_cut_list"))
        
        in_part = next(r for r in result if r["part_id"] == 456)
        self.assertIsNotNone(in_part.get("internal_fab_cut_list"))


if __name__ == "__main__":
    unittest.main()
