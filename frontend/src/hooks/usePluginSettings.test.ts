/**
 * Tests for plugin settings persistence.
 *
 * Ticket #30: includeOptional defaults on, and a localStorage blob written
 * before the key existed must merge over defaults rather than reading the
 * missing key as undefined - otherwise upgrading users would silently lose
 * optional demand on their next generation.
 */

import { createRequire } from 'node:module';
import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  DEFAULT_PLUGIN_SETTINGS,
  SETTINGS_STORAGE_KEY
} from '../types/PluginSettings';

// vite-plugin-externals maps 'react' -> window.React at build time; under
// Node/vitest seed it before importing the hook module (same pattern as
// bomTableColumns.test.tsx).
const require = createRequire(import.meta.url);
const React = require('react') as typeof import('react');
(globalThis as any).window = { ...(globalThis as any).window, React };

const { loadPluginSettings } = await import('./usePluginSettings');

function stubLocalStorage(stored: string | null) {
  vi.stubGlobal('localStorage', {
    getItem: (key: string) => (key === SETTINGS_STORAGE_KEY ? stored : null),
    setItem: vi.fn(),
    removeItem: vi.fn()
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('loadPluginSettings', () => {
  it('returns defaults when nothing is stored', () => {
    stubLocalStorage(null);
    expect(loadPluginSettings()).toEqual(DEFAULT_PLUGIN_SETTINGS);
  });

  it('defaults includeOptional on for a pre-#30 stored blob', () => {
    // Blob written by an older panel version - no includeOptional key.
    stubLocalStorage(
      JSON.stringify({
        maxDepth: 5,
        expandPurchasedAssemblies: true,
        includeSubstitutes: true
      })
    );
    const loaded = loadPluginSettings();
    expect(loaded.maxDepth).toBe(5);
    expect(loaded.includeSubstitutes).toBe(true);
    expect(loaded.includeOptional).toBe(true);
  });

  it('preserves an explicitly stored includeOptional=false', () => {
    stubLocalStorage(
      JSON.stringify({ ...DEFAULT_PLUGIN_SETTINGS, includeOptional: false })
    );
    expect(loadPluginSettings().includeOptional).toBe(false);
  });

  it('falls back to defaults on corrupt JSON', () => {
    stubLocalStorage('{not json');
    expect(loadPluginSettings()).toEqual(DEFAULT_PLUGIN_SETTINGS);
  });
});
