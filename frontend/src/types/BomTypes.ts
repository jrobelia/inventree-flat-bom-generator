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
  is_cut_list_child?: boolean;
  cut_length?: number | null;
  cut_unit?: string;

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
