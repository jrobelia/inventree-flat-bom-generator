/**
 * Plugin generation settings (moved from admin panel to UI in v0.11.0)
 *
 * These settings are persisted to localStorage and sent as query params to backend.
 * They trigger BOM regeneration when changed.
 *
 * Note: Frontend-only display filters (includeAllocations, includeOnOrder, showCutlistRows)
 * are managed as regular useState in Panel.tsx. They don't need persistence or backend
 * communication, so they're kept separate from PluginSettings.
 */
export interface PluginSettings {
  /** Maximum BOM traversal depth (0 = unlimited) */
  maxDepth: number;

  /** Expand assemblies with default suppliers */
  expandPurchasedAssemblies: boolean;

  /** Include Internal Fab parts in cutlist processing */
  includeInternalFabInCutlist: boolean;
}

/**
 * Default plugin settings (hardcoded)
 *
 * These defaults match the old plugin admin panel defaults:
 * - MAX_DEPTH: 0 (unlimited)
 * - SHOW_PURCHASED_ASSEMBLIES: false
 * - INCLUDE_INTERNAL_FAB_IN_CUTLIST: false
 */
export const DEFAULT_PLUGIN_SETTINGS: PluginSettings = {
  maxDepth: 0,
  expandPurchasedAssemblies: false,
  includeInternalFabInCutlist: false
};

/**
 * localStorage key for persisting plugin settings
 * Scoped globally (not per-part)
 */
export const SETTINGS_STORAGE_KEY = 'flatbom_plugin_settings';
