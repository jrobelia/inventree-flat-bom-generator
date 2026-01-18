import { describe, expect, it } from 'vitest';

import type { BomItem } from '../types/BomTypes';
import { useShortfallCalculation } from './useShortfallCalculation';

/**
 * Unit tests for useShortfallCalculation hook
 *
 * Tests shortfall calculations and statistics counting with various
 * buildQuantity, includeAllocations, and includeOnOrder configurations.
 */

// Helper: Create mock BOM item with specified stock values
function createMockItem(
  in_stock: number,
  allocated: number,
  on_order: number,
  total_qty: number = 1
): BomItem {
  return {
    part_id: 1,
    ipn: 'TEST-001',
    part_name: 'Test Part',
    full_name: 'TEST-001 | Test Part',
    description: 'Test description',
    part_type: 'Coml',
    total_qty,
    unit: 'pcs',
    is_assembly: false,
    purchaseable: true,
    has_default_supplier: true,
    default_supplier_name: 'Test Supplier',
    in_stock,
    allocated,
    on_order,
    available: in_stock - allocated,
    image: undefined,
    thumbnail: undefined,
    link: '/part/1/'
  };
}

describe('useShortfallCalculation', () => {
  describe('calculateShortfall', () => {
    it('should calculate basic shortfall with no toggles', () => {
      const { calculateShortfall } = useShortfallCalculation(1, false, false);

      const item = createMockItem(10, 5, 3, 1); // in_stock=10, allocated=5, on_order=3, total_qty=1
      const shortfall = calculateShortfall(item);

      // buildQuantity=1, no allocations, no on_order
      // stockValue = 10 (in_stock only)
      // totalRequired = 1 * 1 = 1
      // shortfall = 10 - 1 = 9
      expect(shortfall).toBe(9);
    });

    it('should calculate shortfall with allocations enabled', () => {
      const { calculateShortfall } = useShortfallCalculation(1, true, false);

      const item = createMockItem(10, 5, 3, 1);
      const shortfall = calculateShortfall(item);

      // stockValue = 10 - 5 (allocated) = 5
      // totalRequired = 1 * 1 = 1
      // shortfall = 5 - 1 = 4
      expect(shortfall).toBe(4);
    });

    it('should calculate shortfall with on order enabled', () => {
      const { calculateShortfall } = useShortfallCalculation(1, false, true);

      const item = createMockItem(10, 5, 3, 1);
      const shortfall = calculateShortfall(item);

      // stockValue = 10 + 3 (on_order) = 13
      // totalRequired = 1 * 1 = 1
      // shortfall = 13 - 1 = 12
      expect(shortfall).toBe(12);
    });

    it('should calculate shortfall with both toggles enabled', () => {
      const { calculateShortfall } = useShortfallCalculation(1, true, true);

      const item = createMockItem(10, 5, 3, 1);
      const shortfall = calculateShortfall(item);

      // stockValue = 10 - 5 (allocated) + 3 (on_order) = 8
      // totalRequired = 1 * 1 = 1
      // shortfall = 8 - 1 = 7
      expect(shortfall).toBe(7);
    });

    it('should multiply required quantity by build quantity', () => {
      const { calculateShortfall } = useShortfallCalculation(10, false, false);

      const item = createMockItem(50, 0, 0, 3); // total_qty = 3
      const shortfall = calculateShortfall(item);

      // stockValue = 50
      // totalRequired = 3 * 10 (buildQuantity) = 30
      // shortfall = 50 - 30 = 20
      expect(shortfall).toBe(20);
    });

    it('should return negative shortfall when insufficient stock', () => {
      const { calculateShortfall } = useShortfallCalculation(5, false, false);

      const item = createMockItem(10, 0, 0, 3); // total_qty = 3
      const shortfall = calculateShortfall(item);

      // stockValue = 10
      // totalRequired = 3 * 5 (buildQuantity) = 15
      // shortfall = 10 - 15 = -5 (need 5 more)
      expect(shortfall).toBe(-5);
    });

    it('should return negative shortfall with allocations reducing stock', () => {
      const { calculateShortfall } = useShortfallCalculation(1, true, false);

      const item = createMockItem(10, 8, 0, 5); // total_qty = 5
      const shortfall = calculateShortfall(item);

      // stockValue = 10 - 8 (allocated) = 2
      // totalRequired = 5 * 1 = 5
      // shortfall = 2 - 5 = -3 (need 3 more)
      expect(shortfall).toBe(-3);
    });

    it('should handle zero stock correctly', () => {
      const { calculateShortfall } = useShortfallCalculation(2, false, false);

      const item = createMockItem(0, 0, 0, 1);
      const shortfall = calculateShortfall(item);

      // stockValue = 0
      // totalRequired = 1 * 2 = 2
      // shortfall = 0 - 2 = -2
      expect(shortfall).toBe(-2);
    });

    it('should handle decimal quantities correctly', () => {
      const { calculateShortfall } = useShortfallCalculation(1, false, false);

      const item = createMockItem(5.5, 0.5, 1.2, 2.3);
      const shortfall = calculateShortfall(item);

      // stockValue = 5.5
      // totalRequired = 2.3 * 1 = 2.3
      // shortfall = 5.5 - 2.3 = 3.2
      expect(shortfall).toBeCloseTo(3.2);
    });
  });

  describe('countNeedToOrder', () => {
    it('should count parts with insufficient stock', () => {
      const { countNeedToOrder } = useShortfallCalculation(1, false, false);

      const items = [
        createMockItem(10, 0, 0, 5), // stock=10, required=5 → OK (surplus)
        createMockItem(5, 0, 0, 10), // stock=5, required=10 → NEED (shortfall=-5)
        createMockItem(8, 0, 0, 8), // stock=8, required=8 → OK (exact)
        createMockItem(2, 0, 0, 5) // stock=2, required=5 → NEED (shortfall=-3)
      ];

      const count = countNeedToOrder(items);
      expect(count).toBe(2); // items[1] and items[3]
    });

    it('should respect build quantity multiplier', () => {
      const { countNeedToOrder } = useShortfallCalculation(3, false, false);

      const items = [
        createMockItem(20, 0, 0, 5), // stock=20, required=5*3=15 → OK
        createMockItem(10, 0, 0, 5), // stock=10, required=5*3=15 → NEED
        createMockItem(15, 0, 0, 5) // stock=15, required=5*3=15 → OK (exact)
      ];

      const count = countNeedToOrder(items);
      expect(count).toBe(1); // items[1]
    });

    it('should respect includeAllocations toggle', () => {
      const { countNeedToOrder } = useShortfallCalculation(1, true, false);

      const items = [
        createMockItem(10, 3, 0, 5), // available=10-3=7, required=5 → OK
        createMockItem(10, 8, 0, 5) // available=10-8=2, required=5 → NEED
      ];

      const count = countNeedToOrder(items);
      expect(count).toBe(1); // items[1]
    });

    it('should respect includeOnOrder toggle', () => {
      const { countNeedToOrder } = useShortfallCalculation(1, false, true);

      const items = [
        createMockItem(5, 0, 10, 10), // available=5+10=15, required=10 → OK
        createMockItem(5, 0, 2, 10) // available=5+2=7, required=10 → NEED
      ];

      const count = countNeedToOrder(items);
      expect(count).toBe(1); // items[1]
    });

    it('should return 0 for empty array', () => {
      const { countNeedToOrder } = useShortfallCalculation(1, false, false);
      expect(countNeedToOrder([])).toBe(0);
    });

    it('should handle all parts OK scenario', () => {
      const { countNeedToOrder } = useShortfallCalculation(1, false, false);

      const items = [
        createMockItem(100, 0, 0, 10),
        createMockItem(50, 0, 0, 5),
        createMockItem(20, 0, 0, 1)
      ];

      expect(countNeedToOrder(items)).toBe(0);
    });
  });

  describe('countOutOfStock', () => {
    it('should count parts with zero or negative stock', () => {
      const items = [
        createMockItem(10, 0, 0, 1), // in_stock > 0 → NOT counted
        createMockItem(0, 0, 0, 1), // in_stock = 0 → COUNTED
        createMockItem(5, 0, 0, 1), // in_stock > 0 → NOT counted
        createMockItem(-1, 0, 0, 1) // in_stock < 0 → COUNTED (shouldn't happen but handle it)
      ];

      const { countOutOfStock } = useShortfallCalculation(1, false, false);
      const count = countOutOfStock(items);

      expect(count).toBe(2); // items[1] and items[3]
    });

    it('should not be affected by toggles (uses raw in_stock)', () => {
      const items = [
        createMockItem(0, 5, 10, 1) // in_stock=0, but allocated=5, on_order=10
      ];

      // Try with all toggle combinations - should always count as out of stock
      expect(
        useShortfallCalculation(1, false, false).countOutOfStock(items)
      ).toBe(1);
      expect(
        useShortfallCalculation(1, true, false).countOutOfStock(items)
      ).toBe(1);
      expect(
        useShortfallCalculation(1, false, true).countOutOfStock(items)
      ).toBe(1);
      expect(
        useShortfallCalculation(1, true, true).countOutOfStock(items)
      ).toBe(1);
    });

    it('should return 0 for empty array', () => {
      const { countOutOfStock } = useShortfallCalculation(1, false, false);
      expect(countOutOfStock([])).toBe(0);
    });

    it('should handle all parts in stock scenario', () => {
      const items = [
        createMockItem(10, 0, 0, 1),
        createMockItem(5, 0, 0, 1),
        createMockItem(1, 0, 0, 1) // Even 1 counts as "in stock"
      ];

      const { countOutOfStock } = useShortfallCalculation(1, false, false);
      expect(countOutOfStock(items)).toBe(0);
    });
  });

  describe('countOnOrder', () => {
    it('should count parts with positive on_order', () => {
      const items = [
        createMockItem(10, 0, 5, 1), // on_order > 0 → COUNTED
        createMockItem(5, 0, 0, 1), // on_order = 0 → NOT counted
        createMockItem(0, 0, 10, 1), // on_order > 0 → COUNTED
        createMockItem(20, 0, 1, 1) // on_order > 0 → COUNTED
      ];

      const { countOnOrder } = useShortfallCalculation(1, false, false);
      const count = countOnOrder(items);

      expect(count).toBe(3); // items[0], items[2], items[3]
    });

    it('should not be affected by toggles (uses raw on_order)', () => {
      const items = [
        createMockItem(10, 5, 3, 1) // on_order=3
      ];

      // Try with all toggle combinations - should always count as "on order"
      expect(useShortfallCalculation(1, false, false).countOnOrder(items)).toBe(
        1
      );
      expect(useShortfallCalculation(1, true, false).countOnOrder(items)).toBe(
        1
      );
      expect(useShortfallCalculation(1, false, true).countOnOrder(items)).toBe(
        1
      );
      expect(useShortfallCalculation(1, true, true).countOnOrder(items)).toBe(
        1
      );
    });

    it('should return 0 for empty array', () => {
      const { countOnOrder } = useShortfallCalculation(1, false, false);
      expect(countOnOrder([])).toBe(0);
    });

    it('should handle all parts with no orders scenario', () => {
      const items = [
        createMockItem(10, 0, 0, 1),
        createMockItem(5, 0, 0, 1),
        createMockItem(20, 0, 0, 1)
      ];

      const { countOnOrder } = useShortfallCalculation(1, false, false);
      expect(countOnOrder(items)).toBe(0);
    });
  });
});
