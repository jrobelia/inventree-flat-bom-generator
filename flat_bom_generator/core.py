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
    MIN_VERSION = "1.6.0"
    # MAX_VERSION = '2.0.0'

    # Plugin settings (from SettingsMixin)
    # Ref: https://docs.inventree.org/en/latest/plugins/mixins/settings/
    # Note: MAX_DEPTH and expand-purchased-assemblies toggles live in the
    # frontend UI and are passed as query parameters. Internal suppliers are
    # detected via the supplier company's native is_internal flag, not plugin
    # settings.
    SETTINGS = {  # noqa: RUF012
        # Category-based display-label settings (labels only - no behavior)
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
        "SHOW_SUBSTITUTE_PARTS": {
            "name": "Show Substitute Parts",
            "description": "Include substitute parts in flat BOM display (shown as child rows with individual stock levels). Disable to hide substitutes.",
            "validator": bool,
            "default": False,
        },
        "INCLUDE_OPTIONAL_PARTS": {
            "name": "Include Optional Parts",
            "description": "Include optional BOM-line demand in flat BOM totals (optional demand is real demand, so the default keeps it on). Disable to exclude optional lines - and their whole subtrees - from totals, derived figures, and the cut list.",
            "validator": bool,
            "default": True,
        },
    }

    # Custom URL endpoints (from UrlsMixin)
    # Ref: https://docs.inventree.org/en/latest/plugins/mixins/urls/
    def setup_urls(self):
        """Configure custom URL endpoints for this plugin.

        Note: This endpoint is used by the plugin's frontend UI panel to fetch data.
        It isn't a public REST API, but remains accessible to the plugin's own
        frontend code.
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
                        panel = {
                            "key": "flat-bom-viewer-panel",
                            "title": "Flat BOM Viewer",
                            "description": "View flattened bill of materials with all sub-assemblies",
                            "icon": "ti:list-tree:outline",
                            "source": self.plugin_static_file(
                                f"Panel.js:renderFlatBOMGeneratorPanel?v={PLUGIN_VERSION}"
                            ),
                        }
                        panels.append(panel)
                except Part.DoesNotExist:
                    pass

        return panels
