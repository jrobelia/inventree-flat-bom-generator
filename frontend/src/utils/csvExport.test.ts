/**
 * Tests for CSV export - ruling R-017: CSV values are the same
 * build-quantity-scaled values shown in the table.
 */

import { describe, expect, it } from 'vitest';
import type { BomItem } from '../types/BomTypes';
import { flattenBomData } from './bomDataProcessing';
import { generateCsvContent } from './csvExport';

function createBomItem(overrides: Partial<BomItem>): BomItem {
  return {
    part_id: 1,
    ipn: 'TEST-001',
    part_name: 'Test Part',
    full_name: 'TEST-001 | Test Part',
    description: 'Test description',
    part_type: 'Fab',
    is_assembly: false,
    purchaseable: true,
    total_qty: 1,
    unit: 'mm',
    in_stock: 0,
    on_order: 0,
    allocated: 0,
    available: 0,
    link: '/part/1/',
    is_child_row: false,
    ...overrides
  } as BomItem;
}

describe('generateCsvContent', () => {
  it('scales cut-list counts by buildQuantity like the table does', () => {
    // A '500 x 6' cut row at buildQuantity 2 must export Total Qty = 12,
    // matching the table's count x buildQuantity cell.
    const items = [
      createBomItem({
        part_id: 10,
        ipn: 'BAR-500',
        part_name: 'Steel Bar',
        total_qty: 3000,
        cut_list: [{ size: 500, count: 6, unit: 'mm' }]
      })
    ];
    const flat = flattenBomData(items);

    const csv = generateCsvContent(flat, 2, true, true);
    const lines = csv.split('\n');
    const header = lines[0].split(',');
    const qtyCol = header.indexOf('Total Qty');
    const cutCol = header.indexOf('Cut Length');

    // Parent: 3000 x 2 = 6000
    expect(Number(lines[1].split(',')[qtyCol])).toBe(6000);
    // Cut child: 6 pieces x 2 = 12, cut length stays 500
    const childCells = lines[2].split(',');
    expect(Number(childCells[qtyCol])).toBe(12);
    expect(Number(childCells[cutCol])).toBe(500);
  });

  it('exports Net Stock and To Order before Build Margin, unscaled by buildQuantity', () => {
    // Ticket #15: both are part-level stock signals like in_stock, not
    // requirements - buildQuantity must not scale them (R-017 covers
    // requirement scaling only).
    const items = [
      createBomItem({
        net_stock: -5,
        quantity_to_order: 7.5,
        in_stock: 3,
        allocated: 8,
        on_order: 0
      })
    ];
    const csv = generateCsvContent(items, 10, true, true);
    const lines = csv.split('\n');
    const header = lines[0].split(',');
    const netCol = header.indexOf('Net Stock');
    const toOrderCol = header.indexOf('To Order');
    const marginCol = header.indexOf('Build Margin');

    expect(netCol).toBeGreaterThan(-1);
    expect(toOrderCol).toBeGreaterThan(-1);
    expect(netCol).toBeLessThan(marginCol);
    expect(toOrderCol).toBeLessThan(marginCol);

    const cells = lines[1].split(',');
    expect(Number(cells[netCol])).toBe(-5);
    expect(Number(cells[toOrderCol])).toBe(7.5);
  });

  it('emits placeholders for the shortage columns on cut-list child rows', () => {
    const items = [
      createBomItem({
        cut_list: [{ size: 500, count: 2, unit: 'mm' }]
      })
    ];
    const csv = generateCsvContent(flattenBomData(items), 1, true, true);
    const lines = csv.split('\n');
    const header = lines[0].split(',');
    const childCells = lines[2].split(',');

    expect(childCells[header.indexOf('Net Stock')]).toBe('-');
    expect(childCells[header.indexOf('To Order')]).toBe('-');
    // Row width still matches the header
    expect(childCells.length).toBe(header.length);
  });

  it('keeps unit cell on the cut row, blank on the parent', () => {
    const items = [
      createBomItem({
        cut_list: [{ size: 250, count: 4, unit: 'mm' }]
      })
    ];
    const csv = generateCsvContent(flattenBomData(items), 1, false, false);
    const lines = csv.split('\n');
    const header = lines[0].split(',');
    const cutUnitCol = header.indexOf('Cut Unit');

    expect(lines[2].split(',')[cutUnitCol]).toBe('mm');
  });
});
