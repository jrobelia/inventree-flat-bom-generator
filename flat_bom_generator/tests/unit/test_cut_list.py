"""Unit tests for the dimensionality-based cut list (issue #14, ruling R-016).

Contract (maintainer spec amendment):
- Every child BOM line whose sub_part's `units` have pint [length]
  dimensionality is a cut-list candidate, regardless of which expanded parent
  it sits under. Internal-fab status is unrelated.
- Each entry is {size: bom_item.quantity, count: ceil(piece_count x ancestor
  multiplier)} and entries aggregate by (part, piece size): same sizes merge,
  mixed sizes stay separate.
- piece_count == 1 lines list as one piece of `quantity` size.
- Blank or unparseable units are not cut lines. BOM note text is never parsed.
- Units resolve through the InvenTree conversion registry (custom units
  resolve); in bare test environments the registry resolves to a plain pint
  registry or the tests patch the registry seam.

Tests pin the aggregation seam, not pint internals: a fake registry supplies
the pint contract (Quantity().check()) so the suite runs without Django.
"""

import unittest
from unittest.mock import patch

from flat_bom_generator.bom_traversal import (
    _resolve_unit_registry,
    _units_have_length_dimension,
    deduplicate_and_sum,
)


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


def _leaf(part_id=10, ipn="P-10", quantity=None, piece_count=1, cumulative_qty=0.0,
          unit="pcs", note="", **overrides):
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
        "note": note,
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
        "inherited_from": None,
    }
    leaf.update(overrides)
    return leaf


class TestCutListAggregation(unittest.TestCase):
    """deduplicate_and_sum() cut_list aggregation under a stubbed registry."""

    def setUp(self):
        patcher = patch(
            "flat_bom_generator.bom_traversal._resolve_unit_registry",
            return_value=_FakeRegistry(),
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_piece_count_line_single_entry(self):
        """{quantity: 500, piece_count: 4} yields one entry {size 500, count 4}."""
        rows = deduplicate_and_sum([
            _leaf(quantity=500, piece_count=4, cumulative_qty=2000, unit="mm"),
        ])
        self.assertEqual(
            rows[0]["cut_list"], [{"size": 500, "count": 4, "unit": "mm"}]
        )
        self.assertEqual(rows[0]["total_qty"], 2000)

    def test_ancestor_multiplier_scales_count(self):
        """count derives from cumulative_qty, so ancestor multipliers apply."""
        rows = deduplicate_and_sum([
            _leaf(quantity=500, piece_count=4, cumulative_qty=4000, unit="mm"),
        ])
        self.assertEqual(rows[0]["cut_list"][0]["count"], 8)

    def test_same_size_across_parents_merges(self):
        """500x4 under one assembly + 500x2 under another -> '500 x 6'."""
        rows = deduplicate_and_sum([
            _leaf(quantity=500, piece_count=4, cumulative_qty=2000, unit="mm"),
            _leaf(quantity=500, piece_count=2, cumulative_qty=1000, unit="mm"),
        ])
        self.assertEqual(len(rows), 1)
        self.assertEqual(
            rows[0]["cut_list"], [{"size": 500, "count": 6, "unit": "mm"}]
        )
        self.assertEqual(rows[0]["total_qty"], 3000)

    def test_piece_count_one_lists_as_single(self):
        """500x1 stays '500 x 1' - single-piece lines are still cut lines."""
        rows = deduplicate_and_sum([
            _leaf(quantity=500, piece_count=1, cumulative_qty=500, unit="mm"),
        ])
        self.assertEqual(
            rows[0]["cut_list"], [{"size": 500, "count": 1, "unit": "mm"}]
        )

    def test_mixed_sizes_stay_separate(self):
        """500x4 + 250x8 on the same part keep two entries."""
        rows = deduplicate_and_sum([
            _leaf(quantity=500, piece_count=4, cumulative_qty=2000, unit="mm"),
            _leaf(quantity=250, piece_count=8, cumulative_qty=2000, unit="mm"),
        ])
        self.assertEqual(
            rows[0]["cut_list"],
            [
                {"size": 500, "count": 4, "unit": "mm"},
                {"size": 250, "count": 8, "unit": "mm"},
            ],
        )

    def test_non_length_unit_no_entry(self):
        """A BOM line in 'each' with piece_count > 1 is not a cut line."""
        rows = deduplicate_and_sum([
            _leaf(quantity=10, piece_count=5, cumulative_qty=50, unit="each"),
        ])
        self.assertIsNone(rows[0]["cut_list"])
        self.assertEqual(rows[0]["total_qty"], 50)

    def test_unparseable_unit_no_entry(self):
        """Units the registry cannot parse are not cut lines."""
        rows = deduplicate_and_sum([
            _leaf(quantity=500, piece_count=4, cumulative_qty=2000, unit="bananas"),
        ])
        self.assertIsNone(rows[0]["cut_list"])

    def test_blank_unit_no_entry(self):
        """Blank units are not cut lines."""
        rows = deduplicate_and_sum([
            _leaf(quantity=500, piece_count=4, cumulative_qty=2000, unit=""),
        ])
        self.assertIsNone(rows[0]["cut_list"])

    def test_no_quantity_no_entry(self):
        """A leaf with no BOM quantity cannot size a piece."""
        rows = deduplicate_and_sum([
            _leaf(quantity=None, piece_count=4, cumulative_qty=2000, unit="mm"),
        ])
        self.assertIsNone(rows[0]["cut_list"])

    def test_note_text_is_never_parsed(self):
        """Free text in the BOM note cannot create or size a cut entry."""
        rows = deduplicate_and_sum([
            _leaf(quantity=10, piece_count=1, cumulative_qty=10, unit="pcs",
                  note="cut 25 mm"),
        ])
        self.assertIsNone(rows[0]["cut_list"])

    def test_float_ratio_snaps_to_whole(self):
        """Float dust must not over-ceil a whole piece count."""
        rows = deduplicate_and_sum([
            _leaf(quantity=0.1, piece_count=3, cumulative_qty=0.3 + 1e-9,
                  unit="mm"),
        ])
        self.assertEqual(rows[0]["cut_list"][0]["count"], 3)

    def test_genuine_fraction_ceils_up(self):
        """A real fractional remainder rounds up - never under-order."""
        rows = deduplicate_and_sum([
            _leaf(quantity=3.0, piece_count=2, cumulative_qty=6.5, unit="mm"),
        ])
        self.assertEqual(rows[0]["cut_list"][0]["count"], 3)

    def test_no_cut_list_key_value_when_empty(self):
        """Rows expose cut_list=None when the part has no cut entries."""
        rows = deduplicate_and_sum([_leaf(unit="pcs", cumulative_qty=4)])
        self.assertIn("cut_list", rows[0])
        self.assertIsNone(rows[0]["cut_list"])

    def test_regular_rollup_still_applies(self):
        """Totals/consumable aggregation unchanged: consumable must hold for
        every appearance to stay true."""
        rows = deduplicate_and_sum([
            _leaf(cumulative_qty=10, consumable=True),
            _leaf(cumulative_qty=5, consumable=False),
        ])
        self.assertEqual(rows[0]["total_qty"], 15)
        self.assertFalse(rows[0]["consumable"])


_REAL_REGISTRY = _resolve_unit_registry()


@unittest.skipUnless(
    _REAL_REGISTRY is not None,
    "no unit registry available in this environment",
)
class TestLengthUnitDimensionalityRealRegistry(unittest.TestCase):
    """Pin the real registry path: [length] check plus blank/unknown units."""

    def test_mm_is_length(self):
        self.assertTrue(_units_have_length_dimension("mm", _REAL_REGISTRY))

    def test_meter_is_length(self):
        self.assertTrue(_units_have_length_dimension("meter", _REAL_REGISTRY))

    def test_each_is_not_length(self):
        self.assertFalse(_units_have_length_dimension("each", _REAL_REGISTRY))

    def test_blank_is_not_length(self):
        self.assertFalse(_units_have_length_dimension("", _REAL_REGISTRY))

    def test_garbage_is_not_length(self):
        self.assertFalse(_units_have_length_dimension("zzz", _REAL_REGISTRY))


if __name__ == "__main__":
    unittest.main()
