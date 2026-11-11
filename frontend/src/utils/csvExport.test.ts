/**
 * Tests for CSV export - ruling R-017: CSV values are the same
 * build-quantity-scaled values shown in the table.
 */

import { describe, expect, it } from 'vitest';
import type { BomItem, SubstitutePart } from '../types/BomTypes';
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

// Helper to create a minimal SubstitutePart for testing (same shape as
// bomDataProcessing.test.ts)
function createSubstitutePart(
  overrides: Partial<SubstitutePart>
): SubstitutePart {
  return {
    substitute_id: 1,
    part_id: 99,
    ipn: 'SUB-001',
    part_name: 'Substitute Part',
    full_name: 'SUB-001 | Substitute Part',
    description: '',
    unit: 'pcs',
    parent_total_qty: 5,
    in_stock: 0,
    on_order: 0,
    allocated: 0,
    available: 0,
    net_stock: 0,
    quantity_to_order: 0,
    image: null,
    thumbnail: null,
    link: '',
    ...overrides
  };
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

describe('Inherited From column (ticket #24, ruling R-026; #44 drops Pieces)', () => {
  // The CSV mirrors the table (R-017): Inherited From keeps its grid
  // position - after Cut Length / Cut Unit, before In Stock. A merged row
  // that nulls the scalar (R-025) exports a blank cell where the table
  // shows a dimmed dash.
  // The Pieces column is gone (#44, R-025 amendment): flat rows are
  // material lumps with piece_count uniformly 1, so the column could only
  // ever export a degenerate 1 - same treatment as the grid, which no
  // longer defines the column. Piece structure lives in the cut list.
  // Header literals below ('Inherited From', 'Cut Unit', 'In Stock') pin
  // the `headers` array in generateCsvContent (csvExport.ts).

  it('keeps Inherited From in grid order between Cut Unit and In Stock', () => {
    const items = [createBomItem({ inherited_from: 'WELD-T' })];
    const csv = generateCsvContent(items, 1, true, true);
    const lines = csv.split('\n');
    const header = lines[0].split(',');

    expect(header.indexOf('Pieces')).toBe(-1);
    const inheritedCol = header.indexOf('Inherited From');
    expect(inheritedCol).toBeGreaterThan(-1);
    // Grid: ... Cut Length, Inherited From, In Stock ...
    expect(inheritedCol).toBe(header.indexOf('Cut Unit') + 1);
    expect(header.indexOf('In Stock')).toBe(inheritedCol + 1);

    const cells = lines[1].split(',');
    expect(cells[inheritedCol]).toBe('WELD-T');
    expect(cells.length).toBe(header.length);
  });

  it('emits a blank cell when nothing is inherited (all-direct row)', () => {
    const items = [createBomItem({ inherited_from: null })];
    const csv = generateCsvContent(items, 1, true, true);
    const lines = csv.split('\n');
    const header = lines[0].split(',');
    const cells = lines[1].split(',');

    expect(cells[header.indexOf('Inherited From')]).toBe('');
    expect(cells.length).toBe(header.length);
  });

  it('keeps child rows truthful on inherited_from', () => {
    // A cut-list child inherits the parent's inherited_from (the table
    // renders that IPN on the child row too); a substitute child carries
    // the field blank.
    const items = [
      createBomItem({
        inherited_from: 'WELD-T',
        cut_list: [{ size: 500, count: 2, unit: 'mm' }],
        has_substitutes: true,
        substitute_parts: [createSubstitutePart({})]
      })
    ];
    const csv = generateCsvContent(flattenBomData(items), 1, true, true);
    const lines = csv.split('\n');
    const header = lines[0].split(',');
    const inheritedCol = header.indexOf('Inherited From');

    // Row order: parent, cut-list child, substitute child
    const cutChild = lines[2].split(',');
    expect(cutChild[inheritedCol]).toBe('WELD-T');
    expect(cutChild.length).toBe(header.length);

    const subChild = lines[3].split(',');
    expect(subChild[inheritedCol]).toBe('');
    expect(subChild.length).toBe(header.length);
  });
});

describe('Max Stock columns (ticket #26, ruling R-026 parity)', () => {
  // The CSV mirrors the table (R-017): the Max Stock column and the
  // exceeds_max_stock flag are contract fields on the API row, so both
  // get CSV counterparts in grid order - after To Order, before Build
  // Margin. An unset ceiling exports blank cells where the table shows a
  // dimmed dash (same encoding as the merged-null scalars).
  // Header literals below ('Max Stock', 'Exceeds Max Stock', 'To Order',
  // 'Build Margin') pin the `headers` array in generateCsvContent
  // (csvExport.ts).

  it('adds Max Stock and Exceeds Max Stock between To Order and Build Margin', () => {
    const items = [
      createBomItem({ maximum_stock: 40, exceeds_max_stock: true })
    ];
    const csv = generateCsvContent(items, 1, true, true);
    const lines = csv.split('\n');
    const header = lines[0].split(',');

    const maxCol = header.indexOf('Max Stock');
    const flagCol = header.indexOf('Exceeds Max Stock');
    expect(maxCol).toBe(header.indexOf('To Order') + 1);
    expect(flagCol).toBe(maxCol + 1);
    expect(header.indexOf('Build Margin')).toBe(flagCol + 1);

    const cells = lines[1].split(',');
    expect(cells[maxCol]).toBe('40');
    expect(cells[flagCol]).toBe('Yes');
    expect(cells.length).toBe(header.length);
  });

  it('exports the value and a No flag when the row is under its ceiling', () => {
    const items = [
      createBomItem({ maximum_stock: 150, exceeds_max_stock: false })
    ];
    const csv = generateCsvContent(items, 1, true, true);
    const lines = csv.split('\n');
    const header = lines[0].split(',');
    const cells = lines[1].split(',');

    expect(cells[header.indexOf('Max Stock')]).toBe('150');
    expect(cells[header.indexOf('Exceeds Max Stock')]).toBe('No');
  });

  it('emits blank cells when no ceiling is set', () => {
    const items = [
      createBomItem({ maximum_stock: null, exceeds_max_stock: null })
    ];
    const csv = generateCsvContent(items, 1, true, true);
    const lines = csv.split('\n');
    const header = lines[0].split(',');
    const cells = lines[1].split(',');

    expect(cells[header.indexOf('Max Stock')]).toBe('');
    expect(cells[header.indexOf('Exceeds Max Stock')]).toBe('');
    expect(cells.length).toBe(header.length);
  });

  it('keeps child rows truthful: dashes on cut rows, blanks on substitutes', () => {
    // Cut-list children show the stock-family dash like their sibling
    // columns; substitute children carry neither field and export blank.
    const items = [
      createBomItem({
        maximum_stock: 40,
        exceeds_max_stock: true,
        cut_list: [{ size: 500, count: 2, unit: 'mm' }],
        has_substitutes: true,
        substitute_parts: [createSubstitutePart({})]
      })
    ];
    const csv = generateCsvContent(flattenBomData(items), 1, true, true);
    const lines = csv.split('\n');
    const header = lines[0].split(',');
    const maxCol = header.indexOf('Max Stock');
    const flagCol = header.indexOf('Exceeds Max Stock');

    const cutChild = lines[2].split(',');
    expect(cutChild[maxCol]).toBe('-');
    expect(cutChild[flagCol]).toBe('-');
    expect(cutChild.length).toBe(header.length);

    const subChild = lines[3].split(',');
    expect(subChild[maxCol]).toBe('');
    expect(subChild[flagCol]).toBe('');
    expect(subChild.length).toBe(header.length);
  });
});
