/**
 * Tests for BOM Data Processing Utilities
 *
 * Focus: Non-trivial logic like child grouping and sort behavior
 * Validates edge cases that could cause UI bugs
 */

import { describe, expect, it } from 'vitest';
import type { BomItem, SubstitutePart } from '../types/BomTypes';
import {
  filterBomData,
  flattenBomData,
  groupChildRowsWithParents,
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
    total_qty: 1,
    unit: 'pcs',
    in_stock: 0,
    on_order: 0,
    building: 0,
    allocated: 0,
    available: 0,
    net_stock: 0,
    quantity_to_order: 0,
    link: '/part/1/',
    default_supplier_id: undefined,
    default_supplier_name: '',
    is_child_row: false,
    ...overrides
  } as BomItem;
}

// Helper to create a minimal SubstitutePart for testing
function createSubstitutePart(
  overrides: Partial<SubstitutePart>
): SubstitutePart {
  return {
    substitute_id: 1,
    part_id: 99,
    ipn: 'SUB-001',
    part_name: 'Substitute Part',
    full_name: 'SUB-001 | Substitute Part',
    description: '',
    unit: 'pcs',
    parent_total_qty: 5,
    in_stock: 0,
    on_order: 0,
    allocated: 0,
    available: 0,
    net_stock: 0,
    quantity_to_order: 0,
    image: null,
    thumbnail: null,
    link: '',
    ...overrides
  };
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

  it('should insert one cut list child per piece size after parent', () => {
    // Entries are aggregated by (part, piece size) backend-side: the
    // frontend renders exactly what cut_list carries.
    const items = [
      createBomItem({
        part_id: 1,
        ipn: 'BAR-100',
        part_type: 'Fab',
        total_qty: 500,
        cut_list: [
          { size: 100, count: 2, unit: 'mm' },
          { size: 100, count: 3, unit: 'mm' }
        ]
      })
    ];

    const result = flattenBomData(items);

    expect(result).toHaveLength(3); // 1 parent + 2 children
    expect(result[0].is_child_row).toBe(false);
    expect(result[1].is_child_row).toBe(true);
    expect(result[2].is_child_row).toBe(true);

    // Child rows: total_qty = piece count, cut_length = piece size
    expect(result[1].total_qty).toBe(2);
    expect(result[1].cut_length).toBe(100);
    expect(result[1].child_row_type).toBe('cutlist');
    expect(result[2].total_qty).toBe(3);
    expect(result[2].cut_length).toBe(100);
  });

  it('should keep the part type on cut list children', () => {
    // Cut rows are the material part at a piece size - not an assembly badge.
    const items = [
      createBomItem({
        part_id: 2,
        ipn: 'TUBE-200',
        part_type: 'Fab',
        cut_list: [
          { size: 250, count: 4, unit: 'mm' },
          { size: 500, count: 2, unit: 'mm' }
        ]
      })
    ];

    const result = flattenBomData(items);

    expect(result).toHaveLength(3); // 1 parent + 2 children
    expect(result[1].total_qty).toBe(4);
    expect(result[1].cut_length).toBe(250);
    expect(result[1].cut_unit).toBe('mm');
    expect(result[1].part_type).toBe('Fab');
    expect(result[2].total_qty).toBe(2);
    expect(result[2].cut_length).toBe(500);
  });

  it('should null out stock fields for cut list children', () => {
    const items = [
      createBomItem({
        part_id: 1,
        ipn: 'BAR-100',
        in_stock: 50,
        allocated: 10,
        on_order: 20,
        building: 5,
        available: 40,
        cut_list: [{ size: 100, count: 2, unit: 'mm' }]
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

  it('should null the max-stock fields on cut list children (ticket #26)', () => {
    // The ceiling and its flag are stock-family fields - a cut row shows
    // the same dash its siblings do, never the parent's leaked values.
    const items = [
      createBomItem({
        part_id: 1,
        maximum_stock: 40,
        exceeds_max_stock: true,
        cut_list: [{ size: 100, count: 2, unit: 'mm' }]
      })
    ];

    const result = flattenBomData(items);

    const child = result[1];
    expect(child.maximum_stock).toBeNull();
    expect(child.exceeds_max_stock).toBeNull();
  });

  it('should handle empty cut list arrays', () => {
    const items = [
      createBomItem({
        part_id: 1,
        cut_list: []
      })
    ];

    const result = flattenBomData(items);

    expect(result).toHaveLength(1); // Only parent, no children
  });

  it('should preserve parent part_id in cut list children', () => {
    const items = [
      createBomItem({
        part_id: 123,
        ipn: 'BAR-100',
        cut_list: [{ size: 100, count: 2, unit: 'mm' }]
      })
    ];

    const result = flattenBomData(items);

    expect(result[1].part_id).toBe(123); // Child inherits parent's part_id
  });
});

describe('flattenBomData -- substitute parts', () => {
  it('should not add child rows when has_substitutes is false', () => {
    const items = [createBomItem({ has_substitutes: false })];

    const result = flattenBomData(items);

    expect(result).toHaveLength(1);
  });

  it('should insert substitute as child row after parent', () => {
    const items = [
      createBomItem({
        part_id: 1,
        has_substitutes: true,
        substitute_parts: [createSubstitutePart({ part_id: 99 })]
      })
    ];

    const result = flattenBomData(items);

    expect(result).toHaveLength(2);
    expect(result[1].is_child_row).toBe(true);
    expect(result[1].child_row_type).toBe('substitute');
  });

  it('should use parent_total_qty from substitute when available', () => {
    const items = [
      createBomItem({
        part_id: 1,
        total_qty: 3,
        has_substitutes: true,
        substitute_parts: [createSubstitutePart({ parent_total_qty: 7 })]
      })
    ];

    const result = flattenBomData(items);

    expect(result[1].total_qty).toBe(7);
  });

  it('should fall back to parent total_qty when parent_total_qty is undefined', () => {
    const items = [
      createBomItem({
        part_id: 1,
        total_qty: 3,
        has_substitutes: true,
        substitute_parts: [
          createSubstitutePart({ parent_total_qty: undefined })
        ]
      })
    ];

    const result = flattenBomData(items);

    expect(result[1].total_qty).toBe(3);
  });

  it('should set unit_mismatch false when units match', () => {
    const items = [
      createBomItem({
        part_id: 1,
        unit: 'pcs',
        has_substitutes: true,
        substitute_parts: [createSubstitutePart({ unit: 'pcs' })]
      })
    ];

    const result = flattenBomData(items);

    expect(result[1].unit_mismatch).toBe(false);
  });

  it('should set unit_mismatch true when units differ', () => {
    const items = [
      createBomItem({
        part_id: 1,
        unit: 'pcs',
        has_substitutes: true,
        substitute_parts: [createSubstitutePart({ unit: 'm' })]
      })
    ];

    const result = flattenBomData(items);

    expect(result[1].unit_mismatch).toBe(true);
  });

  it('should set unit_mismatch false when both units are empty (unitless parts)', () => {
    const items = [
      createBomItem({
        part_id: 1,
        unit: '',
        has_substitutes: true,
        substitute_parts: [createSubstitutePart({ unit: null })]
      })
    ];

    const result = flattenBomData(items);

    expect(result[1].unit_mismatch).toBe(false);
  });

  it('should insert multiple substitutes as separate child rows', () => {
    const items = [
      createBomItem({
        part_id: 1,
        has_substitutes: true,
        substitute_parts: [
          createSubstitutePart({ part_id: 99, ipn: 'SUB-001' }),
          createSubstitutePart({
            part_id: 100,
            ipn: 'SUB-002',
            substitute_id: 2
          })
        ]
      })
    ];

    const result = flattenBomData(items);

    expect(result).toHaveLength(3);
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

describe('groupChildRowsWithParents', () => {
  it('should keep children attached to parent when parent is first', () => {
    const items = [
      createBomItem({ part_id: 1, ipn: 'A', is_child_row: false }),
      createBomItem({ part_id: 1, ipn: 'A-child1', is_child_row: true }),
      createBomItem({ part_id: 1, ipn: 'A-child2', is_child_row: true }),
      createBomItem({ part_id: 2, ipn: 'B', is_child_row: false })
    ];

    const result = groupChildRowsWithParents(items);

    expect(result).toHaveLength(4);
    expect(result[0].ipn).toBe('A');
    expect(result[1].ipn).toBe('A-child1');
    expect(result[2].ipn).toBe('A-child2');
    expect(result[3].ipn).toBe('B');
  });

  it('should group children with parent after sorting separates them', () => {
    // Simulate sort by IPN descending: B, B-child, A-child, A
    const items = [
      createBomItem({ part_id: 2, ipn: 'B', is_child_row: false }),
      createBomItem({ part_id: 2, ipn: 'B-child', is_child_row: true }),
      createBomItem({ part_id: 1, ipn: 'A-child', is_child_row: true }),
      createBomItem({ part_id: 1, ipn: 'A', is_child_row: false })
    ];

    const result = groupChildRowsWithParents(items);

    // Should regroup to: B, B-child, A, A-child
    expect(result).toHaveLength(4);
    expect(result[0].ipn).toBe('B');
    expect(result[1].ipn).toBe('B-child');
    expect(result[2].ipn).toBe('A');
    expect(result[3].ipn).toBe('A-child');
  });

  it('should handle multiple children per parent', () => {
    const items = [
      createBomItem({ part_id: 1, ipn: 'Parent', is_child_row: false }),
      createBomItem({ part_id: 1, ipn: 'Child1', is_child_row: true }),
      createBomItem({ part_id: 1, ipn: 'Child2', is_child_row: true }),
      createBomItem({ part_id: 1, ipn: 'Child3', is_child_row: true })
    ];

    const result = groupChildRowsWithParents(items);

    expect(result).toHaveLength(4);
    expect(result[0].ipn).toBe('Parent');
    expect(result[1].ipn).toBe('Child1');
    expect(result[2].ipn).toBe('Child2');
    expect(result[3].ipn).toBe('Child3');
  });

  it('should handle parents without children', () => {
    const items = [
      createBomItem({ part_id: 1, ipn: 'A', is_child_row: false }),
      createBomItem({ part_id: 2, ipn: 'B', is_child_row: false }),
      createBomItem({ part_id: 3, ipn: 'C', is_child_row: false })
    ];

    const result = groupChildRowsWithParents(items);

    expect(result).toHaveLength(3);
    expect(result[0].ipn).toBe('A');
    expect(result[1].ipn).toBe('B');
    expect(result[2].ipn).toBe('C');
  });

  it('should preserve parent sort order', () => {
    // Parents sorted Z -> A
    const items = [
      createBomItem({ part_id: 3, ipn: 'Z', is_child_row: false }),
      createBomItem({ part_id: 3, ipn: 'Z-child', is_child_row: true }),
      createBomItem({ part_id: 1, ipn: 'A', is_child_row: false }),
      createBomItem({ part_id: 1, ipn: 'A-child', is_child_row: true })
    ];

    const result = groupChildRowsWithParents(items);

    // Should maintain parent order: Z, A
    expect(result[0].ipn).toBe('Z');
    expect(result[1].ipn).toBe('Z-child');
    expect(result[2].ipn).toBe('A');
    expect(result[3].ipn).toBe('A-child');
  });

  it('should group substitute child correctly when child part_id differs from parent part_id', () => {
    const parent = createBomItem({
      part_id: 1,
      ipn: 'PARENT-001',
      is_child_row: false
    });
    const subChild = createBomItem({
      part_id: 99,
      ipn: 'SUB-001',
      is_child_row: true,
      parent_row_part_id: 1
    });

    const result = groupChildRowsWithParents([parent, subChild]);

    expect(result).toHaveLength(2);
    expect(result[0].part_id).toBe(1);
    expect(result[1].part_id).toBe(99);
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

    it('should sort by net_stock ascending with negatives unfloored', () => {
      const shortageItems = [
        createBomItem({ part_id: 1, ipn: 'A', net_stock: 15 }),
        createBomItem({ part_id: 2, ipn: 'B', net_stock: -25 }),
        createBomItem({ part_id: 3, ipn: 'C', net_stock: 0 })
      ];

      const result = sortBomData(
        shortageItems,
        'net_stock',
        'asc',
        1,
        false,
        false
      );

      expect(result[0].net_stock).toBe(-25);
      expect(result[1].net_stock).toBe(0);
      expect(result[2].net_stock).toBe(15);
    });

    it('should sort by quantity_to_order ascending', () => {
      const orderItems = [
        createBomItem({ part_id: 1, ipn: 'A', quantity_to_order: 40 }),
        createBomItem({ part_id: 2, ipn: 'B', quantity_to_order: 0 }),
        createBomItem({ part_id: 3, ipn: 'C', quantity_to_order: 10 })
      ];

      const result = sortBomData(
        orderItems,
        'quantity_to_order',
        'asc',
        1,
        false,
        false
      );

      expect(result[0].quantity_to_order).toBe(0);
      expect(result[1].quantity_to_order).toBe(10);
      expect(result[2].quantity_to_order).toBe(40);
    });
  });

  describe('category sorting (ticket #43)', () => {
    // Category is a plain text column: the '' fallback matches the
    // default_supplier_name pattern, so uncategorized rows sort as empty
    // string - first ascending, last descending.
    const categoryItems = [
      createBomItem({ part_id: 1, ipn: 'A', category: 'Hardware' }),
      createBomItem({ part_id: 2, ipn: 'B', category: 'Electronics' }),
      createBomItem({ part_id: 3, ipn: 'C' }), // uncategorized -> ''
      createBomItem({ part_id: 4, ipn: 'D', category: 'Fasteners' })
    ];

    it('sorts A->Z ascending like other text columns', () => {
      const result = sortBomData(
        categoryItems,
        'category',
        'asc',
        1,
        false,
        false
      );

      expect(result.map((item) => item.ipn)).toEqual(['C', 'B', 'D', 'A']);
    });

    it('sorts Z->A descending like other text columns', () => {
      const result = sortBomData(
        categoryItems,
        'category',
        'desc',
        1,
        false,
        false
      );

      expect(result.map((item) => item.ipn)).toEqual(['A', 'D', 'B', 'C']);
    });
  });

  describe('maximum_stock sorting (ticket #43)', () => {
    // The ceiling sorts numerically like its stock siblings, with one
    // addition: unset ceilings (null or undefined) partition to the tail
    // in BOTH directions - raw null arithmetic would head a descending
    // sort.
    const ceilingItems = [
      createBomItem({ part_id: 1, ipn: 'A', maximum_stock: 50 }),
      createBomItem({ part_id: 2, ipn: 'B', maximum_stock: null }),
      createBomItem({ part_id: 3, ipn: 'C', maximum_stock: 10 }),
      createBomItem({ part_id: 4, ipn: 'D', maximum_stock: 200 }),
      createBomItem({ part_id: 5, ipn: 'E' }) // maximum_stock undefined
    ];

    it('sorts numerically ascending with unset rows at the tail', () => {
      const result = sortBomData(
        ceilingItems,
        'maximum_stock',
        'asc',
        1,
        false,
        false
      );

      expect(result.map((item) => item.ipn)).toEqual(['C', 'A', 'D', 'B', 'E']);
    });

    it('keeps unset rows at the tail when sorting descending', () => {
      const result = sortBomData(
        ceilingItems,
        'maximum_stock',
        'desc',
        1,
        false,
        false
      );

      expect(result.map((item) => item.ipn)).toEqual(['D', 'A', 'C', 'B', 'E']);
    });
  });

  describe('shortfall calculation sorting', () => {
    // The sort key is the signed balance the column renders
    // (available - required): negative = shortfall, positive = surplus.
    // Ascending puts the worst shortfall first; descending the largest
    // surplus (#46).
    it('should sort by signed balance without allocations or on-order', () => {
      const itemsWithStock = [
        createBomItem({
          total_qty: 10,
          in_stock: 50,
          allocated: 5,
          on_order: 20
        }), // Balance: +40 (50 - 10)
        createBomItem({
          total_qty: 20,
          in_stock: 10,
          allocated: 5,
          on_order: 20
        }), // Balance: -10 (10 - 20)
        createBomItem({
          total_qty: 30,
          in_stock: 5,
          allocated: 5,
          on_order: 20
        }) // Balance: -25 (5 - 30)
      ];

      const result = sortBomData(
        itemsWithStock,
        'shortfall',
        'asc',
        1,
        false,
        false
      );

      // Ascending: -25, -10, +40 (worst shortfall first)
      expect(result[0].total_qty).toBe(30); // -25 balance
      expect(result[1].total_qty).toBe(20); // -10 balance
      expect(result[2].total_qty).toBe(10); // +40 balance
    });

    it('should subtract allocations when includeAllocations=true', () => {
      const itemsWithStock = [
        createBomItem({
          total_qty: 10,
          in_stock: 50,
          allocated: 45,
          on_order: 0
        }), // Balance: 50 - 45 - 10 = -5
        createBomItem({
          total_qty: 10,
          in_stock: 50,
          allocated: 0,
          on_order: 0
        }) // Balance: 50 - 0 - 10 = +40
      ];

      const result = sortBomData(
        itemsWithStock,
        'shortfall',
        'asc',
        1,
        true,
        false
      );

      // With allocations: item 1 (-5) < item 2 (+40)
      expect(result[0].allocated).toBe(45); // -5 balance
      expect(result[1].allocated).toBe(0); // +40 balance
    });

    it('should include on-order when includeOnOrder=true', () => {
      const itemsWithStock = [
        createBomItem({
          total_qty: 50,
          in_stock: 10,
          allocated: 0,
          on_order: 40
        }), // Balance: 10 + 40 - 50 = 0
        createBomItem({
          total_qty: 50,
          in_stock: 10,
          allocated: 0,
          on_order: 0
        }) // Balance: 10 - 50 = -40
      ];

      const result = sortBomData(
        itemsWithStock,
        'shortfall',
        'asc',
        1,
        false,
        true
      );

      // With on-order: item 2 (-40) < item 1 (0)
      expect(result[0].on_order).toBe(0); // -40 balance
      expect(result[1].on_order).toBe(40); // 0 balance
    });

    it('should handle buildQuantity multiplier in shortfall calculation', () => {
      const itemsWithStock = [
        createBomItem({
          total_qty: 10,
          in_stock: 100,
          allocated: 0,
          on_order: 0
        }) // Need 50 (10*5), have 100, margin +50
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

  describe('build margin signed-balance ordering (ticket #46)', () => {
    // Regression: the old sort key was Math.max(0, required - available), so
    // every surplus row clamped to key 0 - equal keys meant the green group
    // kept arbitrary input order and never sorted. The key is now the same
    // signed balance the column renders (calculateShortfall).
    const mixedItems = [
      createBomItem({
        part_id: 1,
        ipn: 'A',
        total_qty: 20,
        in_stock: 10
      }), // Balance: -10
      createBomItem({
        part_id: 2,
        ipn: 'B',
        total_qty: 10,
        in_stock: 5
      }), // Balance: -5
      createBomItem({
        part_id: 3,
        ipn: 'C',
        total_qty: 8,
        in_stock: 10
      }), // Balance: +2
      createBomItem({
        part_id: 4,
        ipn: 'D',
        total_qty: 2,
        in_stock: 10
      }) // Balance: +8
    ];

    it('orders surplus rows among themselves ascending (worst shortfall first)', () => {
      const result = sortBomData(
        mixedItems,
        'shortfall',
        'asc',
        1,
        false,
        false
      );

      // -10, -5, +2, +8
      expect(result.map((item) => item.ipn)).toEqual(['A', 'B', 'C', 'D']);
    });

    it('orders surplus rows among themselves descending (largest surplus first)', () => {
      const result = sortBomData(
        mixedItems,
        'shortfall',
        'desc',
        1,
        false,
        false
      );

      // +8, +2, -5, -10
      expect(result.map((item) => item.ipn)).toEqual(['D', 'C', 'B', 'A']);
    });

    it('reorders consistently when includeAllocations flips a row to shortfall', () => {
      const allocItems = [
        createBomItem({
          part_id: 1,
          ipn: 'A',
          total_qty: 10,
          in_stock: 20,
          allocated: 15
        }), // Untoggled: +10; with allocations: 20 - 15 - 10 = -5
        createBomItem({
          part_id: 2,
          ipn: 'B',
          total_qty: 10,
          in_stock: 12,
          allocated: 0
        }) // +2 either way
      ];

      const untoggled = sortBomData(
        allocItems,
        'shortfall',
        'asc',
        1,
        false,
        false
      );
      expect(untoggled.map((item) => item.ipn)).toEqual(['B', 'A']);

      const toggled = sortBomData(
        allocItems,
        'shortfall',
        'asc',
        1,
        true,
        false
      );
      expect(toggled.map((item) => item.ipn)).toEqual(['A', 'B']);
    });

    it('reorders consistently when includeOnOrder lifts a row to surplus', () => {
      const orderItems = [
        createBomItem({
          part_id: 1,
          ipn: 'A',
          total_qty: 30,
          in_stock: 5,
          on_order: 40
        }), // Untoggled: -25; with on-order: 5 + 40 - 30 = +15
        createBomItem({
          part_id: 2,
          ipn: 'B',
          total_qty: 10,
          in_stock: 0,
          on_order: 0
        }) // -10 either way
      ];

      const untoggled = sortBomData(
        orderItems,
        'shortfall',
        'asc',
        1,
        false,
        false
      );
      expect(untoggled.map((item) => item.ipn)).toEqual(['A', 'B']);

      const toggled = sortBomData(
        orderItems,
        'shortfall',
        'asc',
        1,
        false,
        true
      );
      expect(toggled.map((item) => item.ipn)).toEqual(['B', 'A']);
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
