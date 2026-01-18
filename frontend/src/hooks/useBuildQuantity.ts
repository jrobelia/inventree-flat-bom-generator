import { useState } from 'react';

/**
 * Hook result interface for build quantity state
 */
export interface UseBuildQuantityResult {
  buildQuantity: number;
  setBuildQuantity: (value: number) => void;
}

/**
 * Custom hook for managing build quantity state
 *
 * Simple state management for the number of assemblies to build.
 * Used as a multiplier for all BOM quantity calculations.
 *
 * @param initialValue - Initial build quantity (default: 1)
 * @returns Build quantity state and setter
 */
export function useBuildQuantity(
  initialValue: number = 1
): UseBuildQuantityResult {
  const [buildQuantity, setBuildQuantity] = useState<number>(initialValue);

  return {
    buildQuantity,
    setBuildQuantity
  };
}
