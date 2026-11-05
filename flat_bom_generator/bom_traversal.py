from __future__ import annotations

import logging
import math
from collections import defaultdict

from .categorization import categorize_part

logger = logging.getLogger("inventree")

# Sentinel distinguishing "primary supplier not provided" from "provided as None".
_UNSET = object()


def get_bom_items(part) -> list[dict]:
    """
    Fetch BOM items for a given part with related data.

    Args:
        part: Part model instance

    Returns:
        List of BOM item dictionaries with: sub_part, quantity, reference, etc.
    """
    from company.models import SupplierPart
    from part.models import BomItem

    try:
        # Prefetch sub_part for categorization
        bom_items = list(BomItem.objects.filter(part=part).select_related("sub_part"))

        # Batch-fetch the primary SupplierPart for every sub_part in a single
        # query (keyed by part id) to avoid an N+1 lookup per BOM line.
        sub_part_ids = [bi.sub_part.pk for bi in bom_items if bi.sub_part]
        primary_suppliers = {
            sp.part_id: sp
            for sp in SupplierPart.objects.filter(
                part_id__in=sub_part_ids, primary=True
            ).select_related("supplier")
        }

        items = []
        for bom_item in bom_items:
            if not bom_item.sub_part:
                continue

            primary_supplier = primary_suppliers.get(bom_item.sub_part.pk)

            item = {
                "sub_part": bom_item.sub_part,
                "sub_part_id": bom_item.sub_part.pk,
                "bom_item_pk": bom_item.pk,
                "quantity": float(bom_item.quantity),
                "reference": bom_item.reference or "",
                "note": bom_item.note or "",
                "optional": bom_item.optional,
                "consumable": bom_item.consumable,
                "inherited": bom_item.inherited,
                "has_default_supplier": primary_supplier is not None,
                "primary_supplier": primary_supplier,
            }
            items.append(item)

        return items

    except Exception as e:  # noqa: BLE001
        logger.error(f"Could not fetch BOM items for part {part.pk}: {e}")
        return []


def traverse_bom(
    part,
    level: int = 0,
    parent_qty: float = 1.0,
    parent_ipn: str | None = None,
    visited: set[int] | None = None,
    max_depth: int | None = None,
    category_mappings: dict[str, int] | None = None,
    imp_counter: dict[str, int] | None = None,
    depth_tracker: dict[str, int] | None = None,
    primary_supplier=_UNSET,
) -> dict:
    """
    Recursively traverse BOM structure and build tree.

    CRITICAL: Uses visited.copy() pattern to allow same part in different
    branches while preventing infinite loops from circular references.

    NOTE: InvenTree prevents circular BOMs at database level. The circular
    check here is a safety mechanism that raises ValueError if triggered.

    Args:
        part: Part model instance
        level: Current depth in BOM tree (0 = top)
        parent_qty: Cumulative quantity from parent levels
        parent_ipn: IPN of parent part
        visited: Set of visited part IDs (to detect circular references)
        max_depth: Maximum depth to traverse (None = unlimited)
        category_mappings: Dict mapping label types to lists of category IDs
            (includes descendants); used for display labels only
        imp_counter: Dictionary to count Internal Fab parts {'count': 0} (mutable for recursion)

    Returns:
        Dictionary representing BOM node with all metadata and children
    """
    if category_mappings is None:
        category_mappings = {}
    # Initialize visited set on first call
    if visited is None:
        visited = set()
    # Initialize IFP counter on first call
    if imp_counter is None:
        imp_counter = {"count": 0}

    part_id = part.pk

    # CRITICAL: Prevent infinite loops from circular BOMs
    # NOTE: InvenTree validates BOMs at database level, so this should never trigger.
    # If it does, database integrity is compromised.
    if part_id in visited:
        raise ValueError(
            f"CRITICAL: Circular BOM reference detected for {part.IPN or 'Unknown'} "
            f"(Part ID: {part_id}) at level {level}. This should not be possible - "
            f"InvenTree database integrity may be compromised. Please report this issue."
        )

    # Add to visited for this branch
    visited.add(part_id)

    # Extract part metadata
    ipn = part.IPN or ""
    part_name = part.name
    units = part.units or ""
    is_assembly = part.assembly
    purchaseable = part.purchaseable
    description = part.description or ""
    # The caller (get_bom_items) batches primary-supplier lookups and passes
    # the result in (possibly None); only query here when nothing was supplied
    # (e.g. the root part).
    if primary_supplier is _UNSET:
        from company.models import SupplierPart

        primary_qs = SupplierPart.objects.filter(part=part, primary=True)
        primary_supplier = primary_qs.select_related("supplier").first()
    default_supplier_id = primary_supplier.pk if primary_supplier else None
    # Internal suppliers are detected from the supplier company's native
    # is_internal flag - no plugin settings involved.
    internal_supplier = bool(
        primary_supplier
        and primary_supplier.supplier
        and primary_supplier.supplier.is_internal
    )

    # Assign display label (labels do not drive expansion decisions)
    is_top_level = level == 0
    part_category_id = part.category.pk if part.category else None
    part_type = categorize_part(
        part_name,
        is_assembly,
        is_top_level,
        default_supplier_id,
        internal_supplier,
        part_category_id,
        category_mappings,
    )

    # Count Internal Fab parts processed during traversal
    # These are assemblies we fabricate internally (need to expand to find child parts)
    if part_type == "Internal Fab":
        imp_counter["count"] += 1

    # Track maximum depth reached
    if depth_tracker is not None:
        depth_tracker["max_level"] = max(depth_tracker.get("max_level", 0), level)

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
        "internal_supplier": internal_supplier,
        "part_type": part_type,
        "children": [],
        "max_depth_exceeded": False,  # Will be set to True if depth limit stops expansion
    }

    # Check if we should expand this node's BOM
    skip_bom_expansion = False
    max_depth_hit = False

    # Don't expand if max depth reached
    if max_depth is not None and level >= max_depth:
        logger.debug(f"Max depth ({max_depth}) reached at part {ipn}")
        skip_bom_expansion = True
        max_depth_hit = True

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
                    category_mappings=category_mappings,
                    primary_supplier=bom_item.get("primary_supplier", _UNSET),
                    imp_counter=imp_counter,
                    depth_tracker=depth_tracker,
                )

                # Set child-specific values
                child_node["quantity"] = child_qty
                child_node["reference"] = child_ref
                child_node["note"] = child_note
                child_node["optional"] = bom_item.get("optional", False)
                child_node["consumable"] = bom_item.get("consumable", False)
                child_node["bom_item_pk"] = bom_item.get("bom_item_pk")

                # Children of an internal-supplier assembly become cut-list
                # rows: one entry per BOM item occurrence, cut_length is the
                # BOM item quantity in the child's native unit. Assemblies are
                # not marked - their descendants are treated as regular parts.
                if internal_supplier and not child_node["is_assembly"]:
                    child_node["from_internal_fab_parent"] = True
                    child_node["parent_ipn"] = ipn
                    child_node["parent_part_id"] = part_id
                    child_node["cut_length"] = child_qty
                    logger.info(
                        f"[FlatBOM][traverse_bom] Marked child as from_internal_fab_parent: child_part_id={child_node.get('part_id')}, parent_part_id={part_id}, child_unit={child_node.get('unit')}"
                    )

                # Add to children list
                node["children"].append(child_node)

    # Mark if max depth prevented expansion of an assembly
    if max_depth_hit and is_assembly:
        node["max_depth_exceeded"] = True

    return node


def get_leaf_parts_only(
    tree: dict,
    leaves: list[dict] | None = None,
    expand_purchased_assemblies: bool = False,
) -> list[dict]:
    """
    Flatten BOM tree to line items (leaf rows), driven by assembly status and
    primary supplier — never by the display label in part_type.

    Line-item / expansion matrix:
    - Top-level (level 0) input part: exempt — never emitted as a row for
      itself; an assembly root always expands (ruling R-015). A childless
      unsourced root still emits, carrying the assembly_no_children warning.
    - Non-assembly part: line item (always a leaf row).
    - Assembly with external primary supplier: line item, not expanded
      (expand_purchased_assemblies=True expands it into children instead).
    - Assembly with internal primary supplier (supplier.is_internal):
      line item AND expanded — the row covers the internal purchase order
      while its children become the raw-material pull.
    - Assembly with no primary supplier: expanded as a build-order candidate;
      the assembly itself is not a line item unless it has no children, in
      which case it is emitted and flagged assembly_no_children.

    Args:
        tree: BOM tree from traverse_bom()
        leaves: Accumulator list (for recursion)
        expand_purchased_assemblies: If True, expand external-supplier
            assemblies to show subcomponents instead of the assembly row

    Returns:
        Flat list of line-item rows with cumulative quantities
    """
    if leaves is None:
        leaves = []

    def _emit(node: dict, extra: dict | None = None) -> None:
        leaf = {
            "part_id": node["part_id"],
            "ipn": node["ipn"],
            "part_name": node["part_name"],
            "description": node.get("description", ""),
            "cumulative_qty": node["cumulative_qty"],
            "unit": node.get("unit", ""),
            "is_assembly": node["is_assembly"],
            "purchaseable": node["purchaseable"],
            "default_supplier_id": node.get("default_supplier_id"),
            "internal_supplier": node.get("internal_supplier", False),
            "part_type": node.get("part_type", "Unknown"),
            "reference": node.get("reference", ""),
            "note": node.get("note", ""),
            "level": node["level"],
            "bom_item_pk": node.get("bom_item_pk"),
            "from_internal_fab_parent": node.get("from_internal_fab_parent", False),
            "parent_ipn": node.get("parent_ipn"),
            "parent_part_id": node.get("parent_part_id"),
            "cut_length": node.get("cut_length"),
            "max_depth_exceeded": node.get("max_depth_exceeded", False),
            "optional": node.get("optional", False),
            "consumable": node.get("consumable", False),
        }
        if extra:
            leaf.update(extra)
        leaves.append(leaf)

    children = tree.get("children", [])
    is_assembly = tree.get("is_assembly", False)
    has_supplier = tree.get("default_supplier_id") is not None
    is_internal = tree.get("internal_supplier", False)

    # The level-0 TLA root is exempt from the emit matrix (ruling R-015):
    # a flat BOM never collapses to a single row naming the part it was
    # run on - the panel is opened on that part to see inside it. An
    # assembly root always expands; the matrix below applies to
    # descendants only. A childless root still falls through so an
    # unsourced one emits its assembly_no_children warning.
    is_root = tree.get("level") == 0
    if is_root and is_assembly and children:
        for child in children:
            get_leaf_parts_only(child, leaves, expand_purchased_assemblies)
        return leaves

    # Non-assembly parts are always line items
    if not is_assembly:
        if not is_root:
            _emit(tree)
        return leaves

    # Internal-supplier assembly: line item AND expand into children
    if has_supplier and is_internal:
        if not is_root:
            _emit(tree)
        for child in children:
            get_leaf_parts_only(child, leaves, expand_purchased_assemblies)
        return leaves

    # External-supplier assembly: line item, not expanded (unless the
    # expand_purchased_assemblies toggle is on, which shows children instead)
    if has_supplier:
        if is_root or expand_purchased_assemblies:
            for child in children:
                get_leaf_parts_only(child, leaves, expand_purchased_assemblies)
        else:
            _emit(tree)
        return leaves

    # Unsourced assembly: build-order candidate. Expand; the assembly itself
    # becomes a line item only when it has no children (flagged for warning,
    # unless the empty tree is a max_depth artifact).
    if children:
        for child in children:
            get_leaf_parts_only(child, leaves, expand_purchased_assemblies)
        return leaves

    max_depth_exceeded = tree.get("max_depth_exceeded", False)
    assembly_no_children_flag = not max_depth_exceeded
    if assembly_no_children_flag:
        logger.info(
            f"[FlatBOM][get_leaf] DETECTED assembly with no children (genuine BOM issue): {tree['part_id']}"
        )
    _emit(tree, {"assembly_no_children": assembly_no_children_flag})
    return leaves


def deduplicate_and_sum(
    leaf_parts: list[dict],
    enable_ifab_cuts: bool = False,
) -> list[dict]:
    """
    Sum quantities for parts appearing multiple times.

    Every line item aggregates by part_id with the standard cumulative
    quantity rollup. Children of internal-supplier assemblies additionally
    contribute an internal_fab_cut_list entry per BOM item occurrence:
    piece_qty is the BOM item quantity and count is the ancestor multiplier
    (how many times that occurrence fires, rounded up when non-integral).
    No note parsing, no unit filter.

    Args:
        leaf_parts: List of leaf parts from get_leaf_parts_only()
        enable_ifab_cuts: Attach internal_fab_cut_list entries to rows for
            children of internal-supplier assemblies

    Returns:
        Deduplicated list with aggregated quantities
    """
    totals = defaultdict(float)
    part_info = {}
    part_references = defaultdict(list)  # Store all note strings for aggregation
    internal_fab_cut_lists = defaultdict(
        list
    )  # Cut list entries for internal-fab assembly children
    # Track which BomItems contributed what qty to each deduplicated part
    # Used by views.py to aggregate substitute qtys per substitute part
    bom_item_contributions = defaultdict(
        dict
    )  # {part_key: {bom_item_pk: cumulative_qty}}

    for leaf in leaf_parts:
        part_id = leaf["part_id"]
        key = part_id  # Always use part_id as key (single row per part)

        # Track BomItem contribution for substitute qty aggregation
        bom_item_pk = leaf.get("bom_item_pk")
        if bom_item_pk is not None:
            bom_item_contributions[key][bom_item_pk] = (
                bom_item_contributions[key].get(bom_item_pk, 0.0)
                + leaf["cumulative_qty"]
            )

        totals[key] += leaf["cumulative_qty"]

        # One cut-list entry per BOM item occurrence under an
        # internal-supplier assembly. count = how many times this occurrence
        # fires (the ancestor quantity multiplier, rounded up when
        # non-integral - a cut list never under-orders); piece_qty = BOM qty.
        if (
            enable_ifab_cuts
            and leaf.get("from_internal_fab_parent")
            and leaf.get("cut_length") is not None
        ):
            cut_length = leaf["cut_length"]
            if cut_length:
                ratio = leaf["cumulative_qty"] / cut_length
                # Snap a ratio within float error of a whole count -
                # an integral multiplier must not over-ceil by one
                # piece (e.g. 3 x 0.1 -> ratio 3.0000000000000004).
                nearest = round(ratio)
                count = (
                    int(nearest)
                    if math.isclose(ratio, nearest, abs_tol=1e-6)
                    else math.ceil(ratio)
                )
            else:
                count = 1
            cut_entry = {
                "count": max(count, 1),
                "piece_qty": cut_length,
                "unit": leaf.get("unit") or "",
            }
            internal_fab_cut_lists[key].append(cut_entry)

        # Collect note strings for aggregation (display only - never parsed)
        note = leaf.get("note", "")
        if note and note.strip():
            part_references[key].append(note)

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
                "internal_supplier": leaf.get("internal_supplier", False),
                "part_type": leaf["part_type"],
                "note": leaf.get("note", ""),  # BOM item notes
                "assembly_no_children": leaf.get("assembly_no_children", False),
                "max_depth_exceeded": leaf.get("max_depth_exceeded", False),
                "optional": leaf.get(
                    "optional", False
                ),  # Start as False, set to True only if ALL instances are optional
                "consumable": leaf.get(
                    "consumable", False
                ),  # Start as False, set to True only if ALL instances are consumable
                "optional_instances": 0,  # Track how many times part appears as optional
                "consumable_instances": 0,  # Track how many times part appears as consumable
                "total_instances": 0,  # Track total appearances
            }

        # Track flag statistics for aggregation logic
        # A part is optional=True only if it's optional in ALL BOM appearances
        # A part is consumable=True only if it's consumable in ALL BOM appearances
        part_info[key]["total_instances"] += 1
        if leaf.get("optional", False):
            part_info[key]["optional_instances"] += 1
        if leaf.get("consumable", False):
            part_info[key]["consumable_instances"] += 1

    all_keys = set(totals.keys()) | {k for k, v in internal_fab_cut_lists.items() if v}

    result = []
    for key in sorted(all_keys, key=lambda k: part_info[k]["ipn"]):
        # Combine all note strings from multiple BOM paths
        combined_reference = (
            ", ".join(part_references[key]) if part_references[key] else ""
        )

        # Finalize optional and consumable flags based on ALL instances
        # Part is optional=True only if it's optional in ALL BOM appearances
        # Part is consumable=True only if it's consumable in ALL BOM appearances
        info = part_info[key]
        is_optional = (
            info["total_instances"] > 0
            and info["optional_instances"] == info["total_instances"]
        )
        is_consumable = (
            info["total_instances"] > 0
            and info["consumable_instances"] == info["total_instances"]
        )

        row = {
            "part_id": part_info[key]["part_id"],
            "total_qty": totals.get(key, 0),
            "ipn": part_info[key]["ipn"],
            "part_name": part_info[key]["part_name"],
            "description": part_info[key]["description"],
            "unit": part_info[key]["unit"],
            "is_assembly": part_info[key]["is_assembly"],
            "purchaseable": part_info[key]["purchaseable"],
            "default_supplier_id": part_info[key]["default_supplier_id"],
            "internal_supplier": part_info[key]["internal_supplier"],
            "part_type": part_info[key]["part_type"],
            "note": part_info[key]["note"],  # BOM item notes
            "reference": combined_reference,  # Aggregated note strings
            "internal_fab_cut_list": internal_fab_cut_lists.get(key) or None,
            "assembly_no_children": part_info[key].get("assembly_no_children", False),
            "max_depth_exceeded": part_info[key].get("max_depth_exceeded", False),
            "optional": is_optional,
            "consumable": is_consumable,
            "bom_item_contributions": dict(bom_item_contributions.get(key, {})),
        }
        result.append(row)

    return result


def get_flat_bom(
    part_id: int,
    max_depth: int | None = None,
    expand_purchased_assemblies: bool = False,
    category_mappings: dict[str, int] | None = None,
    enable_ifab_cuts: bool = False,
) -> tuple:
    """
    Get flat BOM line items with deduplicated quantities.

    Pipeline:
    1. traverse_bom() - Build complete tree with cumulative quantities
    2. get_leaf_parts_only() - Apply the line-item/expansion matrix
    3. deduplicate_and_sum() - Aggregate quantities for duplicate parts

    Args:
        part_id: Part ID to get flat BOM for
        max_depth: Maximum BOM depth to traverse (None = unlimited)
        expand_purchased_assemblies: If True, expand external-supplier
            assemblies to show subcomponents
        category_mappings: Dict mapping label types to lists of category IDs
            (display labels only - does not affect expansion)
        enable_ifab_cuts: Attach internal_fab_cut_list entries to rows

    Returns:
        Tuple of (flat_bom_list, total_internal_fab_processed, warnings_list,
                  max_depth_reached)
    """
    if category_mappings is None:
        category_mappings = {}
    from part.models import Part

    try:
        # Fetch part with category prefetched
        part = Part.objects.select_related("category").get(pk=part_id)

        # Step 1: Traverse BOM to build tree and count Internal Fab parts
        logger.info(f"Traversing BOM for part {part_id} ({part.IPN})")
        imp_counter = {"count": 0}
        depth_tracker = {"max_level": 0}
        bom_tree = traverse_bom(
            part,
            max_depth=max_depth,
            category_mappings=category_mappings,
            imp_counter=imp_counter,
            depth_tracker=depth_tracker,
        )

        # Step 2: Apply line-item / expansion matrix
        logger.info(
            f"Applying line-item matrix (expand_purchased_assemblies={expand_purchased_assemblies})"
        )
        leaf_parts = get_leaf_parts_only(
            bom_tree, expand_purchased_assemblies=expand_purchased_assemblies
        )
        logger.info(f"Found {len(leaf_parts)} line-item instances")

        # Step 3: Deduplicate and sum quantities
        logger.info("Deduplicating and summing quantities")
        flat_bom = deduplicate_and_sum(leaf_parts, enable_ifab_cuts=enable_ifab_cuts)

        logger.info(
            f"Result: {len(flat_bom)} unique line items, {imp_counter['count']} Internal Fab parts processed, max depth reached: {depth_tracker['max_level']}"
        )

        return flat_bom, imp_counter["count"], [], depth_tracker["max_level"]

    except Part.DoesNotExist:
        logger.error(f"Part {part_id} does not exist")
        return [], 0, [], 0
    except Exception:
        logger.exception(f"Error generating flat BOM for part {part_id}")
        return [], 0, [], 0
