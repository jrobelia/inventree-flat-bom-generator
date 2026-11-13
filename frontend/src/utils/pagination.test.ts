/**
 * Tests for the DataTable pagination helpers (ticket #34).
 *
 * The 'All' rows-per-page option is retired: the options list is numbers
 * only (10/25/50/100/500/1000, matching InvenTree's pagination values),
 * the state union collapses to `number`, and page slicing always slices.
 *
 * `parseRecordsPerPage` is the persisted-state migration seam: a stale
 * stored 'All' maps to 1000 (preserves "show the most" intent), any other
 * unparseable value falls back to the 50 default as before.
 *
 * Pure functions -- no React or DOM needed.
 */

import { describe, expect, it } from 'vitest';
import {
  paginateRecords,
  parseRecordsPerPage,
  RECORDS_PER_PAGE_OPTIONS
} from './pagination';

// ---------------------------------------------------------------------------
// RECORDS_PER_PAGE_OPTIONS: numeric only, InvenTree-standard values
// ---------------------------------------------------------------------------

describe('RECORDS_PER_PAGE_OPTIONS', () => {
  it('offers 10/25/50/100/500/1000 and no other values', () => {
    expect(RECORDS_PER_PAGE_OPTIONS).toEqual([10, 25, 50, 100, 500, 1000]);
  });

  it('contains no non-numeric entries (the retired "All")', () => {
    expect(RECORDS_PER_PAGE_OPTIONS).not.toContain('All');
    expect(
      RECORDS_PER_PAGE_OPTIONS.every((option) => typeof option === 'number')
    ).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// parseRecordsPerPage: localStorage read + 'All' migration
// ---------------------------------------------------------------------------

describe('parseRecordsPerPage -- stored-value migration', () => {
  it('maps a stale stored "All" to 1000 (ticket #34)', () => {
    // "Show the most" intent is preserved by the largest offered page size.
    expect(parseRecordsPerPage('All')).toBe(1000);
  });

  it('returns the parsed number for a valid stored value', () => {
    expect(parseRecordsPerPage('10')).toBe(10);
    expect(parseRecordsPerPage('25')).toBe(25);
    expect(parseRecordsPerPage('100')).toBe(100);
    expect(parseRecordsPerPage('500')).toBe(500);
    expect(parseRecordsPerPage('1000')).toBe(1000);
  });

  it('honours any positive stored number, not just offered options', () => {
    // Pre-existing lenient behavior is retained: the stored value is trusted.
    expect(parseRecordsPerPage('75')).toBe(75);
  });

  it('falls back to 50 when nothing was ever stored', () => {
    expect(parseRecordsPerPage(null)).toBe(50);
  });

  it('falls back to 50 on unparseable stored values', () => {
    expect(parseRecordsPerPage('abc')).toBe(50);
    expect(parseRecordsPerPage('')).toBe(50);
    // Only exact 'All' was ever persisted; anything else is garbage.
    expect(parseRecordsPerPage('all')).toBe(50);
  });

  it('falls back to 50 on non-positive stored numbers', () => {
    expect(parseRecordsPerPage('0')).toBe(50);
    expect(parseRecordsPerPage('-25')).toBe(50);
  });
});

// ---------------------------------------------------------------------------
// paginateRecords: page slicing always slices
// ---------------------------------------------------------------------------

describe('paginateRecords', () => {
  const rows = Array.from({ length: 250 }, (_, i) => i + 1);

  it('returns the first page', () => {
    const page = paginateRecords(rows, 1, 100);
    expect(page).toHaveLength(100);
    expect(page[0]).toBe(1);
    expect(page[99]).toBe(100);
  });

  it('returns a middle page at the correct offset', () => {
    const page = paginateRecords(rows, 2, 100);
    expect(page).toHaveLength(100);
    expect(page[0]).toBe(101);
    expect(page[99]).toBe(200);
  });

  it('returns a short final page without over-slicing', () => {
    const page = paginateRecords(rows, 3, 100);
    expect(page).toHaveLength(50);
    expect(page[0]).toBe(201);
    expect(page[49]).toBe(250);
  });

  it('respects the page boundary for small page sizes', () => {
    const page = paginateRecords(rows, 2, 25);
    expect(page[0]).toBe(26);
    expect(page[24]).toBe(50);
  });

  it('returns every row when the data fits on one page', () => {
    const small = [1, 2, 3];
    expect(paginateRecords(small, 1, 10)).toEqual([1, 2, 3]);
  });

  it('returns an empty page beyond the last page', () => {
    expect(paginateRecords(rows, 4, 100)).toEqual([]);
  });
});
