/**
 * Tests for the flat-BOM query string contract.
 *
 * Ticket #30: include_optional is always sent (like include_substitutes)
 * so the UI toggle wins over the plugin admin default.
 */

import { createRequire } from 'node:module';
import { describe, expect, it } from 'vitest';
import { DEFAULT_PLUGIN_SETTINGS } from '../types/PluginSettings';

// vite-plugin-externals maps 'react' -> window.React at build time; under
// Node/vitest seed it before importing the hook module (same pattern as
// bomTableColumns.test.tsx).
const require = createRequire(import.meta.url);
const React = require('react') as typeof import('react');
(globalThis as any).window = { ...(globalThis as any).window, React };

const { buildFlatBomQuery } = await import('./useFlatBom');

function paramsOf(query: string): URLSearchParams {
  return new URLSearchParams(query);
}

describe('buildFlatBomQuery', () => {
  it('sends include_optional=true at defaults', () => {
    const params = paramsOf(buildFlatBomQuery(DEFAULT_PLUGIN_SETTINGS));
    expect(params.get('include_optional')).toBe('true');
  });

  it('sends include_optional=false when the toggle is off', () => {
    const params = paramsOf(
      buildFlatBomQuery({ ...DEFAULT_PLUGIN_SETTINGS, includeOptional: false })
    );
    expect(params.get('include_optional')).toBe('false');
  });

  it('keeps the established always-send params alongside the new one', () => {
    const params = paramsOf(buildFlatBomQuery(DEFAULT_PLUGIN_SETTINGS));
    expect(params.get('include_substitutes')).toBe('false');
    expect(params.get('max_depth')).toBeNull();
    expect(params.get('expand_purchased_assemblies')).toBeNull();
  });
});
