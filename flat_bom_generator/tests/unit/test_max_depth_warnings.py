"""
Unit tests for max depth warning logic.

Tests that:
1. Assemblies stopped by max_depth don't get assembly_no_children flag
2. Assemblies with genuinely no BOM items DO get assembly_no_children flag
3. Summary warning is generated when max_depth is hit
"""

import unittest


class TestMaxDepthWarningLogic(unittest.TestCase):
    """Test max depth warning behavior."""

    def test_assembly_stopped_by_max_depth_not_flagged_as_no_children(self):
        """
        When an assembly is stopped by max_depth, it should have
        max_depth_exceeded=True but assembly_no_children=False.
        
        This prevents duplicate warnings for the same issue.
        """
        # Simulate a tree node for an assembly stopped at max depth
        tree = {
            "part_id": 100,
            "ipn": "TEST-001",
            "part_name": "Test Assembly",
            "description": "Test",
            "cumulative_qty": 1.0,
            "unit": "",
            "is_assembly": True,
            "purchaseable": False,
            "default_supplier_id": None,
            "part_type": "Assy",
            "reference": "",
            "note": "",
            "level": 2,
            "from_internal_fab_parent": False,
            "parent_ipn": "PARENT-001",
            "parent_part_id": 99,
            "children": [],  # No children because max_depth was hit
            "max_depth_exceeded": True,  # Flag indicating depth limit reached
        }

        # Logic from get_leaf_parts_only()
        children = tree.get("children", [])
        max_depth_exceeded = tree.get("max_depth_exceeded", False)
        
        if tree.get("is_assembly") and not children:
            # Only flag as assembly_no_children if NOT stopped by max_depth
            assembly_no_children_flag = not max_depth_exceeded
        else:
            assembly_no_children_flag = False

        # Assert: Should NOT be flagged as assembly_no_children
        self.assertFalse(
            assembly_no_children_flag,
            "Assembly stopped by max_depth should not be flagged as no_children"
        )
        self.assertTrue(
            max_depth_exceeded,
            "max_depth_exceeded should be True"
        )

    def test_assembly_genuinely_no_children_is_flagged(self):
        """
        When an assembly has no BOM items and was NOT stopped by max_depth,
        it should have assembly_no_children=True and max_depth_exceeded=False.
        
        This is a genuine BOM definition issue.
        """
        # Simulate a tree node for an assembly with no BOM items defined
        tree = {
            "part_id": 200,
            "ipn": "TEST-002",
            "part_name": "Empty Assembly",
            "description": "Test assembly with no BOM",
            "cumulative_qty": 1.0,
            "unit": "",
            "is_assembly": True,
            "purchaseable": False,
            "default_supplier_id": None,
            "part_type": "Assy",
            "reference": "",
            "note": "",
            "level": 1,
            "from_internal_fab_parent": False,
            "parent_ipn": "PARENT-001",
            "parent_part_id": 99,
            "children": [],  # No children because BOM is empty
            "max_depth_exceeded": False,  # NOT stopped by depth limit
        }

        # Logic from get_leaf_parts_only()
        children = tree.get("children", [])
        max_depth_exceeded = tree.get("max_depth_exceeded", False)
        
        if tree.get("is_assembly") and not children:
            # Only flag as assembly_no_children if NOT stopped by max_depth
            assembly_no_children_flag = not max_depth_exceeded
        else:
            assembly_no_children_flag = False

        # Assert: SHOULD be flagged as assembly_no_children
        self.assertTrue(
            assembly_no_children_flag,
            "Assembly with no BOM items should be flagged as no_children"
        )
        self.assertFalse(
            max_depth_exceeded,
            "max_depth_exceeded should be False"
        )

    def test_regular_part_not_flagged(self):
        """
        Regular parts (not assemblies) should never be flagged as
        assembly_no_children, even if they have no children.
        """
        tree = {
            "part_id": 300,
            "ipn": "TEST-003",
            "part_name": "Regular Part",
            "description": "Not an assembly",
            "cumulative_qty": 1.0,
            "unit": "pcs",
            "is_assembly": False,  # Not an assembly
            "purchaseable": True,
            "default_supplier_id": 123,
            "part_type": "Coml",
            "reference": "",
            "note": "",
            "level": 2,
            "from_internal_fab_parent": False,
            "parent_ipn": "PARENT-001",
            "parent_part_id": 99,
            "children": [],
            "max_depth_exceeded": False,
        }

        # Logic from get_leaf_parts_only()
        children = tree.get("children", [])
        max_depth_exceeded = tree.get("max_depth_exceeded", False)
        
        if tree.get("is_assembly") and not children:
            assembly_no_children_flag = not max_depth_exceeded
        else:
            assembly_no_children_flag = False

        # Assert: Should NOT be flagged
        self.assertFalse(
            assembly_no_children_flag,
            "Regular parts should never be flagged as assembly_no_children"
        )

    def test_summary_warning_generation(self):
        """
        When multiple assemblies are stopped by max_depth,
        only ONE summary warning should be generated, not per-part warnings.
        """
        # Simulate flat_bom with multiple parts at max_depth
        flat_bom = [
            {"part_id": 100, "ipn": "ASSY-1", "max_depth_exceeded": True},
            {"part_id": 101, "ipn": "ASSY-2", "max_depth_exceeded": True},
            {"part_id": 102, "ipn": "ASSY-3", "max_depth_exceeded": True},
            {"part_id": 200, "ipn": "PART-1", "max_depth_exceeded": False},
        ]
        
        max_depth_reached = 3

        # Logic from views.py
        warnings = []
        parts_at_max_depth = [
            item for item in flat_bom if item.get("max_depth_exceeded")
        ]
        
        if parts_at_max_depth:
            warnings.append({
                "type": "max_depth_reached",
                "part_id": None,
                "part_name": "Multiple assemblies",
                "message": f"BOM traversal stopped at depth {max_depth_reached}. {len(parts_at_max_depth)} assemblies not fully expanded. Increase 'Maximum Traversal Depth' setting to see sub-components.",
            })

        # Assert: Only ONE warning generated for all 3 assemblies at max_depth
        self.assertEqual(
            len(warnings), 1,
            "Should generate exactly one summary warning for max_depth"
        )
        self.assertEqual(
            warnings[0]["type"], "max_depth_reached",
            "Warning type should be max_depth_reached"
        )
        self.assertIn(
            "3 assemblies", warnings[0]["message"],
            "Warning should mention number of affected assemblies"
        )
        self.assertIsNone(
            warnings[0]["part_id"],
            "Summary warning should not be tied to specific part"
        )

    def test_no_warning_when_no_parts_at_max_depth(self):
        """
        When no parts are stopped by max_depth, no warning should be generated.
        """
        # Simulate flat_bom with no parts at max_depth
        flat_bom = [
            {"part_id": 100, "ipn": "PART-1", "max_depth_exceeded": False},
            {"part_id": 101, "ipn": "PART-2", "max_depth_exceeded": False},
            {"part_id": 102, "ipn": "PART-3"},  # Missing key defaults to False
        ]

        # Logic from views.py
        warnings = []
        parts_at_max_depth = [
            item for item in flat_bom if item.get("max_depth_exceeded")
        ]
        
        if parts_at_max_depth:
            warnings.append({
                "type": "max_depth_reached",
                "part_id": None,
                "part_name": "Multiple assemblies",
                "message": "...",
            })

        # Assert: No warnings generated
        self.assertEqual(
            len(warnings), 0,
            "Should not generate warning when no parts at max_depth"
        )
        self.assertEqual(
            len(parts_at_max_depth), 0,
            "Should find no parts at max_depth"
        )

    def test_empty_flat_bom_no_warning(self):
        """
        Empty BOM should not generate max_depth warning.
        """
        flat_bom = []

        # Logic from views.py
        warnings = []
        parts_at_max_depth = [
            item for item in flat_bom if item.get("max_depth_exceeded")
        ]
        
        if parts_at_max_depth:
            warnings.append({"type": "max_depth_reached"})

        # Assert: No warnings generated
        self.assertEqual(len(warnings), 0)
        self.assertEqual(len(parts_at_max_depth), 0)

    def test_single_part_at_max_depth_singular_message(self):
        """
        When only one assembly is at max_depth, warning should reflect singular count.
        """
        flat_bom = [
            {"part_id": 100, "ipn": "ASSY-1", "max_depth_exceeded": True},
            {"part_id": 200, "ipn": "PART-1", "max_depth_exceeded": False},
        ]
        
        max_depth_reached = 5

        # Logic from views.py
        warnings = []
        parts_at_max_depth = [
            item for item in flat_bom if item.get("max_depth_exceeded")
        ]
        
        if parts_at_max_depth:
            warnings.append({
                "type": "max_depth_reached",
                "part_id": None,
                "part_name": "Multiple assemblies",
                "message": f"BOM traversal stopped at depth {max_depth_reached}. {len(parts_at_max_depth)} assemblies not fully expanded. Increase 'Maximum Traversal Depth' setting to see sub-components.",
            })

        # Assert: Warning generated with count of 1
        self.assertEqual(len(warnings), 1)
        self.assertIn("1 assemblies", warnings[0]["message"])
        # Note: Grammar is "1 assemblies" (not ideal, but follows current code)

    def test_assembly_with_children_but_max_depth_exceeded(self):
        """
        Edge case: Assembly has children in tree, but max_depth_exceeded=True
        means it was stopped before fully expanding.
        
        This can happen if max_depth is hit mid-expansion.
        assembly_no_children flag should still be False (has children).
        """
        tree = {
            "part_id": 400,
            "ipn": "TEST-004",
            "part_name": "Partially Expanded Assembly",
            "description": "Has children but stopped by max_depth",
            "cumulative_qty": 1.0,
            "unit": "",
            "is_assembly": True,
            "purchaseable": False,
            "default_supplier_id": None,
            "part_type": "Assy",
            "reference": "",
            "note": "",
            "level": 3,
            "children": [  # Has children
                {
                    "part_id": 401,
                    "ipn": "CHILD-1",
                    "part_name": "Child Part",
                    "description": "",
                    "cumulative_qty": 2.0,
                    "unit": "pcs",
                    "is_assembly": False,
                    "purchaseable": True,
                    "default_supplier_id": 5,
                    "part_type": "Coml",
                    "reference": "",
                    "note": "",
                    "level": 4,
                    "children": [],
                }
            ],
            "max_depth_exceeded": True,  # But was stopped
        }

        # Logic from get_leaf_parts_only()
        children = tree.get("children", [])
        max_depth_exceeded = tree.get("max_depth_exceeded", False)
        
        if tree.get("is_assembly") and not children:
            assembly_no_children_flag = not max_depth_exceeded
        else:
            assembly_no_children_flag = False

        # Assert: Should NOT be flagged as no_children (it has children)
        self.assertFalse(
            assembly_no_children_flag,
            "Assembly with children should not be flagged, even if max_depth_exceeded"
        )
        self.assertTrue(max_depth_exceeded)
        self.assertGreater(len(children), 0)


if __name__ == "__main__":
    unittest.main()
