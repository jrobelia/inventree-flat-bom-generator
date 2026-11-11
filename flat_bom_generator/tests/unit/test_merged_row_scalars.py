"""Unit tests for merged-row field contracts (issues #23/#44/#45).

Contract (maintainer ruling R-025, #14 R1-F10 adjudication; amended for
piece_count by #44 and for inherited_from by #45, both 2026-11-11): a merged
flat row - one part aggregated across multiple BOM occurrences - must not
show one occurrence's value while a sibling occurrence disagrees or is
silently dropped.

- piece_count: withdrawn from the disagreement rule entirely - a per-line
  piece count cannot survive quantity aggregation even when sources agree
  (500x4 + 500x4 shows "4" while the cut list truthfully says 500x8; a
  single-source row under a 3x ancestor shows 6000mm beside "4", implying
  1500mm pieces). Every flat row is a material lump and emits
  piece_count=1; piece structure lives exclusively in the cut list.
- inherited_from (#45 ruling): categorical provenance rendered, not nulled -
  the merged row lists the distinct source template IPNs comma-joined and
  sorted, with the marker `local` appended when direct (non-inherited)
  lines are in the mix. Blank when nothing is inherited.
- Warning flags (#45): assembly_no_children and max_depth_exceeded OR
  across occurrences - a flagged occurrence must not vanish because it
  was not first-seen. max_depth_exceeded is per-path, so this is how a
  truncated path's lost subtree demand stays visible.
- note (#45): dedupe-joins all distinct occurrence notes, first-seen
  order - later occurrences' notes are no longer dropped.
- reference (#45): carries dedupe-joined bom_item.reference designator
  tokens, first-seen order - previously dropped entirely while the field
  misleadingly carried joined notes (the notes-in-reference swap).
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
          cumulative_qty=0.0, unit="pcs", inherited_from=None,
          reference="", **overrides):
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
        "reference": reference,
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

    def test_inherited_plus_direct_marks_local(self):
        """Inherited + direct occurrences render the template IPN with the
        `local` marker, in either occurrence order (#45 ruling)."""
        for first, second in [("WELD-T", None), (None, "WELD-T")]:
            with self.subTest(first=first, second=second):
                rows = deduplicate_and_sum([
                    _leaf(cumulative_qty=1, inherited_from=first),
                    _leaf(cumulative_qty=2, inherited_from=second),
                ])
                self.assertEqual(
                    rows[0]["inherited_from"], "WELD-T, local"
                )

    def test_distinct_inherited_froms_render_sorted(self):
        """Occurrences inherited from different templates render the
        distinct IPNs comma-joined and sorted (#45 ruling)."""
        rows = deduplicate_and_sum([
            _leaf(cumulative_qty=1, inherited_from="WELD-T"),
            _leaf(cumulative_qty=2, inherited_from="MACH-A"),
        ])
        self.assertEqual(rows[0]["inherited_from"], "MACH-A, WELD-T")

    def test_mixed_templates_and_direct_render_sorted_with_local(self):
        """T-A + T-B + direct renders 'T-A, T-B, local' (#45 ruling)."""
        rows = deduplicate_and_sum([
            _leaf(cumulative_qty=1, inherited_from="WELD-T"),
            _leaf(cumulative_qty=2, inherited_from=None),
            _leaf(cumulative_qty=3, inherited_from="MACH-A"),
        ])
        self.assertEqual(
            rows[0]["inherited_from"], "MACH-A, WELD-T, local"
        )

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

    def test_max_depth_exceeded_ors_across_occurrences(self):
        """A part reached via one truncated path and one full path shows
        max_depth_exceeded=True on the merged row, in either order (#45
        AC1 - the truncated path's subtree demand must stay visible)."""
        for first, second in [(True, False), (False, True)]:
            with self.subTest(first=first, second=second):
                rows = deduplicate_and_sum([
                    _leaf(cumulative_qty=1, max_depth_exceeded=first),
                    _leaf(cumulative_qty=2, max_depth_exceeded=second),
                ])
                self.assertTrue(rows[0]["max_depth_exceeded"])

    def test_assembly_no_children_ors_across_occurrences(self):
        """A flagged occurrence wins over an unflagged one, in either
        order - first-occurrence-wins made the warning vanish (#45)."""
        for first, second in [(True, False), (False, True)]:
            with self.subTest(first=first, second=second):
                rows = deduplicate_and_sum([
                    _leaf(cumulative_qty=1, assembly_no_children=first),
                    _leaf(cumulative_qty=2, assembly_no_children=second),
                ])
                self.assertTrue(rows[0]["assembly_no_children"])

    def test_merged_note_joins_distinct_notes_first_seen(self):
        """Every occurrence's note reaches the merged row's note field,
        distinct notes joined in first-seen order (#45)."""
        rows = deduplicate_and_sum([
            _leaf(cumulative_qty=1, note="Cut to length"),
            _leaf(cumulative_qty=2, note="Deburr edges"),
        ])
        self.assertEqual(rows[0]["note"], "Cut to length, Deburr edges")

    def test_merged_note_dedupes_identical_notes(self):
        """Identical notes do not duplicate; blanks are dropped (#45)."""
        rows = deduplicate_and_sum([
            _leaf(cumulative_qty=1, note="Use M6"),
            _leaf(cumulative_qty=2, note=""),
            _leaf(cumulative_qty=3, note="Use M6"),
        ])
        self.assertEqual(rows[0]["note"], "Use M6")

    def test_reference_carries_designators_not_notes(self):
        """reference emits bom_item.reference designators while note keeps
        the BOM item notes - the notes-in-reference swap is fixed and each
        field carries its own source data (#45 AC4)."""
        rows = deduplicate_and_sum([
            _leaf(cumulative_qty=1, note="torque spec", reference="R1"),
        ])
        self.assertEqual(rows[0]["note"], "torque spec")
        self.assertEqual(rows[0]["reference"], "R1")

    def test_reference_joins_distinct_designator_tokens(self):
        """Designator tokens merge across occurrences, deduped at token
        level and joined in first-seen order (#45 AC2)."""
        rows = deduplicate_and_sum([
            _leaf(cumulative_qty=1, reference="R1, R2"),
            _leaf(cumulative_qty=2, reference="R2, R3"),
        ])
        self.assertEqual(rows[0]["reference"], "R1, R2, R3")

    def test_single_source_reference_designators_emit(self):
        """A single-source row emits its bom_item.reference designators -
        previously dropped on every row (#45 AC3)."""
        rows = deduplicate_and_sum([
            _leaf(cumulative_qty=1, reference="R1, R2"),
        ])
        self.assertEqual(rows[0]["reference"], "R1, R2")

    def test_no_reference_designators_emit_blank(self):
        """A row with no designators emits a blank reference, not null."""
        rows = deduplicate_and_sum([
            _leaf(cumulative_qty=1),
            _leaf(cumulative_qty=2, reference="  "),
        ])
        self.assertEqual(rows[0]["reference"], "")

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
