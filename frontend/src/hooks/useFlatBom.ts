import type { InvenTreePluginContext } from '@inventreedb/ui';
import { useState } from 'react';

import type { FlatBomResponse } from '../types/BomTypes';
import type { PluginSettings } from '../types/PluginSettings';

/**
 * Hook result interface for flat BOM API operations
 */
export interface UseFlatBomResult {
  bomData: FlatBomResponse | null;
  loading: boolean;
  error: string | null;
  generateFlatBom: (settings: PluginSettings) => Promise<void>;
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
   * @param settings - Plugin settings to apply (converted to query params)
   */
  const generateFlatBom = async (settings: PluginSettings) => {
    if (!partId) {
      setError('No part ID available');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Build query params from settings (only include non-defaults)
      const queryParams = new URLSearchParams();

      // max_depth: Include if non-zero (0 = unlimited)
      if (settings.maxDepth > 0) {
        queryParams.append('max_depth', settings.maxDepth.toString());
      }

      // expand_purchased_assemblies: Include if true (default false)
      if (settings.expandPurchasedAssemblies) {
        queryParams.append('expand_purchased_assemblies', 'true');
      }

      // include_internal_fab_in_cutlist: Include if true (default false)
      if (settings.includeInternalFabInCutlist) {
        queryParams.append('include_internal_fab_in_cutlist', 'true');
      }

      const queryString = queryParams.toString();
      const url = `/plugin/flat-bom-generator/flat-bom/${partId}/${
        queryString ? `?${queryString}` : ''
      }`;

      // Call the plugin API endpoint with 30 second timeout
      const response = await context.api.get(url, { timeout: 30000 });

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
