"""
Unit tests for Cut-to-Length (CtL) aggregation in deduplicate_and_sum.

Tests cover:
- CtL total length calculation (cumulative_qty * cut_length)
- Cut list generation and deduplication by length
- Multiple parts with cut lists
- Edge cases: None values, empty lists, zero quantities
- Note: Unit mismatch warnings require Django/Part models (tested in integration)

Run: python -m unittest flat_bom_generator.tests.test_cut_to_length_aggregation
"""

import unittest

from flat_bom_generator.bom_traversal import deduplicate_and_sum


class CutToLengthAggregationTests(unittest.TestCase):
    def test_cumulative_length_and_cut_list(self):
        # Two lengths for same part: 35.0 and 50.0
        leaves = [
            {
                "part_id": 400,
                "ipn": "CT-001",
                "part_name": "Bar",
                "description": "",
                "cumulative_qty": 2.0,
                "cut_length": 35.0,
                "unit": "mm",
                "part_type": "CtL",
                "from_internal_fab_parent": False,
                "quantity": 2,
                "is_assembly": False,
                "purchaseable": True,
            },
            {
                "part_id": 400,
                "ipn": "CT-001",
                "part_name": "Bar",
                "description": "",
                "cumulative_qty": 3.0,
                "cut_length": 35.0,
                "unit": "mm",
                "part_type": "CtL",
                "from_internal_fab_parent": False,
                "quantity": 3,
                "is_assembly": False,
                "purchaseable": True,
            },
            {
                "part_id": 400,
                "ipn": "CT-001",
                "part_name": "Bar",
                "description": "",
                "cumulative_qty": 5.0,
                "cut_length": 50.0,
                "unit": "mm",
                "part_type": "CtL",
                "from_internal_fab_parent": False,
                "quantity": 5,
                "is_assembly": False,
                "purchaseable": True,
            },
        ]

        result = deduplicate_and_sum(leaves)

        row = next((r for r in result if r["part_id"] == 400), None)
        self.assertIsNotNone(row)

        # total length = (2+3)*35 + 5*50 = 5*35 + 250 = 175 + 250 = 425
        self.assertAlmostEqual(row["total_qty"], 425.0)

        cut_list = row.get("cut_list") or []
        # Should have two entries (35.0 and 50.0)
        self.assertEqual(len(cut_list), 2)
        # Find entries by length
        by_len = {c["length"]: c["quantity"] for c in cut_list}
        self.assertEqual(by_len.get(35.0), 5.0)
        self.assertEqual(by_len.get(50.0), 5.0)

    def test_empty_leaves_list(self):
        """Empty leaves list should return empty result."""
        leaves = []
        result = deduplicate_and_sum(leaves)
        self.assertEqual(len(result), 0)

    def test_ctl_part_with_none_cut_length(self):
        """CtL part with cut_length=None should fall through to regular part handling."""
        leaves = [
            {
                "part_id": 500,
                "ipn": "CT-002",
                "part_name": "Bar Without Length",
                "description": "",
                "cumulative_qty": 2.0,
                "cut_length": None,  # Missing cut_length
                "unit": "mm",
                "part_type": "CtL",
                "from_internal_fab_parent": False,
                "quantity": 2,
                "is_assembly": False,
                "purchaseable": True,
            },
        ]

        result = deduplicate_and_sum(leaves)
        
        # Part should be included but treated as regular part (line 558-560)
        row = next((r for r in result if r["part_id"] == 500), None)
        self.assertIsNotNone(row)
        # When cut_length is None, falls through to regular part logic: uses cumulative_qty
        self.assertEqual(row["total_qty"], 2.0)
        # Should NOT have cut_list (cut_length is None)
        self.assertIsNone(row.get("cut_list"))

    def test_multiple_parts_with_cut_lists(self):
        """Multiple different CtL parts should each have their own cut lists."""
        leaves = [
            # Part 1: Steel bar
            {
                "part_id": 600,
                "ipn": "STEEL-BAR",
                "part_name": "Steel Bar",
                "description": "",
                "cumulative_qty": 3.0,
                "cut_length": 100.0,
                "unit": "mm",
                "part_type": "CtL",
                "from_internal_fab_parent": False,
                "quantity": 3,
                "is_assembly": False,
                "purchaseable": True,
            },
            # Part 2: Aluminum bar
            {
                "part_id": 601,
                "ipn": "AL-BAR",
                "part_name": "Aluminum Bar",
                "description": "",
                "cumulative_qty": 2.0,
                "cut_length": 50.0,
                "unit": "mm",
                "part_type": "CtL",
                "from_internal_fab_parent": False,
                "quantity": 2,
                "is_assembly": False,
                "purchaseable": True,
            },
        ]

        result = deduplicate_and_sum(leaves)

        # Check part 1
        part1 = next((r for r in result if r["part_id"] == 600), None)
        self.assertIsNotNone(part1)
        self.assertAlmostEqual(part1["total_qty"], 300.0)  # 3 * 100
        cut_list1 = part1.get("cut_list") or []
        self.assertEqual(len(cut_list1), 1)
        self.assertEqual(cut_list1[0]["length"], 100.0)
        self.assertEqual(cut_list1[0]["quantity"], 3.0)

        # Check part 2
        part2 = next((r for r in result if r["part_id"] == 601), None)
        self.assertIsNotNone(part2)
        self.assertAlmostEqual(part2["total_qty"], 100.0)  # 2 * 50
        cut_list2 = part2.get("cut_list") or []
        self.assertEqual(len(cut_list2), 1)
        self.assertEqual(cut_list2[0]["length"], 50.0)
        self.assertEqual(cut_list2[0]["quantity"], 2.0)

    def test_zero_quantity_ctl_part(self):
        """CtL part with zero cumulative_qty should result in zero total length."""
        leaves = [
            {
                "part_id": 700,
                "ipn": "CT-003",
                "part_name": "Zero Qty Bar",
                "description": "",
                "cumulative_qty": 0.0,
                "cut_length": 100.0,
                "unit": "mm",
                "part_type": "CtL",
                "from_internal_fab_parent": False,
                "quantity": 0,
                "is_assembly": False,
                "purchaseable": True,
            },
        ]

        result = deduplicate_and_sum(leaves)

        row = next((r for r in result if r["part_id"] == 700), None)
        self.assertIsNotNone(row)
        self.assertAlmostEqual(row["total_qty"], 0.0)  # 0 * 100 = 0
        cut_list = row.get("cut_list") or []
        self.assertEqual(len(cut_list), 1)
        self.assertEqual(cut_list[0]["quantity"], 0.0)

    def test_ctl_deduplication_same_length(self):
        """Multiple CtL entries with same length should deduplicate correctly."""
        leaves = [
            {
                "part_id": 800,
                "ipn": "CT-004",
                "part_name": "Dedup Bar",
                "description": "",
                "cumulative_qty": 2.0,
                "cut_length": 75.0,
                "unit": "mm",
                "part_type": "CtL",
                "from_internal_fab_parent": False,
                "quantity": 2,
                "is_assembly": False,
                "purchaseable": True,
            },
            {
                "part_id": 800,
                "ipn": "CT-004",
                "part_name": "Dedup Bar",
                "description": "",
                "cumulative_qty": 3.0,
                "cut_length": 75.0,  # Same length as above
                "unit": "mm",
                "part_type": "CtL",
                "from_internal_fab_parent": False,
                "quantity": 3,
                "is_assembly": False,
                "purchaseable": True,
            },
        ]

        result = deduplicate_and_sum(leaves)

        row = next((r for r in result if r["part_id"] == 800), None)
        self.assertIsNotNone(row)
        self.assertAlmostEqual(row["total_qty"], 375.0)  # (2+3) * 75 = 375
        
        cut_list = row.get("cut_list") or []
        # Should have only ONE entry (deduplicated)
        self.assertEqual(len(cut_list), 1)
        self.assertEqual(cut_list[0]["length"], 75.0)
        self.assertEqual(cut_list[0]["quantity"], 5.0)  # 2 + 3 deduplicated

    def test_non_ctl_part_no_cut_list(self):
        """Non-CtL parts should not have cut_list even if they have cut_length."""
        leaves = [
            {
                "part_id": 900,
                "ipn": "COML-001",
                "part_name": "Regular Part",
                "description": "",
                "cumulative_qty": 5.0,
                "cut_length": 100.0,  # Has cut_length but not CtL
                "unit": "pcs",
                "part_type": "Coml",  # NOT CtL
                "from_internal_fab_parent": False,
                "quantity": 5,
                "is_assembly": False,
                "purchaseable": True,
            },
        ]

        result = deduplicate_and_sum(leaves)

        row = next((r for r in result if r["part_id"] == 900), None)
        self.assertIsNotNone(row)
        # Regular parts use cumulative_qty, not cut_length calculation
        self.assertAlmostEqual(row["total_qty"], 5.0)
        # Should NOT have cut_list
        self.assertIsNone(row.get("cut_list"))

    def test_ctl_with_decimal_quantities(self):
        """CtL parts can have decimal quantities (e.g., 2.5 pieces)."""
        leaves = [
            {
                "part_id": 1000,
                "ipn": "CT-005",
                "part_name": "Decimal Bar",
                "description": "",
                "cumulative_qty": 2.5,
                "cut_length": 40.0,
                "unit": "mm",
                "part_type": "CtL",
                "from_internal_fab_parent": False,
                "quantity": 2.5,
                "is_assembly": False,
                "purchaseable": True,
            },
        ]

        result = deduplicate_and_sum(leaves)

        row = next((r for r in result if r["part_id"] == 1000), None)
        self.assertIsNotNone(row)
        self.assertAlmostEqual(row["total_qty"], 100.0)  # 2.5 * 40 = 100
        
        cut_list = row.get("cut_list") or []
        self.assertEqual(len(cut_list), 1)
        self.assertEqual(cut_list[0]["quantity"], 2.5)


if __name__ == "__main__":
    unittest.main()
