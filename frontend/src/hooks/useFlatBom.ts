import type { InvenTreePluginContext } from '@inventreedb/ui';
import { useState } from 'react';

import type { FlatBomResponse } from '../types/BomTypes';

/**
 * Hook result interface for flat BOM API operations
 */
export interface UseFlatBomResult {
  bomData: FlatBomResponse | null;
  loading: boolean;
  error: string | null;
  generateFlatBom: () => Promise<void>;
  clearError: () => void;
}

/**
 * Custom hook for managing flat BOM API calls and state
 *
 * Handles:
 * - API request state (loading, error, data)
 * - Calling plugin API endpoint with timeout
 * - Error extraction from API responses
 *
 * @param partId - Part ID to generate flat BOM for
 * @param context - InvenTree plugin context for API calls
 * @returns API state and control functions
 */
export function useFlatBom(
  partId: number | undefined,
  context: InvenTreePluginContext
): UseFlatBomResult {
  const [loading, setLoading] = useState(false);
  const [bomData, setBomData] = useState<FlatBomResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  /**
   * Generate flat BOM by calling the plugin API
   */
  const generateFlatBom = async () => {
    if (!partId) {
      setError('No part ID available');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Call the plugin API endpoint with 30 second timeout
      const response = await context.api.get(
        `/plugin/flat-bom-generator/flat-bom/${partId}/`,
        { timeout: 30000 }
      );

      if (response.status === 200) {
        console.log('[FlatBOM] API Response:', response.data);
        console.log('[FlatBOM] Metadata:', response.data.metadata);
        console.log('[FlatBOM] Warnings:', response.data.metadata?.warnings);
        setBomData(response.data);
      } else {
        setError(`API returned status ${response.status}`);
      }
    } catch (err: any) {
      setError(
        err?.response?.data?.error ||
          err.message ||
          'Failed to generate flat BOM'
      );
      console.error('Error generating flat BOM:', err);
    } finally {
      setLoading(false);
    }
  };

  /**
   * Clear error state (for dismissing error alerts)
   */
  const clearError = () => {
    setError(null);
  };

  return {
    bomData,
    loading,
    error,
    generateFlatBom,
    clearError
  };
}
