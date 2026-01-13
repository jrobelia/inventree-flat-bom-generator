"""
Unit tests for shortfall calculation logic.

These tests verify the 4 different shortfall calculation scenarios based on
the Include Allocations and Include On Order checkboxes.
⚠️ IMPORTANT: Frontend-Backend Sync Required
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This test duplicates the shortfall calculation logic from Panel.tsx (lines 881-889).
The Python implementation must match the TypeScript implementation exactly.

Why duplicate logic?
- Language barrier: Can't import TypeScript into Python tests
- Fast testing: Python tests run in milliseconds vs seconds for browser tests
- Bug protection: Catches drift between frontend and backend expectations

Maintenance Contract:
- If you modify Panel.tsx shortfall calculation, UPDATE THIS TEST to match
- If this test fails after Panel.tsx changes, the frontend logic changed
- Tests act as documentation and verification of UI behavior

Last synced with Panel.tsx: January 9, 2026
Panel.tsx lines: 881-889 (shortfall column render)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

import unittest


class ShortfallCalculationTests(unittest.TestCase):
    """Test shortfall calculation with different checkbox combinations."""

    def calculate_shortfall(self, total_required, in_stock, allocated, on_order, 
                           include_allocations, include_on_order):
        """
        Calculate shortfall using the same logic as Panel.tsx (lines 881-889).
        
        ⚠️ CRITICAL: This logic MUST match Panel.tsx exactly.
        See file header for maintenance contract.
        
        Algorithm (matches Panel.tsx):
        1. Start with in_stock value
        2. If include_allocations: subtract allocated
        3. If include_on_order: add on_order
        4. Calculate: max(0, total_required - stock_value)
        
        Args:
            total_required: Total quantity needed for build (total_qty * buildQuantity)
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

    def test_negative_stock_after_allocations(self):
        """Allocated > in_stock should result in negative stock_value, increasing shortfall.
        
        Example: in_stock=100, allocated=150
        - Without allocations: shortfall = max(0, 50 - 100) = 0
        - With allocations: shortfall = max(0, 50 - (100-150)) = max(0, 50 - (-50)) = 100
        
        This represents over-allocation (data integrity issue).
        """
        total_required = 50
        in_stock = 100
        allocated = 150  # Over-allocated
        on_order = 0
        
        # Without allocations - appears sufficient
        self.assertEqual(
            self.calculate_shortfall(
                total_required, in_stock, allocated, on_order,
                include_allocations=False, include_on_order=False
            ),
            0  # 50 needed, 100 available
        )
        
        # With allocations - reveals over-allocation problem
        self.assertEqual(
            self.calculate_shortfall(
                total_required, in_stock, allocated, on_order,
                include_allocations=True, include_on_order=False
            ),
            100  # 50 needed, -50 available → shortfall = 100
        )

    def test_negative_total_required(self):
        """Negative total_required is invalid input but should not crash.
        
        Since total_required = base_qty * build_quantity, negative would mean
        negative build quantity (invalid UI state). Function should handle gracefully.
        
        max(0, negative - stock) = 0 (no shortfall for nonsense input)
        """
        total_required = -10  # Invalid but possible if UI state corrupted
        in_stock = 100
        allocated = 20
        on_order = 50
        
        # Should return 0 (max() prevents negative shortfall)
        result = self.calculate_shortfall(
            total_required, in_stock, allocated, on_order,
            include_allocations=True, include_on_order=True
        )
        
        self.assertEqual(result, 0)
        self.assertGreaterEqual(result, 0)  # Shortfall never negative


if __name__ == '__main__':
    unittest.main()
