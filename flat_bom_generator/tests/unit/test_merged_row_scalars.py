"""Unit tests for merged-row per-line scalars (issues #23/#44, ruling R-025).

Contract (maintainer ruling R-025, #14 R1-F10 adjudication; amended for
piece_count by #44, 2026-11-11): a merged flat row - one part aggregated
across multiple BOM occurrences - must not show a per-line scalar from one
occurrence while a sibling occurrence disagrees.

- piece_count: withdrawn from the disagreement rule entirely - a per-line
  piece count cannot survive quantity aggregation even when sources agree
  (500x4 + 500x4 shows "4" while the cut list truthfully says 500x8; a
  single-source row under a 3x ancestor shows 6000mm beside "4", implying
  1500mm pieces). Every flat row is a material lump and emits
  piece_count=1; piece structure lives exclusively in the cut list.
- inherited_from: categorical provenance, not a quantity - it still carries
  only when uniform and nulls on disagreement.
- The cut list is unaffected: it aggregates by (part, piece size), not by
  the BOM line's scalar fields.

Tests pin the deduplicate_and_sum() merge seam with leaf dicts; the cut-list
check uses the same fake registry seam as test_cut_list.py.
"""

import unittest
from unittest.mock import patch

from flat_bom_generator.bom_traversal import deduplicate_and_sum


_LENGTH_UNITS = {"mm", "cm", "m", "in", "ft", "meter"}
_KNOWN_UNITS = _LENGTH_UNITS | {"each", "pcs", "kg"}


class _FakeQuantity:
    """Pint Quantity stand-in: only .check(dimensionality) is consumed."""

    def __init__(self, units):
        self._units = units

    def check(self, dimensionality):
        return dimensionality == "[length]" and self._units in _LENGTH_UNITS


class _FakeRegistry:
    """Pint UnitRegistry stand-in: Quantity() parses-or-raises like pint."""

    def Quantity(self, value, units):
        if not units or not str(units).strip():
            raise ValueError("blank unit")
        units = str(units).strip()
        if units not in _KNOWN_UNITS:
            raise ValueError(f"undefined unit {units}")
        return _FakeQuantity(units)


def _leaf(part_id=10, ipn="P-10", quantity=None, piece_count=1,
          cumulative_qty=0.0, unit="pcs", inherited_from=None, **overrides):
    """Minimal leaf dict matching the get_leaf_parts_only() seam."""
    leaf = {
        "part_id": part_id,
        "ipn": ipn,
        "part_name": f"Part {ipn}",
        "description": f"Part {ipn} description",
        "purchaseable": True,
        "part_type": "Coml",
        "unit": unit,
        "quantity": quantity,
        "piece_count": piece_count,
        "cumulative_qty": cumulative_qty,
        "internal_supplier": False,
        "note": "",
        "has_substitutes": False,
        "consumable": False,
        "bom_item_contributions": {},
        "ancestor_part_ids": [],
        "is_assembly": False,
        "is_purchased_assy": False,
        "from_purchased_assy": False,
        "expanded_assy_parts": [],
        "category": None,
        "default_supplier_name": None,
        "supplier_name": None,
        "inherited_from": inherited_from,
    }
    leaf.update(overrides)
    return leaf


class TestMergedRowScalars(unittest.TestCase):
    """deduplicate_and_sum() per-line scalar contract (R-025 as amended)."""

    def setUp(self):
        patcher = patch(
            "flat_bom_generator.bom_traversal._resolve_unit_registry",
            return_value=_FakeRegistry(),
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_disagreeing_piece_count_still_one(self):
        """500x4 + 500x2 on one part -> merged row piece_count is 1, in
        either occurrence order; the lump has no per-line piece count."""
        for counts in [(4, 2), (2, 4)]:
            with self.subTest(counts=counts):
                rows = deduplicate_and_sum([
                    _leaf(quantity=500, piece_count=counts[0],
                          cumulative_qty=2000, unit="mm"),
                    _leaf(quantity=500, piece_count=counts[1],
                          cumulative_qty=1000, unit="mm"),
                ])
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["piece_count"], 1)

    def test_agreeing_piece_count_still_one(self):
        """Even when every occurrence agrees (500x4 + 500x4), the merged
        row's lump quantity cannot carry a per-line count -> piece_count 1."""
        rows = deduplicate_and_sum([
            _leaf(piece_count=4, cumulative_qty=2000),
            _leaf(piece_count=4, cumulative_qty=2000),
        ])
        self.assertEqual(rows[0]["piece_count"], 1)

    def test_single_occurrence_piece_count_normalizes(self):
        """A lone occurrence normalizes too - under a multiplied ancestor its
        source count would imply the wrong piece size on the lump total."""
        rows = deduplicate_and_sum([
            _leaf(piece_count=4, cumulative_qty=6000),
        ])
        self.assertEqual(rows[0]["piece_count"], 1)

    def test_disagreeing_inherited_from_nulls(self):
        """Inherited + direct occurrences merge to inherited_from=None, in
        either occurrence order."""
        for first, second in [("WELD-T", None), (None, "WELD-T")]:
            with self.subTest(first=first, second=second):
                rows = deduplicate_and_sum([
                    _leaf(cumulative_qty=1, inherited_from=first),
                    _leaf(cumulative_qty=2, inherited_from=second),
                ])
                self.assertIsNone(rows[0]["inherited_from"])

    def test_two_different_inherited_froms_null(self):
        """Occurrences inherited from different templates also null."""
        rows = deduplicate_and_sum([
            _leaf(cumulative_qty=1, inherited_from="WELD-T"),
            _leaf(cumulative_qty=2, inherited_from="MACH-A"),
        ])
        self.assertIsNone(rows[0]["inherited_from"])

    def test_uniform_inherited_from_carries(self):
        """Every occurrence inherited from the same template keeps the IPN."""
        rows = deduplicate_and_sum([
            _leaf(cumulative_qty=1, inherited_from="WELD-T"),
            _leaf(cumulative_qty=2, inherited_from="WELD-T"),
        ])
        self.assertEqual(rows[0]["inherited_from"], "WELD-T")

    def test_all_direct_merge_stays_none(self):
        """Merged all-direct rows keep inherited_from=None (uniform null)."""
        rows = deduplicate_and_sum([
            _leaf(cumulative_qty=1),
            _leaf(cumulative_qty=2),
        ])
        self.assertIsNone(rows[0]["inherited_from"])

    def test_single_occurrence_inherited_from_unaffected(self):
        """A lone inherited occurrence keeps its inherited_from IPN."""
        rows = deduplicate_and_sum([
            _leaf(cumulative_qty=2, inherited_from="WELD-T"),
        ])
        self.assertEqual(rows[0]["inherited_from"], "WELD-T")

    def test_cut_list_carries_piece_structure(self):
        """Disagreeing piece_count still merges cut rows by piece size -
        '500 x 6' is the piece structure while the lump's piece_count is 1
        (R-025 scope bound, amended)."""
        rows = deduplicate_and_sum([
            _leaf(quantity=500, piece_count=4, cumulative_qty=2000, unit="mm"),
            _leaf(quantity=500, piece_count=2, cumulative_qty=1000, unit="mm"),
        ])
        self.assertEqual(rows[0]["piece_count"], 1)
        self.assertEqual(
            rows[0]["cut_list"], [{"size": 500, "count": 6, "unit": "mm"}]
        )
        self.assertEqual(rows[0]["total_qty"], 3000)


if __name__ == "__main__":
    unittest.main()
