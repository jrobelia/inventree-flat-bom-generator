import { useEffect, useState } from 'react';

import type { FlatBomResponse } from '../types/BomTypes';

/**
 * Hook result interface for column visibility management
 */
export interface UseColumnVisibilityResult {
  hiddenColumns: Set<string>;
  toggleColumn: (accessor: string) => void;
}

/**
 * Custom hook for managing DataTable column visibility with localStorage persistence
 *
 * Features:
 * - Persists hidden columns in localStorage
 * - Auto-manages cut_length column based on BOM data (shows only if CtL parts present)
 * - Provides toggle function for column visibility
 *
 * @param bomData - Current BOM data (used to detect cut-to-length parts)
 * @returns Hidden columns set and toggle function
 */
export function useColumnVisibility(
  bomData: FlatBomResponse | null
): UseColumnVisibilityResult {
  // Column visibility state - stored in localStorage
  const [hiddenColumns, setHiddenColumns] = useState<Set<string>>(() => {
    const stored = localStorage.getItem('flat-bom-hidden-columns');
    return stored ? new Set(JSON.parse(stored)) : new Set();
  });

  // Auto-manage cut_length column visibility based on BOM data
  useEffect(() => {
    if (bomData) {
      const hasCtLParts = bomData.bom_items.some(
        (item) => item.cut_list && item.cut_list.length > 0
      );

      setHiddenColumns((prev) => {
        const newSet = new Set(prev);

        if (hasCtLParts) {
          newSet.delete('cut_length');
        } else {
          newSet.add('cut_length');
        }

        localStorage.setItem(
          'flat-bom-hidden-columns',
          JSON.stringify([...newSet])
        );

        return newSet;
      });
    }
  }, [bomData]);

  /**
   * Toggle column visibility and persist to localStorage
   *
   * @param accessor - Column accessor to toggle
   */
  const toggleColumn = (accessor: string) => {
    setHiddenColumns((prev) => {
      const newSet = new Set(prev);

      if (newSet.has(accessor)) {
        newSet.delete(accessor);
      } else {
        newSet.add(accessor);
      }

      localStorage.setItem(
        'flat-bom-hidden-columns',
        JSON.stringify([...newSet])
      );

      return newSet;
    });
  };

  return {
    hiddenColumns,
    toggleColumn
  };
}
