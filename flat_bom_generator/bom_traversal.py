"""
BOM Traversal and Flattening Operations

Functions for recursively traversing Bill of Materials hierarchies
and flattening the tree structure for display and export.

Uses InvenTree internal models (safe when accessed through plugin context).
"""

from typing import Dict, List, Optional, Set
from collections import defaultdict
import logging

from .categorization import categorize_part, _extract_length_from_notes

logger = logging.getLogger("inventree")


def get_bom_items(part) -> List[Dict]:
    """
    Fetch BOM items for a given part with related data.

    Args:
        part: Part model instance

    Returns:
        List of BOM item dictionaries with: sub_part, quantity, reference, etc.
    """
    from part.models import BomItem

    try:
        # Prefetch sub_part and its default_supplier for categorization
        bom_items = BomItem.objects.filter(part=part).select_related(
            "sub_part", "sub_part__default_supplier"
        )

        items = []
        for bom_item in bom_items:
            if not bom_item.sub_part:
                continue

            items.append({
                "sub_part": bom_item.sub_part,
                "sub_part_id": bom_item.sub_part.pk,
                "quantity": float(bom_item.quantity),
                "reference": bom_item.reference or "",
                "note": bom_item.note or "",
                "notes": bom_item.note or "",  # Alias for categorization
                "optional": bom_item.optional,
                "inherited": bom_item.inherited,
                "has_default_supplier": bool(bom_item.sub_part.default_supplier),
            })

        return items

    except Exception as e:
        logger.error(f"Could not fetch BOM items for part {part.pk}: {e}")
        return []


def traverse_bom(
    part,
    level: int = 0,
    parent_qty: float = 1.0,
    parent_ipn: Optional[str] = None,
    visited: Optional[Set[int]] = None,
    max_depth: Optional[int] = None,
    internal_supplier_ids: Optional[List[int]] = None,
    category_mappings: Optional[Dict[str, int]] = None,
    bom_item_notes: Optional[str] = None,
    imp_counter: Optional[Dict[str, int]] = None,
) -> Dict:
    """
    Recursively traverse BOM structure and build tree.

    CRITICAL: Uses visited.copy() pattern to allow same part in different
    branches while preventing circular references.

    Args:
        part: Part model instance
        level: Current depth in BOM tree (0 = top)
        parent_qty: Cumulative quantity from parent levels
        parent_ipn: IPN of parent part
        visited: Set of visited part IDs (to detect circular references)
        max_depth: Maximum depth to traverse (None = unlimited)
        internal_supplier_ids: List of internal supplier IDs for categorization
        category_mappings: Dict mapping category types to lists of IDs (includes descendants)
        bom_item_notes: Notes from BOM line item (for Cut-to-Length length extraction)
        imp_counter: Dictionary to count Internal Fab parts {'count': 0} (mutable for recursion)

    Returns:
        Dictionary representing BOM node with all metadata and children
    """
    if internal_supplier_ids is None:
        internal_supplier_ids = []
    if category_mappings is None:
        category_mappings = {}
    # Initialize visited set on first call
    if visited is None:
        visited = set()
    # Initialize IMP counter on first call
    if imp_counter is None:
        imp_counter = {"count": 0}

    part_id = part.pk

    # CRITICAL: Check for circular reference BEFORE adding to visited
    if part_id in visited:
        logger.warning(f"Circular reference detected for part ID {part_id}")
        return {
            "error": "circular_reference",
            "part_id": part_id,
            "ipn": part.IPN or "",
            "part_name": part.name,
            "level": level,
        }

    # Add to visited for this branch
    visited.add(part_id)

    # Extract part metadata
    ipn = part.IPN or ""
    part_name = part.name
    units = part.units or ""
    is_assembly = part.assembly
    purchaseable = part.purchaseable
    description = part.description or ""
    default_supplier_id = part.default_supplier.pk if part.default_supplier else None

    # Categorize part
    is_top_level = level == 0
    part_category_id = part.category.pk if part.category else None
    part_type = categorize_part(
        part_name,
        is_assembly,
        is_top_level,
        default_supplier_id,
        internal_supplier_ids,
        part_category_id,
        category_mappings,
        bom_item_notes,
    )

    # Count Internal Fab parts processed during traversal
    # These are assemblies we fabricate internally (need to expand to find child parts)
    if part_type == "Internal Fab":
        imp_counter["count"] += 1

    # Initialize node
    node = {
        "part_id": part_id,
        "ipn": ipn,
        "part_name": part_name,
        "description": description,
        "cumulative_qty": parent_qty,
        "level": level,
        "parent_ipn": parent_ipn,
        "unit": units,
        "is_assembly": is_assembly,
        "purchaseable": purchaseable,
        "default_supplier_id": default_supplier_id,
        "part_type": part_type,
        "children": [],
    }

    # Check if we should expand this node's BOM
    skip_bom_expansion = False

    # Don't expand if max depth reached
    if max_depth is not None and level >= max_depth:
        logger.debug(f"Max depth ({max_depth}) reached at part {ipn}")
        skip_bom_expansion = True

    # Traverse children if this is an assembly
    if is_assembly and not skip_bom_expansion:
        bom_items = get_bom_items(part)

        if bom_items:
            for bom_item in bom_items:
                child_part = bom_item["sub_part"]
                child_qty = bom_item["quantity"]
                child_ref = bom_item["reference"]
                child_note = bom_item["note"]
                child_notes = bom_item.get("notes", "")  # For CtL categorization

                # Calculate cumulative quantity for child
                child_cumulative_qty = parent_qty * child_qty

                # CRITICAL: Pass visited.copy() to allow same part in different branches
                child_node = traverse_bom(
                    child_part,
                    level=level + 1,
                    parent_qty=child_cumulative_qty,
                    parent_ipn=ipn,
                    visited=visited.copy(),  # ← CRITICAL for correct deduplication
                    max_depth=max_depth,
                    internal_supplier_ids=internal_supplier_ids,
                    category_mappings=category_mappings,
                    bom_item_notes=child_notes,  # Pass BOM notes for CtL
                    imp_counter=imp_counter,
                )

                # Set child-specific values
                child_node["quantity"] = child_qty
                child_node["reference"] = child_ref
                child_node["note"] = child_note

                # Add to children list
                node["children"].append(child_node)

    return node


def get_leaf_parts_only(
    tree: Dict,
    leaves: Optional[List[Dict]] = None,
    expand_purchased_assemblies: bool = False,
) -> List[Dict]:
    """
    Flatten BOM tree to leaf parts only.

    Leaf parts are parts that should be purchased/ordered:
    - Commercial: Purchased non-assembly parts
    - Fabrication: Non-assembly fabricated parts
    - Cut-to-Length: Raw material with length in notes
    - External Assembly: Assemblies purchased complete (if expand=True)

    NOT leaf parts (will be expanded to find their children):
    - TLA: Top level assembly
    - Assembly: Internal assemblies
    - Internal Fab: Fabricated assemblies (expand to find child parts to buy)
    - Other: Uncategorized

    Args:
        tree: BOM tree from traverse_bom()
        leaves: Accumulator list (for recursion)
        expand_purchased_assemblies: If False, treat External Assemblies as leaf parts
                                      If True, expand them to show subcomponents

    Returns:
        Flat list of leaf parts with cumulative quantities
    """
    if leaves is None:
        leaves = []

    # Skip error nodes
    if "error" in tree:
        return leaves

    # Check if this is a leaf part
    part_type = tree.get("part_type", "Unknown")
    is_purchaseable_assembly = part_type == "Purchased Assy"

    # Determine if this part should be included as a leaf
    # Include non-assembly leaf parts based on category
    is_non_assembly_leaf = part_type in [
        "Coml",  # Purchased parts
        "Fab",  # Fabricated non-assembly parts
        "CtL",  # Raw material with specified length
    ]

    if is_non_assembly_leaf:
        # Always include non-assembly leaf parts
        cumulative_qty = tree["cumulative_qty"]
        cut_length = None

        # For Cut-to-Length parts, extract length from notes but keep as separate field
        # Don't multiply into quantity - we want piece count and length separate for cut lists
        if part_type == "CtL":
            note_text = tree.get("note", "")
            cut_length = _extract_length_from_notes(note_text)

        leaves.append({
            "part_id": tree["part_id"],
            "ipn": tree["ipn"],
            "part_name": tree["part_name"],
            "description": tree.get("description", ""),
            "cumulative_qty": cumulative_qty,
            "cut_length": cut_length,  # Length for CtL parts, None for others
            "unit": tree.get("unit", ""),
            "is_assembly": tree["is_assembly"],
            "purchaseable": tree["purchaseable"],
            "default_supplier_id": tree.get("default_supplier_id"),
            "part_type": part_type,
            "reference": tree.get("reference", ""),
            "note": tree.get("note", ""),
            "level": tree["level"],
        })
    elif is_purchaseable_assembly and not expand_purchased_assemblies:
        # Include purchased assembly as a leaf and DON'T recurse into children
        leaves.append({
            "part_id": tree["part_id"],
            "ipn": tree["ipn"],
            "part_name": tree["part_name"],
            "description": tree.get("description", ""),
            "cumulative_qty": tree["cumulative_qty"],
            "unit": tree.get("unit", ""),
            "is_assembly": tree["is_assembly"],
            "purchaseable": tree["purchaseable"],
            "default_supplier_id": tree.get("default_supplier_id"),
            "part_type": part_type,
            "reference": tree.get("reference", ""),
            "note": tree.get("note", ""),
            "level": tree["level"],
        })
        # Stop here - don't recurse into children
        return leaves

    # Recurse into children for:
    # - Non-leaf parts (regular assemblies)
    # - Purchaseable assemblies when expand_purchased_assemblies is True
    for child in tree.get("children", []):
        get_leaf_parts_only(child, leaves, expand_purchased_assemblies)

    return leaves


def deduplicate_and_sum(leaf_parts: List[Dict]) -> List[Dict]:
    """
    Sum quantities for parts appearing multiple times.

    For Cut-to-Length parts, creates a single row per part with total quantity,
    and stores cut list details in a nested array for row expansion.

    For other parts, groups by part_id only.

    Args:
        leaf_parts: List of leaf parts from get_leaf_parts_only()

    Returns:
        Deduplicated list with aggregated quantities and cut_list metadata
    """
    # Use defaultdict to accumulate quantities
    totals = defaultdict(float)
    part_info = {}
    cut_lists = defaultdict(list)  # Store cut list details for CtL parts

    for leaf in leaf_parts:
        part_id = leaf["part_id"]
        part_type = leaf["part_type"]
        cut_length = leaf.get("cut_length")

        # Always use part_id as key (single row per part)
        key = part_id

        # For CtL parts, accumulate total length (qty * length)
        # For other parts, accumulate piece count
        if part_type == "CtL" and cut_length is not None:
            totals[key] += leaf["cumulative_qty"] * cut_length
        else:
            totals[key] += leaf["cumulative_qty"]

        # Store part info (first occurrence wins for metadata)
        if key not in part_info:
            part_info[key] = {
                "part_id": part_id,
                "ipn": leaf["ipn"],
                "part_name": leaf["part_name"],
                "description": leaf["description"],
                "unit": leaf["unit"],
                "is_assembly": leaf["is_assembly"],
                "purchaseable": leaf["purchaseable"],
                "default_supplier_id": leaf.get("default_supplier_id"),
                "part_type": part_type,
            }

        # For CtL parts, accumulate cut list details
        if part_type == "CtL" and cut_length is not None:
            cut_lists[key].append({
                "quantity": leaf["cumulative_qty"],
                "length": cut_length,
            })

    # Convert to sorted list
    result = [
        {
            "part_id": part_info[key]["part_id"],
            "total_qty": qty,
            "ipn": part_info[key]["ipn"],
            "part_name": part_info[key]["part_name"],
            "description": part_info[key]["description"],
            "unit": part_info[key]["unit"],
            "is_assembly": part_info[key]["is_assembly"],
            "purchaseable": part_info[key]["purchaseable"],
            "default_supplier_id": part_info[key]["default_supplier_id"],
            "part_type": part_info[key]["part_type"],
            "cut_list": cut_lists.get(key, None),  # Cut list details for expansion
        }
        for key, qty in sorted(
            totals.items(),
            key=lambda x: part_info[x[0]]["ipn"],
        )
    ]

    return result


def get_flat_bom(
    part_id: int,
    max_depth: Optional[int] = None,
    expand_purchased_assemblies: bool = False,
    internal_supplier_ids: Optional[List[int]] = None,
    category_mappings: Optional[Dict[str, int]] = None,
) -> tuple:
    """
    Get flat BOM with leaf parts only and deduplicated quantities.

    Pipeline:
    1. traverse_bom() - Build complete tree with cumulative quantities
    2. get_leaf_parts_only() - Filter to leaf parts (Commercial/Fabrication/External Assembly)
    3. deduplicate_and_sum() - Aggregate quantities for duplicate parts

    Args:
        part_id: Part ID to get flat BOM for
        max_depth: Maximum BOM depth to traverse (None = unlimited)
        expand_purchased_assemblies: If True, expand purchased assemblies to show subcomponents
        internal_supplier_ids: List of internal supplier IDs for categorization
        category_mappings: Dict mapping category types to lists of IDs (includes descendants)

    Returns:
        Tuple of (flat_bom_list, total_internal_fab_processed)
    """
    if internal_supplier_ids is None:
        internal_supplier_ids = []
    if category_mappings is None:
        category_mappings = {}
    from part.models import Part

    try:
        # Fetch part with default_supplier and category prefetched
        part = Part.objects.select_related("default_supplier", "category").get(
            pk=part_id
        )

        # Step 1: Traverse BOM to build tree and count Internal Fab parts
        logger.info(f"Traversing BOM for part {part_id} ({part.IPN})")
        imp_counter = {"count": 0}
        bom_tree = traverse_bom(
            part,
            max_depth=max_depth,
            internal_supplier_ids=internal_supplier_ids,
            category_mappings=category_mappings,
            imp_counter=imp_counter,
        )

        # Step 2: Filter to leaf parts only
        logger.info(
            f"Filtering to leaf parts only (expand_purchased_assemblies={expand_purchased_assemblies})"
        )
        leaf_parts = get_leaf_parts_only(
            bom_tree, expand_purchased_assemblies=expand_purchased_assemblies
        )
        logger.info(f"Found {len(leaf_parts)} leaf part instances")

        # Step 3: Deduplicate and sum quantities
        logger.info("Deduplicating and summing quantities")
        flat_bom = deduplicate_and_sum(leaf_parts)
        logger.info(
            f"Result: {len(flat_bom)} unique leaf parts, {imp_counter['count']} Internal Fab parts processed"
        )

        return flat_bom, imp_counter["count"]

    except Part.DoesNotExist:
        logger.error(f"Part {part_id} does not exist")
        return [], 0
    except Exception as e:
        logger.error(
            f"Error generating flat BOM for part {part_id}: {e}", exc_info=True
        )
        return [], 0
