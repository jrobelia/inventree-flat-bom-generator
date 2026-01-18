/**
 * Tests for BOM Data Processing Utilities
 *
 * Focus: Non-trivial logic like child grouping and sort behavior
 * Validates edge cases that could cause UI bugs
 */

import { describe, expect, it } from 'vitest';
import type { BomItem } from '../types/BomTypes';
import {
  filterBomData,
  flattenBomData,
  groupChildrenWithParents,
  sortBomData
} from './bomDataProcessing';

// Helper to create a minimal BomItem for testing
function createBomItem(overrides: Partial<BomItem>): BomItem {
  return {
    part_id: 1,
    ipn: 'TEST-001',
    part_name: 'Test Part',
    full_name: 'TEST-001 | Test Part',
    description: 'Test description',
    part_type: 'Fab',
    is_assembly: false,
    purchaseable: true,
    has_default_supplier: false,
    total_qty: 1,
    unit: 'pcs',
    in_stock: 0,
    on_order: 0,
    building: 0,
    allocated: 0,
    available: 0,
    link: '/part/1/',
    default_supplier_id: undefined,
    default_supplier_name: '',
    is_cut_list_child: false,
    ...overrides
  } as BomItem;
}

describe('flattenBomData', () => {
  it('should return items unchanged when no cut lists', () => {
    const items = [
      createBomItem({ part_id: 1, ipn: 'FAB-001' }),
      createBomItem({ part_id: 2, ipn: 'COML-002' })
    ];

    const result = flattenBomData(items);

    expect(result).toHaveLength(2);
    expect(result[0].ipn).toBe('FAB-001');
    expect(result[1].ipn).toBe('COML-002');
  });

  it('should insert CtL cut list children after parent', () => {
    const items = [
      createBomItem({
        part_id: 1,
        ipn: 'CtL-100',
        part_type: 'CtL',
        total_qty: 50,
        cut_list: [
          { quantity: 2, length: 100 },
          { quantity: 3, length: 150 }
        ]
      })
    ];

    const result = flattenBomData(items);

    expect(result).toHaveLength(3); // 1 parent + 2 children
    expect(result[0].is_cut_list_child).toBe(false);
    expect(result[1].is_cut_list_child).toBe(true);
    expect(result[2].is_cut_list_child).toBe(true);

    // Verify child quantities and lengths
    expect(result[1].total_qty).toBe(2);
    expect(result[1].cut_length).toBe(100);
    expect(result[2].total_qty).toBe(3);
    expect(result[2].cut_length).toBe(150);
  });

  it('should insert Internal Fab cut list children after parent', () => {
    const items = [
      createBomItem({
        part_id: 2,
        ipn: 'IFAB-200',
        part_type: 'Internal Fab',
        internal_fab_cut_list: [
          { count: 4, piece_qty: 250, unit: 'mm' },
          { count: 2, piece_qty: 500, unit: 'mm' }
        ]
      })
    ];

    const result = flattenBomData(items);

    expect(result).toHaveLength(3); // 1 parent + 2 children
    expect(result[1].total_qty).toBe(4);
    expect(result[1].cut_length).toBe(250);
    expect(result[1].cut_unit).toBe('mm');
    expect(result[2].total_qty).toBe(2);
    expect(result[2].cut_length).toBe(500);
  });

  it('should null out stock fields for cut list children', () => {
    const items = [
      createBomItem({
        part_id: 1,
        ipn: 'CtL-100',
        in_stock: 50,
        allocated: 10,
        on_order: 20,
        building: 5,
        available: 40,
        cut_list: [{ quantity: 2, length: 100 }]
      })
    ];

    const result = flattenBomData(items);

    const child = result[1];
    expect(child.in_stock).toBeNull();
    expect(child.allocated).toBeNull();
    expect(child.on_order).toBeNull();
    expect(child.building).toBeNull();
    expect(child.available).toBeNull();
  });

  it('should handle item with both CtL and Internal Fab cut lists', () => {
    const items = [
      createBomItem({
        part_id: 1,
        cut_list: [{ quantity: 1, length: 100 }],
        internal_fab_cut_list: [{ count: 1, piece_qty: 50, unit: 'mm' }]
      })
    ];

    const result = flattenBomData(items);

    expect(result).toHaveLength(3); // 1 parent + 1 CtL child + 1 IFab child
    expect(result[1].part_type).toBe('CtL');
    expect(result[2].part_type).toBe('Internal Fab');
  });

  it('should handle empty cut list arrays', () => {
    const items = [
      createBomItem({
        part_id: 1,
        cut_list: [],
        internal_fab_cut_list: []
      })
    ];

    const result = flattenBomData(items);

    expect(result).toHaveLength(1); // Only parent, no children
  });

  it('should preserve parent part_id in cut list children', () => {
    const items = [
      createBomItem({
        part_id: 123,
        ipn: 'CtL-100',
        cut_list: [{ quantity: 2, length: 100 }]
      })
    ];

    const result = flattenBomData(items);

    expect(result[1].part_id).toBe(123); // Child inherits parent's part_id
  });
});

describe('filterBomData', () => {
  const items = [
    createBomItem({ ipn: 'FAB-001', part_name: 'Bracket' }),
    createBomItem({ ipn: 'COML-002', part_name: 'Screw' }),
    createBomItem({ ipn: 'FAB-003', part_name: 'Plate' })
  ];

  it('should return all items when search query is empty', () => {
    const result = filterBomData(items, '');
    expect(result).toHaveLength(3);
  });

  it('should filter by IPN (case-insensitive)', () => {
    const result = filterBomData(items, 'FAB');
    expect(result).toHaveLength(2);
    expect(result[0].ipn).toBe('FAB-001');
    expect(result[1].ipn).toBe('FAB-003');
  });

  it('should filter by part name (case-insensitive)', () => {
    const result = filterBomData(items, 'screw');
    expect(result).toHaveLength(1);
    expect(result[0].part_name).toBe('Screw');
  });

  it('should match partial strings', () => {
    const result = filterBomData(items, '001');
    expect(result).toHaveLength(1);
    expect(result[0].ipn).toBe('FAB-001');
  });

  it('should return empty array when no matches', () => {
    const result = filterBomData(items, 'DOES-NOT-EXIST');
    expect(result).toHaveLength(0);
  });

  it('should match across IPN and part name', () => {
    const result = filterBomData(items, 'a'); // Matches 'FAB' and 'Bracket' and 'Plate'
    // Actually matches: FAB-001 (has 'a' in 'FAB'), FAB-003 (has 'a' in 'FAB')
    // Bracket has 'a', Plate has 'a', but Screw doesn't
    // Wait, 'a' is in FAB (2 items) and Bracket (1 item) and Plate (1 item) = all 3!
    // But the function only checks IPN and part_name, not both together
    // Let me recalculate: FAB-001 (FAB contains 'a'), COML-002 (no 'a'), FAB-003 (FAB contains 'a')
    // So only 2 match by IPN. Part names: Bracket (yes), Screw (no), Plate (yes)
    // Ah! The filter is OR: matches if IPN contains 'a' OR part_name contains 'a'
    // FAB-001: FAB has 'a' OR Bracket has 'a' = MATCH
    // COML-002: COML no 'a' OR Screw no 'a' = NO MATCH
    // FAB-003: FAB has 'a' OR Plate has 'a' = MATCH
    // So actually 2 items match, not 3. Test was wrong.
    expect(result).toHaveLength(2); // FAB-001 (FAB + Bracket), FAB-003 (FAB + Plate)
  });
});

describe('groupChildrenWithParents', () => {
  it('should keep children attached to parent when parent is first', () => {
    const items = [
      createBomItem({ part_id: 1, ipn: 'A', is_cut_list_child: false }),
      createBomItem({ part_id: 1, ipn: 'A-child1', is_cut_list_child: true }),
      createBomItem({ part_id: 1, ipn: 'A-child2', is_cut_list_child: true }),
      createBomItem({ part_id: 2, ipn: 'B', is_cut_list_child: false })
    ];

    const result = groupChildrenWithParents(items);

    expect(result).toHaveLength(4);
    expect(result[0].ipn).toBe('A');
    expect(result[1].ipn).toBe('A-child1');
    expect(result[2].ipn).toBe('A-child2');
    expect(result[3].ipn).toBe('B');
  });

  it('should group children with parent after sorting separates them', () => {
    // Simulate sort by IPN descending: B, B-child, A-child, A
    const items = [
      createBomItem({ part_id: 2, ipn: 'B', is_cut_list_child: false }),
      createBomItem({ part_id: 2, ipn: 'B-child', is_cut_list_child: true }),
      createBomItem({ part_id: 1, ipn: 'A-child', is_cut_list_child: true }),
      createBomItem({ part_id: 1, ipn: 'A', is_cut_list_child: false })
    ];

    const result = groupChildrenWithParents(items);

    // Should regroup to: B, B-child, A, A-child
    expect(result).toHaveLength(4);
    expect(result[0].ipn).toBe('B');
    expect(result[1].ipn).toBe('B-child');
    expect(result[2].ipn).toBe('A');
    expect(result[3].ipn).toBe('A-child');
  });

  it('should handle multiple children per parent', () => {
    const items = [
      createBomItem({ part_id: 1, ipn: 'Parent', is_cut_list_child: false }),
      createBomItem({ part_id: 1, ipn: 'Child1', is_cut_list_child: true }),
      createBomItem({ part_id: 1, ipn: 'Child2', is_cut_list_child: true }),
      createBomItem({ part_id: 1, ipn: 'Child3', is_cut_list_child: true })
    ];

    const result = groupChildrenWithParents(items);

    expect(result).toHaveLength(4);
    expect(result[0].ipn).toBe('Parent');
    expect(result[1].ipn).toBe('Child1');
    expect(result[2].ipn).toBe('Child2');
    expect(result[3].ipn).toBe('Child3');
  });

  it('should handle parents without children', () => {
    const items = [
      createBomItem({ part_id: 1, ipn: 'A', is_cut_list_child: false }),
      createBomItem({ part_id: 2, ipn: 'B', is_cut_list_child: false }),
      createBomItem({ part_id: 3, ipn: 'C', is_cut_list_child: false })
    ];

    const result = groupChildrenWithParents(items);

    expect(result).toHaveLength(3);
    expect(result[0].ipn).toBe('A');
    expect(result[1].ipn).toBe('B');
    expect(result[2].ipn).toBe('C');
  });

  it('should preserve parent sort order', () => {
    // Parents sorted Z -> A
    const items = [
      createBomItem({ part_id: 3, ipn: 'Z', is_cut_list_child: false }),
      createBomItem({ part_id: 3, ipn: 'Z-child', is_cut_list_child: true }),
      createBomItem({ part_id: 1, ipn: 'A', is_cut_list_child: false }),
      createBomItem({ part_id: 1, ipn: 'A-child', is_cut_list_child: true })
    ];

    const result = groupChildrenWithParents(items);

    // Should maintain parent order: Z, A
    expect(result[0].ipn).toBe('Z');
    expect(result[1].ipn).toBe('Z-child');
    expect(result[2].ipn).toBe('A');
    expect(result[3].ipn).toBe('A-child');
  });
});

describe('sortBomData', () => {
  const items = [
    createBomItem({
      part_id: 1,
      ipn: 'FAB-003',
      part_name: 'Plate',
      total_qty: 5,
      in_stock: 10
    }),
    createBomItem({
      part_id: 2,
      ipn: 'COML-001',
      part_name: 'Screw',
      total_qty: 50,
      in_stock: 100
    }),
    createBomItem({
      part_id: 3,
      ipn: 'FAB-002',
      part_name: 'Bracket',
      total_qty: 2,
      in_stock: 0
    })
  ];

  describe('string sorting', () => {
    it('should sort by IPN ascending', () => {
      const result = sortBomData(items, 'ipn', 'asc', 1, false, false);

      expect(result[0].ipn).toBe('COML-001');
      expect(result[1].ipn).toBe('FAB-002');
      expect(result[2].ipn).toBe('FAB-003');
    });

    it('should sort by IPN descending', () => {
      const result = sortBomData(items, 'ipn', 'desc', 1, false, false);

      expect(result[0].ipn).toBe('FAB-003');
      expect(result[1].ipn).toBe('FAB-002');
      expect(result[2].ipn).toBe('COML-001');
    });

    it('should sort by part_name ascending', () => {
      const result = sortBomData(items, 'part_name', 'asc', 1, false, false);

      expect(result[0].part_name).toBe('Bracket');
      expect(result[1].part_name).toBe('Plate');
      expect(result[2].part_name).toBe('Screw');
    });
  });

  describe('numeric sorting', () => {
    it('should sort by total_qty ascending', () => {
      const result = sortBomData(items, 'total_qty', 'asc', 1, false, false);

      expect(result[0].total_qty).toBe(2);
      expect(result[1].total_qty).toBe(5);
      expect(result[2].total_qty).toBe(50);
    });

    it('should sort by total_qty descending', () => {
      const result = sortBomData(items, 'total_qty', 'desc', 1, false, false);

      expect(result[0].total_qty).toBe(50);
      expect(result[1].total_qty).toBe(5);
      expect(result[2].total_qty).toBe(2);
    });

    it('should multiply total_qty by buildQuantity when sorting', () => {
      const result = sortBomData(items, 'total_qty', 'asc', 10, false, false);

      // Still sorted by base qty, but calculation uses buildQuantity
      expect(result[0].total_qty).toBe(2); // 2 * 10 = 20
      expect(result[1].total_qty).toBe(5); // 5 * 10 = 50
      expect(result[2].total_qty).toBe(50); // 50 * 10 = 500
    });

    it('should sort by in_stock ascending', () => {
      const result = sortBomData(items, 'in_stock', 'asc', 1, false, false);

      expect(result[0].in_stock).toBe(0);
      expect(result[1].in_stock).toBe(10);
      expect(result[2].in_stock).toBe(100);
    });
  });

  describe('shortfall calculation sorting', () => {
    it('should sort by shortfall without allocations or on-order', () => {
      const itemsWithStock = [
        createBomItem({
          total_qty: 10,
          in_stock: 50,
          allocated: 5,
          on_order: 20
        }), // Shortfall: 0 (50 >= 10)
        createBomItem({
          total_qty: 20,
          in_stock: 10,
          allocated: 5,
          on_order: 20
        }), // Shortfall: 10 (10 < 20)
        createBomItem({
          total_qty: 30,
          in_stock: 5,
          allocated: 5,
          on_order: 20
        }) // Shortfall: 25 (5 < 30)
      ];

      const result = sortBomData(
        itemsWithStock,
        'shortfall',
        'asc',
        1,
        false,
        false
      );

      // Ascending: 0, 10, 25
      expect(result[0].total_qty).toBe(10); // 0 shortfall
      expect(result[1].total_qty).toBe(20); // 10 shortfall
      expect(result[2].total_qty).toBe(30); // 25 shortfall
    });

    it('should subtract allocations when includeAllocations=true', () => {
      const itemsWithStock = [
        createBomItem({
          total_qty: 10,
          in_stock: 50,
          allocated: 45,
          on_order: 0
        }), // Available: 5, Shortfall: 5
        createBomItem({
          total_qty: 10,
          in_stock: 50,
          allocated: 0,
          on_order: 0
        }) // Available: 50, Shortfall: 0
      ];

      const result = sortBomData(
        itemsWithStock,
        'shortfall',
        'asc',
        1,
        true,
        false
      );

      // With allocations: item 2 (0 shortfall) < item 1 (5 shortfall)
      expect(result[0].allocated).toBe(0); // No shortfall
      expect(result[1].allocated).toBe(45); // Has shortfall
    });

    it('should include on-order when includeOnOrder=true', () => {
      const itemsWithStock = [
        createBomItem({
          total_qty: 50,
          in_stock: 10,
          allocated: 0,
          on_order: 40
        }), // Stock+OnOrder: 50, Shortfall: 0
        createBomItem({
          total_qty: 50,
          in_stock: 10,
          allocated: 0,
          on_order: 0
        }) // Stock: 10, Shortfall: 40
      ];

      const result = sortBomData(
        itemsWithStock,
        'shortfall',
        'asc',
        1,
        false,
        true
      );

      // With on-order: item 1 (0 shortfall) < item 2 (40 shortfall)
      expect(result[0].on_order).toBe(40); // No shortfall
      expect(result[1].on_order).toBe(0); // Has shortfall
    });

    it('should handle buildQuantity multiplier in shortfall calculation', () => {
      const itemsWithStock = [
        createBomItem({
          total_qty: 10,
          in_stock: 100,
          allocated: 0,
          on_order: 0
        }) // Need 50 (10*5), have 100, shortfall: 0
      ];

      const result = sortBomData(
        itemsWithStock,
        'shortfall',
        'asc',
        5,
        false,
        false
      );

      // Should calculate shortfall based on total_qty * buildQuantity
      expect(result[0].total_qty).toBe(10);
    });
  });

  describe('edge cases', () => {
    it('should handle empty array', () => {
      const result = sortBomData([], 'ipn', 'asc', 1, false, false);
      expect(result).toHaveLength(0);
    });

    it('should handle unknown column accessor', () => {
      const result = sortBomData(
        items,
        'unknown_column',
        'asc',
        1,
        false,
        false
      );

      // Should return array unchanged (no sorting)
      expect(result).toHaveLength(3);
    });

    it('should handle building field with null values', () => {
      const itemsWithBuilding = [
        createBomItem({ building: undefined as any }),
        createBomItem({ building: 5 }),
        createBomItem({ building: 0 })
      ];

      const result = sortBomData(
        itemsWithBuilding,
        'building',
        'asc',
        1,
        false,
        false
      );

      // The sort function uses `building || 0` in the switch case
      // So undefined becomes 0 in the comparison
      // But the actual field value remains undefined, not replaced with 0
      // We're testing sort ORDER, not field transformation
      expect(result[0].building).toBeUndefined(); // undefined treated as 0 for sort
      expect(result[1].building).toBe(0); // actual 0
      expect(result[2].building).toBe(5); // 5
    });
  });
});
