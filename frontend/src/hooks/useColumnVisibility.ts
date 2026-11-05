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
 * - Auto-manages data-dependent columns (cut_length, piece_count,
 *   inherited_from) based on BOM data (shows only when data is present)
 * - Provides toggle function for column visibility
 *
 * @param bomData - Current BOM data (used to detect cut lists, piece
 *   counts, and inherited BOM lines)
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
      const hasCutListRows = bomData.bom_items.some(
        (item) => item.cut_list && item.cut_list.length > 0
      );
      const hasPieceCounts = bomData.bom_items.some(
        (item) => (item.piece_count ?? 1) > 1
      );
      const hasInheritedLines = bomData.bom_items.some(
        (item) => !!item.inherited_from
      );

      setHiddenColumns((prev) => {
        const newSet = new Set(prev);

        for (const [accessor, present] of [
          ['cut_length', hasCutListRows],
          ['piece_count', hasPieceCounts],
          ['inherited_from', hasInheritedLines]
        ] as const) {
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
