"""Integration tests for the include_optional toggle (issue #30).

Fixture: fixtures/optional_lines.yaml. OPT-ROOT (9201) carries required
lines, optional leaf lines, an optional-entry subassembly (SUB-OPT) whose
children are required lines, an optional length line feeding the cut list,
and a required-entry subassembly (SUB-ALLOPT) whose only line is optional.

Contracts under test:

- include_optional=false prunes each optional line's whole subtree at the
  traversal seam: PART-OPT-ONLY, PART-BAR-OPT, PART-SUB-LEAF, and
  PART-SUBLEAF-OPT disappear; PART-MIXED keeps only its required share.
- An assembly emptied by pruning (SUB-ALLOPT) emits nothing - no leaf row,
  no assembly_no_children warning.
- optional_qty partitions every row's total: 0 required-only, full on
  all-optional, partial on mixed. Path-optional occurrences (required line
  under an optional parent) count as optional - exactly the demand the
  toggle removes.
- Derived stock/order figures recompute from the filtered total_qty.
- The default (param absent / setting unset) reproduces the pre-toggle
  output: every optional contribution included.
"""

import os
from unittest.mock import patch

from django.core.management import call_command
from rest_framework.test import APIRequestFactory, force_authenticate
from InvenTree.unit_test import InvenTreeTestCase
from part.models import Part

from flat_bom_generator.views import FlatBOMView


class IncludeOptionalViewTests(InvenTreeTestCase):
    """End-to-end view behavior for the include_optional query param."""

    @classmethod
    def setUpTestData(cls):
        """Load the optional-lines fixture once for all tests."""
        super().setUpTestData()

        test_dir = os.path.dirname(__file__)  # integration/
        fixtures_dir = os.path.dirname(test_dir)  # tests/
        fixture_path = os.path.join(
            fixtures_dir, 'fixtures', 'optional_lines.yaml'
        )
        call_command('loaddata', fixture_path, verbosity=0)

        cls.user.groups.add(cls.group)
        cls.assignRole('bom.view')

        cls.root = Part.objects.get(pk=9201)

    def setUp(self):
        """Request factory per test (re-import for registry reloads)."""
        super().setUp()
        from flat_bom_generator.views import FlatBOMView as _View

        self.factory = APIRequestFactory()
        self.view = _View.as_view()

    def _rows(self, query=''):
        request = self.factory.get(f'/fake-url/{self.root.pk}/{query}')
        force_authenticate(request, user=self.user)
        response = self.view(request, part_id=self.root.pk)
        self.assertEqual(response.status_code, 200)
        items = response.data['bom_items']
        return {item['part_id']: item for item in items}, response.data

    def test_default_includes_all_optional_demand(self):
        """No param -> setting default True -> pre-toggle output."""
        rows, _ = self._rows()

        self.assertEqual(
            set(rows), {9202, 9203, 9205, 9206, 9207, 9209}
        )
        self.assertEqual(rows[9202]['total_qty'], 2)
        self.assertEqual(rows[9202]['optional_qty'], 0)
        self.assertFalse(rows[9202]['optional'])

        # All-optional leaf keeps the badge and a full partition
        self.assertEqual(rows[9203]['total_qty'], 3)
        self.assertEqual(rows[9203]['optional_qty'], 3)
        self.assertTrue(rows[9203]['optional'])

        # Required line under an optional parent is optional demand
        self.assertEqual(rows[9205]['total_qty'], 4)
        self.assertEqual(rows[9205]['optional_qty'], 4)
        self.assertTrue(rows[9205]['optional'])

        # One required + one path-optional occurrence -> mixed partition
        self.assertEqual(rows[9206]['total_qty'], 2)
        self.assertEqual(rows[9206]['optional_qty'], 1)
        self.assertFalse(rows[9206]['optional'])

        # Optional length line keeps its cut-list entry in include mode
        self.assertEqual(rows[9207]['total_qty'], 500)
        self.assertEqual(rows[9207]['optional_qty'], 500)
        self.assertEqual(
            rows[9207]['cut_list'],
            [{'size': 500, 'count': 1, 'unit': 'mm'}],
        )

        self.assertEqual(rows[9209]['total_qty'], 2)
        self.assertEqual(rows[9209]['optional_qty'], 2)

    def test_explicit_true_matches_default(self):
        """include_optional=true sends the same set as the default."""
        rows, _ = self._rows('?include_optional=true')
        self.assertEqual(set(rows), {9202, 9203, 9205, 9206, 9207, 9209})
        self.assertEqual(rows[9206]['optional_qty'], 1)

    def test_exclude_prunes_optional_lines_and_subtrees(self):
        """include_optional=false drops every optional contribution."""
        rows, _ = self._rows('?include_optional=false')

        # Only the required shares survive
        self.assertEqual(set(rows), {9202, 9206})
        self.assertEqual(rows[9202]['total_qty'], 2)
        self.assertEqual(rows[9202]['optional_qty'], 0)
        self.assertEqual(rows[9206]['total_qty'], 1)
        self.assertEqual(rows[9206]['optional_qty'], 0)

    def test_exclude_suppresses_emptied_assembly_warning(self):
        """SUB-ALLOPT has lines, all optional - no assembly_no_children."""
        _, data = self._rows('?include_optional=false')
        warnings = data['metadata']['warnings']
        no_children = [
            w for w in warnings
            if w.get('type') == 'assembly_no_children'
        ]
        self.assertEqual(no_children, [])

    def test_exclude_recomputes_order_figures(self):
        """quantity_to_order derives from the filtered total_qty."""
        rows_inc, _ = self._rows('?include_optional=true')
        rows_exc, _ = self._rows('?include_optional=false')

        inc = rows_inc[9206]
        exc = rows_exc[9206]
        # Required-only total is smaller, so To Order cannot grow
        self.assertLessEqual(
            exc['quantity_to_order'], inc['quantity_to_order']
        )
        self.assertEqual(exc['total_qty'], 1)
        self.assertIn('net_stock', exc)

    def test_query_param_overrides_plugin_setting(self):
        """Setting False + param true -> include wins (UI owns the call)."""
        from flat_bom_generator.core import FlatBOMGenerator

        plugin = FlatBOMGenerator()
        plugin.set_setting('INCLUDE_OPTIONAL_PARTS', False)

        with patch(
            'plugin.registry.registry.get_plugin', return_value=plugin
        ):
            rows, _ = self._rows('?include_optional=true')
        self.assertEqual(set(rows), {9202, 9203, 9205, 9206, 9207, 9209})

    def test_plugin_setting_false_prunes_without_param(self):
        """Setting False, no param -> required-only output."""
        from flat_bom_generator.core import FlatBOMGenerator

        plugin = FlatBOMGenerator()
        plugin.set_setting('INCLUDE_OPTIONAL_PARTS', False)

        with patch(
            'plugin.registry.registry.get_plugin', return_value=plugin
        ):
            rows, _ = self._rows()
        self.assertEqual(set(rows), {9202, 9206})
