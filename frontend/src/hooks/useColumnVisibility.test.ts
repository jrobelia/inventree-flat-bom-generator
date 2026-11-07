/**
 * Tests for the auto-managed column set in useColumnVisibility.
 *
 * The presence computation is a pure exported function so the auto-hide
 * contract is testable without a React renderer: each data-dependent
 * column reports whether the BOM data carries its signal, and the hook
 * hides/shows the accessor accordingly. The 'maximum_stock' entry is the
 * ticket-#26 member - a Max Stock column that stays hidden unless a row
 * has a ceiling set.
 */

import { createRequire } from 'node:module';
import { describe, expect, it } from 'vitest';
import type { BomItem } from '../types/BomTypes';

// vite-plugin-externals maps 'react' -> window.React at build time; under
// Node/vitest the externals shim reads window.React, which does not exist
// until seeded. Seed it before importing the hook module (same pattern as
// bomTableColumns.test.tsx) - the test only calls the pure presence
// function, never the hook itself.
const require = createRequire(import.meta.url);
(globalThis as any).window = {
  ...(globalThis as any).window,
  React: require('react')
};

const { autoManagedColumnPresence } = await import('./useColumnVisibility');

function item(overrides: Partial<BomItem>): BomItem {
  return {
    part_id: 1,
    ipn: 'TEST-001',
    part_name: 'Test Part',
    full_name: 'TEST-001 | Test Part',
    description: '',
    part_type: 'Coml',
    is_assembly: false,
    purchaseable: true,
    total_qty: 1,
    unit: 'pcs',
    in_stock: 0,
    on_order: 0,
    allocated: 0,
    available: 0,
    net_stock: 0,
    quantity_to_order: 0,
    link: '/part/1/',
    ...overrides
  } as BomItem;
}

function presenceOf(items: BomItem[], accessor: string): boolean {
  const entry = autoManagedColumnPresence(items).find(
    ([name]) => name === accessor
  );
  if (!entry) {
    throw new Error(`accessor '${accessor}' is not auto-managed`);
  }
  return entry[1];
}

describe('autoManagedColumnPresence', () => {
  it('manages cut_length, piece_count, inherited_from, and maximum_stock', () => {
    const accessors = autoManagedColumnPresence([item({})]).map(
      ([name]) => name
    );
    expect(accessors).toEqual([
      'cut_length',
      'piece_count',
      'inherited_from',
      'maximum_stock'
    ]);
  });

  it('shows Max Stock when any row carries a ceiling (ticket #26)', () => {
    expect(
      presenceOf(
        [item({ maximum_stock: null }), item({ maximum_stock: 40 })],
        'maximum_stock'
      )
    ).toBe(true);
  });

  it('hides Max Stock when no row has a ceiling set (ticket #26)', () => {
    expect(presenceOf([item({ maximum_stock: null })], 'maximum_stock')).toBe(
      false
    );
    // Upstream stores 0 for 'no maximum' - a 0 that slips through must not
    // count as a ceiling.
    expect(presenceOf([item({ maximum_stock: 0 })], 'maximum_stock')).toBe(
      false
    );
    // Field absent entirely (older payload) also stays hidden.
    expect(presenceOf([item({})], 'maximum_stock')).toBe(false);
  });
});
