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

  // Categorization
  part_type:
    | 'TLA'
    | 'Coml'
    | 'Fab'
    | 'CtL'
    | 'Purchased Assy'
    | 'Internal Fab'
    | 'Assy'
    | 'Other';
  is_assembly: boolean;
  purchaseable: boolean;
  has_default_supplier: boolean;
  optional?: boolean;
  consumable?: boolean;

  // Quantities (aggregated/deduplicated)
  total_qty: number;
  unit: string;

  // Cut list support
  cut_list?: Array<{ quantity: number; length: number }> | null;
  internal_fab_cut_list?: Array<{
    count: number;
    piece_qty: number;
    unit: string;
  }> | null;
  cut_length?: number | null;
  cut_unit?: string;

  // Generic child row system (v0.11.24+)
  is_child_row?: boolean; // True if cutlist/substitute/variant child
  child_row_type?: 'cutlist_ctl' | 'cutlist_ifab' | 'substitute' | 'variant';
  parent_row_part_id?: number; // Parent row's part_id

  // Stock and order information
  in_stock: number;
  on_order: number;
  building?: number;
  allocated: number;
  available: number;

  // Procurement
  default_supplier_name?: string;

  // Display
  image?: string;
  thumbnail?: string;
  link: string;

  // Substitute parts support (added in v0.11.39)
  has_substitutes?: boolean;
  substitute_parts?: SubstitutePart[] | null;
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
    cutlist_units_for_ifab?: string; // Added in v0.11.0 - units for Internal Fab cutlist display
  };
}
