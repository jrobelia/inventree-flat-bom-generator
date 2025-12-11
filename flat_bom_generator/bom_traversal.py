"""
BOM Traversal and Flattening Operations

Functions for recursively traversing Bill of Materials hierarchies
and flattening the tree structure for display and export.

Uses InvenTree internal models (safe when accessed through plugin context).
"""

from typing import Dict, List, Optional, Set
from collections import defaultdict
import logging

from .categorization import categorize_part

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
    imp_counter: Optional[Dict[str, int]] = None,
    fab_prefix: str = "fab",
    coml_prefix: str = "coml",
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
        internal_supplier_ids: List of internal supplier IDs for IMP categorization
        imp_counter: Dictionary to count IMPs {'count': 0} (mutable for recursion)
        fab_prefix: Prefix for fabricated parts (default: 'fab')
        coml_prefix: Prefix for commercial parts (default: 'coml')

    Returns:
        Dictionary representing BOM node with all metadata and children
    """
    if internal_supplier_ids is None:
        internal_supplier_ids = []
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
    part_type = categorize_part(
        part_name,
        is_assembly,
        is_top_level,
        default_supplier_id,
        internal_supplier_ids,
        fab_prefix,
        coml_prefix,
    )

    # Count IMPs processed during traversal
    if part_type == "IMP":
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
                    imp_counter=imp_counter,
                    fab_prefix=fab_prefix,
                    coml_prefix=coml_prefix,
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

    Leaf parts are:
    - Fab Part (fabricated, non-assembly)
    - Coml Part (commercial, non-assembly)
    - Purchaseable Assembly (assembly with external supplier) - UNLESS expand_purchased_assemblies is True

    NOT leaf parts (will be expanded):
    - IMP (Internally Manufactured Part) - always expand to show internal components
    - Regular assemblies without suppliers

    Args:
        tree: BOM tree from traverse_bom()
        leaves: Accumulator list (for recursion)
        expand_purchased_assemblies: If True, expand purchased assemblies to show subcomponents

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
    is_purchaseable_assembly = part_type == "Purchaseable Assembly"

    # Determine if this part should be included as a leaf
    # Include non-assembly parts: Fab Part, Coml Part, Unknown (for companies without naming conventions)
    is_non_assembly_leaf = (
        part_type.endswith(" Part")  # Matches "fab Part", "Coml Part", etc.
        or (
            part_type == "Unknown" and not tree.get("is_assembly", False)
        )  # Unknown non-assemblies
    )

    if is_non_assembly_leaf:
        # Always include non-assembly leaf parts
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

    Args:
        leaf_parts: List of leaf parts from get_leaf_parts_only()

    Returns:
        Deduplicated list with aggregated quantities
    """
    # Use defaultdict to accumulate quantities
    totals = defaultdict(float)
    part_info = {}

    for leaf in leaf_parts:
        part_id = leaf["part_id"]

        # Sum quantities
        totals[part_id] += leaf["cumulative_qty"]

        # Store part info (first occurrence wins for metadata)
        if part_id not in part_info:
            part_info[part_id] = {
                "ipn": leaf["ipn"],
                "part_name": leaf["part_name"],
                "description": leaf["description"],
                "unit": leaf["unit"],
                "is_assembly": leaf["is_assembly"],
                "purchaseable": leaf["purchaseable"],
                "default_supplier_id": leaf.get("default_supplier_id"),
                "part_type": leaf["part_type"],
            }

    # Convert to sorted list
    result = [
        {
            "part_id": part_id,
            "total_qty": qty,
            "ipn": part_info[part_id]["ipn"],
            "part_name": part_info[part_id]["part_name"],
            "description": part_info[part_id]["description"],
            "unit": part_info[part_id]["unit"],
            "is_assembly": part_info[part_id]["is_assembly"],
            "purchaseable": part_info[part_id]["purchaseable"],
            "default_supplier_id": part_info[part_id]["default_supplier_id"],
            "part_type": part_info[part_id]["part_type"],
        }
        for part_id, qty in sorted(totals.items(), key=lambda x: part_info[x[0]]["ipn"])
    ]

    return result


def get_flat_bom(
    part_id: int,
    max_depth: Optional[int] = None,
    expand_purchased_assemblies: bool = False,
    internal_supplier_ids: Optional[List[int]] = None,
    fab_prefix: str = "fab",
    coml_prefix: str = "coml",
) -> tuple:
    """
    Get flat BOM with leaf parts only and deduplicated quantities.

    Pipeline:
    1. traverse_bom() - Build complete tree with cumulative quantities
    2. get_leaf_parts_only() - Filter to leaf parts (Fab/Coml/Purchaseable Assembly)
    3. deduplicate_and_sum() - Aggregate quantities for duplicate parts

    Args:
        part_id: Part ID to get flat BOM for
        max_depth: Maximum depth to traverse (None = unlimited)
        expand_purchased_assemblies: If True, expand purchased assemblies to show subcomponents
        internal_supplier_ids: List of internal supplier IDs for IMP categorization
        fab_prefix: Prefix for fabricated parts (default: 'fab')
        coml_prefix: Prefix for commercial parts (default: 'coml')

    Returns:
        Tuple of (flat_bom_list, total_imps_processed)
    """
    if internal_supplier_ids is None:
        internal_supplier_ids = []
    from part.models import Part

    try:
        # Fetch part with default_supplier prefetched
        part = Part.objects.select_related("default_supplier").get(pk=part_id)

        # Step 1: Traverse BOM to build tree and count IMPs
        logger.info(f"Traversing BOM for part {part_id} ({part.IPN})")
        imp_counter = {"count": 0}
        bom_tree = traverse_bom(
            part,
            max_depth=max_depth,
            internal_supplier_ids=internal_supplier_ids,
            imp_counter=imp_counter,
            fab_prefix=fab_prefix,
            coml_prefix=coml_prefix,
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
            f"Result: {len(flat_bom)} unique leaf parts, {imp_counter['count']} IMPs processed"
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
