/**
 * BOM Data Processing Utilities
 * Pure functions for flattening, filtering, and sorting BOM data
 */

import type { BomItem } from '../types/BomTypes';

/**
 * Flatten BOM data by inserting cut list child rows after parents
 * Handles both CtL (Cut-to-Length) and Internal Fab cut lists
 *
 * @param items - Array of BOM items from API
 * @returns Flattened array with child rows inserted after parents
 *
 * @example
 * const items = [{ part_id: 1, cut_list: [{ quantity: 2, length: 100 }] }];
 * const flattened = flattenBomData(items);
 * // Returns: [parent, child_with_quantity_2_length_100]
 */
export function flattenBomData(items: BomItem[]): BomItem[] {
  const flattenedData: BomItem[] = [];

  for (const item of items) {
    // Add parent row
    flattenedData.push(item);

    // Add CtL cut list children
    if (item.cut_list && item.cut_list.length > 0) {
      for (const cut of item.cut_list) {
        flattenedData.push({
          ...item,
          total_qty: cut.quantity,
          part_type: 'CtL' as any,
          in_stock: null as any,
          on_order: null as any,
          allocated: null as any,
          building: null as any,
          available: null as any,
          default_supplier_name: '',
          cut_length: cut.length,
          is_cut_list_child: true,
          cut_list: null
        });
      }
    }

    // Add Internal Fab cut breakdown children
    if (item.internal_fab_cut_list && item.internal_fab_cut_list.length > 0) {
      for (const piece of item.internal_fab_cut_list) {
        flattenedData.push({
          ...item,
          total_qty: piece.count,
          part_type: 'Internal Fab' as any,
          in_stock: null as any,
          on_order: null as any,
          allocated: null as any,
          building: null as any,
          available: null as any,
          default_supplier_name: '',
          cut_length: piece.piece_qty,
          cut_unit: piece.unit,
          is_cut_list_child: true,
          cut_list: null,
          internal_fab_cut_list: null
        });
      }
    }
  }

  return flattenedData;
}

/**
 * Filter BOM items by search query (IPN and Part Name only)
 * Case-insensitive search
 *
 * @param items - Array of BOM items
 * @param searchQuery - Search string
 * @returns Filtered array of BOM items
 *
 * @example
 * filterBomData(items, 'FAB') // Returns items with 'fab' in IPN or name
 * filterBomData(items, '') // Returns all items (no filter)
 */
export function filterBomData(
  items: BomItem[],
  searchQuery: string
): BomItem[] {
  if (!searchQuery) return items;

  const query = searchQuery.toLowerCase();
  return items.filter(
    (item) =>
      item.ipn.toLowerCase().includes(query) ||
      item.part_name.toLowerCase().includes(query)
  );
}

/**
 * Group cut list children with their parents after sorting
 * Ensures children stay attached to parent when column sort is applied
 *
 * @param items - Sorted array of BOM items
 * @returns Array with children grouped immediately after parents
 *
 * @example
 * // After sorting by stock, children might be separated from parent
 * const sorted = sortItems(items);
 * // Group brings them back together
 * const grouped = groupChildrenWithParents(sorted);
 */
export function groupChildrenWithParents(items: BomItem[]): BomItem[] {
  const parents: BomItem[] = [];
  const childrenByParentId = new Map<number, BomItem[]>();

  // Separate parents and children
  for (const item of items) {
    if (item.is_cut_list_child) {
      // Children inherit parent's part_id
      const parentId = item.part_id;
      if (!childrenByParentId.has(parentId)) {
        childrenByParentId.set(parentId, []);
      }
      childrenByParentId.get(parentId)!.push(item);
    } else {
      parents.push(item);
    }
  }

  // Rebuild array with children immediately after their parents
  const result: BomItem[] = [];
  for (const parent of parents) {
    result.push(parent);
    const children = childrenByParentId.get(parent.part_id);
    if (children) {
      result.push(...children);
    }
  }

  return result;
}

/**
 * Sort BOM items by column accessor
 * Handles string and numeric sorting with proper direction
 *
 * @param items - Array of BOM items
 * @param columnAccessor - Column to sort by
 * @param direction - Sort direction ('asc' or 'desc')
 * @param buildQuantity - Build quantity for total_qty calculation
 * @param includeAllocations - Whether to subtract allocations for shortfall
 * @param includeOnOrder - Whether to include on-order for shortfall
 * @returns Sorted array of BOM items
 *
 * @example
 * sortBomData(items, 'ipn', 'asc', 1, true, true)
 * sortBomData(items, 'total_qty', 'desc', 5, true, true)
 */
export function sortBomData(
  items: BomItem[],
  columnAccessor: string,
  direction: 'asc' | 'desc',
  buildQuantity: number,
  includeAllocations: boolean,
  includeOnOrder: boolean
): BomItem[] {
  const sorted = [...items].sort((a, b) => {
    let aValue: any;
    let bValue: any;

    // Handle nested accessors and special cases
    switch (columnAccessor) {
      case 'ipn':
        aValue = a.ipn;
        bValue = b.ipn;
        break;
      case 'full_name':
        aValue = a.full_name;
        bValue = b.full_name;
        break;
      case 'part_name':
        aValue = a.part_name;
        bValue = b.part_name;
        break;
      case 'description':
        aValue = a.description;
        bValue = b.description;
        break;
      case 'part_type':
        aValue = a.part_type;
        bValue = b.part_type;
        break;
      case 'total_qty':
        aValue = a.total_qty * buildQuantity;
        bValue = b.total_qty * buildQuantity;
        break;
      case 'in_stock':
        aValue = a.in_stock;
        bValue = b.in_stock;
        break;
      case 'on_order':
        aValue = a.on_order;
        bValue = b.on_order;
        break;
      case 'building':
        aValue = a.building || 0;
        bValue = b.building || 0;
        break;
      case 'allocated':
        aValue = a.allocated;
        bValue = b.allocated;
        break;
      case 'shortfall':
        // Calculate shortfall for sorting
        let aStockValue = a.in_stock;
        let bStockValue = b.in_stock;
        if (includeAllocations) {
          aStockValue -= a.allocated;
          bStockValue -= b.allocated;
        }
        if (includeOnOrder) {
          aStockValue += a.on_order;
          bStockValue += b.on_order;
        }
        aValue = Math.max(0, a.total_qty * buildQuantity - aStockValue);
        bValue = Math.max(0, b.total_qty * buildQuantity - bStockValue);
        break;
      case 'default_supplier_name':
        aValue = a.default_supplier_name || '';
        bValue = b.default_supplier_name || '';
        break;
      default:
        return 0;
    }

    // Handle string vs number comparison
    if (typeof aValue === 'string' && typeof bValue === 'string') {
      return direction === 'asc'
        ? aValue.localeCompare(bValue)
        : bValue.localeCompare(aValue);
    } else {
      return direction === 'asc'
        ? (aValue as number) - (bValue as number)
        : (bValue as number) - (aValue as number);
    }
  });

  return sorted;
}
