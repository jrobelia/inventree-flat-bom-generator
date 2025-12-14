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


if __name__ == "__main__":
    unittest.main()
