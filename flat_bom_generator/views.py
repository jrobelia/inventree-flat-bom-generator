"""API views for the FlatBOMGenerator plugin."""

import logging

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .bom_traversal import get_flat_bom
from .categorization import _check_unit_mismatch
from .serializers import (
    BOMWarningSerializer,
    FlatBOMItemSerializer,
    FlatBOMResponseSerializer,
)

logger = logging.getLogger("inventree")


def _extract_id_from_value(value, setting_name):
    """
    Extract integer ID from various value types (int, str, object with pk/id).

    Args:
        value: Value to extract ID from (int, str, or object with pk/id attribute)
        setting_name: Name of setting (for logging purposes)

    Returns:
        Integer ID if valid, None otherwise
    """
    if not value:
        return None

    if isinstance(value, int):
        return value
    elif isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            logger.warning(f"{setting_name} has invalid string value: '{value}'")
            return None
    elif hasattr(value, "pk"):
        return value.pk
    elif hasattr(value, "id"):
        return value.id

    return None


def get_internal_supplier_ids(plugin):
    """
    Get list of internal supplier IDs from plugin settings.

    Combines PRIMARY_INTERNAL_SUPPLIER and ADDITIONAL_INTERNAL_SUPPLIERS,
    validates IDs exist in database, deduplicates, and returns sorted list of unique IDs.

    Args:
        plugin: Plugin instance

    Returns:
        List of unique internal supplier IDs (integers)
    """
    from company.models import Company

    internal_ids = []

    # Handle None plugin (test environment)
    if plugin is None:
        return []

    # Get primary internal supplier
    try:
        primary_supplier = plugin.get_setting("PRIMARY_INTERNAL_SUPPLIER")
        supplier_id = _extract_id_from_value(
            primary_supplier, "PRIMARY_INTERNAL_SUPPLIER"
        )
        if supplier_id is not None:
            internal_ids.append(supplier_id)
    except Exception as e:
        logger.warning(f"Error retrieving PRIMARY_INTERNAL_SUPPLIER: {e}")

    # Get additional internal suppliers (comma-separated string)
    try:
        additional = plugin.get_setting("ADDITIONAL_INTERNAL_SUPPLIERS", "")
        if additional and additional.strip():
            # Parse comma-separated IDs
            for id_str in additional.split(","):
                try:
                    supplier_id = int(id_str.strip())
                    if supplier_id > 0:
                        internal_ids.append(supplier_id)
                except (ValueError, TypeError):
                    logger.warning(
                        f"Invalid supplier ID in ADDITIONAL_INTERNAL_SUPPLIERS: '{id_str}'"
                    )
    except Exception as e:
        logger.warning(f"Error parsing ADDITIONAL_INTERNAL_SUPPLIERS: {e}")

    # Deduplicate
    unique_ids = list(set(internal_ids))

    # Validate that IDs exist in database
    validated_ids = []
    for supplier_id in unique_ids:
        try:
            if Company.objects.filter(pk=supplier_id).exists():
                validated_ids.append(supplier_id)
            else:
                logger.warning(
                    f"Internal supplier ID {supplier_id} does not exist in database. Ignoring."
                )
        except Exception as e:
            logger.warning(f"Error validating supplier ID {supplier_id}: {e}")

    return sorted(validated_ids)


def get_category_mappings(plugin):
    """
    Build category mappings from plugin settings.

    Retrieves InvenTree category IDs for each part type (Fabrication, Commercial,
    Cut-to-Length) from plugin settings. For each category, includes
    the category itself plus all descendant (child) categories to support
    hierarchical category structures.

    Args:
        plugin: Plugin instance

    Returns:
        Dict mapping category type keys to lists of category IDs (includes descendants):
        {
            'fabrication': [5, 12, 13],  # Parent + children
            'commercial': [8, 9, 10],
            'cut_to_length': [20]
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
        "cut_to_length": "CUT_TO_LENGTH_CATEGORY",
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
        except Exception as e:
            logger.error(f"Error retrieving {setting_name}: {e}", exc_info=True)

    return category_mappings


class FlatBOMView(APIView):
    """API view to get flattened BOM for a part.

    Returns a flattened bill of materials with cumulative quantities
    calculated through the entire assembly hierarchy.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, part_id, *args, **kwargs):
        """
        Get flattened BOM for a specific part.

        Args:
            part_id: Part ID to get flat BOM for

        Query Parameters:
            max_depth: Maximum depth to traverse (optional)

        Returns:
            List of unique leaf parts with total quantities and display metadata
        """
        from part.models import Part
        from plugin.registry import registry

        # Get optional max_depth parameter from query (overrides plugin setting)
        max_depth = request.query_params.get("max_depth", None)
        if max_depth is not None:
            try:
                max_depth = int(max_depth)
            except (ValueError, TypeError):
                return Response(
                    {"error": "Invalid max_depth parameter"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Get plugin settings
        plugin = registry.get_plugin("flat-bom-generator")

        # If max_depth not provided in query, use plugin setting
        if max_depth is None:
            max_depth_setting = plugin.get_setting("MAX_DEPTH", 0) if plugin else 0
            max_depth = (
                int(max_depth_setting)
                if max_depth_setting and int(max_depth_setting) > 0
                else None
            )

        expand_purchased_assemblies = False
        internal_supplier_ids = []
        category_mappings = {}
        enable_ifab_cuts = False
        ifab_units = set()

        if plugin:
            expand_purchased_assemblies = plugin.get_setting(
                "SHOW_PURCHASED_ASSEMBLIES", False
            )
            internal_supplier_ids = get_internal_supplier_ids(plugin)
            category_mappings = get_category_mappings(plugin)
            enable_ifab_cuts = plugin.get_setting("INTERNAL_FAB_CUT_BREAKDOWN", False)
            units_csv = plugin.get_setting("INTERNAL_FAB_CUT_UNITS", "")
            if units_csv:
                ifab_units = set(u.strip() for u in units_csv.split(",") if u.strip())

            logger.info("[FlatBOM] Settings loaded:")
            logger.info(
                f"  - expand_purchased_assemblies: {expand_purchased_assemblies}"
            )
            logger.info(f"  - internal_supplier_ids: {internal_supplier_ids}")
            logger.info(f"  - category_mappings: {category_mappings}")
            logger.info(f"  - enable_ifab_cuts: {enable_ifab_cuts}")
            logger.info(f"  - ifab_units: {ifab_units}")
            logger.info(
                f"[FlatBOM][DEBUG] Using settings for cut_list logic: enable_ifab_cuts={enable_ifab_cuts}, ifab_units={ifab_units}"
            )
        else:
            logger.error("[FlatBOM] Plugin 'flat-bom-generator' not found in registry!")

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
            flat_bom, total_ifps_processed, ctl_warnings, max_depth_reached = (
                get_flat_bom(
                    part_id,
                    max_depth=max_depth,
                    expand_purchased_assemblies=expand_purchased_assemblies,
                    internal_supplier_ids=internal_supplier_ids,
                    category_mappings=category_mappings,
                    enable_ifab_cuts=enable_ifab_cuts,
                    ifab_units=ifab_units,
                )
            )
            logger.info(
                f"[FlatBOM] Traversal complete: {len(flat_bom)} unique parts, {total_ifps_processed} IFPs processed, max depth: {max_depth_reached}"
            )

            # Start with CtL warnings from deduplicate_and_sum
            warnings = ctl_warnings.copy()

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
                    # Fetch full part details
                    part_obj = Part.objects.select_related("default_supplier").get(
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

                    # Check for unit mismatch in BOM notes (non-CtL parts only)
                    # CtL parts already checked above to catch all cut list variants
                    if item.get("part_type") != "CtL":
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
                    }
                    serializer = FlatBOMItemSerializer(data=enriched_data)
                    serializer.is_valid(raise_exception=True)
                    enriched_bom.append(serializer.validated_data)

                except Part.DoesNotExist:
                    logger.warning(
                        f"Part {item['part_id']} not found during enrichment"
                    )
                    enriched_bom.append(item)

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
                "metadata": {"warnings": warnings},
            }

            # Validate with serializer
            serializer = FlatBOMResponseSerializer(data=response_data)
            serializer.is_valid(raise_exception=True)

            return Response(
                serializer.validated_data,
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(
                f"Error generating flat BOM for part {part_id}: {e}", exc_info=True
            )
            return Response(
                {"error": f"Failed to generate flat BOM: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
