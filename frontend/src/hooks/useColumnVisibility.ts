import { useEffect, useState } from 'react';

import type { BomItem, FlatBomResponse } from '../types/BomTypes';

/**
 * Hook result interface for column visibility management
 */
export interface UseColumnVisibilityResult {
  hiddenColumns: Set<string>;
  toggleColumn: (accessor: string) => void;
}

/**
 * Auto-managed column presence: the data-dependent columns that hide
 * unless the BOM data carries their signal. Returns [accessor, present]
 * pairs; the hook shows the column when present is true and hides it
 * otherwise.
 *
 * - cut_length: any item carries cut-list entries
 * - piece_count: any line needs more than one piece
 * - inherited_from: any line is inherited from an ancestor part
 * - maximum_stock: any part has a stock ceiling set (null or 0 = unset)
 */
export function autoManagedColumnPresence(
  items: BomItem[]
): Array<[string, boolean]> {
  return [
    [
      'cut_length',
      items.some((item) => item.cut_list && item.cut_list.length > 0)
    ],
    ['piece_count', items.some((item) => (item.piece_count ?? 1) > 1)],
    ['inherited_from', items.some((item) => !!item.inherited_from)],
    ['maximum_stock', items.some((item) => !!item.maximum_stock)]
  ];
}

/**
 * Custom hook for managing DataTable column visibility with localStorage persistence
 *
 * Features:
 * - Persists hidden columns in localStorage
 * - Auto-manages data-dependent columns (cut_length, piece_count,
 *   inherited_from, maximum_stock) based on BOM data (shows only when
 *   data is present)
 * - Provides toggle function for column visibility
 *
 * @param bomData - Current BOM data (used to detect cut lists, piece
 *   counts, inherited BOM lines, and stock ceilings)
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

  // Auto-manage data-dependent column visibility based on BOM data
  useEffect(() => {
    if (bomData) {
      setHiddenColumns((prev) => {
        const newSet = new Set(prev);

        for (const [accessor, present] of autoManagedColumnPresence(
          bomData.bom_items
        )) {
          if (present) {
            newSet.delete(accessor);
          } else {
            newSet.add(accessor);
          }
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
