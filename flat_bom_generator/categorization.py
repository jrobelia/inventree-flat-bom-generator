"""
Part Categorization

Functions for assigning display labels to flat-BOM line items.

categorize_part answers exactly one question: "what display label should this
line item show?" It does not decide whether a part appears in the flat BOM or
whether its BOM expands — those decisions live in bom_traversal and are driven
by Part.assembly, the primary SupplierPart, and the supplier company's
is_internal flag.
"""

from __future__ import annotations

import re


def categorize_part(
    part_name: str,
    is_assembly: bool,
    is_top_level: bool = False,
    default_supplier_id: int | None = None,
    supplier_is_internal: bool = False,
    part_category_id: int | None = None,
    category_mappings: dict | None = None,
) -> str:
    """
    Assign a display label to a flat-BOM line item.

    Label priority order:
    1. Top Level Assembly (TLA) - the input part at level 0
    2. Assembly labels (Part.assembly flag):
       - Internal Fab: assembly whose primary supplier is flagged is_internal
       - Purchased Assy: assembly with a primary supplier that is not internal
       - Assy: assembly with no primary supplier (build-order candidate)
    3. InvenTree category labels for non-assembly parts:
       - Coml: part category in the configured Commercial category set
       - Fab: part category in the configured Fabrication category set
    4. Fallback: "Other"

    Args:
        part_name: Part name (may have indentation from BOM display)
        is_assembly: Assembly flag from part model (Part.assembly)
        is_top_level: True if this is the input part (level 0)
        default_supplier_id: ID of the primary SupplierPart (None if not set)
        supplier_is_internal: True when the primary supplier's company is
            flagged is_internal in InvenTree
        part_category_id: Part's category ID from InvenTree
        category_mappings: Dict mapping label types to lists of category IDs
            (includes descendants). Example:
            {'fabrication': [5, 12, 13], 'commercial': [8, 9]}

    Returns:
        Label string: "TLA", "Purchased Assy", "Internal Fab", "Assy",
                      "Coml", "Fab", or "Other"
    """
    if category_mappings is None:
        category_mappings = {}

    if is_top_level:
        return "TLA"

    if is_assembly:
        if default_supplier_id is None:
            return "Assy"
        if supplier_is_internal:
            return "Internal Fab"
        return "Purchased Assy"

    if part_category_id:
        coml_category_ids = category_mappings.get("commercial", [])
        if coml_category_ids and part_category_id in coml_category_ids:
            return "Coml"

        fab_category_ids = category_mappings.get("fabrication", [])
        if fab_category_ids and part_category_id in fab_category_ids:
            return "Fab"

    return "Other"


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
