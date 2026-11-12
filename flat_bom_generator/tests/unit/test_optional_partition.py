"""Unit tests for the optional-line partition (issue #30).

Contract (issue #30, Option D ruling 2026-11-11): the flat-BOM dedup carries
a per-row quantity partition, `optional_qty` - the sum of cumulative
quantities across occurrences whose BOM line is flagged optional - so the
frontend can render `mixed (X opt / Y req)` on a row carrying both optional
and required demand. The all-instances `optional` flag keeps its ADR-0006
collapse; `optional_qty` is additive evidence alongside it.

- optional_qty sums only optional-flagged occurrences; a required-only row
  emits 0.
- An all-optional row emits optional_qty == total_qty (and optional=True);
  a mixed row emits 0 < optional_qty < total_qty (and optional=False).
- The `consumable` flag is untouched - consumable lines stay real demand.

Prune guard (same ticket): when `include_optional=false` traversal skips
optional BOM lines and marks the parent node `optional_lines_pruned`. A node
whose expansion produced no children *because lines were pruned* is not a
genuine empty assembly - get_leaf_parts_only must emit nothing for it (no
phantom row, no assembly_no_children warning). A genuinely childless
assembly still emits with the flag.

Tests pin deduplicate_and_sum() with leaf dicts and get_leaf_parts_only()
with tree dicts; the cut-list check uses the same fake registry seam as
test_merged_row_scalars.py.
"""

import unittest
from unittest.mock import patch

from flat_bom_generator.bom_traversal import (
    deduplicate_and_sum,
    get_leaf_parts_only,
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


def _leaf(part_id=10, ipn="P-10", quantity=None, cumulative_qty=0.0,
          unit="pcs", optional=False, **overrides):
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
        "piece_count": 1,
        "cumulative_qty": cumulative_qty,
        "internal_supplier": False,
        "note": "",
        "reference": "",
        "is_assembly": False,
        "inherited_from": None,
        "optional": optional,
        "consumable": False,
    }
    leaf.update(overrides)
    return leaf


def _assy_node(part_id=1, children=None, **overrides):
    """Minimal tree node for an unsourced assembly."""
    node = {
        "part_id": part_id,
        "ipn": "ASY-1",
        "part_name": "Assembly 1",
        "description": "",
        "cumulative_qty": 1.0,
        "unit": "pcs",
        "is_assembly": True,
        "purchaseable": False,
        "default_supplier_id": None,
        "internal_supplier": False,
        "part_type": "Assy",
        "level": 1,
        "children": children if children is not None else [],
    }
    node.update(overrides)
    return node


class TestOptionalQtyPartition(unittest.TestCase):
    """deduplicate_and_sum() optional_qty partition (issue #30)."""

    def setUp(self):
        patcher = patch(
            "flat_bom_generator.bom_traversal._resolve_unit_registry",
            return_value=_FakeRegistry(),
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_optional_qty_emitted_on_every_row(self):
        """Every flat row carries optional_qty, including required-only."""
        rows = deduplicate_and_sum([_leaf(cumulative_qty=4)])
        self.assertIn("optional_qty", rows[0])
        self.assertEqual(rows[0]["optional_qty"], 0)

    def test_all_optional_row_partitions_full_total(self):
        """An all-optional row emits optional_qty == total_qty and keeps
        optional=True (ADR-0006 collapse unchanged)."""
        rows = deduplicate_and_sum([
            _leaf(cumulative_qty=3, optional=True),
            _leaf(cumulative_qty=2, optional=True),
        ])
        self.assertEqual(rows[0]["total_qty"], 5)
        self.assertEqual(rows[0]["optional_qty"], 5)
        self.assertTrue(rows[0]["optional"])

    def test_mixed_row_partitions_optional_share(self):
        """3 optional + 2 required -> total 5, optional_qty 3, optional False
        (the ticket's worked example -> `mixed (3 opt / 2 req)`)."""
        rows = deduplicate_and_sum([
            _leaf(cumulative_qty=3, optional=True),
            _leaf(cumulative_qty=2, optional=False),
        ])
        self.assertEqual(rows[0]["total_qty"], 5)
        self.assertEqual(rows[0]["optional_qty"], 3)
        self.assertFalse(rows[0]["optional"])

    def test_required_only_row_partitions_zero(self):
        """A row with no optional occurrences emits optional_qty 0 and a
        False optional flag."""
        rows = deduplicate_and_sum([
            _leaf(cumulative_qty=2, optional=False),
            _leaf(cumulative_qty=4, optional=False),
        ])
        self.assertEqual(rows[0]["optional_qty"], 0)
        self.assertFalse(rows[0]["optional"])

    def test_consumable_flag_unaffected_by_partition(self):
        """Consumable stays out of the toggle's scope - its all-instances
        collapse is unchanged and consumable qty is not partitioned."""
        rows = deduplicate_and_sum([
            _leaf(cumulative_qty=1, consumable=True),
            _leaf(cumulative_qty=2, consumable=True, optional=True),
        ])
        self.assertTrue(rows[0]["consumable"])
        self.assertEqual(rows[0]["optional_qty"], 2)

    def test_optional_partition_coexists_with_cut_list(self):
        """An optional length line still contributes its cut entries under
        the default toggle - cut_list and optional_qty are independent."""
        rows = deduplicate_and_sum([
            _leaf(quantity=500, cumulative_qty=500, unit="mm", optional=True),
        ])
        self.assertEqual(rows[0]["optional_qty"], 500)
        self.assertEqual(
            rows[0]["cut_list"], [{"size": 500, "count": 1, "unit": "mm"}]
        )


class TestPrunedOptionalChildrenGuard(unittest.TestCase):
    """get_leaf_parts_only() optional_lines_pruned guard (issue #30).

    Under include_optional=false, traversal skips optional BOM lines and
    marks the parent `optional_lines_pruned`. A node whose children all
    dropped that way yields no required demand - it must emit nothing, not
    a phantom row carrying a false 'no BOM items' warning.
    """

    def test_pruned_unsourced_assembly_emits_nothing(self):
        """Required-path assembly whose only children were optional lines:
        no leaf row, no assembly_no_children flag."""
        node = _assy_node(children=[], optional_lines_pruned=True)
        leaves = get_leaf_parts_only(node)
        self.assertEqual(leaves, [])

    def test_pruned_root_assembly_emits_nothing(self):
        """A TLA root whose whole BOM was optional emits an empty flat BOM -
        R-015's self-row exemption holds; the all-optional case yields
        no required demand, not a self row."""
        node = _assy_node(level=0, children=[], optional_lines_pruned=True)
        leaves = get_leaf_parts_only(node)
        self.assertEqual(leaves, [])

    def test_genuinely_childless_assembly_still_emits(self):
        """Control: no pruning happened - the childless unsourced assembly
        keeps its assembly_no_children emit (unchanged R-015 behavior)."""
        node = _assy_node(children=[])
        leaves = get_leaf_parts_only(node)
        self.assertEqual(len(leaves), 1)
        self.assertTrue(leaves[0]["assembly_no_children"])

    def test_pruned_parent_with_surviving_children_expands(self):
        """A node that pruned some lines but kept required children expands
        normally - the marker only matters when expansion emptied it."""
        child = {
            "part_id": 20,
            "ipn": "CH-1",
            "part_name": "Child",
            "description": "",
            "cumulative_qty": 2.0,
            "unit": "pcs",
            "is_assembly": False,
            "purchaseable": True,
            "part_type": "Coml",
            "level": 2,
            "children": [],
        }
        node = _assy_node(children=[child], optional_lines_pruned=True)
        leaves = get_leaf_parts_only(node)
        self.assertEqual(len(leaves), 1)
        self.assertEqual(leaves[0]["part_id"], 20)


if __name__ == "__main__":
    unittest.main()
