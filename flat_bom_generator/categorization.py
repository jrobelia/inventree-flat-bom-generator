"""
Part Categorization

Functions for categorizing parts based on naming conventions and assembly flags.
"""


def categorize_part(
    part_name: str,
    is_assembly: bool,
    is_top_level: bool = False,
    default_supplier_id: int = None,
    internal_supplier_ids: list = None,
    fab_prefix: str = "fab",
    coml_prefix: str = "coml",
) -> str:
    """
    Categorize part based on assembly flag, name prefix, default_supplier, and position in BOM.

    Categories:
    - TLA: Top Level Assembly (the input part at level 0)
    - IMP: Internally Manufactured Part (has default_supplier matching internal supplier, can be assembly or non-assembly)
      * Only expands children if is_assembly=True (respects SHOW_PURCHASED_ASSEMBLIES setting)
    - Purchaseable Assembly: is_assembly=True + external default_supplier (not internal) (leaf part unless expand setting enabled)
    - Assembly: is_assembly=True + no default_supplier, name starts with "Assy"
    - Made From: is_assembly=True + no default_supplier, name starts with fab_prefix
    - Fab Part: name starts with fab_prefix (case-insensitive) (leaf part)
    - Coml Part: name starts with coml_prefix (case-insensitive) (leaf part)
    - Unknown: doesn't match any pattern

    Args:
        part_name: Part name (may have indentation from BOM display)
        is_assembly: Assembly flag
        is_top_level: True if this is the input part (level 0)
        default_supplier_id: ID of default_supplier (None if no default_supplier set)
        internal_supplier_ids: List of internal supplier IDs (empty list if none configured)
        fab_prefix: Prefix for fabricated parts (default: 'fab', case-insensitive)
        coml_prefix: Prefix for commercial parts (default: 'coml', case-insensitive)

    Returns:
        Category string
    """
    if internal_supplier_ids is None:
        internal_supplier_ids = []

    # Top level assembly gets special TLA category
    if is_top_level:
        return "TLA"

    # Clean name - remove indentation and get first word before comma or hyphen
    name_clean = part_name.strip().split(",")[0].split("-")[0].strip()
    name_lower = name_clean.lower()

    # Handle empty prefixes - allow blank if company doesn't use fab/coml naming
    fab_prefix_clean = fab_prefix.strip() if fab_prefix else ""
    coml_prefix_clean = coml_prefix.strip() if coml_prefix else ""
    fab_prefix_lower = fab_prefix_clean.lower()
    coml_prefix_lower = coml_prefix_clean.lower()

    # Check IMP FIRST (can be assembly or non-assembly)
    # IMP = Internally Manufactured Part (has default_supplier that is in internal supplier list)
    if default_supplier_id and default_supplier_id in internal_supplier_ids:
        return "IMP"

    # Then check if it's an assembly
    if is_assembly:
        # Assemblies with external default_supplier are treated as leaf parts (purchased as complete units)
        if default_supplier_id:
            return "Purchaseable Assembly"
        elif name_lower.startswith("assy"):
            return "Assembly"
        elif fab_prefix_clean and name_lower.startswith(fab_prefix_lower):
            return f"Made From {fab_prefix_clean}"
        else:
            return "Unknown"
    else:
        # Non-assembly parts - categorize by name prefix (case-insensitive)
        # Skip empty prefixes (graceful handling for companies not using fab/coml naming)
        if fab_prefix_clean and name_lower.startswith(fab_prefix_lower):
            return f"{fab_prefix_clean} Part"
        elif coml_prefix_clean and name_lower.startswith(coml_prefix_lower):
            return f"{coml_prefix_clean} Part"
        else:
            return "Unknown"
