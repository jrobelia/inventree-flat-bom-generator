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
        "MAX_DEPTH": {
            "name": "Maximum Traversal Depth",
            "description": "Maximum depth to traverse BOM hierarchy (0 = unlimited)",
            "validator": int,
            "default": 0,
        },
        "SHOW_PURCHASED_ASSEMBLIES": {
            "name": "Expand Purchased Assemblies",
            "description": "Expand BOM for assemblies that have a default supplier (usually purchased as complete units)",
            "validator": bool,
            "default": False,
        },
        "PRIMARY_INTERNAL_SUPPLIER": {
            "name": "Primary Internal Supplier",
            "description": "Your primary internal manufacturing company/supplier. Parts with this supplier will be categorized as Internal Fab.",
            "model": "company.company",
            "default": None,
        },
        "ADDITIONAL_INTERNAL_SUPPLIERS": {
            "name": "Additional Internal Suppliers",
            "description": 'Additional internal supplier IDs (comma-separated, e.g., "5,12"). Leave empty if you only have one internal supplier.',
            "validator": str,
            "default": "",
        },
        # Category-based classification settings
        "FABRICATION_CATEGORY": {
            "name": "Fabrication Category",
            "description": "InvenTree category for fabricated parts (internal or external manufacturing, e.g., machine shop, PCB fab)",
            "model": "part.partcategory",
            "default": None,
        },
        "COMMERCIAL_CATEGORY": {
            "name": "Commercial Parts Category",
            "description": "InvenTree category for commercial/COTS purchased parts",
            "model": "part.partcategory",
            "default": None,
        },
        "ASSEMBLY_CATEGORY": {
            "name": "Assembly Category",
            "description": "InvenTree category for assemblies (internal or external build)",
            "model": "part.partcategory",
            "default": None,
        },
        "CUT_TO_LENGTH_CATEGORY": {
            "name": "Cut-to-Length Category",
            "description": "InvenTree category for raw material parts with length requirements (wire, tubing, bar stock). Length must be specified in BOM line item notes field.",
            "model": "part.partcategory",
            "default": None,
        },
        "INTERNAL_FAB_CUT_BREAKDOWN": {
            "name": "Enable Internal Fab Cut Breakdown",
            "description": "Show Internal Fab children as grouped cut breakdowns (like CtL) for specified units.",
            "validator": bool,
            "default": False,
        },
        "INTERNAL_FAB_CUT_UNITS": {
            "name": "Internal Fab Cut Units",
            "description": "Comma-separated list of units (e.g., mm,in,cm) to apply cut breakdown to Internal Fab children.",
            "validator": str,
            "default": "mm,in,cm",
        },
    }

    # Custom URL endpoints (from UrlsMixin)
    # Ref: https://docs.inventree.org/en/latest/plugins/mixins/urls/
    def setup_urls(self):
        """Configure custom URL endpoints for this plugin.

        Note: This endpoint is used by the plugin's frontend UI panel to fetch data.
        Even though InvenTree 1.1.6 doesn't expose /api/plugin/ as a public REST API,
        the endpoint is still accessible to the plugin's own frontend code.
        """
        from django.urls import path
        from .views import FlatBOMView

        return [
            # API endpoint used by the frontend panel to get flattened BOM data
            path("flat-bom/<int:part_id>/", FlatBOMView.as_view(), name="flat-bom"),
        ]

    # User interface elements (from UserInterfaceMixin)
    # Ref: https://docs.inventree.org/en/latest/plugins/mixins/ui/

    # Custom UI panels
    def get_ui_panels(self, request, context: dict, **kwargs):
        """Return a list of custom panels to be rendered in the InvenTree user interface."""

        panels = []

        # Only display this panel for parts that are assemblies
        if context.get("target_model") == "part":
            # Get the part ID from context
            part_id = context.get("target_id")

            if part_id:
                # Import here to avoid circular dependencies
                from part.models import Part

                try:
                    part = Part.objects.get(pk=part_id)

                    # Only show panel if this part is an assembly (has a BOM)
                    if part.assembly:
                        panels.append({
                            "key": "flat-bom-viewer-panel",
                            "title": "Flat BOM Viewer",
                            "description": "View flattened bill of materials with all sub-assemblies",
                            "icon": "ti:list-tree:outline",
                            "source": self.plugin_static_file(
                                "Panel.js:renderFlatBOMGeneratorPanel"
                            ),
                        })
                except Part.DoesNotExist:
                    pass

        return panels
