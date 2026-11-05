/**
 * Component tests for the flat-BOM DataTable column definitions.
 *
 * Ticket #15: 'Net Stock' and 'To Order' columns render the upstream
 * shortage fields. Column definitions are plain objects — render()
 * returns React elements without needing a DOM.
 */

import { createRequire } from 'node:module';
import type { ReactElement, ReactNode } from 'react';
import { describe, expect, it } from 'vitest';
import type { BomItem } from '../types/BomTypes';

// vite-plugin-externals maps 'react' -> window.React and
// '@mantine/core' -> window.MantineCore at build time; classic-runtime JSX
// resolves a free 'React' global. Under Node/vitest neither exists, so seed
// them before importing the columns module (tag-string stand-ins are enough -
// the test only reads element props/children, it never mounts a DOM).
const require = createRequire(import.meta.url);
const React = require('react') as typeof import('react');
(globalThis as any).React = React;
(globalThis as any).window = {
  ...(globalThis as any).window,
  React,
  MantineCore: {
    Anchor: 'a',
    Badge: 'span',
    Group: 'div',
    Text: 'span',
    Tooltip: 'div'
  }
};

const { createBomTableColumns } = await import('./bomTableColumns');

/**
 * Collect all text leaves from a React element tree.
 * Elements are plain objects; props.children holds nested content.
 */
function textOf(node: ReactNode): string {
  if (node == null || typeof node === 'boolean') {
    return '';
  }
  if (typeof node === 'string' || typeof node === 'number') {
    return String(node);
  }
  if (Array.isArray(node)) {
    return node.map(textOf).join('');
  }
  if (typeof node === 'object' && 'props' in node) {
    return textOf(
      (node as ReactElement<{ children?: ReactNode }>).props.children
    );
  }
  return '';
}

function makeItem(overrides: Partial<BomItem>): BomItem {
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
    is_child_row: false,
    ...overrides
  } as BomItem;
}

function columnBy(accessor: string) {
  const columns = createBomTableColumns({
    buildQuantity: 1,
    includeAllocations: true,
    includeOnOrder: true,
    calculateShortfall: () => 0
  });
  const column = columns.find((c) => c.accessor === accessor);
  if (!column?.render) {
    throw new Error(`column '${accessor}' not found or has no render`);
  }
  return column;
}

describe('shortage field columns (ticket #15)', () => {
  it('exposes Net Stock and To Order columns, sortable and toggleable', () => {
    const net = columnBy('net_stock');
    const toOrder = columnBy('quantity_to_order');

    expect(net.title).toBe('Net Stock');
    expect(toOrder.title).toBe('To Order');
    expect(net.sortable).toBe(true);
    expect(toOrder.sortable).toBe(true);
  });

  it('sits between On Order and Build Margin', () => {
    const columns = createBomTableColumns({
      buildQuantity: 1,
      includeAllocations: true,
      includeOnOrder: true,
      calculateShortfall: () => 0
    });
    const accessors = columns.map((c) => c.accessor);

    expect(accessors.indexOf('net_stock')).toBeGreaterThan(
      accessors.indexOf('on_order')
    );
    expect(accessors.indexOf('net_stock')).toBeLessThan(
      accessors.indexOf('shortfall')
    );
    expect(accessors.indexOf('quantity_to_order')).toBeLessThan(
      accessors.indexOf('shortfall')
    );
  });

  it('renders a negative net_stock as a shortage signal, unfloored', () => {
    const net = columnBy('net_stock');
    const text = textOf(
      net.render!(makeItem({ net_stock: -5 }), 0) as ReactNode
    );
    expect(text).toContain('-5.00');
  });

  it('renders positive net_stock and quantity_to_order values with unit', () => {
    const net = columnBy('net_stock');
    const toOrder = columnBy('quantity_to_order');

    expect(
      textOf(net.render!(makeItem({ net_stock: 12 }), 0) as ReactNode)
    ).toContain('12.00');
    expect(
      textOf(
        toOrder.render!(makeItem({ quantity_to_order: 7.5 }), 0) as ReactNode
      )
    ).toContain('7.50');
    expect(
      textOf(
        toOrder.render!(makeItem({ quantity_to_order: 7.5 }), 0) as ReactNode
      )
    ).toContain('[pcs]');
  });

  it('renders a dimmed dash for zero and for child rows', () => {
    const net = columnBy('net_stock');
    const toOrder = columnBy('quantity_to_order');

    // Zero cells mirror the sibling stock columns: '-' plus [unit]
    expect(textOf(net.render!(makeItem({ net_stock: 0 }), 0))).toBe('-[pcs]');
    expect(textOf(toOrder.render!(makeItem({ quantity_to_order: 0 }), 0))).toBe(
      '-[pcs]'
    );

    const cutChild = makeItem({
      is_child_row: true,
      child_row_type: 'cutlist'
    });
    expect(textOf(net.render!(cutChild, 0))).toBe('-');
    expect(textOf(toOrder.render!(cutChild, 0))).toBe('-');

    // Substitute child rows lack the fields entirely -> still a clean dash
    const subChild = makeItem({
      is_child_row: true,
      child_row_type: 'substitute',
      net_stock: undefined,
      quantity_to_order: undefined
    });
    expect(textOf(net.render!(subChild, 0))).toBe('-[pcs]');
    expect(textOf(toOrder.render!(subChild, 0))).toBe('-[pcs]');
  });
});
