import { useCallback, useEffect, useState } from 'react';

import {
  DEFAULT_PLUGIN_SETTINGS,
  HAS_GENERATED_STORAGE_KEY,
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

  /** Track if user has generated BOM at least once (for progressive disclosure) */
  hasGeneratedOnce: boolean;

  /** Mark as generated (triggers progressive disclosure) */
  markAsGenerated: () => void;
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
  const [settings, setSettings] = useState<PluginSettings>(() => {
    try {
      const stored = localStorage.getItem(SETTINGS_STORAGE_KEY);
      if (stored) {
        return JSON.parse(stored);
      }
    } catch (err) {
      console.warn('Failed to load settings from localStorage:', err);
    }
    return DEFAULT_PLUGIN_SETTINGS;
  });

  // Track if user has generated BOM before (for progressive disclosure)
  const [hasGeneratedOnce, setHasGeneratedOnce] = useState<boolean>(() => {
    try {
      return localStorage.getItem(HAS_GENERATED_STORAGE_KEY) === 'true';
    } catch (err) {
      console.warn('Failed to load generation state from localStorage:', err);
      return false;
    }
  });

  // Persist settings to localStorage whenever they change
  useEffect(() => {
    try {
      localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(settings));
    } catch (err) {
      console.warn('Failed to save settings to localStorage:', err);
      // Continue with in-memory settings only
    }
  }, [settings]);

  // Persist hasGeneratedOnce to localStorage
  useEffect(() => {
    try {
      localStorage.setItem(
        HAS_GENERATED_STORAGE_KEY,
        hasGeneratedOnce.toString()
      );
    } catch (err) {
      console.warn('Failed to save generation state to localStorage:', err);
    }
  }, [hasGeneratedOnce]);

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
    settings.includeInternalFabInCutlist !==
      DEFAULT_PLUGIN_SETTINGS.includeInternalFabInCutlist;

  /**
   * Mark as generated (triggers progressive disclosure)
   */
  const markAsGenerated = useCallback(() => {
    setHasGeneratedOnce(true);
  }, []);

  return {
    settings,
    updateSetting,
    resetToDefaults,
    hasCustomSettings,
    hasGeneratedOnce,
    markAsGenerated
  };
}
