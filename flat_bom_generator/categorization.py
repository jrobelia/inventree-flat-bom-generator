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
       - Assembly: Any other assembly (detected by Part.assembly flag)
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

    # Any other assembly (detected by Part.assembly flag, no specific category check)
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


def _extract_length_with_unit(notes: str) -> dict:
    """
    Extract numeric length value AND adjacent unit from BOM notes field.

    Looks for number followed immediately by common length units.
    Used for detecting unit mismatches between notes and part native unit.

    Handles formats:
    - "100mm" → {"value": 100.0, "unit": "mm"}
    - "50.5 inches" → {"value": 50.5, "unit": "inches"}
    - "Cut 12mm from stock" → {"value": 12.0, "unit": "mm"}
    - "100" → {"value": 100.0, "unit": None}
    - "No numbers" → {"value": None, "unit": None}

    Args:
        notes: BOM line item notes string

    Returns:
        Dict with "value" (float or None) and "unit" (str or None)
    """
    if not notes:
        return {"value": None, "unit": None}

    # Pattern: number optionally followed by space and unit
    # Captures: (number) (optional space) (unit)
    # Common length units: mm, millimeters, cm, centimeters, m, meters, in, inches, ft, feet
    # NOTE: Order matters! Put longer matches BEFORE shorter ones (inches? before in)
    pattern = r"(\d+\.?\d*|\.\d+)\s*(millimeters?|centimeters?|meters?|inches?|feet|mm|cm|in|ft|m)?"
    match = re.search(pattern, notes.strip(), re.IGNORECASE)

    if match:
        try:
            value = float(match.group(1))
            unit = match.group(2).lower() if match.group(2) else None
            return {"value": value, "unit": unit}
        except (ValueError, AttributeError):
            return {"value": None, "unit": None}

    return {"value": None, "unit": None}


def _check_unit_mismatch(notes: str, part_unit: str) -> str:
    """
    Check if BOM notes contain a unit that differs from part's native unit.

    Only checks the unit immediately adjacent to the first number in notes,
    ignoring other unit references elsewhere in the text.

    Args:
        notes: BOM line item notes string
        part_unit: Part's native unit from InvenTree

    Returns:
        Warning message if mismatch detected, None otherwise
    """
    if not notes or not part_unit:
        return None

    extracted = _extract_length_with_unit(notes)

    if extracted["unit"] and extracted["unit"] != part_unit.lower():
        return f"BOM notes specify '{extracted['unit']}' but part uses '{part_unit}'"

    return None
