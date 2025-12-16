"""
Unit tests for assembly parts with no children.

Tests the bug fix where assemblies/internal fab parts with no BOM items
were silently excluded from flat BOM.
"""

import unittest
from unittest.mock import MagicMock


class TestAssemblyNoChildren(unittest.TestCase):
    """Test handling of assembly parts with no BOM items defined."""

    def test_assembly_with_no_children_included_in_leaves(self):
        """Assembly part with no BOM items should appear in leaf parts list."""
        from flat_bom_generator.bom_traversal import get_leaf_parts_only

        # Create a tree representing an assembly with no children
        tree = {
            "part_id": 999,
            "ipn": "ASM-001",
            "part_name": "Empty Assembly",
            "description": "Test assembly with no BOM",
            "cumulative_qty": 1.0,
            "unit": "pcs",
            "is_assembly": True,
            "assembly": True,
            "purchaseable": False,
            "default_supplier_id": None,
            "part_type": "Assembly",
            "reference": "",
            "note": "",
            "level": 0,
            "children": [],  # No children!
        }

        leaves = get_leaf_parts_only(tree, expand_purchased_assemblies=False)

        # Should have exactly one leaf - the assembly itself
        self.assertEqual(len(leaves), 1)
        self.assertEqual(leaves[0]["part_id"], 999)
        self.assertEqual(leaves[0]["ipn"], "ASM-001")
        self.assertTrue(leaves[0].get("assembly_no_children"))

    def test_internal_fab_with_no_children_included_in_leaves(self):
        """Internal Fab part with no BOM items should appear in leaf parts list."""
        from flat_bom_generator.bom_traversal import get_leaf_parts_only

        tree = {
            "part_id": 888,
            "ipn": "IFAB-001",
            "part_name": "Empty Internal Fab",
            "description": "Test internal fab with no BOM",
            "cumulative_qty": 5.0,
            "unit": "pcs",
            "is_assembly": True,
            "assembly": True,
            "purchaseable": False,
            "default_supplier_id": None,
            "part_type": "Internal Fab",
            "reference": "",
            "note": "",
            "level": 1,
            "children": [],  # No children!
        }

        leaves = get_leaf_parts_only(tree, expand_purchased_assemblies=False)

        self.assertEqual(len(leaves), 1)
        self.assertEqual(leaves[0]["part_id"], 888)
        self.assertEqual(leaves[0]["part_type"], "Internal Fab")
        self.assertTrue(leaves[0].get("assembly_no_children"))

    def test_assembly_with_children_not_flagged(self):
        """Assembly with children should NOT be flagged as assembly_no_children."""
        from flat_bom_generator.bom_traversal import get_leaf_parts_only

        tree = {
            "part_id": 100,
            "ipn": "ASM-002",
            "part_name": "Normal Assembly",
            "description": "Assembly with children",
            "cumulative_qty": 1.0,
            "unit": "pcs",
            "is_assembly": True,
            "assembly": True,
            "purchaseable": False,
            "default_supplier_id": None,
            "part_type": "Assembly",
            "reference": "",
            "note": "",
            "level": 0,
            "children": [
                {
                    "part_id": 101,
                    "ipn": "COML-001",
                    "part_name": "Commercial Part",
                    "description": "Child part",
                    "cumulative_qty": 2.0,
                    "unit": "pcs",
                    "is_assembly": False,
                    "assembly": False,
                    "purchaseable": True,
                    "default_supplier_id": 5,
                    "part_type": "Coml",
                    "reference": "",
                    "note": "",
                    "level": 1,
                    "children": [],
                }
            ],
        }

        leaves = get_leaf_parts_only(tree, expand_purchased_assemblies=False)

        # Should have one leaf - the child commercial part, NOT the parent assembly
        self.assertEqual(len(leaves), 1)
        self.assertEqual(leaves[0]["part_id"], 101)
        self.assertEqual(leaves[0]["part_type"], "Coml")
        self.assertFalse(leaves[0].get("assembly_no_children", False))

    def test_non_assembly_leaf_not_affected(self):
        """Non-assembly leaf parts should work as before."""
        from flat_bom_generator.bom_traversal import get_leaf_parts_only

        tree = {
            "part_id": 200,
            "ipn": "COML-002",
            "part_name": "Commercial Part",
            "description": "Regular commercial part",
            "cumulative_qty": 10.0,
            "unit": "pcs",
            "is_assembly": False,
            "assembly": False,
            "purchaseable": True,
            "default_supplier_id": 3,
            "part_type": "Coml",
            "reference": "",
            "note": "",
            "level": 0,
            "children": [],
        }

        leaves = get_leaf_parts_only(tree, expand_purchased_assemblies=False)

        self.assertEqual(len(leaves), 1)
        self.assertEqual(leaves[0]["part_id"], 200)
        self.assertFalse(leaves[0].get("assembly_no_children", False))

    def test_purchased_assembly_no_children_not_flagged(self):
        """Purchased Assembly with no children is valid (purchased complete)."""
        from flat_bom_generator.bom_traversal import get_leaf_parts_only

        tree = {
            "part_id": 300,
            "ipn": "PASS-001",
            "part_name": "Purchased Assembly",
            "description": "Bought complete from supplier",
            "cumulative_qty": 1.0,
            "unit": "pcs",
            "is_assembly": True,
            "assembly": True,
            "purchaseable": True,
            "default_supplier_id": 7,
            "part_type": "Purchased Assy",
            "reference": "",
            "note": "",
            "level": 0,
            "children": [],  # No children is expected for purchased assemblies
        }

        leaves = get_leaf_parts_only(tree, expand_purchased_assemblies=False)

        self.assertEqual(len(leaves), 1)
        self.assertEqual(leaves[0]["part_id"], 300)
        # Should NOT have assembly_no_children flag (this is normal for purchased assy)
        self.assertFalse(leaves[0].get("assembly_no_children", False))


if __name__ == "__main__":
    unittest.main()
