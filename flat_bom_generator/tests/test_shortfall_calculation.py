"""
Unit tests for shortfall calculation logic.

These tests verify the 4 different shortfall calculation scenarios based on
the Include Allocations and Include On Order checkboxes.
"""

import unittest


class ShortfallCalculationTests(unittest.TestCase):
    """Test shortfall calculation with different checkbox combinations."""

    def calculate_shortfall(self, total_required, in_stock, allocated, on_order, 
                           include_allocations, include_on_order):
        """
        Calculate shortfall using the same logic as Panel.tsx.
        
        Args:
            total_required: Total quantity needed for build
            in_stock: Current stock level
            allocated: Stock already allocated to other builds/orders
            on_order: Stock on order from suppliers
            include_allocations: Whether to subtract allocations from stock
            include_on_order: Whether to add on order to available stock
            
        Returns:
            Shortfall amount (0 if no shortfall)
        """
        stock_value = in_stock
        
        if include_allocations:
            stock_value -= allocated
        
        if include_on_order:
            stock_value += on_order
        
        return max(0, total_required - stock_value)

    def test_scenario_1_neither_checked(self):
        """
        Scenario 1: Neither checkbox checked
        Formula: max(0, total_required - in_stock)
        
        Example: Need 100, have 50 in stock
        Expected: 50 shortfall
        """
        shortfall = self.calculate_shortfall(
            total_required=100,
            in_stock=50,
            allocated=10,
            on_order=20,
            include_allocations=False,
            include_on_order=False
        )
        self.assertEqual(shortfall, 50)

    def test_scenario_2_allocations_only(self):
        """
        Scenario 2: Only Include Allocations checked
        Formula: max(0, total_required - (in_stock - allocated))
        
        Example: Need 100, have 50 in stock, 10 allocated
        Expected: 60 shortfall (100 - (50 - 10) = 60)
        """
        shortfall = self.calculate_shortfall(
            total_required=100,
            in_stock=50,
            allocated=10,
            on_order=20,
            include_allocations=True,
            include_on_order=False
        )
        self.assertEqual(shortfall, 60)

    def test_scenario_3_on_order_only(self):
        """
        Scenario 3: Only Include On Order checked
        Formula: max(0, total_required - (in_stock + on_order))
        
        Example: Need 100, have 50 in stock, 20 on order
        Expected: 30 shortfall (100 - (50 + 20) = 30)
        """
        shortfall = self.calculate_shortfall(
            total_required=100,
            in_stock=50,
            allocated=10,
            on_order=20,
            include_allocations=False,
            include_on_order=True
        )
        self.assertEqual(shortfall, 30)

    def test_scenario_4_both_checked(self):
        """
        Scenario 4: Both checkboxes checked
        Formula: max(0, total_required - (in_stock - allocated + on_order))
        
        Example: Need 100, have 50 in stock, 10 allocated, 20 on order
        Expected: 40 shortfall (100 - (50 - 10 + 20) = 40)
        """
        shortfall = self.calculate_shortfall(
            total_required=100,
            in_stock=50,
            allocated=10,
            on_order=20,
            include_allocations=True,
            include_on_order=True
        )
        self.assertEqual(shortfall, 40)

    def test_no_shortfall_scenario(self):
        """
        Test when there's sufficient stock (no shortfall).
        
        Example: Need 100, have 150 in stock
        Expected: 0 shortfall
        """
        shortfall = self.calculate_shortfall(
            total_required=100,
            in_stock=150,
            allocated=0,
            on_order=0,
            include_allocations=False,
            include_on_order=False
        )
        self.assertEqual(shortfall, 0)

    def test_exact_match_no_shortfall(self):
        """
        Test when stock exactly matches requirement.
        
        Example: Need 100, have exactly 100 in stock
        Expected: 0 shortfall
        """
        shortfall = self.calculate_shortfall(
            total_required=100,
            in_stock=100,
            allocated=0,
            on_order=0,
            include_allocations=False,
            include_on_order=False
        )
        self.assertEqual(shortfall, 0)

    def test_high_allocations_creates_shortfall(self):
        """
        Test that high allocations can create/increase shortfall.
        
        Example: Need 50, have 100 in stock, but 80 allocated
        Without allocations: 0 shortfall
        With allocations: 30 shortfall (50 - (100 - 80) = 30)
        """
        # Without allocations - no shortfall
        shortfall_without = self.calculate_shortfall(
            total_required=50,
            in_stock=100,
            allocated=80,
            on_order=0,
            include_allocations=False,
            include_on_order=False
        )
        self.assertEqual(shortfall_without, 0)

        # With allocations - creates shortfall
        shortfall_with = self.calculate_shortfall(
            total_required=50,
            in_stock=100,
            allocated=80,
            on_order=0,
            include_allocations=True,
            include_on_order=False
        )
        self.assertEqual(shortfall_with, 30)

    def test_on_order_eliminates_shortfall(self):
        """
        Test that incoming stock can eliminate shortfall.
        
        Example: Need 100, have 50 in stock, 60 on order
        Without on order: 50 shortfall
        With on order: 0 shortfall (100 - (50 + 60) = -10, max with 0 = 0)
        """
        # Without on order - has shortfall
        shortfall_without = self.calculate_shortfall(
            total_required=100,
            in_stock=50,
            allocated=0,
            on_order=60,
            include_allocations=False,
            include_on_order=False
        )
        self.assertEqual(shortfall_without, 50)

        # With on order - no shortfall
        shortfall_with = self.calculate_shortfall(
            total_required=100,
            in_stock=50,
            allocated=0,
            on_order=60,
            include_allocations=False,
            include_on_order=True
        )
        self.assertEqual(shortfall_with, 0)

    def test_zero_values(self):
        """
        Test edge case with all zero values.
        
        Example: Need 0, have 0 in stock
        Expected: 0 shortfall
        """
        shortfall = self.calculate_shortfall(
            total_required=0,
            in_stock=0,
            allocated=0,
            on_order=0,
            include_allocations=False,
            include_on_order=False
        )
        self.assertEqual(shortfall, 0)

    def test_decimal_quantities(self):
        """
        Test with decimal quantities (common for units like meters, kg, etc.).
        
        Example: Need 10.5, have 5.25 in stock, 2.5 allocated, 3.0 on order
        With both checked: 10.5 - (5.25 - 2.5 + 3.0) = 4.75 shortfall
        """
        shortfall = self.calculate_shortfall(
            total_required=10.5,
            in_stock=5.25,
            allocated=2.5,
            on_order=3.0,
            include_allocations=True,
            include_on_order=True
        )
        self.assertAlmostEqual(shortfall, 4.75, places=2)

    def test_realistic_scenario(self):
        """
        Test a realistic production scenario.
        
        Build 10 units, each needs 5 parts = 50 total needed
        In stock: 30 parts
        Allocated to other builds: 8 parts
        On order from supplier: 25 parts
        
        All scenarios:
        - Neither: 50 - 30 = 20 shortfall
        - Allocations only: 50 - (30 - 8) = 28 shortfall
        - On order only: 50 - (30 + 25) = 0 shortfall
        - Both: 50 - (30 - 8 + 25) = 3 shortfall
        """
        # Neither checked
        self.assertEqual(
            self.calculate_shortfall(50, 30, 8, 25, False, False),
            20
        )
        
        # Allocations only
        self.assertEqual(
            self.calculate_shortfall(50, 30, 8, 25, True, False),
            28
        )
        
        # On order only
        self.assertEqual(
            self.calculate_shortfall(50, 30, 8, 25, False, True),
            0
        )
        
        # Both checked
        self.assertEqual(
            self.calculate_shortfall(50, 30, 8, 25, True, True),
            3
        )


if __name__ == '__main__':
    unittest.main()
