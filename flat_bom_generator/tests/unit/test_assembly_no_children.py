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
        """Internal-supplier assembly with no BOM items is still a line item.

        The assembly_no_children warning applies only to assemblies with no
        default supplier - an internal-supplier assembly is a valid line item
        (nothing to expand, but the internal PO line still stands).
        """
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
            "default_supplier_id": 42,
            "internal_supplier": True,
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
        # NOT flagged - warning is only for assemblies with no default supplier
        self.assertFalse(leaves[0].get("assembly_no_children", False))

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

    def test_error_node_removed(self):
        """Error nodes can't exist - circular references raise ValueError.
        
        This test is kept to document that error node handling was removed
        because InvenTree prevents circular BOMs at database level, and our
        code now raises ValueError if somehow triggered."""
        # NOTE: This test used to check that error nodes were skipped.
        # Now that circular refs raise ValueError, error nodes can't exist.
        # Keeping test as documentation that this behavior changed.
        pass

    def test_uncategorized_non_assembly_fallback(self):
        """Non-assembly part with 'Other' type should still be included as leaf."""
        from flat_bom_generator.bom_traversal import get_leaf_parts_only

        tree = {
            "part_id": 500,
            "ipn": "MISC-001",
            "part_name": "Miscellaneous Part",
            "description": "Uncategorized part",
            "cumulative_qty": 3.0,
            "unit": "pcs",
            "is_assembly": False,
            "assembly": False,
            "purchaseable": True,
            "default_supplier_id": None,
            "part_type": "Other",  # Not Coml or Fab
            "reference": "",
            "note": "",
            "level": 1,
            "children": [],
        }

        leaves = get_leaf_parts_only(tree)

        # Should include as leaf despite "Other" category
        self.assertEqual(len(leaves), 1)
        self.assertEqual(leaves[0]["part_id"], 500)
        self.assertEqual(leaves[0]["part_type"], "Other")

    def test_note_text_is_never_parsed_for_cut_length(self):
        """BOM item notes are free text - no length extraction anywhere."""
        from flat_bom_generator.bom_traversal import get_leaf_parts_only

        tree = {
            "part_id": 600,
            "ipn": "BAR-001",
            "part_name": "Steel Bar",
            "description": "Raw material",
            "cumulative_qty": 2.0,
            "unit": "mm",
            "is_assembly": False,
            "assembly": False,
            "purchaseable": True,
            "default_supplier_id": 8,
            "part_type": "Coml",
            "reference": "",
            "note": "Cut to 350mm",  # Free text - must not be interpreted
            "level": 2,
            "children": [],
        }

        leaves = get_leaf_parts_only(tree)

        self.assertEqual(len(leaves), 1)
        self.assertEqual(leaves[0]["part_id"], 600)
        # cut_length is set only for internal-fab children - never from notes
        self.assertIsNone(leaves[0]["cut_length"])

    def test_internal_fab_child_preserves_cut_length(self):
        """Part from Internal Fab parent should preserve cut_length from tree."""
        from flat_bom_generator.bom_traversal import get_leaf_parts_only

        tree = {
            "part_id": 700,
            "ipn": "COML-003",
            "part_name": "Aluminum Extrusion",
            "description": "Child of Internal Fab",
            "cumulative_qty": 4.0,
            "cut_length": 120.0,  # Set by traverse_bom for Internal Fab children
            "unit": "pcs",
            "is_assembly": False,
            "assembly": False,
            "purchaseable": True,
            "default_supplier_id": 9,
            "part_type": "Coml",
            "reference": "",
            "note": "",
            "level": 2,
            "from_internal_fab_parent": True,  # Special flag
            "children": [],
        }

        leaves = get_leaf_parts_only(tree)

        self.assertEqual(len(leaves), 1)
        self.assertEqual(leaves[0]["part_id"], 700)
        self.assertEqual(leaves[0]["cut_length"], 120.0)  # Should preserve from tree

    def test_assembly_no_children_due_to_max_depth_not_flagged(self):
        """Assembly with no children due to max_depth should NOT be flagged."""
        from flat_bom_generator.bom_traversal import get_leaf_parts_only

        tree = {
            "part_id": 800,
            "ipn": "ASM-003",
            "part_name": "Deep Assembly",
            "description": "Assembly stopped by max_depth",
            "cumulative_qty": 1.0,
            "unit": "pcs",
            "is_assembly": True,
            "assembly": True,
            "purchaseable": False,
            "default_supplier_id": None,
            "part_type": "Assembly",
            "reference": "",
            "note": "",
            "level": 5,
            "max_depth_exceeded": True,  # Stopped by max_depth
            "children": [],  # No children due to depth limit
        }

        leaves = get_leaf_parts_only(tree)

        self.assertEqual(len(leaves), 1)
        self.assertEqual(leaves[0]["part_id"], 800)
        # Should NOT flag as assembly_no_children (it's expected behavior)
        self.assertFalse(leaves[0].get("assembly_no_children", False))
        # Should preserve max_depth_exceeded flag
        self.assertTrue(leaves[0].get("max_depth_exceeded", False))

    def test_purchased_assembly_expanded_when_flag_true(self):
        """Purchased Assembly with expand=True should recurse into children."""
        from flat_bom_generator.bom_traversal import get_leaf_parts_only

        tree = {
            "part_id": 900,
            "ipn": "PASS-002",
            "part_name": "Purchased Assembly to Expand",
            "description": "Should expand to show subcomponents",
            "cumulative_qty": 1.0,
            "unit": "pcs",
            "is_assembly": True,
            "assembly": True,
            "purchaseable": True,
            "default_supplier_id": 10,
            "part_type": "Purchased Assy",
            "reference": "",
            "note": "",
            "level": 0,
            "children": [
                {
                    "part_id": 901,
                    "ipn": "COML-004",
                    "part_name": "Commercial Subcomponent",
                    "description": "Child of purchased assembly",
                    "cumulative_qty": 3.0,
                    "unit": "pcs",
                    "is_assembly": False,
                    "assembly": False,
                    "purchaseable": True,
                    "default_supplier_id": 11,
                    "part_type": "Coml",
                    "reference": "",
                    "note": "",
                    "level": 1,
                    "children": [],
                }
            ],
        }

        # With expand_purchased_assemblies=True, should see child, not parent
        leaves = get_leaf_parts_only(tree, expand_purchased_assemblies=True)

        self.assertEqual(len(leaves), 1)
        self.assertEqual(leaves[0]["part_id"], 901)  # Child, not parent
        self.assertEqual(leaves[0]["ipn"], "COML-004")

    def test_fab_part_leaf(self):
        """Fab part (non-assembly) should be included as leaf."""
        from flat_bom_generator.bom_traversal import get_leaf_parts_only

        tree = {
            "part_id": 1000,
            "ipn": "FAB-001",
            "part_name": "Fabricated Bracket",
            "description": "Welded steel bracket",
            "cumulative_qty": 4.0,
            "unit": "pcs",
            "is_assembly": False,
            "assembly": False,
            "purchaseable": False,
            "default_supplier_id": None,
            "part_type": "Fab",
            "reference": "",
            "note": "",
            "level": 2,
            "children": [],
        }

        leaves = get_leaf_parts_only(tree)

        self.assertEqual(len(leaves), 1)
        self.assertEqual(leaves[0]["part_id"], 1000)
        self.assertEqual(leaves[0]["part_type"], "Fab")
        self.assertFalse(leaves[0].get("assembly_no_children", False))

    def test_mixed_tree_with_leaves_and_assemblies(self):
        """Tree with mix of leaf parts and assemblies that recurse."""
        from flat_bom_generator.bom_traversal import get_leaf_parts_only

        tree = {
            "part_id": 1200,
            "ipn": "ASM-004",
            "part_name": "Top Assembly",
            "description": "Mixed tree",
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
                    "part_id": 1201,
                    "ipn": "COML-005",
                    "part_name": "Commercial Part A",
                    "description": "Direct leaf child",
                    "cumulative_qty": 2.0,
                    "unit": "pcs",
                    "is_assembly": False,
                    "assembly": False,
                    "purchaseable": True,
                    "default_supplier_id": 13,
                    "part_type": "Coml",
                    "reference": "",
                    "note": "",
                    "level": 1,
                    "children": [],
                },
                {
                    "part_id": 1202,
                    "ipn": "ASM-005",
                    "part_name": "Sub-Assembly",
                    "description": "Nested assembly",
                    "cumulative_qty": 1.0,
                    "unit": "pcs",
                    "is_assembly": True,
                    "assembly": True,
                    "purchaseable": False,
                    "default_supplier_id": None,
                    "part_type": "Assembly",
                    "reference": "",
                    "note": "",
                    "level": 1,
                    "children": [
                        {
                            "part_id": 1203,
                            "ipn": "FAB-002",
                            "part_name": "Fabricated Part B",
                            "description": "Nested leaf",
                            "cumulative_qty": 4.0,
                            "unit": "pcs",
                            "is_assembly": False,
                            "assembly": False,
                            "purchaseable": False,
                            "default_supplier_id": None,
                            "part_type": "Fab",
                            "reference": "",
                            "note": "",
                            "level": 2,
                            "children": [],
                        }
                    ],
                },
            ],
        }

        leaves = get_leaf_parts_only(tree)

        # Should have 2 leaves: COML-005 and FAB-002 (not ASM-004 or ASM-005)
        self.assertEqual(len(leaves), 2)
        leaf_ids = [leaf["part_id"] for leaf in leaves]
        self.assertIn(1201, leaf_ids)  # COML-005
        self.assertIn(1203, leaf_ids)  # FAB-002
        self.assertNotIn(1200, leaf_ids)  # ASM-004 (top)
        self.assertNotIn(1202, leaf_ids)  # ASM-005 (sub)


class TestLineItemExpansionMatrix(unittest.TestCase):
    """The full line-item / expansion decision matrix.

    Expansion is driven by assembly status + primary supplier presence +
    supplier.is_internal - never by the part_type display label or the
    purchaseable flag.
    """

    def _node(self, **overrides):
        """Build a minimal tree node for matrix tests."""
        node = {
            "part_id": 1,
            "ipn": "N-001",
            "part_name": "Node",
            "description": "",
            "cumulative_qty": 1.0,
            "unit": "pcs",
            "is_assembly": False,
            "purchaseable": False,
            "default_supplier_id": None,
            "internal_supplier": False,
            "part_type": "Other",
            "reference": "",
            "note": "",
            "level": 1,
            "children": [],
        }
        node.update(overrides)
        return node

    def _child(self, **overrides):
        child = self._node(part_id=2, ipn="CHILD-001", part_name="Child",
                           purchaseable=True, part_type="Coml")
        child.update(overrides)
        return child

    def test_external_supplier_assembly_is_leaf_not_expanded(self):
        """External supplier -> line item, do not expand."""
        from flat_bom_generator.bom_traversal import get_leaf_parts_only

        tree = self._node(
            part_id=10, is_assembly=True, purchaseable=True,
            default_supplier_id=5, internal_supplier=False,
            part_type="Purchased Assy",
            children=[self._child()],
        )
        leaves = get_leaf_parts_only(tree, expand_purchased_assemblies=False)

        self.assertEqual(len(leaves), 1)
        self.assertEqual(leaves[0]["part_id"], 10)
        self.assertFalse(leaves[0]["from_internal_fab_parent"])

    def test_external_supplier_assembly_expands_with_toggle(self):
        """External supplier + expand_purchased_assemblies -> children only."""
        from flat_bom_generator.bom_traversal import get_leaf_parts_only

        tree = self._node(
            part_id=10, is_assembly=True, purchaseable=True,
            default_supplier_id=5, internal_supplier=False,
            part_type="Purchased Assy",
            children=[self._child()],
        )
        leaves = get_leaf_parts_only(tree, expand_purchased_assemblies=True)

        self.assertEqual(len(leaves), 1)
        self.assertEqual(leaves[0]["part_id"], 2)  # Child, not parent

    def test_internal_supplier_assembly_is_leaf_and_expanded(self):
        """Internal supplier -> line item AND expand."""
        from flat_bom_generator.bom_traversal import get_leaf_parts_only

        tree = self._node(
            part_id=20, is_assembly=True, purchaseable=True,
            default_supplier_id=7, internal_supplier=True,
            part_type="Internal Fab",
            children=[self._child(from_internal_fab_parent=True,
                                  cut_length=35.0, parent_part_id=20)],
        )
        leaves = get_leaf_parts_only(tree, expand_purchased_assemblies=False)

        self.assertEqual(len(leaves), 2)
        by_id = {leaf["part_id"]: leaf for leaf in leaves}
        self.assertIn(20, by_id)  # assembly itself is a line item
        self.assertIn(2, by_id)  # child expanded too
        self.assertTrue(by_id[20]["internal_supplier"])

    def test_unsourced_assembly_expands_only(self):
        """No supplier + assembly -> expand, not itself a line item."""
        from flat_bom_generator.bom_traversal import get_leaf_parts_only

        tree = self._node(
            part_id=30, is_assembly=True, purchaseable=False,
            default_supplier_id=None,
            part_type="Assy",
            children=[self._child()],
        )
        leaves = get_leaf_parts_only(tree, expand_purchased_assemblies=False)

        self.assertEqual(len(leaves), 1)
        self.assertEqual(leaves[0]["part_id"], 2)

    def test_unsourced_assembly_expands_even_when_purchaseable(self):
        """purchaseable=True must not suppress expansion of unsourced assemblies."""
        from flat_bom_generator.bom_traversal import get_leaf_parts_only

        tree = self._node(
            part_id=31, is_assembly=True, purchaseable=True,  # purchaseable!
            default_supplier_id=None,
            part_type="Assy",
            children=[self._child()],
        )
        leaves = get_leaf_parts_only(tree, expand_purchased_assemblies=False)

        self.assertEqual(len(leaves), 1)
        self.assertEqual(leaves[0]["part_id"], 2)

    def test_unsourced_assembly_no_children_flagged(self):
        """No supplier + assembly + no children -> line item with warning flag."""
        from flat_bom_generator.bom_traversal import get_leaf_parts_only

        tree = self._node(
            part_id=32, is_assembly=True, default_supplier_id=None,
            part_type="Assy", children=[],
        )
        leaves = get_leaf_parts_only(tree)

        self.assertEqual(len(leaves), 1)
        self.assertTrue(leaves[0].get("assembly_no_children"))

    def test_display_label_does_not_change_expansion(self):
        """Same supplier state, different labels -> identical leaf outcome."""
        from flat_bom_generator.bom_traversal import get_leaf_parts_only

        for label in ("Fab", "Coml", "Other", "Assy"):
            tree = self._node(
                part_id=40, is_assembly=True,
                default_supplier_id=None,
                part_type=label,  # Label should be irrelevant
                children=[self._child()],
            )
            leaves = get_leaf_parts_only(tree)
            self.assertEqual(
                [leaf["part_id"] for leaf in leaves],
                [2],
                f"part_type={label} changed expansion behavior",
            )

    def test_non_assembly_is_always_line_item(self):
        """Non-assembly parts are line items regardless of supplier state."""
        from flat_bom_generator.bom_traversal import get_leaf_parts_only

        for supplier_id, internal in ((None, False), (5, False), (5, True)):
            tree = self._node(
                part_id=50, is_assembly=False,
                default_supplier_id=supplier_id,
                internal_supplier=internal,
                part_type="Coml",
            )
            leaves = get_leaf_parts_only(tree)
            self.assertEqual(len(leaves), 1)
            self.assertEqual(leaves[0]["part_id"], 50)


if __name__ == "__main__":
    unittest.main()
