"""API views for the FlatBOMGenerator plugin."""

import logging

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .bom_traversal import get_flat_bom

logger = logging.getLogger("inventree")


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

    # Get primary internal supplier
    try:
        primary_supplier = plugin.get_setting("PRIMARY_INTERNAL_SUPPLIER")
        if primary_supplier:
            # Handle int, str, or object with pk/id attribute
            if isinstance(primary_supplier, int):
                internal_ids.append(primary_supplier)
            elif isinstance(primary_supplier, str):
                try:
                    internal_ids.append(int(primary_supplier))
                except ValueError:
                    logger.warning(
                        f"PRIMARY_INTERNAL_SUPPLIER has invalid string value: '{primary_supplier}'"
                    )
            elif hasattr(primary_supplier, "pk"):
                internal_ids.append(primary_supplier.pk)
            elif hasattr(primary_supplier, "id"):
                internal_ids.append(primary_supplier.id)
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
    Assembly, Cut-to-Length) from plugin settings. For each category, includes
    the category itself plus all descendant (child) categories to support
    hierarchical category structures.

    Args:
        plugin: Plugin instance

    Returns:
        Dict mapping category type keys to lists of category IDs (includes descendants):
        {
            'fabrication': [5, 12, 13],  # Parent + children
            'commercial': [8, 9, 10],
            'assembly': [15, 16],
            'cut_to_length': [20]
        }
        Empty dict if no categories configured.
    """
    from part.models import PartCategory

    category_mappings = {}

    category_settings = {
        "fabrication": "FABRICATION_CATEGORY",
        "commercial": "COMMERCIAL_CATEGORY",
        "assembly": "ASSEMBLY_CATEGORY",
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

        # Get optional max_depth parameter
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
        expand_purchased_assemblies = False
        internal_supplier_ids = []
        category_mappings = {}
        if plugin:
            expand_purchased_assemblies = plugin.get_setting(
                "SHOW_PURCHASED_ASSEMBLIES", False
            )
            internal_supplier_ids = get_internal_supplier_ids(plugin)
            category_mappings = get_category_mappings(plugin)

            logger.info("[FlatBOM] Settings loaded:")
            logger.info(
                f"  - expand_purchased_assemblies: {expand_purchased_assemblies}"
            )
            logger.info(f"  - internal_supplier_ids: {internal_supplier_ids}")
            logger.info(f"  - category_mappings: {category_mappings}")
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
            flat_bom, total_imps_processed = get_flat_bom(
                part_id,
                max_depth=max_depth,
                expand_purchased_assemblies=expand_purchased_assemblies,
                internal_supplier_ids=internal_supplier_ids,
                category_mappings=category_mappings,
            )
            logger.info(
                f"[FlatBOM] Traversal complete: {len(flat_bom)} unique parts, {total_imps_processed} IMPs processed"
            )

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

                    enriched_item = {
                        **item,  # Include all fields from flat_bom
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
                        "units": part_obj.units or "",
                        "link": part_obj.get_absolute_url()
                        if hasattr(part_obj, "get_absolute_url")
                        else f"/part/{part_obj.pk}/",
                    }
                    enriched_bom.append(enriched_item)

                except Part.DoesNotExist:
                    logger.warning(
                        f"Part {item['part_id']} not found during enrichment"
                    )
                    enriched_bom.append(item)

            return Response(
                {
                    "part_id": part_id,
                    "part_name": part.name,
                    "ipn": part.IPN or "",
                    "total_unique_parts": len(enriched_bom),
                    "total_imps_processed": total_imps_processed,
                    "bom_items": enriched_bom,
                },
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
