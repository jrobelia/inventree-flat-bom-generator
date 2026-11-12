/**
 * TypeScript interfaces for Flat BOM Generator
 * Extracted from Panel.tsx for better organization and reusability
 */

/**
 * Individual BOM item with stock and cut list information
 */
export interface BomItem {
  // Identity
  part_id: number;
  ipn: string;
  part_name: string;
  full_name: string;
  description: string;

  // Display label (labels do not drive expansion - flags below do)
  part_type:
    | 'TLA'
    | 'Coml'
    | 'Fab'
    | 'Purchased Assy'
    | 'Internal Fab'
    | 'Assy'
    | 'Other';
  category?: string;
  is_assembly: boolean;
  purchaseable: boolean;
  default_supplier_id?: number | null;
  internal_supplier?: boolean;
  optional?: boolean;
  /** Share of total_qty from optional BOM-line occurrences (issue #30) */
  optional_qty?: number;
  consumable?: boolean;

  // Quantities (aggregated/deduplicated)
  total_qty: number;
  unit: string;

  // Cut list support (length-unit BOM lines, any expanded parent - R-016)
  // Entries aggregate by (part, piece size): size = BOM line quantity,
  // count = ceil(piece_count x ancestor multiplier)
  cut_list?: Array<{
    size: number;
    count: number;
    unit: string;
  }> | null;
  cut_length?: number | null;
  cut_unit?: string;

  // Upstream BOM line semantics (InvenTree 1.6): inherited_from = the
  // distinct source template IPNs the merged lines were inherited through,
  // comma-joined and sorted, with marker 'local' appended when direct
  // lines are in the mix; null when nothing is inherited (#45 ruling).
  // piece_count is a per-line concept - flat rows are material
  // lumps and always carry 1; piece structure lives in cut_list (R-025
  // amendment, issue #44).
  piece_count?: number;
  inherited_from?: string | null;

  // Generic child row system (v0.11.24+)
  is_child_row?: boolean; // True if cutlist/substitute/variant child
  child_row_type?: 'cutlist' | 'substitute' | 'variant';
  parent_row_part_id?: number; // Parent row's part_id

  // Stock and order information
  in_stock: number;
  on_order: number;
  building?: number;
  allocated: number;
  available: number;
  // Upstream shortage signals (InvenTree Part properties, ticket #15)
  net_stock: number; // total_stock - allocated + on_order; can go negative
  quantity_to_order: number; // upstream suggested order quantity (floored at 0)

  // Stock ceiling (upstream Part.maximum_stock, 1.4.0+, ticket #26):
  // null = no ceiling (upstream stores 0 for 'no maximum')
  maximum_stock?: number | null;
  exceeds_max_stock?: boolean | null; // net_stock + quantity_to_order > maximum_stock

  // Procurement
  default_supplier_name?: string;

  // Display
  image?: string;
  thumbnail?: string;
  link: string;

  // Substitute parts support (added in v0.11.39)
  has_substitutes?: boolean;
  substitute_parts?: SubstitutePart[] | null;

  // Set on substitute child rows when parent and sub units differ
  unit_mismatch?: boolean;
}

/**
 * Substitute part data with individual stock information
 * Added in v0.11.39 for substitute parts feature
 *
 * Each substitute is an alternative part that can fulfill the same BOM requirement.
 * Includes its own stock, allocation, and availability data to help users
 * identify which alternative has the best availability.
 */
export interface SubstitutePart {
  // Core identifiers
  substitute_id: number; // BomItemSubstitute primary key
  part_id: number; // Substitute Part primary key
  ipn: string; // Internal Part Number
  part_name: string; // Part name
  full_name: string; // Full display name with variant info
  description: string; // Part description
  unit: string | null; // Unit of measurement
  parent_total_qty?: number; // Parent BOM item quantity (for unit matching)
  parent_unit?: string | null; // Parent BOM item unit (for unit matching)

  // Stock data
  in_stock: number; // Total inventory
  on_order: number; // On incomplete purchase orders
  allocated: number; // Reserved for builds/sales
  available: number; // in_stock - allocated
  net_stock: number; // in_stock - allocated + on_order (upstream; can go negative)
  quantity_to_order: number; // upstream suggested order quantity (floored at 0)

  // Display metadata
  image: string | null; // Full-size image URL
  thumbnail: string | null; // Thumbnail URL
  link: string; // Part detail page URL
}

/**
 * Warning from BOM analysis
 */
export interface Warning {
  type: string;
  part_id: number;
  part_name: string;
  message: string;
}

/**
 * API response from flat BOM endpoint
 */
export interface FlatBomResponse {
  part_id: number;
  part_name: string;
  ipn: string;
  total_unique_parts: number;
  total_ifps_processed: number;
  max_depth_reached: number;
  bom_items: BomItem[];
  metadata?: {
    warnings?: Warning[];
  };
}
