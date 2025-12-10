"""API views for the FlatBOMGenerator plugin."""

import logging

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .bom_traversal import get_flat_bom

logger = logging.getLogger('inventree')


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
        primary_supplier = plugin.get_setting('PRIMARY_INTERNAL_SUPPLIER')
        if primary_supplier:
            # Handle both ID (int) and object with pk attribute
            if isinstance(primary_supplier, int):
                internal_ids.append(primary_supplier)
            elif hasattr(primary_supplier, 'pk'):
                internal_ids.append(primary_supplier.pk)
            elif hasattr(primary_supplier, 'id'):
                internal_ids.append(primary_supplier.id)
    except Exception as e:
        logger.warning(f"Error retrieving PRIMARY_INTERNAL_SUPPLIER: {e}")
    
    # Get additional internal suppliers (comma-separated string)
    try:
        additional = plugin.get_setting('ADDITIONAL_INTERNAL_SUPPLIERS', '')
        if additional and additional.strip():
            # Parse comma-separated IDs
            for id_str in additional.split(','):
                try:
                    supplier_id = int(id_str.strip())
                    if supplier_id > 0:
                        internal_ids.append(supplier_id)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid supplier ID in ADDITIONAL_INTERNAL_SUPPLIERS: '{id_str}'")
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
                logger.warning(f"Internal supplier ID {supplier_id} does not exist in database. Ignoring.")
        except Exception as e:
            logger.warning(f"Error validating supplier ID {supplier_id}: {e}")
    
    return sorted(validated_ids)


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
        max_depth = request.query_params.get('max_depth', None)
        if max_depth is not None:
            try:
                max_depth = int(max_depth)
            except (ValueError, TypeError):
                return Response(
                    {'error': 'Invalid max_depth parameter'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Get plugin settings
        plugin = registry.get_plugin('flat-bom-generator')
        expand_purchased_assemblies = False
        internal_supplier_ids = []
        fab_prefix = 'fab'  # Default
        coml_prefix = 'coml'  # Default
        if plugin:
            expand_purchased_assemblies = plugin.get_setting('SHOW_PURCHASED_ASSEMBLIES', False)
            internal_supplier_ids = get_internal_supplier_ids(plugin)
            # Get prefixes - allow blank for companies not using fab/coml naming
            fab_prefix = plugin.get_setting('FAB_PREFIX', 'fab') or ''
            coml_prefix = plugin.get_setting('COML_PREFIX', 'coml') or ''
        
        # Validate part exists and is an assembly
        try:
            part = Part.objects.get(pk=part_id)
            
            if not part.assembly:
                return Response(
                    {'error': 'Part is not an assembly'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Part.DoesNotExist:
            return Response(
                {'error': 'Part not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Generate flat BOM (deduplicated leaf parts)
        try:
            flat_bom, total_imps_processed = get_flat_bom(part_id, max_depth=max_depth, expand_purchased_assemblies=expand_purchased_assemblies, internal_supplier_ids=internal_supplier_ids, fab_prefix=fab_prefix, coml_prefix=coml_prefix)
            
            # Enrich with additional data for UI display
            enriched_bom = []
            for item in flat_bom:
                try:
                    # Fetch full part details
                    part_obj = Part.objects.select_related('default_supplier').get(pk=item['part_id'])
                    
                    # Calculate stock and order quantities
                    total_stock = part_obj.total_stock or 0
                    on_order = part_obj.on_order  # From incomplete purchase orders
                    allocated = part_obj.allocation_count()  # Stock allocated to builds + sales orders
                    available = part_obj.available_stock  # total_stock - allocated
                    
                    enriched_item = {
                        **item,  # Include all fields from flat_bom
                        'full_name': part_obj.full_name if hasattr(part_obj, 'full_name') else part_obj.name,
                        'image': part_obj.image.url if part_obj.image else None,
                        'thumbnail': part_obj.image.thumbnail.url if part_obj.image else None,
                        'in_stock': total_stock,
                        'on_order': on_order,
                        'allocated': allocated,
                        'available': available,
                        'units': part_obj.units or '',
                        'link': part_obj.get_absolute_url() if hasattr(part_obj, 'get_absolute_url') else f'/part/{part_obj.pk}/'
                    }
                    enriched_bom.append(enriched_item)
                    
                except Part.DoesNotExist:
                    logger.warning(f"Part {item['part_id']} not found during enrichment")
                    enriched_bom.append(item)
            
            return Response({
                'part_id': part_id,
                'part_name': part.name,
                'ipn': part.IPN or '',
                'total_unique_parts': len(enriched_bom),
                'total_imps_processed': total_imps_processed,
                'bom_items': enriched_bom
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error generating flat BOM for part {part_id}: {e}", exc_info=True)
            return Response(
                {'error': f'Failed to generate flat BOM: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
