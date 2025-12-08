"""
Part Categorization

Functions for categorizing parts based on naming conventions and assembly flags.
"""


def categorize_part(part_name: str, is_assembly: bool, is_top_level: bool = False, has_default_supplier: bool = False) -> str:
    """
    Categorize part based on assembly flag, name prefix, and position in BOM.
    
    Categories:
    - TLA: Top Level Assembly (the input part at level 0)
    - Purchaseable Assembly: assembly=True, has default supplier (leaf part)
    - Assembly: assembly=True, name starts with "Assy"
    - Made From: assembly=True, name starts with "Fab"
    - Fab Part: assembly=False, name starts with "Fab" ← INCLUDE in flat BOM
    - Coml Part: assembly=False, name starts with "Coml" ← INCLUDE in flat BOM
    - Unknown: doesn't match any pattern
    
    Args:
        part_name: Part name (may have indentation from BOM display)
        is_assembly: Assembly flag
        is_top_level: True if this is the input part (level 0)
        has_default_supplier: True if part has a default supplier (for purchaseable assemblies)
        
    Returns:
        Category string
    """
    # Top level assembly gets special TLA category
    if is_top_level:
        return 'TLA'
    
    # Clean name - remove indentation and get first word before comma or hyphen
    name_clean = part_name.strip().split(',')[0].split('-')[0].strip()
    name_lower = name_clean.lower()
    
    if is_assembly:
        # Assemblies with default suppliers are treated as leaf parts (purchased as complete units)
        if has_default_supplier:
            return 'Purchaseable Assembly'
        elif name_lower.startswith('assy'):
            return 'Assembly'
        elif name_lower.startswith('fab'):
            return 'Made From'
        else:
            return 'Unknown'
    else:
        if name_lower.startswith('fab'):
            return 'Fab Part'
        elif name_lower.startswith('coml'):
            return 'Coml Part'
        else:
            return 'Unknown'
