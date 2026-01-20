import type { BomItem } from '../types/BomTypes';

/**
 * Hook result interface for shortfall calculations
 */
export interface UseShortfallCalculationResult {
  calculateShortfall: (item: BomItem) => number;
  countNeedToOrder: (items: BomItem[]) => number;
  countOutOfStock: (items: BomItem[]) => number;
  countOnOrder: (items: BomItem[]) => number;
}

/**
 * Custom hook for BOM shortfall and statistics calculations
 *
 * Calculates:
 * - Individual item shortfall (margin) based on build quantity and stock options
 * - Statistics: parts needing order, out of stock, on order
 *
 * All calculations respect buildQuantity multiplier and toggle states:
 * - includeAllocations: subtracts allocated stock from available
 * - includeOnOrder: adds incoming purchase orders to available
 *
 * @param buildQuantity - Number of assemblies to build (multiplier for requirements)
 * @param includeAllocations - Whether to subtract allocated stock
 * @param includeOnOrder - Whether to add incoming stock
 * @returns Calculation functions for shortfall and statistics
 */
export function useShortfallCalculation(
  buildQuantity: number,
  includeAllocations: boolean,
  includeOnOrder: boolean
): UseShortfallCalculationResult {
  /**
   * Calculate shortfall (margin) for a single BOM item
   *
   * Positive = surplus, Negative = shortfall
   *
   * Formula: available_stock - total_required
   * Where:
   *   available_stock = in_stock - (allocated if enabled) + (on_order if enabled)
   *   total_required = total_qty * buildQuantity
   *
   * @param item - BOM item to calculate shortfall for
   * @returns Shortfall value (negative = need to order, positive = surplus)
   */
  const calculateShortfall = (item: BomItem): number => {
    const totalRequired = item.total_qty * buildQuantity;

    let stockValue = item.in_stock;

    if (includeAllocations) {
      stockValue -= item.allocated;
    }

    if (includeOnOrder) {
      stockValue += item.on_order;
    }

    return stockValue - totalRequired;
  };

  /**
   * Count how many parts need to be ordered (shortfall < 0)
   *
   * @param items - Array of BOM items to check
   * @returns Count of items with insufficient stock
   */
  const countNeedToOrder = (items: BomItem[]): number => {
    return items.filter((item) => {
      const totalRequired = item.total_qty * buildQuantity;

      let stockValue = item.in_stock;

      if (includeAllocations) {
        stockValue -= item.allocated;
      }

      if (includeOnOrder) {
        stockValue += item.on_order;
      }

      return totalRequired > stockValue;
    }).length;
  };

  /**
   * Count how many parts are completely out of stock (in_stock <= 0)
   *
   * @param items - Array of BOM items to check
   * @returns Count of items with zero or negative stock
   */
  const countOutOfStock = (items: BomItem[]): number => {
    return items.filter((item) => item.in_stock <= 0).length;
  };

  /**
   * Count how many parts have incoming purchase orders (on_order > 0)
   *
   * @param items - Array of BOM items to check
   * @returns Count of items with pending orders
   */
  const countOnOrder = (items: BomItem[]): number => {
    return items.filter((item) => item.on_order > 0).length;
  };

  return {
    calculateShortfall,
    countNeedToOrder,
    countOutOfStock,
    countOnOrder
  };
}
