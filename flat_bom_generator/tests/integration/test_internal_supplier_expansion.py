"""Integration tests for the line-item / expansion decision matrix.

Uses internal_supplier_expansion.yaml to verify, with real InvenTree models:

- Internal-supplier assembly (Company.is_internal=True): line item AND expanded
- External-supplier assembly: line item, NOT expanded
- Unsourced assembly: expanded as build-order candidate regardless of
  purchaseable flag, and not itself a line item
- Cut list (R-016): every child line whose sub_part units have [length]
  dimensionality produces entries {size: BOM quantity, count: piece_count x
  ancestor multiplier} aggregated by (part, piece size), regardless of which
  expanded parent the line sits under - no note parsing
- Sourced TLA roots (R-015): the input part is exempt from the emit matrix -
  it always expands and never appears as a row in its own flat BOM
"""

import os
import unittest

from django.core.management import call_command
from InvenTree.unit_test import InvenTreeTestCase
from part.models import Part


class InternalSupplierExpansionTests(InvenTreeTestCase):
    """get_flat_bom() honors Company.is_internal and the expansion matrix."""

    @classmethod
    def setUpTestData(cls):
        """Load the expansion fixture once for all tests."""
        super().setUpTestData()

        test_dir = os.path.dirname(__file__)  # integration/
        fixtures_dir = os.path.dirname(test_dir)  # tests/
        fixture_path = os.path.join(
            fixtures_dir, 'fixtures', 'internal_supplier_expansion.yaml'
        )
        call_command('loaddata', fixture_path, verbosity=0)

        cls.tla = Part.objects.get(pk=8001)
        cls.ifab_assy = Part.objects.get(pk=8002)
        cls.steel = Part.objects.get(pk=8003)
        cls.purchased_assy = Part.objects.get(pk=8004)
        cls.hidden_child = Part.objects.get(pk=8005)
        cls.unsourced_assy = Part.objects.get(pk=8006)
        cls.screw = Part.objects.get(pk=8007)
        cls.internal_tla = Part.objects.get(pk=8010)
        cls.bar_stock = Part.objects.get(pk=8011)

    def _flat_bom(self, part=None, **kwargs):
        from flat_bom_generator.bom_traversal import get_flat_bom

        flat_bom, _ifps, _warnings, _depth = get_flat_bom(
            (part or self.tla).pk, **kwargs
        )
        return {row['part_id']: row for row in flat_bom}

    def test_internal_supplier_assembly_is_line_item_and_expanded(self):
        """is_internal supplier -> assembly appears AND children expand."""
        rows = self._flat_bom()

        # The internal-fab assembly itself is a line item
        self.assertIn(self.ifab_assy.pk, rows)
        assy = rows[self.ifab_assy.pk]
        self.assertTrue(assy['is_assembly'])
        self.assertTrue(assy['internal_supplier'])
        self.assertEqual(assy['part_type'], 'Internal Fab')
        self.assertEqual(assy['total_qty'], 2.0)

        # Its child expanded into the flat list
        self.assertIn(self.steel.pk, rows)

    def test_external_supplier_assembly_is_line_item_not_expanded(self):
        """External supplier -> assembly appears, children stay hidden."""
        rows = self._flat_bom()

        self.assertIn(self.purchased_assy.pk, rows)
        assy = rows[self.purchased_assy.pk]
        self.assertTrue(assy['is_assembly'])
        self.assertFalse(assy['internal_supplier'])
        self.assertEqual(assy['part_type'], 'Purchased Assy')

        # Its child must not appear
        self.assertNotIn(self.hidden_child.pk, rows)

    def test_external_supplier_assembly_expands_with_toggle(self):
        """expand_purchased_assemblies=True expands the external assembly."""
        rows = self._flat_bom(expand_purchased_assemblies=True)

        self.assertNotIn(self.purchased_assy.pk, rows)
        self.assertIn(self.hidden_child.pk, rows)

    def test_unsourced_assembly_expands_regardless_of_purchaseable(self):
        """No primary supplier -> expand; purchaseable flag is irrelevant."""
        rows = self._flat_bom()

        # purchaseable=True on the fixture proves the flag doesn't suppress
        # expansion: the screw appears, the assembly itself does not.
        self.assertNotIn(self.unsourced_assy.pk, rows)
        self.assertIn(self.screw.pk, rows)
        self.assertEqual(rows[self.screw.pk]['total_qty'], 4.0)
        self.assertEqual(rows[self.screw.pk]['part_type'], 'Other')

    def test_cut_list_entry_uses_bom_quantity_as_size(self):
        """Cut list: size = BOM line quantity, count = piece_count x multiplier."""
        rows = self._flat_bom()
        steel = rows[self.steel.pk]

        # 2 assemblies x 3 mm-pieces each = 6 total (piece_count defaults to 1)
        self.assertEqual(steel['total_qty'], 6.0)

        cut_list = steel['cut_list']
        self.assertEqual(len(cut_list), 1)
        self.assertEqual(cut_list[0]['size'], 3.0)  # BOM item quantity
        self.assertEqual(cut_list[0]['count'], 2)  # ancestor multiplier
        self.assertEqual(cut_list[0]['unit'], 'mm')

    def test_cut_list_emitted_without_toggle(self):
        """The new cut list is always computed - no view/traversal flag."""
        rows = self._flat_bom()
        self.assertIsNotNone(rows[self.steel.pk]['cut_list'])

    def test_non_length_unit_produces_no_cut_entry(self):
        """The screw (unit 'pcs', unparseable) is not a cut line."""
        rows = self._flat_bom()
        self.assertIsNone(rows[self.screw.pk]['cut_list'])

    def test_cut_list_ignores_bom_note_text(self):
        """Note 'cut as needed' must not create extra or different entries."""
        rows = self._flat_bom()
        cut_list = rows[self.steel.pk]['cut_list']
        self.assertEqual(len(cut_list), 1)
        self.assertEqual(cut_list[0]['size'], 3.0)

    def test_sourced_tla_root_expands_without_self_row(self):
        """Externally sourced TLA (R-015): expands, never emits a self row."""
        rows = self._flat_bom()

        # The whole flat BOM must not collapse to the input part
        self.assertNotIn(self.tla.pk, rows)
        self.assertGreater(len(rows), 1)
        self.assertIn(self.ifab_assy.pk, rows)
        self.assertIn(self.purchased_assy.pk, rows)
        self.assertIn(self.screw.pk, rows)

    def test_sourced_tla_root_expansion_ignores_toggle(self):
        """Root always expands - expand_purchased_assemblies gates
        descendants only."""
        rows = self._flat_bom(expand_purchased_assemblies=True)

        self.assertNotIn(self.tla.pk, rows)
        # The external descendant now expands, but the root still does not
        self.assertIn(self.hidden_child.pk, rows)

    def test_internal_sourced_tla_root_expands_without_self_row(self):
        """Internally sourced TLA (R-015): children expand, no self row -
        and the child still carries its internal-fab cut entry."""
        rows = self._flat_bom(part=self.internal_tla)

        self.assertNotIn(self.internal_tla.pk, rows)
        self.assertEqual(list(rows), [self.bar_stock.pk])

        bar = rows[self.bar_stock.pk]
        self.assertEqual(bar['total_qty'], 5.0)
        cut_list = bar['cut_list']
        self.assertEqual(len(cut_list), 1)
        self.assertEqual(cut_list[0]['size'], 5.0)
        self.assertEqual(cut_list[0]['count'], 1)


if __name__ == '__main__':
    unittest.main()
