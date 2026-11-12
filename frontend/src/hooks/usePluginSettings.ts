import { useCallback, useEffect, useState } from 'react';

import {
  DEFAULT_PLUGIN_SETTINGS,
  type PluginSettings,
  SETTINGS_STORAGE_KEY
} from '../types/PluginSettings';

/**
 * Hook result interface for plugin settings management
 */
export interface UsePluginSettingsResult {
  /** Current plugin settings */
  settings: PluginSettings;

  /** Update a single setting */
  updateSetting: <K extends keyof PluginSettings>(
    key: K,
    value: PluginSettings[K]
  ) => void;

  /** Reset all settings to defaults */
  resetToDefaults: () => void;

  /** Check if settings differ from defaults */
  hasCustomSettings: boolean;
}

/**
 * Load persisted settings, merged over defaults.
 *
 * Merge (not verbatim return) is the contract: settings added after a
 * stored blob was written - e.g. includeOptional in #30 - must keep their
 * declared default. A missing key must not read as undefined/false.
 *
 * Exported for unit tests; the hook calls it as its useState initializer.
 */
export function loadPluginSettings(): PluginSettings {
  try {
    const stored = localStorage.getItem(SETTINGS_STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      if (parsed && typeof parsed === 'object') {
        return { ...DEFAULT_PLUGIN_SETTINGS, ...parsed };
      }
    }
  } catch (err) {
    console.warn('Failed to load settings from localStorage:', err);
  }
  return DEFAULT_PLUGIN_SETTINGS;
}

/**
 * Custom hook for managing plugin settings with localStorage persistence
 *
 * Handles:
 * - Loading settings from localStorage on mount
 * - Auto-persisting settings changes to localStorage
 * - Graceful degradation if localStorage unavailable
 * - Progressive disclosure state (show panel vs. gear icon)
 * - Detecting custom vs. default settings
 *
 * @returns Plugin settings state and control functions
 */
export function usePluginSettings(): UsePluginSettingsResult {
  // Load from localStorage or use defaults
  const [settings, setSettings] = useState<PluginSettings>(loadPluginSettings);

  // Persist settings to localStorage whenever they change
  useEffect(() => {
    try {
      localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(settings));
    } catch (err) {
      console.warn('Failed to save settings to localStorage:', err);
      // Continue with in-memory settings only
    }
  }, [settings]);

  /**
   * Update individual setting
   */
  const updateSetting = useCallback(
    <K extends keyof PluginSettings>(key: K, value: PluginSettings[K]) => {
      setSettings((prev) => ({ ...prev, [key]: value }));
    },
    []
  );

  /**
   * Reset to defaults
   */
  const resetToDefaults = useCallback(() => {
    setSettings(DEFAULT_PLUGIN_SETTINGS);
  }, []);

  /**
   * Check if settings differ from defaults
   */
  const hasCustomSettings =
    settings.maxDepth !== DEFAULT_PLUGIN_SETTINGS.maxDepth ||
    settings.expandPurchasedAssemblies !==
      DEFAULT_PLUGIN_SETTINGS.expandPurchasedAssemblies ||
    settings.includeSubstitutes !==
      DEFAULT_PLUGIN_SETTINGS.includeSubstitutes ||
    settings.includeOptional !== DEFAULT_PLUGIN_SETTINGS.includeOptional;

  return {
    settings,
    updateSetting,
    resetToDefaults,
    hasCustomSettings
  };
}
