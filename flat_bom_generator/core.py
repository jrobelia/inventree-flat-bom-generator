"""Displays flattened bill of materials for assemblies with recursive traversal and export capabilities"""

from plugin import InvenTreePlugin

from plugin.mixins import SettingsMixin, UrlsMixin, UserInterfaceMixin

from . import PLUGIN_VERSION


class FlatBOMGenerator(SettingsMixin, UrlsMixin, UserInterfaceMixin, InvenTreePlugin):

    """FlatBOMGenerator - custom InvenTree plugin."""

    # Plugin metadata
    TITLE = "Flat BOM Generator"
    NAME = "FlatBOMGenerator"
    SLUG = "flat-bom-generator"
    DESCRIPTION = "Displays flattened bill of materials for assemblies with recursive traversal and export capabilities"
    VERSION = PLUGIN_VERSION

    # Additional project information
    AUTHOR = "Jon Robelia"
    
    LICENSE = "MIT"

    # Optionally specify supported InvenTree versions
    # MIN_VERSION = '0.18.0'
    # MAX_VERSION = '2.0.0'

    # Plugin settings (from SettingsMixin)
    # Ref: https://docs.inventree.org/en/latest/plugins/mixins/settings/
    SETTINGS = {
        'MAX_DEPTH': {
            'name': 'Maximum Traversal Depth',
            'description': 'Maximum depth to traverse BOM hierarchy (0 = unlimited)',
            'validator': int,
            'default': 0,
        },
        'SHOW_PURCHASED_ASSEMBLIES': {
            'name': 'Expand Purchased Assemblies',
            'description': 'Expand BOM for assemblies that have a default supplier (usually purchased as complete units)',
            'validator': bool,
            'default': False,
        },
        'PRIMARY_INTERNAL_SUPPLIER': {
            'name': 'Primary Internal Supplier',
            'description': 'Your primary internal manufacturing company/supplier. Parts/assemblies with this supplier will be categorized as Internally Manufactured Parts (IMP).',
            'model': 'company.company',
            'default': None,
        },
        'ADDITIONAL_INTERNAL_SUPPLIERS': {
            'name': 'Additional Internal Suppliers',
            'description': 'Additional internal supplier IDs (comma-separated, e.g., "5,12"). Leave empty if you only have one internal supplier.',
            'validator': str,
            'default': '',
        },
        'FAB_PREFIX': {
            'name': 'Fabricated Part Prefix',
            'description': 'Part name prefix for fabricated parts (case-insensitive). Default: "fab"',
            'validator': str,
            'default': 'fab',
        },
        'COML_PREFIX': {
            'name': 'Commercial Part Prefix',
            'description': 'Part name prefix for commercial/COTS parts (case-insensitive). Default: "coml"',
            'validator': str,
            'default': 'coml',
        }
    }

    # Custom URL endpoints (from UrlsMixin)
    # Ref: https://docs.inventree.org/en/latest/plugins/mixins/urls/
    def setup_urls(self):
        """Configure custom URL endpoints for this plugin."""
        from django.urls import path
        from .views import FlatBOMView

        return [
            # API endpoint to get flattened BOM for a part
            path('flat-bom/<int:part_id>/', FlatBOMView.as_view(), name='flat-bom'),
        ]
    

    # User interface elements (from UserInterfaceMixin)
    # Ref: https://docs.inventree.org/en/latest/plugins/mixins/ui/
    
    # Custom UI panels
    def get_ui_panels(self, request, context: dict, **kwargs):
        """Return a list of custom panels to be rendered in the InvenTree user interface."""

        panels = []

        # Only display this panel for parts that are assemblies
        if context.get('target_model') == 'part':
            # Get the part ID from context
            part_id = context.get('target_id')
            
            if part_id:
                # Import here to avoid circular dependencies
                from part.models import Part
                
                try:
                    part = Part.objects.get(pk=part_id)
                    
                    # Only show panel if this part is an assembly (has a BOM)
                    if part.assembly:
                        panels.append({
                            'key': 'flat-bom-viewer-panel',
                            'title': 'Flat BOM Viewer',
                            'description': 'View flattened bill of materials with all sub-assemblies',
                            'icon': 'ti:list-tree:outline',
                            'source': self.plugin_static_file('Panel.js:renderFlatBOMGeneratorPanel'),
                        })
                except Part.DoesNotExist:
                    pass
        
        return panels
