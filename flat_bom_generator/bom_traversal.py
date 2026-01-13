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
    depth_tracker: Optional[Dict[str, int]] = None,
) -> Dict:
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
    default_supplier_id = part.default_supplier.pk if part.default_supplier else None
    # Get the supplier company ID from the SupplierPart, if available
    default_supplier_company_id = None
    if (
        part.default_supplier
        and hasattr(part.default_supplier, "supplier")
        and part.default_supplier.supplier
    ):
        default_supplier_company_id = part.default_supplier.supplier.pk

    # Categorize part
    is_top_level = level == 0
    part_category_id = part.category.pk if part.category else None
    part_type = categorize_part(
        part_name,
        is_assembly,
        is_top_level,
        default_supplier_company_id,  # Pass the supplier company ID, not the SupplierPart PK
        internal_supplier_ids,
        part_category_id,
        category_mappings,
        bom_item_notes,
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
                    depth_tracker=depth_tracker,
                )

                # Set child-specific values
                child_node["quantity"] = child_qty
                child_node["reference"] = child_ref
                child_node["note"] = child_note

                # If parent is Internal Fab and child is a leaf part (Fab/Coml), mark for cut row logic
                # Don't mark assemblies - their descendants should be treated as regular parts
                child_part_type = child_node.get("part_type", "")
                if part_type == "Internal Fab" and child_part_type in ("Fab", "Coml"):
                    child_node["from_internal_fab_parent"] = True
                    child_node["parent_ipn"] = ipn
                    child_node["parent_part_id"] = part_id
                    # For Internal Fab children, cut_length is the BOM quantity (native unit)
                    child_node["cut_length"] = child_qty
                    # Ensure cut_length is set (should never be None if BOM is valid)
                    if child_qty is None:
                        raise ValueError(
                            f"Internal Fab child has None quantity: parent={ipn} (ID={part_id}), child={child_part.IPN}"
                        )
                    logger.info(
                        f"[FlatBOM][traverse_bom] Marked child as from_internal_fab_parent: child_part_id={child_node.get('part_id')}, child_type={child_part_type}, parent_part_id={part_id}, child_unit={child_node.get('unit')}"
                    )

                # Add to children list
                node["children"].append(child_node)

    # Mark if max depth prevented expansion of an assembly
    if max_depth_hit and is_assembly:
        node["max_depth_exceeded"] = True

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

    # Fallback: If no category assigned and part is not an assembly,
    # treat it as a leaf part (graceful degradation without categories)
    if not is_non_assembly_leaf and not tree["is_assembly"]:
        is_non_assembly_leaf = True
        logger.info(
            f"[FlatBOM][get_leaf] Part {tree['part_id']} ({tree['ipn']}) is leaf (non-assembly) despite part_type='{part_type}'"
        )

    if is_non_assembly_leaf:
        # Always include non-assembly leaf parts
        cumulative_qty = tree["cumulative_qty"]
        cut_length = None

        # For Cut-to-Length parts, extract length from notes but keep as separate field
        # Don't multiply into quantity - we want piece count and length separate for cut lists
        if part_type == "CtL":
            note_text = tree.get("note", "")
            cut_length = _extract_length_from_notes(note_text)
        # For Internal Fab children, preserve the cut_length already set in traverse_bom
        elif tree.get("from_internal_fab_parent"):
            cut_length = tree.get("cut_length")

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
            "from_internal_fab_parent": tree.get("from_internal_fab_parent", False),
            "parent_ipn": tree.get("parent_ipn"),
            "parent_part_id": tree.get("parent_part_id"),
            "max_depth_exceeded": tree.get("max_depth_exceeded", False),
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
            "from_internal_fab_parent": tree.get("from_internal_fab_parent", False),
            "parent_ipn": tree.get("parent_ipn"),
            "parent_part_id": tree.get("parent_part_id"),
            "max_depth_exceeded": tree.get("max_depth_exceeded", False),
        })
        # Stop here - don't recurse into children
        return leaves

    # Check for assemblies with no children (potential BOM definition issue)
    # These should be included in flat BOM and flagged for warning
    # BUT: Don't flag if no children is due to max_depth being hit
    children = tree.get("children", [])
    max_depth_exceeded = tree.get("max_depth_exceeded", False)
    logger.info(
        f"[FlatBOM][get_leaf] Part {tree['part_id']} is_assembly={tree.get('is_assembly')}, children={len(children)}, max_depth_exceeded={max_depth_exceeded}"
    )
    if tree.get("is_assembly") and not children:
        # Only flag as assembly_no_children if NOT stopped by max_depth
        # If stopped by max_depth, it's expected behavior (will be covered by summary warning)
        assembly_no_children_flag = not max_depth_exceeded
        if assembly_no_children_flag:
            logger.info(
                f"[FlatBOM][get_leaf] DETECTED assembly with no children (genuine BOM issue): {tree['part_id']}"
            )
        else:
            logger.info(
                f"[FlatBOM][get_leaf] Assembly with no children due to max_depth: {tree['part_id']}"
            )
        # Assembly part with no BOM items defined - include as leaf with special flag
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
            "from_internal_fab_parent": tree.get("from_internal_fab_parent", False),
            "parent_ipn": tree.get("parent_ipn"),
            "parent_part_id": tree.get("parent_part_id"),
            "assembly_no_children": assembly_no_children_flag,  # Only flag if NOT due to max_depth
            "max_depth_exceeded": max_depth_exceeded,
        })
        return leaves

    # Recurse into children for:
    # - Non-leaf parts (regular assemblies)
    # - Purchaseable assemblies when expand_purchased_assemblies is True
    for child in children:
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
    part_references = defaultdict(list)  # Store all reference strings for aggregation
    cut_lists = defaultdict(list)  # Store cut list details for CtL parts
    internal_fab_cut_lists = defaultdict(
        list
    )  # Store cut list details for Internal Fab children
    ctl_warnings = []  # Store warnings for CtL and Internal Fab issues

    # Retrieve allowed units for Internal Fab cut breakdown from attached attribute (set by get_flat_bom)
    if hasattr(deduplicate_and_sum, "ifab_units"):
        allowed_ifab_units = deduplicate_and_sum.ifab_units
    else:
        allowed_ifab_units = set()

    logger.info(
        f"[FlatBOM][deduplicate_and_sum] allowed_ifab_units={allowed_ifab_units}, {len(leaf_parts)} leaf parts"
    )

    for leaf in leaf_parts:
        part_id = leaf["part_id"]
        part_type = leaf["part_type"]
        cut_length = leaf.get("cut_length")
        unit = leaf.get("unit")
        from_ifab = leaf.get("from_internal_fab_parent", False)

        # --- OA-00270 DEBUG LOGGING ---
        # OA-00270 is the IPN of interest; log all aggregation for this part and its children
        ipn = leaf.get("ipn")
        parent_ipn = leaf.get("parent_ipn")
        if ipn == "OA-00270" or parent_ipn == "OA-00270":
            logger.info(
                f"[OA-00270][deduplicate_and_sum] part_id={part_id}, ipn={ipn}, parent_ipn={parent_ipn}, part_type={part_type}, unit={unit}, cut_length={cut_length}, from_ifab={from_ifab}, cumulative_qty={leaf.get('cumulative_qty')}, quantity={leaf.get('quantity')}"
            )

        # Always use part_id as key (single row per part)
        key = part_id

        # For CtL parts, accumulate total length (qty * length)
        if part_type == "CtL" and cut_length is not None:
            totals[key] += leaf["cumulative_qty"] * cut_length
            # Deduplicate by length
            found = False
            for cut in cut_lists[key]:
                if cut["length"] == cut_length:
                    cut["quantity"] += leaf["cumulative_qty"]
                    found = True
                    break
            if not found:
                cut_lists[key].append({
                    "quantity": leaf["cumulative_qty"],
                    "length": cut_length,
                })
        elif from_ifab and cut_length is not None:
            # Internal fab parts should have consistent units
            # If unit doesn't match allowed set, skip cut_list logic (treat as regular part)
            if unit not in allowed_ifab_units:
                # Silently treat as regular part (no warning)
                # For internal fab leaves, cut_length is the quantity (cumulative_qty not used)
                piece_count_inc = leaf.get("quantity") or 1
                totals[key] += cut_length * piece_count_inc
            else:
                # Piece count is the BOM qty of the Internal Fab child in its parent
                piece_count_inc = leaf.get("quantity") or 1

                logger.info(
                    f"[FlatBOM][deduplicate_and_sum] Adding internal_fab_cut_list for Internal Fab child part_id={part_id}, unit={unit}, piece_qty={cut_length}, piece_count_inc={piece_count_inc}, parent_ipn={leaf.get('parent_ipn')}, parent_part_id={leaf.get('parent_part_id')}"
                )
                # Track total qty as piece_qty * piece_count (reflect cut-list rollup)
                # Note: quantity is not set in leaf dict, so this always defaults to 1
                piece_count_inc = leaf.get("quantity") or 1
                totals[key] += cut_length * piece_count_inc
                found = False
                for piece in internal_fab_cut_lists[key]:
                    if (
                        piece.get("piece_qty") == cut_length
                        and piece.get("unit") == unit
                    ):
                        piece["count"] += piece_count_inc
                        found = True
                        break
                if not found:
                    internal_fab_cut_lists[key].append({
                        "count": piece_count_inc,
                        "piece_qty": cut_length,
                        "unit": unit,
                    })
        else:
            # Regular parts (not CtL, not internal fab)
            totals[key] += leaf["cumulative_qty"]

        # Collect reference designators for aggregation (from BOM item notes)
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
                "part_type": part_type,
                "note": leaf.get("note", ""),  # BOM item notes
                "assembly_no_children": leaf.get("assembly_no_children", False),
                "max_depth_exceeded": leaf.get("max_depth_exceeded", False),
            }

    # Check CtL parts for unit mismatches across all their note variants
    from .categorization import _check_unit_mismatch

    ctl_parts_notes = {}  # part_id -> set of unique note strings
    for leaf in leaf_parts:
        part_type = leaf.get("part_type")
        if part_type == "CtL":
            part_id_leaf = leaf["part_id"]
            note = leaf.get("note", "")
            if note:  # Only track non-empty notes
                if part_id_leaf not in ctl_parts_notes:
                    ctl_parts_notes[part_id_leaf] = (set(), leaf["part_name"])
                ctl_parts_notes[part_id_leaf][0].add(note)

    # Check each CtL part for unit mismatches - warn for EACH unique note with mismatch
    # Each note represents a unique user BOM entry, so all mismatches should be flagged
    if ctl_parts_notes:
        # Only import when needed (for unit tests that don't use Django)
        from part.models import Part

        for part_id_leaf, (note_set, part_name) in ctl_parts_notes.items():
            try:
                part_obj = Part.objects.get(pk=part_id_leaf)
                part_units = part_obj.units or ""
                part_full_name = (
                    part_obj.full_name if hasattr(part_obj, "full_name") else part_name
                )

                for note in note_set:
                    unit_warning = _check_unit_mismatch(note, part_units)
                    if unit_warning:
                        logger.info(
                            f"[FlatBOM][deduplicate_and_sum] Unit mismatch in CtL part {part_id_leaf} ({part_full_name}), note='{note}': {unit_warning}"
                        )
                        # Add warning with note text to distinguish multiple entries
                        ctl_warnings.append({
                            "type": "unit_mismatch",
                            "part_id": part_id_leaf,
                            "part_name": part_full_name,
                            "message": f"{unit_warning} (in note: '{note}')",
                        })
            except Exception as e:
                logger.error(
                    f"[FlatBOM][deduplicate_and_sum] Error checking CtL part {part_id_leaf}: {e}"
                )

    # Store CtL warnings on function for retrieval in get_flat_bom
    deduplicate_and_sum.ctl_warnings = ctl_warnings

    # --- End Internal Fab Cut Breakdown ---

    # Always include any part with a non-empty cut_list or internal_fab_cut_list
    all_keys = (
        set(totals.keys())
        | set(k for k, v in cut_lists.items() if v)
        | set(k for k, v in internal_fab_cut_lists.items() if v)
    )

    # Log parts with cut_lists and internal_fab_cut_lists
    parts_with_cuts = [k for k, v in cut_lists.items() if v]
    parts_with_ifab_cuts = [k for k, v in internal_fab_cut_lists.items() if v]
    logger.info(
        f"[FlatBOM][deduplicate_and_sum] Found {len(parts_with_cuts)} parts with cut_lists, {len(parts_with_ifab_cuts)} parts with internal_fab_cut_lists, {len(ctl_warnings)} CtL unit warnings"
    )
    for key in parts_with_cuts:
        logger.info(
            f"[FlatBOM][deduplicate_and_sum] Part {part_info[key]['ipn']} (ID: {part_info[key]['part_id']}) has {len(cut_lists[key])} cut entries"
        )
    for key in parts_with_ifab_cuts:
        logger.info(
            f"[FlatBOM][deduplicate_and_sum] Part {part_info[key]['ipn']} (ID: {part_info[key]['part_id']}) has {len(internal_fab_cut_lists[key])} internal fab cut entries"
        )

    # --- OA-00270 FINAL INSPECTION ---
    # Log final totals and internal_fab_cut_list contents for OA-00270 (if present)
    for key in parts_with_ifab_cuts:
        try:
            if part_info[key].get("ipn") == "OA-00270":
                logger.info(
                    f"[OA-00270][deduplicate_and_sum][FINAL] totals={totals.get(key)}, internal_fab_cut_list={internal_fab_cut_lists.get(key)}, cut_list={cut_lists.get(key)}"
                )
        except Exception:
            pass

    # Only include internal_fab_cut_list if enable_ifab_cuts is True
    enable_ifab_cuts = getattr(deduplicate_and_sum, "enable_ifab_cuts", False)
    result = []
    for key in sorted(all_keys, key=lambda k: part_info[k]["ipn"]):
        # Combine all reference designators from multiple BOM paths
        combined_reference = (
            ", ".join(part_references[key]) if part_references[key] else ""
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
            "part_type": part_info[key]["part_type"],
            "note": part_info[key]["note"],  # BOM item notes
            "reference": combined_reference,  # Aggregated reference designators
            "cut_list": cut_lists[key] if cut_lists.get(key) else None,
            "assembly_no_children": part_info[key].get("assembly_no_children", False),
            "max_depth_exceeded": part_info[key].get("max_depth_exceeded", False),
        }
        if enable_ifab_cuts:
            row["internal_fab_cut_list"] = (
                internal_fab_cut_lists[key] if internal_fab_cut_lists.get(key) else None
            )
        result.append(row)

    # Log final result counts
    results_with_cuts = [r for r in result if r.get("cut_list")]
    results_with_ifab_cuts = [r for r in result if r.get("internal_fab_cut_list")]
    logger.info(
        f"[FlatBOM][deduplicate_and_sum] Returning {len(result)} total parts: {len(results_with_cuts)} have cut_list, {len(results_with_ifab_cuts)} have internal_fab_cut_list"
    )

    return result


def get_flat_bom(
    part_id: int,
    max_depth: Optional[int] = None,
    expand_purchased_assemblies: bool = False,
    internal_supplier_ids: Optional[List[int]] = None,
    category_mappings: Optional[Dict[str, int]] = None,
    enable_ifab_cuts: bool = False,
    ifab_units: Optional[set] = None,
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
        Tuple of (flat_bom_list, total_internal_fab_processed, ctl_warnings_list)
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
        depth_tracker = {"max_level": 0}
        bom_tree = traverse_bom(
            part,
            max_depth=max_depth,
            internal_supplier_ids=internal_supplier_ids,
            category_mappings=category_mappings,
            imp_counter=imp_counter,
            depth_tracker=depth_tracker,
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
        # Set ifab_units before calling deduplicate_and_sum so it can access via hasattr
        if ifab_units is None:
            ifab_units = set()
        deduplicate_and_sum.ifab_units = ifab_units
        # Attach enable_ifab_cuts to deduplicate_and_sum so it can be checked when building result rows
        deduplicate_and_sum.enable_ifab_cuts = enable_ifab_cuts
        flat_bom = deduplicate_and_sum(leaf_parts)

        # Retrieve CtL warnings from deduplicate_and_sum
        ctl_warnings = getattr(deduplicate_and_sum, "ctl_warnings", [])

        logger.info(
            f"Result: {len(flat_bom)} unique leaf parts, {imp_counter['count']} Internal Fab parts processed, max depth reached: {depth_tracker['max_level']}"
        )

        return flat_bom, imp_counter["count"], ctl_warnings, depth_tracker["max_level"]

    except Part.DoesNotExist:
        logger.error(f"Part {part_id} does not exist")
        return [], 0, [], 0
    except Exception as e:
        logger.error(
            f"Error generating flat BOM for part {part_id}: {e}", exc_info=True
        )
        return [], 0, [], 0
