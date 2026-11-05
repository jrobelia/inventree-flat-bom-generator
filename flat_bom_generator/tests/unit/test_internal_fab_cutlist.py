"""
Tests for internal_fab_cut_list generation in deduplicate_and_sum.

Contract (ticket #6):
- Children of internal-supplier assemblies get one cut-list entry per
  BOM item occurrence (per leaf), never merged.
- piece_qty = the BOM item quantity (cut_length on the leaf).
- count = the ancestor quantity multiplier (cumulative_qty / cut_length),
  rounded up when non-integral - a cut list never under-orders (R-016).
- No BOM-item-note parsing: free-text notes never become lengths.
- No unit filter: any part unit can produce a cut-list row.
- enable_ifab_cuts is an explicit parameter, not a function attribute.
"""

import unittest

from flat_bom_generator.bom_traversal import deduplicate_and_sum


def create_leaf(
    part_id,
    ipn,
    part_name,
    cumulative_qty,
    cut_length,
    unit,
    from_internal_fab_parent=True,
    part_type="Coml",
    note="",
    description="",
):
    """
    Build one leaf occurrence.

    cumulative_qty is the rolled-up quantity (BOM item qty x ancestors);
    cut_length is the BOM item quantity for this occurrence.
    """
    return {
        "part_id": part_id,
        "ipn": ipn,
        "part_name": part_name,
        "description": description,
        "cumulative_qty": cumulative_qty,
        "cut_length": cut_length,
        "unit": unit,
        "note": note,
        "from_internal_fab_parent": from_internal_fab_parent,
        "part_type": part_type,
        "is_assembly": False,
        "purchaseable": True,
    }


class InternalFabCutListTests(unittest.TestCase):
    """One cut-list entry per BOM item occurrence."""

    def test_single_occurrence_single_entry(self):
        """One leaf produces one entry: count=1, piece_qty=BOM qty."""
        leaves = [
            create_leaf(123, "TEST-001", "Test Part", 25.0, 25.0, "mm")
        ]
        result = deduplicate_and_sum(leaves, enable_ifab_cuts=True)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["part_id"], 123)
        self.assertEqual(result[0]["total_qty"], 25.0)

        cut_entries = result[0]["internal_fab_cut_list"]
        self.assertEqual(len(cut_entries), 1)
        self.assertEqual(cut_entries[0]["piece_qty"], 25.0)
        self.assertEqual(cut_entries[0]["count"], 1)
        self.assertEqual(cut_entries[0]["unit"], "mm")

    def test_ancestor_multiplier_becomes_count(self):
        """cut_length=BOM qty, count=ancestor multiplier (cumulative/qty)."""
        # TLA needs 2 internal-fab assemblies; each uses a 35mm piece.
        leaves = [
            create_leaf(123, "TUBE-001", "Tube", 70.0, 35.0, "mm")
        ]
        result = deduplicate_and_sum(leaves, enable_ifab_cuts=True)

        self.assertEqual(result[0]["total_qty"], 70.0)
        cut_entries = result[0]["internal_fab_cut_list"]
        self.assertEqual(len(cut_entries), 1)
        self.assertEqual(cut_entries[0]["piece_qty"], 35.0)
        self.assertEqual(cut_entries[0]["count"], 2)

    def test_fractional_multiplier_rounds_up(self):
        """Non-integral ancestor multipliers round up - never under-order.

        Ruling R-016: where the piece count is not integral, use ceiling.
        6.25 / 2.5 = 2.5 -> 3 pieces (round-half-even would emit 2).
        """
        leaves = [
            create_leaf(123, "TUBE-001", "Tube", 6.25, 2.5, "mm")
        ]
        result = deduplicate_and_sum(leaves, enable_ifab_cuts=True)

        cut_entries = result[0]["internal_fab_cut_list"]
        self.assertEqual(len(cut_entries), 1)
        self.assertEqual(cut_entries[0]["piece_qty"], 2.5)
        self.assertEqual(cut_entries[0]["count"], 3)

    def test_occurrences_not_merged(self):
        """Two BOM item occurrences stay as two entries, even at same length."""
        leaves = [
            create_leaf(123, "TUBE-001", "Tube", 25.0, 25.0, "mm"),
            create_leaf(123, "TUBE-001", "Tube", 25.0, 25.0, "mm"),
        ]
        result = deduplicate_and_sum(leaves, enable_ifab_cuts=True)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["total_qty"], 50.0)
        cut_entries = result[0]["internal_fab_cut_list"]
        self.assertEqual(len(cut_entries), 2)
        for entry in cut_entries:
            self.assertEqual(entry["piece_qty"], 25.0)
            self.assertEqual(entry["count"], 1)

    def test_different_lengths_separate_entries(self):
        """Occurrences at different lengths produce separate entries."""
        leaves = [
            create_leaf(123, "TUBE-001", "Tube", 25.0, 25.0, "mm"),
            create_leaf(123, "TUBE-001", "Tube", 50.0, 50.0, "mm"),
        ]
        result = deduplicate_and_sum(leaves, enable_ifab_cuts=True)

        self.assertEqual(result[0]["total_qty"], 75.0)
        cut_entries = result[0]["internal_fab_cut_list"]
        self.assertEqual(len(cut_entries), 2)
        lengths = {entry["piece_qty"] for entry in cut_entries}
        self.assertEqual(lengths, {25.0, 50.0})

    def test_non_internal_fab_leaf_gets_no_cut_list(self):
        """Leaves without from_internal_fab_parent produce no entries."""
        leaves = [
            create_leaf(
                123,
                "TEST-001",
                "Test Part",
                25.0,
                25.0,
                "mm",
                from_internal_fab_parent=False,
            )
        ]
        result = deduplicate_and_sum(leaves, enable_ifab_cuts=True)

        self.assertEqual(len(result), 1)
        self.assertIsNone(result[0]["internal_fab_cut_list"])

    def test_enable_ifab_cuts_disabled(self):
        """enable_ifab_cuts=False emits no entries (key present, value None)."""
        leaves = [
            create_leaf(123, "TEST-001", "Test Part", 25.0, 25.0, "mm")
        ]
        result = deduplicate_and_sum(leaves, enable_ifab_cuts=False)

        self.assertEqual(len(result), 1)
        self.assertIn("internal_fab_cut_list", result[0])
        self.assertIsNone(result[0]["internal_fab_cut_list"])

    def test_cut_length_none_skips_entry(self):
        """Occurrence with cut_length=None contributes no entry."""
        leaf = create_leaf(500, "IFP-001", "No Cut", 10.0, None, "mm")
        result = deduplicate_and_sum([leaf], enable_ifab_cuts=True)

        row = result[0]
        self.assertEqual(row["total_qty"], 10.0)
        self.assertIsNone(row["internal_fab_cut_list"])


class InternalFabCutListRegressionsTests(unittest.TestCase):
    """Regression coverage for removed mechanisms."""

    def test_no_unit_filter(self):
        """Any unit produces a cut-list row - no configured-units gate."""
        leaves = [
            create_leaf(123, "PART-IN", "Part in inches", 10.0, 10.0, "in"),
            create_leaf(456, "PART-PCS", "Part in pieces", 3.0, 3.0, "pcs"),
        ]
        result = deduplicate_and_sum(leaves, enable_ifab_cuts=True)

        for row in result:
            cut_entries = row["internal_fab_cut_list"]
            self.assertIsNotNone(cut_entries, f"{row['ipn']} lost its cut-list")
            self.assertEqual(len(cut_entries), 1)

    def test_notes_are_not_parsed(self):
        """Free-text BOM notes never influence cut_length or counts."""
        # Note says '1500mm' but the BOM item quantity is 25 - the entry
        # must use the BOM quantity, not anything parsed from the note.
        leaf = create_leaf(
            123, "TEST-001", "Test Part", 25.0, 25.0, "mm", note="1500mm"
        )
        result = deduplicate_and_sum([leaf], enable_ifab_cuts=True)

        cut_entries = result[0]["internal_fab_cut_list"]
        self.assertEqual(len(cut_entries), 1)
        self.assertEqual(cut_entries[0]["piece_qty"], 25.0)
        self.assertEqual(cut_entries[0]["count"], 1)

    def test_missing_unit_still_produces_entry(self):
        """Parts with no unit still get a cut-list row (unit is empty)."""
        leaf = create_leaf(123, "TEST-001", "Test Part", 25.0, 25.0, None)
        result = deduplicate_and_sum([leaf], enable_ifab_cuts=True)

        cut_entries = result[0]["internal_fab_cut_list"]
        self.assertEqual(len(cut_entries), 1)
        self.assertEqual(cut_entries[0]["unit"], "")

    def test_empty_leaves_list(self):
        """Empty leaves list returns empty result."""
        self.assertEqual(deduplicate_and_sum([], enable_ifab_cuts=True), [])

    def test_regular_parts_roll_up_by_cumulative_qty(self):
        """Non-ifab leaves keep the standard cumulative-quantity rollup."""
        leaves = [
            create_leaf(456, "REG-001", "Regular", 30.0, 30.0, "mm",
                        from_internal_fab_parent=False),
            create_leaf(456, "REG-001", "Regular", 12.0, 12.0, "mm",
                        from_internal_fab_parent=False),
        ]
        result = deduplicate_and_sum(leaves, enable_ifab_cuts=True)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["total_qty"], 42.0)
        self.assertIsNone(result[0]["internal_fab_cut_list"])


if __name__ == "__main__":
    unittest.main()
