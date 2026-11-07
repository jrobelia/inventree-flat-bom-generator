"""Integration tests for native InvenTree 1.6 BOM semantics (issue #14).

Uses upstream_bom_semantics.yaml to verify, with real InvenTree models:

- piece_count: a line's total material is quantity x piece_count x ancestor
  multiplier - attrition/setup quantities stay out of plugin totals
- effective consumable: Part.consumable makes a line consumable even when
  the BOM line flag is False (BomItem.is_consumable)
- inherited lines: part.get_bom_items() surfaces template BOM lines on a
  variant (include_inherited=True); they are marked inherited_from=<template
  IPN>, direct lines get null, non-inherited template lines stay out, and
  the inherited line keeps its own bom_item pk for substitute resolution
- cut list (R-016): length-unit children produce {size, count, unit}
  entries aggregated by (part, piece size) - 500x4 + 500x2 = 500x6,
  500x1 stays 500 x 1, mixed sizes stay separate, non-length units
  produce no entries
"""

import os
import unittest

from django.core.management import call_command
from InvenTree.unit_test import InvenTreeTestCase
from part.models import Part


class UpstreamBomSemanticsTests(InvenTreeTestCase):
    """get_flat_bom() applies native 1.6 BOM semantics end to end."""

    @classmethod
    def setUpTestData(cls):
        """Load the semantics fixture once for all tests."""
        super().setUpTestData()

        test_dir = os.path.dirname(__file__)  # integration/
        fixtures_dir = os.path.dirname(test_dir)  # tests/
        fixture_path = os.path.join(
            fixtures_dir, 'fixtures', 'upstream_bom_semantics.yaml'
        )
        call_command('loaddata', fixture_path, verbosity=0)

        cls.tla = Part.objects.get(pk=8100)
        cls.variant = Part.objects.get(pk=8111)

    def _flat(self, part):
        from flat_bom_generator.bom_traversal import get_flat_bom

        flat_bom, _ifps, _warnings, _depth = get_flat_bom(part.pk)
        return {row['part_id']: row for row in flat_bom}

    def test_piece_count_multiplies_line_total(self):
        """500x4 + 500x2 on the bar: quantity x piece_count = 2000 + 1000."""
        rows = self._flat(self.tla)

        self.assertEqual(rows[8103]['total_qty'], 3000.0)

    def test_same_size_pieces_aggregate_across_parents(self):
        """500x4 under A + 500x2 under B merges into one '500 x 6' entry."""
        rows = self._flat(self.tla)

        self.assertEqual(
            rows[8103]['cut_list'],
            [{'size': 500.0, 'count': 6, 'unit': 'mm'}],
        )

    def test_piece_count_one_stays_explicit(self):
        """A 500x1 rail line lists as one '500 x 1' entry, not nothing."""
        rows = self._flat(self.tla)

        rail = rows[8105]
        self.assertEqual(rail['total_qty'], 500.0)
        self.assertEqual(
            rail['cut_list'],
            [{'size': 500.0, 'count': 1, 'unit': 'mm'}],
        )

    def test_mixed_piece_sizes_stay_separate(self):
        """Tube at 500x4 and 250x8 keeps two entries on the same part."""
        rows = self._flat(self.tla)

        self.assertEqual(
            rows[8104]['cut_list'],
            [
                {'size': 500.0, 'count': 4, 'unit': 'mm'},
                {'size': 250.0, 'count': 8, 'unit': 'mm'},
            ],
        )
        self.assertEqual(rows[8104]['total_qty'], 4000.0)

    def test_non_length_piece_count_line_totals_but_no_cut(self):
        """Bolts in 'each' at 10x5: totals scale, no cut entry."""
        rows = self._flat(self.tla)

        bolts = rows[8106]
        self.assertEqual(bolts['total_qty'], 50.0)
        self.assertIsNone(bolts['cut_list'])

    def test_consumable_part_flag_is_effective(self):
        """Part.consumable=True makes the line consumable; flag False line."""
        rows = self._flat(self.tla)

        self.assertTrue(rows[8107]['consumable'])

    def test_inherited_line_marks_inherited_from(self):
        """The template bracket appears on the variant as WELD-T's line."""
        rows = self._flat(self.variant)

        bracket = rows[8120]
        self.assertEqual(bracket['inherited_from'], 'WELD-T')
        self.assertEqual(bracket['total_qty'], 2.0)

    def test_direct_line_inherited_from_is_null(self):
        """The variant's own line carries inherited_from=None."""
        rows = self._flat(self.variant)

        self.assertIsNone(rows[8121]['inherited_from'])

    def test_non_inherited_template_line_excluded(self):
        """A template line with inherited=False stays off the variant BOM."""
        rows = self._flat(self.variant)

        self.assertNotIn(8122, rows)

    def test_inherited_line_keeps_own_bom_item_pk_for_substitutes(self):
        """bom_item_contributions key = the inherited line's own BomItem pk,
        which is what views.py uses to resolve BomItemSubstitute rows."""
        rows = self._flat(self.variant)

        bracket = rows[8120]
        self.assertIn(81020, bracket['bom_item_contributions'])

    def test_piece_count_one_line_unchanged(self):
        """piece_count=1 semantics are a no-op - the cover totals stay 1."""
        rows = self._flat(self.variant)

        cover = rows[8121]
        self.assertEqual(cover['total_qty'], 1.0)
        self.assertEqual(cover['piece_count'], 1)

    def test_merged_row_nulls_disagreeing_piece_count(self):
        """500x4 + 500x2 on the bar: the merged row cannot show either
        count - 'Pieces' goes blank rather than lie (issue #23, R-025)."""
        rows = self._flat(self.tla)

        self.assertIsNone(rows[8103]['piece_count'])

    def test_merged_row_nulls_disagreeing_piece_count_tube(self):
        """The tube's 500x4 + 250x8 merge also nulls piece_count - while
        its two-size cut_list stays aggregated and correct."""
        rows = self._flat(self.tla)

        self.assertIsNone(rows[8104]['piece_count'])
        self.assertEqual(len(rows[8104]['cut_list']), 2)

    def test_uniform_piece_count_survives_merge(self):
        """SEM-PIN at 10x3 under both weldments keeps piece_count=3 on the
        merged row - only disagreement nulls."""
        rows = self._flat(self.tla)

        pin = rows[8130]
        self.assertEqual(pin['piece_count'], 3)
        self.assertEqual(pin['total_qty'], 60.0)

    def test_disagreeing_inherited_from_nulls_on_merge(self):
        """The gasket is on the variant directly AND via the template's
        inherited line - the merged row nulls inherited_from (R-025) while
        uniform piece_count=1 still carries."""
        rows = self._flat(self.variant)

        gasket = rows[8131]
        self.assertIsNone(gasket['inherited_from'])
        self.assertEqual(gasket['total_qty'], 3.0)
        self.assertEqual(gasket['piece_count'], 1)


if __name__ == '__main__':
    unittest.main()
