"""
Part Categorization

Functions for categorizing parts based on InvenTree categories and supplier relationships.
"""

import re


def categorize_part(
    part_name: str,
    is_assembly: bool,
    is_top_level: bool = False,
    default_supplier_id: int = None,
    internal_supplier_ids: list = None,
    part_category_id: int = None,
    category_mappings: dict = None,
    bom_item_notes: str = None,
    # Unused legacy parameters (kept for API compatibility during transition)
    fab_prefix: str = None,
    coml_prefix: str = None,
) -> str:
    """
    Categorize part using InvenTree categories and supplier relationships.

    Category Priority Order:
    1. Top Level Assembly (TLA) - The input part at level 0
    2. External Assembly - Assembly with default supplier that is NOT internal (leaf part)
    3. InvenTree Category-based Classification (for non-assemblies):
       - Cut-to-Length: Raw material with length in BOM notes
       - Commercial: Purchased commercial/COTS parts
       - Fabrication: Fabricated non-assembly parts
    4. Internal Assemblies (traverse deeper, not leaf parts):
       - Internal Fab: Assembly in Fabrication category with internal default supplier
       - Assembly: Assembly in Assembly category or no category
    5. Fallback: "Other"

    Args:
        part_name: Part name (may have indentation from BOM display)
        is_assembly: Assembly flag from part model (Part.assembly)
        is_top_level: True if this is the input part (level 0)
        default_supplier_id: ID of default_supplier (None if not set)
        internal_supplier_ids: List of internal supplier IDs from plugin settings
        part_category_id: Part's category ID from InvenTree
        category_mappings: Dict mapping category types to lists of category IDs (includes descendants)
            Example: {
                'fabrication': [5, 12, 13],  # Parent category + children
                'commercial': [8, 9],
                'assembly': [15, 16, 17],
                'cut_to_length': [20]
            }
        bom_item_notes: Notes field from BOM line item (for CtL length extraction)
        fab_prefix: Unused (kept for API compatibility)
        coml_prefix: Unused (kept for API compatibility)

    Returns:
        Category string: "TLA", "Purchased Assy", "Coml", "Fab",
                        "CtL", "Internal Fab", "Assy", "Other"
    """
    if internal_supplier_ids is None:
        internal_supplier_ids = []

    if category_mappings is None:
        category_mappings = {}

    # Top level assembly gets special TLA category
    if is_top_level:
        return "TLA"

    # Helper booleans
    has_default_supplier = default_supplier_id is not None
    has_internal_supplier = (
        has_default_supplier and default_supplier_id in internal_supplier_ids
    )

    # PRIORITY 1: Internal assemblies (NOT leaf parts - traverse deeper)
    # Assembly in Fabrication category with internal default supplier
    # These are assemblies we fabricate internally - need to expand to find child parts
    if is_assembly:
        fab_category_ids = category_mappings.get("fabrication", [])
        if (
            fab_category_ids
            and part_category_id
            and part_category_id in fab_category_ids
            and has_internal_supplier
        ):
            return "Internal Fab"
        # External Assembly (leaf part - purchased complete)
        # Assembly with default supplier that is NOT in internal suppliers list
        if has_default_supplier and not has_internal_supplier:
            return "Purchased Assy"

    # PRIORITY 2: Non-assembly parts (check InvenTree categories)
    if not is_assembly and part_category_id and category_mappings:
        # Check Cut-to-Length first (requires BOM notes validation)
        ctl_category_ids = category_mappings.get("cut_to_length", [])
        if ctl_category_ids and part_category_id in ctl_category_ids:
            # Validate that BOM notes contain a length value
            if (
                bom_item_notes
                and _extract_length_from_notes(bom_item_notes) is not None
            ):
                return "CtL"
            # If no valid length in notes, treat as fabrication
            return "Fab"

        # Check Commercial category (including descendants)
        coml_category_ids = category_mappings.get("commercial", [])
        if coml_category_ids and part_category_id in coml_category_ids:
            return "Coml"

        # Check Fabrication category (including descendants)
        fab_category_ids = category_mappings.get("fabrication", [])
        if fab_category_ids and part_category_id in fab_category_ids:
            return "Fab"

    # Any other assembly (in Assembly category, no category, or no supplier info)
    if is_assembly:
        return "Assy"

    # PRIORITY 4: No match
    return "Other"


def _extract_length_from_notes(notes: str) -> float:
    """
    Extract numeric length value from BOM line item notes field.

    Handles various formats:
    - "100" → 100.0
    - "100mm" → 100.0
    - "Length: 50.5" → 50.5
    - "Cut to 12.75 inches" → 12.75
    - "Non-numeric text" → None

    Args:
        notes: BOM line item notes string

    Returns:
        Float length value if found, None otherwise
    """
    if not notes:
        return None

    # Try to find first number (int or float) in the notes
    # Pattern matches: 123, 123.45, .45
    pattern = r"\d+\.?\d*|\.\d+"
    match = re.search(pattern, notes.strip())

    if match:
        try:
            return float(match.group())
        except ValueError:
            return None

    return None
