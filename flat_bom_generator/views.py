"""API views for the FlatBOMGenerator plugin."""

import logging

import InvenTree.permissions
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .bom_traversal import get_flat_bom
from .categorization import _check_unit_mismatch
from .serializers import (
    BOMWarningSerializer,
    FlatBOMItemSerializer,
    FlatBOMResponseSerializer,
    SubstitutePartSerializer,
)

logger = logging.getLogger("inventree")


def get_category_mappings(plugin):
    """
    Build category mappings from plugin settings.

    Retrieves InvenTree category IDs for each display label (Fabrication,
    Commercial) from plugin settings. For each category, includes the
    category itself plus all descendant (child) categories to support
    hierarchical category structures. Mappings drive display labels only.

    Args:
        plugin: Plugin instance

    Returns:
        Dict mapping label keys to lists of category IDs (includes descendants):
        {
            'fabrication': [5, 12, 13],  # Parent + children
            'commercial': [8, 9, 10],
        }
        Empty dict if no categories configured.
    """
    from part.models import PartCategory

    category_mappings = {}
    # Handle None plugin (test environment)
    if plugin is None:
        return {}
    category_settings = {
        "fabrication": "FABRICATION_CATEGORY",
        "commercial": "COMMERCIAL_CATEGORY",
    }

    for key, setting_name in category_settings.items():
        try:
            category = plugin.get_setting(setting_name)
            logger.info(
                f"Retrieved {setting_name}: {category} (type: {type(category)})"
            )

            if category:
                # Handle various types: int, str, or object with pk/id attribute
                if isinstance(category, int):
                    category_id = category
                elif isinstance(category, str):
                    # Convert string to int
                    try:
                        category_id = int(category)
                    except ValueError:
                        logger.warning(
                            f"{setting_name} has invalid string value: '{category}'"
                        )
                        continue
                elif hasattr(category, "pk"):
                    category_id = category.pk
                elif hasattr(category, "id"):
                    category_id = category.id
                else:
                    logger.warning(
                        f"{setting_name} has unexpected type: {type(category)}"
                    )
                    continue

                # Validate category exists and fetch the object
                try:
                    category_obj = PartCategory.objects.get(pk=category_id)

                    # Get all descendant categories (including self)
                    # This handles hierarchical category structures
                    descendant_categories = category_obj.get_descendants(
                        include_self=True
                    )
                    descendant_ids = [cat.pk for cat in descendant_categories]

                    category_mappings[key] = descendant_ids
                    logger.info(
                        f"{setting_name}: Category {category_id} + {len(descendant_ids) - 1} descendants = {descendant_ids}"
                    )
                except PartCategory.DoesNotExist:
                    logger.warning(
                        f"Category ID {category_id} from {setting_name} does not exist. Ignoring."
                    )
            else:
                logger.info(f"{setting_name}: No category configured")
        except Exception:
            logger.exception(f"Error retrieving {setting_name}")

    return category_mappings


class FlatBOMView(APIView):
    """API view to get flattened BOM for a part.

    Returns a flattened bill of materials with cumulative quantities
    calculated through the entire assembly hierarchy.
    """

    permission_classes = (InvenTree.permissions.RolePermission,)
    role_required = "bom"

    def get(self, request, part_id, *args, **kwargs):
        """
        Get flattened BOM for a specific part.

        Args:
            part_id: Part ID to get flat BOM for

        Query Parameters:
            max_depth: Maximum depth to traverse (default: 0/unlimited)
            expand_purchased_assemblies: Expand assemblies with suppliers (default: false)
            include_internal_fab_in_cutlist: Process Internal Fab parts as cutlist (default: false)

        Returns:
            List of unique leaf parts with total quantities and display metadata
        """
        from part.models import Part
        from plugin.registry import registry

        # Get query parameters with hardcoded defaults (v0.11.0+)
        # These settings moved from plugin admin to frontend UI
        max_depth_param = request.query_params.get("max_depth", None)
        expand_purchased_assemblies_param = request.query_params.get(
            "expand_purchased_assemblies", None
        )
        include_ifab_cuts_param = request.query_params.get(
            "include_internal_fab_in_cutlist", None
        )
        include_substitutes_param = request.query_params.get(
            "include_substitutes", None
        )

        # Parse max_depth
        max_depth = None
        if max_depth_param is not None:
            try:
                max_depth = int(max_depth_param)
                if max_depth == 0:
                    max_depth = None  # 0 = unlimited
            except (ValueError, TypeError):
                return Response(
                    {"error": "Invalid max_depth parameter"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Get plugin for settings (categories, substitutes default)
        plugin = registry.get_plugin("flat-bom-generator")

        category_mappings = {}

        include_substitutes_default = False

        if plugin:
            category_mappings = get_category_mappings(plugin)

            include_substitutes_setting = plugin.get_setting(
                "SHOW_SUBSTITUTE_PARTS", backup_value=False
            )
            include_substitutes_default = (
                bool(include_substitutes_setting)
                if isinstance(include_substitutes_setting, bool)
                else (
                    str(include_substitutes_setting).lower() == "true"
                    if include_substitutes_setting
                    else False
                )
            )
        else:
            logger.error("[FlatBOM] Plugin 'flat-bom-generator' not found in registry!")

        # Parse boolean parameters (query params only - no plugin-setting fallbacks)
        expand_purchased_assemblies = (
            expand_purchased_assemblies_param is not None
            and expand_purchased_assemblies_param.lower() == "true"
        )

        enable_ifab_cuts = (
            include_ifab_cuts_param is not None
            and include_ifab_cuts_param.lower() == "true"
        )

        if include_substitutes_param is not None:
            include_substitutes = include_substitutes_param.lower() == "true"
        else:
            include_substitutes = include_substitutes_default

        if plugin:
            logger.info("[FlatBOM] Settings loaded:")
            logger.info(
                f"  - expand_purchased_assemblies: {expand_purchased_assemblies} (query param)"
            )
            logger.info(f"  - enable_ifab_cuts: {enable_ifab_cuts} (query param)")
            logger.info(
                f"  - include_substitutes: {include_substitutes} (from {'query param' if include_substitutes_param else 'plugin default'})"
            )
            logger.info(f"  - max_depth: {max_depth} (from query param)")
            logger.info(f"  - category_mappings: {category_mappings}")

        # Validate part exists and is an assembly
        try:
            part = Part.objects.get(pk=part_id)

            if not part.assembly:
                return Response(
                    {"error": "Part is not an assembly"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Part.DoesNotExist:
            return Response(
                {"error": "Part not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Generate flat BOM (deduplicated leaf parts)
        try:
            logger.info(
                f"[FlatBOM] Starting BOM traversal for part {part_id} ({part.name})"
            )
            flat_bom, total_ifps_processed, bom_warnings, max_depth_reached = (
                get_flat_bom(
                    part_id,
                    max_depth=max_depth,
                    expand_purchased_assemblies=expand_purchased_assemblies,
                    category_mappings=category_mappings,
                    enable_ifab_cuts=enable_ifab_cuts,
                )
            )
            logger.info(
                f"[FlatBOM] Traversal complete: {len(flat_bom)} unique parts, {total_ifps_processed} IFPs processed, max depth: {max_depth_reached}"
            )

            warnings = list(bom_warnings)

            # WARNING GENERATION TESTING APPROACH:
            # View-level aggregation logic (lines 334-421) is NOT directly tested via integration
            # tests because InvenTree's Part.check_add_to_bom() validation prevents creating the
            # invalid BOM structures needed for testing. This gap is acceptable because:
            # - 85% of warning logic IS tested via component tests (38 tests total):
            #   * BOMWarningSerializer validation (8 tests in test_serializers.py)
            #   * Flag logic (23 tests in test_assembly_no_children.py + test_max_depth_warnings.py)
            #   * Helper functions (7 tests for _check_unit_mismatch in test_categorization.py)
            # - Aggregation loop has low complexity (cyclomatic complexity ~8-12)
            # - Manual staging tests confirm all 4 warning types work correctly
            # - Industry standard (InvenTree's own): 90% coverage for critical paths
            # Decision rationale: Research showed mock-based tests add brittleness without
            # addressing root cause (InvenTree validation). Risk-based testing approach.

            # Check if any parts were stopped by max_depth - generate ONE summary warning
            parts_at_max_depth = [
                item for item in flat_bom if item.get("max_depth_exceeded")
            ]
            if parts_at_max_depth:
                serializer = BOMWarningSerializer(
                    data={
                        "type": "max_depth_reached",
                        "part_id": None,
                        "part_name": "Multiple assemblies",
                        "message": f"BOM traversal stopped at depth {max_depth_reached}. {len(parts_at_max_depth)} assemblies not fully expanded. Increase 'Maximum Traversal Depth' setting to see sub-components.",
                    }
                )
                serializer.is_valid(raise_exception=True)
                warnings.append(serializer.validated_data)

            # Enrich with additional data for UI display
            enriched_bom = []
            for item in flat_bom:
                try:
                    # Fetch full part details (category prefetched - it is
                    # read for the Category column below)
                    part_obj = Part.objects.select_related("category").get(
                        pk=item["part_id"]
                    )

                    # Calculate stock and order quantities
                    total_stock = part_obj.total_stock or 0
                    on_order = part_obj.on_order  # From incomplete purchase orders
                    allocated = (
                        part_obj.allocation_count()
                    )  # Stock allocated to builds + sales orders
                    available = part_obj.available_stock  # total_stock - allocated

                    # Check for assembly with no children (BOM definition issue)
                    if item.get("assembly_no_children"):
                        part_full_name = (
                            part_obj.full_name
                            if hasattr(part_obj, "full_name")
                            else part_obj.name
                        )
                        part_type = item.get("part_type", "Unknown")
                        serializer = BOMWarningSerializer(
                            data={
                                "type": "assembly_no_children",
                                "part_id": item["part_id"],
                                "part_name": part_full_name,
                                "message": f"{part_type} part has no BOM items defined",
                            }
                        )
                        serializer.is_valid(raise_exception=True)
                        warnings.append(serializer.validated_data)

                    # Check for inactive parts
                    if not part_obj.active:
                        part_full_name = (
                            part_obj.full_name
                            if hasattr(part_obj, "full_name")
                            else part_obj.name
                        )
                        serializer = BOMWarningSerializer(
                            data={
                                "type": "inactive_part",
                                "part_id": item["part_id"],
                                "part_name": part_full_name,
                                "message": "Part is marked inactive and may not be available for production",
                            }
                        )
                        serializer.is_valid(raise_exception=True)
                        warnings.append(serializer.validated_data)

                    # Note: max_depth_exceeded is handled by summary warning above
                    # (one warning for all assemblies instead of per-part warnings)

                    # Check for unit mismatch in BOM notes.
                    # Notes are never parsed for lengths or units to drive
                    # output - this check only surfaces a warning to the user.
                    bom_notes = item.get("note", "")
                    part_units = part_obj.units or ""

                    unit_warning = _check_unit_mismatch(bom_notes, part_units)

                    if unit_warning:
                        part_full_name = (
                            part_obj.full_name
                            if hasattr(part_obj, "full_name")
                            else part_obj.name
                        )
                        serializer = BOMWarningSerializer(
                            data={
                                "type": "unit_mismatch",
                                "part_id": item["part_id"],
                                "part_name": part_full_name,
                                "message": unit_warning,
                            }
                        )
                        serializer.is_valid(raise_exception=True)
                        warnings.append(serializer.validated_data)

                    # Serialize enriched item using FlatBOMItemSerializer
                    enriched_data = {
                        **item,  # All fields from flat_bom (part_id, total_qty, ipn, etc.)
                        "full_name": part_obj.full_name
                        if hasattr(part_obj, "full_name")
                        else part_obj.name,
                        "image": part_obj.image.url if part_obj.image else None,
                        "thumbnail": part_obj.image.thumbnail.url
                        if part_obj.image
                        else None,
                        "in_stock": total_stock,
                        "on_order": on_order,
                        "allocated": allocated,
                        "available": available,
                        "unit": part_obj.units
                        or "",  # Frontend expects 'unit' not 'units'
                        "link": part_obj.get_absolute_url()
                        if hasattr(part_obj, "get_absolute_url")
                        else f"/part/{part_obj.pk}/",
                        "category": part_obj.category.name if part_obj.category else "",
                        "internal_supplier": item.get("internal_supplier", False),
                    }

                    # Enrich with substitute parts if setting enabled
                    if include_substitutes:
                        from part.models import BomItemSubstitute

                        # bom_item_contributions tracks which BomItems contributed
                        # what quantity to this deduplicated part row.
                        # {bom_item_pk: cumulative_qty_contributed}
                        bom_item_contributions = item.get("bom_item_contributions", {})

                        substitute_data = []

                        if bom_item_contributions:
                            # Fetch all BomItemSubstitutes for the contributing BomItems
                            # in one query, grouped by substitute part
                            substitutes = BomItemSubstitute.objects.filter(
                                bom_item__pk__in=bom_item_contributions.keys()
                            ).select_related("part", "bom_item")

                            # Group by substitute part_id so we can aggregate qty
                            sub_groups = {}  # {sub_part_id: {info, total_qty, substitute_id}}
                            for sub in substitutes:
                                sub_part = sub.part
                                sub_part_id = sub_part.pk
                                contrib_qty = bom_item_contributions.get(
                                    sub.bom_item.pk, 0.0
                                )

                                if sub_part_id not in sub_groups:
                                    sub_groups[sub_part_id] = {
                                        "substitute_id": sub.pk,
                                        "part": sub_part,
                                        "total_qty": 0.0,
                                    }
                                sub_groups[sub_part_id]["total_qty"] += contrib_qty

                            parent_unit = (part_obj.units or "").strip().lower()

                            for sub_part_id, group in sub_groups.items():
                                sub_part = group["part"]
                                sub_unit_raw = sub_part.units or ""
                                sub_unit = sub_unit_raw.strip().lower()
                                unit_mismatch = sub_unit != parent_unit

                                # Generate warning for unit mismatch
                                if unit_mismatch:
                                    sub_label = sub_part.IPN or sub_part.name
                                    parent_label = part_obj.IPN or part_obj.name
                                    mismatch_msg = (
                                        f"Substitute '{sub_label}' "
                                        f"has unit '{sub_unit_raw or 'none'}' but parent part "
                                        f"'{parent_label}' "
                                        f"has unit '{part_obj.units or 'none'}'. "
                                        f"Quantities cannot be directly compared."
                                    )
                                    mismatch_serializer = BOMWarningSerializer(
                                        data={
                                            "type": "substitute_unit_mismatch",
                                            "part_id": item["part_id"],
                                            "part_name": item.get("part_name", ""),
                                            "message": mismatch_msg,
                                        }
                                    )
                                    mismatch_serializer.is_valid(raise_exception=True)
                                    warnings.append(mismatch_serializer.validated_data)

                                sub_raw = {
                                    "substitute_id": group["substitute_id"],
                                    "part_id": sub_part.pk,
                                    "ipn": sub_part.IPN or "",
                                    "part_name": sub_part.name,
                                    "full_name": sub_part.full_name
                                    if hasattr(sub_part, "full_name")
                                    else sub_part.name,
                                    "description": sub_part.description or "",
                                    "unit": sub_unit_raw,
                                    # Aggregated qty: sum of contributions from BomItems that list this sub
                                    "parent_total_qty": group["total_qty"],
                                    "parent_unit": part_obj.units or "",
                                    "in_stock": float(sub_part.total_stock or 0),
                                    "on_order": float(sub_part.on_order or 0),
                                    "allocated": float(sub_part.allocation_count()),
                                    "available": float(sub_part.available_stock or 0),
                                    "image": sub_part.image.url
                                    if sub_part.image
                                    else None,
                                    "thumbnail": sub_part.image.thumbnail.url
                                    if sub_part.image
                                    else None,
                                    "link": sub_part.get_absolute_url()
                                    if hasattr(sub_part, "get_absolute_url")
                                    else f"/part/{sub_part.pk}/",
                                }
                                substitute_data.append(sub_raw)

                        if substitute_data:
                            enriched_data["has_substitutes"] = True
                            sub_serializer = SubstitutePartSerializer(
                                data=substitute_data, many=True
                            )
                            if sub_serializer.is_valid(raise_exception=True):
                                enriched_data["substitute_parts"] = (
                                    sub_serializer.validated_data
                                )
                        else:
                            enriched_data["has_substitutes"] = False
                            enriched_data["substitute_parts"] = None
                    else:
                        enriched_data["has_substitutes"] = False
                        enriched_data["substitute_parts"] = None

                    serializer = FlatBOMItemSerializer(data=enriched_data)
                    serializer.is_valid(raise_exception=True)
                    enriched_bom.append(serializer.validated_data)

                except Part.DoesNotExist:
                    logger.warning(
                        f"Part {item['part_id']} not found during enrichment"
                    )
                    # Create minimal enriched data with defaults when part doesn't exist
                    enriched_data = {
                        **item,  # Preserve all fields from get_flat_bom
                        "full_name": item.get("part_name", "Unknown Part"),
                        "image": None,
                        "thumbnail": None,
                        "in_stock": 0,
                        "on_order": 0,
                        "allocated": 0,
                        "available": 0,
                        "unit": item.get("unit", ""),
                        "link": f"/part/{item['part_id']}/",
                    }
                    serializer = FlatBOMItemSerializer(data=enriched_data)
                    serializer.is_valid(raise_exception=True)
                    enriched_bom.append(serializer.validated_data)

            logger.info(f"[FlatBOM] Total warnings collected: {len(warnings)}")
            for idx, warning in enumerate(warnings):
                logger.info(f"[FlatBOM] Warning {idx + 1}: {warning}")

            # Prepare response data
            response_data = {
                "part_id": part_id,
                "part_name": part.name,
                "ipn": part.IPN or "",
                "total_unique_parts": len(enriched_bom),
                "total_ifps_processed": total_ifps_processed,
                "max_depth_reached": max_depth_reached,
                "bom_items": enriched_bom,
                "metadata": {
                    "warnings": warnings,
                },
            }

            # Validate with serializer
            serializer = FlatBOMResponseSerializer(data=response_data)
            serializer.is_valid(raise_exception=True)

            return Response(
                serializer.validated_data,
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.exception(f"Error generating flat BOM for part {part_id}")
            return Response(
                {"error": f"Failed to generate flat BOM: {e!s}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
