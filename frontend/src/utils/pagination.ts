/**
 * DataTable pagination helpers (ticket #34).
 *
 * The rows-per-page options match InvenTree's standard pagination values
 * (10/25/50/100/500/1000); the retired 'All' option is gone, so page
 * slicing always slices and the persisted state is a plain number.
 */

/** localStorage key shared by the initializer and the change handler. */
export const RECORDS_PER_PAGE_STORAGE_KEY = 'flat-bom-records-per-page';

/** Fallback when localStorage is empty or holds an unparseable value. */
export const DEFAULT_RECORDS_PER_PAGE = 50;

/**
 * Rows-per-page options offered by the DataTable. Numbers only - a
 * `number[]` is assignable to `recordsPerPageOptions` without a cast.
 */
export const RECORDS_PER_PAGE_OPTIONS = [10, 25, 50, 100, 500, 1000];

/**
 * Resolve the persisted rows-per-page value to a number.
 *
 * Migration: a stale stored 'All' (the retired option) maps to 1000 -
 * the largest offered size, preserving "show the most" intent. Any other
 * unparseable or non-positive value falls back to the default, matching
 * the pre-#34 fallback.
 */
export function parseRecordsPerPage(stored: string | null): number {
  if (stored === 'All') {
    return 1000;
  }
  const num = Number(stored);
  return num > 0 ? num : DEFAULT_RECORDS_PER_PAGE;
}

/**
 * Slice one page out of the record set. With 'All' retired, every page
 * size is numeric, so slicing is unconditional.
 */
export function paginateRecords<T>(
  records: T[],
  page: number,
  recordsPerPage: number
): T[] {
  return records.slice((page - 1) * recordsPerPage, page * recordsPerPage);
}
