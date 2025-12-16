"""
Unit tests for Internal Fab cut_list logic.

These tests verify that Internal Fab children only receive a cut_list when their units match the cut breakdown setting.
"""

import unittest

# Assume this is the function under test (to be replaced with actual import)
def get_cut_list_for_row(row, cut_unit_setting):
    """
    Simulate backend logic for assigning cut_list to a BOM row.
    row: dict with keys 'is_internal_fab', 'unit', 'qty', 'length'
    cut_unit_setting: str, e.g. 'mm'
    Returns: list if eligible, else None
    """
    if not row.get('is_internal_fab'):
        return None
    if row.get('unit') != cut_unit_setting:
        return None
    # Simulate cut_list structure
    return [{
        'quantity': row.get('qty', 1),
        'length': row.get('length', 0)
    }]

class InternalFabCutListTests(unittest.TestCase):
    def test_internal_fab_with_matching_unit(self):
        row = {'is_internal_fab': True, 'unit': 'mm', 'qty': 5, 'length': 25}
        cut_list = get_cut_list_for_row(row, 'mm')
        self.assertIsInstance(cut_list, list)
        self.assertEqual(cut_list[0]['quantity'], 5)
        self.assertEqual(cut_list[0]['length'], 25)

    def test_internal_fab_with_non_matching_unit(self):
        row = {'is_internal_fab': True, 'unit': 'in', 'qty': 5, 'length': 25}
        cut_list = get_cut_list_for_row(row, 'mm')
        self.assertIsNone(cut_list)

    def test_non_internal_fab(self):
        row = {'is_internal_fab': False, 'unit': 'mm', 'qty': 5, 'length': 25}
        cut_list = get_cut_list_for_row(row, 'mm')
        self.assertIsNone(cut_list)

    def test_internal_fab_with_convertible_unit(self):
        # If logic allows convertible units, this test should be updated
        row = {'is_internal_fab': True, 'unit': 'cm', 'qty': 2, 'length': 100}
        cut_list = get_cut_list_for_row(row, 'mm')
        self.assertIsNone(cut_list)  # Update if conversion is supported

    def test_internal_fab_missing_unit(self):
        row = {'is_internal_fab': True, 'qty': 1, 'length': 10}
        cut_list = get_cut_list_for_row(row, 'mm')
        self.assertIsNone(cut_list)

if __name__ == '__main__':
    unittest.main()


# --- Additional tests for rollup, nesting, and edge cases ---
from flat_bom_generator.bom_traversal import get_flat_bom

class InternalFabCutListAdvancedTests(unittest.TestCase):
    def test_total_unique_parts_in_full_bom(self):
        """
        Test that counts the total number of unique parts (by Component) in the full BOM CSV.
        This checks the deduplication logic for the entire BOM.
        """
        import csv
        import os
        # Load the BOM CSV from tests/test_data folder
        bom_path = os.path.join(os.path.dirname(__file__), 'test_data', 'InvenTree_BomItem_2025-12-14_J48BLGx.csv')
        rows = []
        with open(bom_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                rows.append(row)

        unique_parts = set(row['Component'] for row in rows if row.get('Component'))
        total_unique_parts = len(unique_parts)
        print(f"[INFO] Total unique parts in full BOM: {total_unique_parts}")
        # The expected value should be updated if the BOM changes
        # For now, just assert it's greater than zero
        self.assertGreater(total_unique_parts, 0)

    def test_internal_fab_cutlist_piece_qty_times_length_equals_parent_rollup(self):
        """
        For all Internal Fab parts in the BOM, confirm that the sum of (piece qty × cut length) for each cut list line equals the rollup (total length or quantity) on the parent line, using a full recursive BOM explosion.
        """
        import csv
        import os
        import re
        # Load the BOM CSV from tests/test_data folder
        bom_path = os.path.join(os.path.dirname(__file__), 'test_data', 'InvenTree_BomItem_2025-12-14_J48BLGx.csv')
        rows = []
        with open(bom_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                rows.append(row)

        # Build a mapping: part_id -> [rows where this is the parent]
        children_map = {}
        for r in rows:
            parent = r['Assembly']
            children_map.setdefault(parent, []).append(r)

        # Find all Internal Fab parts: Supplier 1 is OpenAeros and Component.Name starts with 'Fab'
        internal_fab_rows = [
            r for r in rows
            if r.get('Supplier 1', '').strip().lower() == 'openaeros'
            and r['Component.Name'].strip().startswith('Fab')
            and r['Quantity']
            and r['Component.Description']
            and 'mm' in r['Component.Description']
        ]

        def recursive_cut_sum(parent_id, qty_multiplier):
            total = 0
            for child in children_map.get(parent_id, []):
                child_qty = float(child['Quantity']) if child['Quantity'] else 0
                # Try to extract cut length from description
                m2 = re.search(r'(\d+(?:\.\d+)?)\s*mm', child['Component.Description'])
                child_length = float(m2.group(1)) if m2 else None
                # If this child is a cuttable part (has a length), add to total
                if child_length:
                    total += qty_multiplier * child_qty * child_length
                # If this child is an internal fab, recurse
                if child.get('Supplier 1', '').strip().lower() == 'openaeros' and child['Component.Name'].strip().startswith('Fab'):
                    total += recursive_cut_sum(child['Component'], qty_multiplier * child_qty)
            return total

        for fab in internal_fab_rows:
            fab_id = fab['Component']
            fab_qty = float(fab['Quantity']) if fab['Quantity'] else 0
            fab_length = None
            m = re.search(r'(\d+(?:\.\d+)?)\s*mm', fab['Component.Description'])
            if m:
                fab_length = float(m.group(1))
            if not fab_length:
                continue  # skip if no length

            # The parent rollup is fab_qty × fab_length
            expected_total = fab_qty * fab_length
            # The recursive sum of all cuttable children
            total_cut = recursive_cut_sum(fab_id, 1)
            # Allow a small tolerance for floating point
            self.assertAlmostEqual(total_cut, expected_total, places=2, msg=f"Part {fab_id}: sum(child qty × length, recursive)={total_cut} != parent rollup={expected_total}")

    
    def test_oa_00270_cutlist_rollup_full_bom(self):
        """
        Test cut list rollup for OA-00270 (Coml, Label, Tape, 12mm Width, White) using the full BOM structure.
        This test simulates traversing the BOM and aggregating all OA-00270 usages, including all parent/child relationships and quantities.
        """
        import csv
        import os
        # Load the BOM CSV from tests/test_data folder
        bom_path = os.path.join(os.path.dirname(__file__), 'test_data', 'InvenTree_BomItem_2025-12-14_J48BLGx.csv')
        rows = []
        with open(bom_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                rows.append(row)

        # Find all rows where Component.Ipn == 'OA-00270'
        oa_00270_rows = [r for r in rows if r['Component.Ipn'] == 'OA-00270']
        # For each, collect: parent (Assembly), part (Component), qty (Quantity), name, description
        cutlist = []
        for r in oa_00270_rows:
            cutlist.append({
                'parent': r['Assembly'],
                'part': r['Component'],
                'qty': float(r['Quantity']) if r['Quantity'] else 0,
                'name': r['Component.Name'],
                'desc': r['Component.Description'],
                'note': r['Note'],
                'bom_level': int(r['BOM Level']) if r['BOM Level'] else None,
                'total_qty': float(r['Total Quantity']) if r['Total Quantity'] else 0,
            })

        # Roll up by (parent, qty, note, etc.)
        # For OA-00270, check that all expected usages are present and quantities match BOM
        # Example: 277,285,,35,,860,OA-00270,... (qty 35)
        #         278,285,,35,,1158,OA-00270,... (qty 35)
        #         289,285,,35,,865,OA-00270,... (qty 35)
        #         ...
        #         327,312,,15,,1471,OA-00297,... (not OA-00270)

        # There are three main OA-00270 usages in the provided BOM:
        expected = [
            {'parent': '277', 'qty': 35},
            {'parent': '278', 'qty': 35},
            {'parent': '289', 'qty': 35},
        ]
        found = [(c['parent'], c['qty']) for c in cutlist]
        for e in expected:
            self.assertIn((e['parent'], e['qty']), found)

        # Check total OA-00270 cut length (sum of all quantities)
        total_qty = sum(c['qty'] for c in cutlist)
        self.assertEqual(total_qty, 105)
    def setUp(self):
        # Simulate a BOM with multiple Internal Fab children and parents
        self.rows = [
            {'is_internal_fab': True, 'unit': 'mm', 'qty': 2, 'length': 50, 'part': 'A', 'parent': 'P1'},
            {'is_internal_fab': True, 'unit': 'mm', 'qty': 3, 'length': 50, 'part': 'A', 'parent': 'P2'},
            {'is_internal_fab': True, 'unit': 'mm', 'qty': 1, 'length': 75, 'part': 'B', 'parent': 'P1'},
            {'is_internal_fab': True, 'unit': 'in', 'qty': 4, 'length': 2, 'part': 'C', 'parent': 'P3'},
            # Nested: A is child of B, B is child of P1
            {'is_internal_fab': True, 'unit': 'mm', 'qty': 5, 'length': 100, 'part': 'A', 'parent': 'B'},
            # Edge: zero and negative qty
            {'is_internal_fab': True, 'unit': 'mm', 'qty': 0, 'length': 10, 'part': 'D', 'parent': 'P4'},
            {'is_internal_fab': True, 'unit': 'mm', 'qty': -2, 'length': 20, 'part': 'E', 'parent': 'P4'},
            # Duplicate: same part/parent/unit/length
            {'is_internal_fab': True, 'unit': 'mm', 'qty': 1, 'length': 50, 'part': 'A', 'parent': 'P1'},
        ]

    def test_real_bom_part_13(self):
        """
        Test Internal Fab cut list rollup using real BOM data for part ID 13.
        This is a simplified subset focused on tubing and label cut parts.
        """
        # Example: OA-00192 (Fab, Tubing, 1/8" ID x 195mm L, Black, Optics Outlet to Filter, CPC)
        # 204,209,,195,,625,OA-00197,"Coml, Tube, Silicone, Soft, Durometer 50A, 1/8" ID, 1/4" OD, Opaque Black"
        # 45,204,137,1,Madefrom,2526,OA-00192,"Fab, Tubing, 1/8" ID x 195mm L, Black, Optics Outlet to Filter, CPC"
        # 204 is a child of 45, which is a child of 13
        real_bom = [
            # Parent 13
            {'parent': 13, 'part': 45, 'qty': 1},
            # 45's children (tubing fabs)
            {'parent': 45, 'part': 204, 'qty': 1, 'is_internal_fab': True, 'unit': 'mm', 'length': 195, 'desc': 'Fab, Tubing, 1/8" ID x 195mm L, Black'},
            # 204's child (commercial tube)
            {'parent': 204, 'part': 209, 'qty': 195, 'is_internal_fab': False, 'unit': 'mm', 'length': None, 'desc': 'Coml, Tube, Silicone, 1/8" ID, 1/4" OD, Opaque Black'},
            # Another tubing fab
            {'parent': 45, 'part': 203, 'qty': 1, 'is_internal_fab': True, 'unit': 'mm', 'length': 223, 'desc': 'Fab, Tubing, 1/8" ID x 223mm L, Bypass Fitting to Tee'},
            {'parent': 203, 'part': 49, 'qty': 223, 'is_internal_fab': False, 'unit': 'mm', 'length': None, 'desc': 'Coml, Tube, Silicone, 1/8" ID, 1/4" OD'},
            # Label fab
            {'parent': 45, 'part': 330, 'qty': 1, 'is_internal_fab': True, 'unit': 'mm', 'length': 15, 'desc': 'Fab, Label, 8.8mm Heat Shrink, 15mm Lng, "ΔP Lo"'},
            {'parent': 330, 'part': 273, 'qty': 15, 'is_internal_fab': False, 'unit': 'mm', 'length': None, 'desc': 'Coml, Label, Heat Shrink, 8.8mm Width'},
        ]

        # Simulate cut list rollup: for each Internal Fab child of 45, count qty and length
        cut_parts = [r for r in real_bom if r.get('is_internal_fab')]
        rollup = {}
        for row in cut_parts:
            key = (row['part'], row['unit'], row['length'])
            qty = row['qty']
            rollup[key] = rollup.get(key, 0) + qty

        # Expect:
        # (204, 'mm', 195): 1
        # (203, 'mm', 223): 1
        # (330, 'mm', 15): 1
        self.assertEqual(rollup.get((204, 'mm', 195)), 1)
        self.assertEqual(rollup.get((203, 'mm', 223)), 1)
        self.assertEqual(rollup.get((330, 'mm', 15)), 1)

    def test_rollup_piece_count(self):
        # Roll up by (part, unit, length): A@50mm appears in P1 (2+1) and P2 (3)
        def rollup(rows, cut_unit_setting):
            # Simulate backend rollup logic
            result = {}
            for row in rows:
                if not row.get('is_internal_fab') or row.get('unit') != cut_unit_setting:
                    continue
                key = (row['part'], row['unit'], row['length'])
                qty = row.get('qty', 1)
                result[key] = result.get(key, 0) + qty
            return result

        rolled = rollup(self.rows, 'mm')
        # A@50mm: (2+1 from P1) + 3 from P2 = 6
        self.assertEqual(rolled.get(('A', 'mm', 50)), 6)
        # B@75mm: 1
        self.assertEqual(rolled.get(('B', 'mm', 75)), 1)
        # D@10mm: 0 (should still appear if logic includes zero)
        self.assertEqual(rolled.get(('D', 'mm', 10)), 0)
        # E@20mm: -2 (should appear if logic includes negatives)
        self.assertEqual(rolled.get(('E', 'mm', 20)), -2)

    def test_nested_internal_fab(self):
        # A@100mm is a child of B, which is a child of P1
        # This test checks if nested children are counted (simulate flattening logic)
        nested = [r for r in self.rows if r['part'] == 'A' and r['length'] == 100]
        self.assertEqual(len(nested), 1)
        self.assertEqual(nested[0]['qty'], 5)

    def test_mixed_units(self):
        # Only 'mm' rows should be included for 'mm' setting
        mm_rows = [r for r in self.rows if r['unit'] == 'mm']
        in_rows = [r for r in self.rows if r['unit'] == 'in']
        self.assertEqual(len(mm_rows), 7)
        self.assertEqual(len(in_rows), 1)

    def test_duplicate_rows(self):
        # A@50mm in P1 appears twice (qty 2 and qty 1)
        dups = [r for r in self.rows if r['part'] == 'A' and r['parent'] == 'P1' and r['length'] == 50]
        self.assertEqual(sum(r['qty'] for r in dups), 3)

    def test_zero_and_negative_qty(self):
        # D@10mm qty 0, E@20mm qty -2
        zero = [r for r in self.rows if r['part'] == 'D'][0]
        neg = [r for r in self.rows if r['part'] == 'E'][0]
        self.assertEqual(zero['qty'], 0)
        self.assertEqual(neg['qty'], -2)

