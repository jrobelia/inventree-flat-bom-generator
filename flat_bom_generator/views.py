"""API views for the FlatBOMGenerator plugin."""

import logging

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .bom_traversal import get_flat_bom

logger = logging.getLogger('inventree')


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
            flat_bom = get_flat_bom(part_id, max_depth=max_depth)
            
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
                'bom_items': enriched_bom
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error generating flat BOM for part {part_id}: {e}", exc_info=True)
            return Response(
                {'error': f'Failed to generate flat BOM: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
