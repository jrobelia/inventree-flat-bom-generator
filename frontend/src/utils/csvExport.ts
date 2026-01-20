/**
 * CSV Export Utilities
 * Pure functions for generating and downloading CSV files
 */

import type { BomItem } from '../types/BomTypes';

/**
 * Escape CSV field value by:
 * 1. Converting to string
 * 2. Replacing any double quotes with two double quotes (RFC 4180)
 * 3. Wrapping in double quotes if contains comma, quote, or newline
 *
 * @param value - Value to escape (can be any type)
 * @returns Escaped string safe for CSV
 *
 * @example
 * escapeCsvField('Simple') // 'Simple'
 * escapeCsvField('Part, Steel') // '"Part, Steel"'
 * escapeCsvField('Part "Special"') // '"Part ""Special"""'
 */
export function escapeCsvField(value: any): string {
  const str = String(value ?? '');
  // Escape double quotes by doubling them
  const escaped = str.replace(/"/g, '""');
  // Wrap in quotes if contains comma, quote, or newline
  if (
    escaped.includes(',') ||
    escaped.includes('"') ||
    escaped.includes('\n')
  ) {
    return `"${escaped}"`;
  }
  return escaped;
}

/**
 * Generate CSV content from BOM data
 *
 * @param data - Array of BOM items to export
 * @param buildQuantity - Build quantity multiplier
 * @param includeAllocations - Whether to subtract allocations from stock
 * @param includeOnOrder - Whether to include on-order quantity in balance
 * @returns CSV string with headers and data rows
 *
 * @example
 * const csv = generateCsvContent(bomItems, 5, true, true);
 * // Returns: "IPN,Part Name,...\nFAB-001,Bracket,..."
 */
export function generateCsvContent(
  data: BomItem[],
  buildQuantity: number,
  includeAllocations: boolean,
  includeOnOrder: boolean
): string {
  const headers = [
    'IPN',
    'Part Name',
    'Description',
    'Part Type',
    'Total Qty',
    'Unit',
    'Cut Length',
    'Cut Unit',
    'In Stock',
    'Allocated',
    'On Order',
    'Build Margin'
  ];

  const rows = data.map((item) => {
    // Handle cut list children differently
    if (item.is_cut_list_child) {
      return [
        item.ipn,
        item.part_name,
        item.description,
        item.part_type,
        item.total_qty, // Do not multiply by buildQuantity for child rows
        '',
        item.cut_length || '-',
        item.cut_unit || item.unit || '',
        '-',
        '-',
        '-',
        '-'
      ];
    }

    // Normal row calculation
    const totalRequired = item.total_qty * buildQuantity;
    let stockValue = item.in_stock;
    if (includeAllocations) {
      stockValue -= item.allocated;
    }
    if (includeOnOrder) {
      stockValue += item.on_order;
    }
    const balance = stockValue - totalRequired;

    return [
      item.ipn,
      item.part_name,
      item.description,
      item.part_type,
      totalRequired,
      item.unit,
      '-',
      '',
      item.in_stock,
      item.allocated,
      item.on_order,
      balance
    ];
  });

  return [
    headers.map(escapeCsvField).join(','),
    ...rows.map((row) => row.map(escapeCsvField).join(','))
  ].join('\n');
}

/**
 * Download CSV file to user's computer
 *
 * @param csvContent - CSV string to download
 * @param filename - Name for the downloaded file
 *
 * @example
 * const csv = generateCsvContent(items, 1, true, true);
 * downloadCsv(csv, 'flat_bom_ASM-001.csv');
 */
export function downloadCsv(csvContent: string, filename: string): void {
  const blob = new Blob([csvContent], { type: 'text/csv' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  window.URL.revokeObjectURL(url);
}

/**
 * Generate timestamped filename for BOM export
 * Format: flat_bom_{ipn}_qty{qty}_{date}_{time}.csv
 *
 * @param ipn - Internal Part Number
 * @param partId - Part ID (fallback if IPN not available)
 * @param buildQuantity - Build quantity
 * @returns Formatted filename string
 *
 * @example
 * generateFilename('ASM-001', 123, 5)
 * // Returns: 'flat_bom_ASM-001_qty5_2026-01-15_14-30-45.csv'
 */
export function generateFilename(
  ipn: string | undefined,
  partId: number,
  buildQuantity: number
): string {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').split('T');
  const dateStr = timestamp[0]; // YYYY-MM-DD
  const timeStr = timestamp[1].split('Z')[0]; // HH-MM-SS
  return `flat_bom_${ipn || partId}_qty${buildQuantity}_${dateStr}_${timeStr}.csv`;
}
