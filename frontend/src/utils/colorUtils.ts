/**
 * Color Utilities
 * Centralized color logic for badges and UI elements
 */

/**
 * Get stock level color based on requirement
 *
 * @param stockLevel - Current stock level
 * @param required - Required quantity for build
 * @returns Badge color ('green', 'orange', or 'red')
 *
 * @example
 * getStockColor(100, 50) // 'green' - stock >= required
 * getStockColor(25, 50) // 'orange' - some stock but < required
 * getStockColor(0, 50) // 'red' - no stock
 */
export function getStockColor(
  stockLevel: number,
  required: number
): 'green' | 'orange' | 'red' {
  if (stockLevel >= required) return 'green';
  if (stockLevel > 0) return 'orange';
  return 'red';
}

/**
 * Part type badge colors mapping
 * Used for consistent part type visualization
 */
export const PART_TYPE_COLORS: Record<string, string> = {
  TLA: 'grape',
  Coml: 'green',
  Fab: 'blue',
  CtL: 'teal',
  'Purchased Assy': 'orange',
  'Internal Fab': 'cyan',
  Assy: 'violet',
  Other: 'gray'
};

/**
 * Get color for part type badge
 *
 * @param partType - Part type string
 * @returns Color name for Mantine Badge component
 *
 * @example
 * getPartTypeColor('Fab') // 'blue'
 * getPartTypeColor('Unknown') // 'gray' (fallback)
 */
export function getPartTypeColor(partType: string): string {
  return PART_TYPE_COLORS[partType] || 'gray';
}

/**
 * Calculate opacity for dimmed elements
 * Used when checkboxes toggle related data visibility
 *
 * @param isDimmed - Whether element should be dimmed
 * @returns Opacity value (0.4 for dimmed, 1.0 for normal)
 *
 * @example
 * getDimmedOpacity(true) // 0.4
 * getDimmedOpacity(false) // 1.0
 */
export function getDimmedOpacity(isDimmed: boolean): number {
  return isDimmed ? 0.4 : 1.0;
}

/**
 * Get badge color for stock-related columns
 * Generic helper for various stock display scenarios
 *
 * @param value - Numeric value to evaluate
 * @returns Color name for Mantine Badge component
 *
 * @example
 * getStockBadgeColor(100) // 'blue' - on order
 * getStockBadgeColor(0) // returns null (caller handles zero case)
 */
export function getStockBadgeColor(value: number): string {
  if (value > 0) return 'blue'; // For "on order" column
  return 'gray';
}

/**
 * Standard badge colors for specific use cases
 */
export const BADGE_COLORS = {
  ALLOCATED: 'yellow',
  ON_ORDER: 'blue',
  BUILDING: 'cyan',
  SHORTFALL: 'red',
  SURPLUS: 'green',
  WARNING: 'orange'
} as const;
