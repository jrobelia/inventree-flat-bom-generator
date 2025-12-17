import unittest

from flat_bom_generator.bom_traversal import deduplicate_and_sum


class InternalFabCutRollupTests(unittest.TestCase):
    def test_piece_qty_times_count_rollup(self):
        """
        Test that internal_fab_cut_list correctly aggregates multiple occurrences of
        the same Internal Fab child part with the same cut_length.
        
        When a part appears multiple times as an Internal Fab child with the same
        cut_length, deduplicate_and_sum should:
        1. Sum total_qty as piece_qty * count (e.g., 35mm × 3 = 105mm)
        2. Aggregate internal_fab_cut_list entries by piece_qty
        3. Track count of identical cut lengths
        
        This test simulates 3 occurrences of the same part with cut_length=35mm:
        - First two with cumulative_qty=105 (representing 3 pieces from different branches)
        - Third with cumulative_qty=35 (representing 1 piece)
        Expected: One internal_fab_cut_list entry with piece_qty=35.0, count=3
        """
        # Simulate three internal-fab child occurrences for the same part
        leaves = [
            {
                "part_id": 285,
                "ipn": "OA-00270",
                "part_name": "P",
                "description": "",
                "cumulative_qty": 105.0,
                "cut_length": 35.0,
                "unit": "mm",
                "part_type": "Coml",
                "from_internal_fab_parent": True,
                "quantity": 1,
                "is_assembly": False,
                "purchaseable": True,
            },
            {
                "part_id": 285,
                "ipn": "OA-00270",
                "part_name": "P",
                "description": "",
                "cumulative_qty": 105.0,
                "cut_length": 35.0,
                "unit": "mm",
                "part_type": "Coml",
                "from_internal_fab_parent": True,
                "quantity": 1,
                "is_assembly": False,
                "purchaseable": True,
            },
            {
                "part_id": 285,
                "ipn": "OA-00270",
                "part_name": "P",
                "description": "",
                "cumulative_qty": 35.0,
                "cut_length": 35.0,
                "unit": "mm",
                "part_type": "Coml",
                "from_internal_fab_parent": True,
                "quantity": 1,
                "is_assembly": False,
                "purchaseable": True,
            },
        ]

        # Ensure allowed units are set so internal_fab_cut_list is produced
        deduplicate_and_sum.ifab_units = {"mm", "in", "cm", "ft"}
        deduplicate_and_sum.enable_ifab_cuts = True  # Enable internal_fab_cut_list in output
        result = deduplicate_and_sum(leaves)

        # Find the row for part_id 285
        row = next((r for r in result if r["part_id"] == 285), None)
        self.assertIsNotNone(row, "Expected a result row for part_id 285")

        # total should be piece_qty * count = 35.0 * 3 = 105.0
        self.assertAlmostEqual(row["total_qty"], 105.0)

        # internal_fab_cut_list should reflect one entry with count==3 and piece_qty==35.0
        ifab = row.get("internal_fab_cut_list") or []
        self.assertEqual(len(ifab), 1)
        self.assertEqual(ifab[0]["piece_qty"], 35.0)
        self.assertEqual(ifab[0]["count"], 3)


if __name__ == "__main__":
    unittest.main()
