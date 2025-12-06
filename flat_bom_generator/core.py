"""Displays flattened bill of materials for assemblies with recursive traversal and export capabilities"""

from plugin import InvenTreePlugin

from plugin.mixins import ReportMixin, ScheduleMixin, SettingsMixin, UrlsMixin, UserInterfaceMixin

from . import PLUGIN_VERSION


class FlatBOMGenerator(ReportMixin, ScheduleMixin, SettingsMixin, UrlsMixin, UserInterfaceMixin, InvenTreePlugin):

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

    
    
    # Scheduled tasks (from ScheduleMixin)
    # Ref: https://docs.inventree.org/en/latest/plugins/mixins/schedule/
    SCHEDULED_TASKS = {
        # Define your scheduled tasks here...
    }
    
    # Plugin settings (from SettingsMixin)
    # Ref: https://docs.inventree.org/en/latest/plugins/mixins/settings/
    SETTINGS = {
        # Define your plugin settings here...
        'CUSTOM_VALUE': {
            'name': 'Custom Value',
            'description': 'A custom value',
            'validator': int,
            'default': 42,
        }
    }
    
    
    
    
    # Custom report context (from ReportMixin)
    # Ref: https://docs.inventree.org/en/latest/plugins/mixins/report/
    def add_label_context(self, label_instance, model_instance, request, context, **kwargs):
        """Add custom context data to a label rendering context."""
        
        # Add custom context data to the label rendering context
        context['foo'] = 'label_bar'

    def add_report_context(self, report_instance, model_instance, request, context, **kwargs):
        """Add custom context data to a report rendering context."""
        
        # Add custom context data to the report rendering context
        context['foo'] = 'report_bar'

    def report_callback(self, template, instance, report, request, **kwargs):
        """Callback function called after a report is generated."""
        ...
    
    # Custom URL endpoints (from UrlsMixin)
    # Ref: https://docs.inventree.org/en/latest/plugins/mixins/urls/
    def setup_urls(self):
        """Configure custom URL endpoints for this plugin."""
        from django.urls import path
        from .views import ExampleView

        return [
            # Provide path to a simple custom view - replace this with your own views
            path('example/', ExampleView.as_view(), name='example-view'),
        ]
    

    # User interface elements (from UserInterfaceMixin)
    # Ref: https://docs.inventree.org/en/latest/plugins/mixins/ui/
    
    # Custom UI panels
    def get_ui_panels(self, request, context: dict, **kwargs):
        """Return a list of custom panels to be rendered in the InvenTree user interface."""

        panels = []

        # Only display this panel for the 'part' target
        if context.get('target_model') == 'part':
            panels.append({
                'key': 'flat-bom-generator-panel',
                'title': 'Flat BOM Generator',
                'description': 'Custom panel description',
                'icon': 'ti:mood-smile:outline',
                'source': self.plugin_static_file('Panel.js:renderFlatBOMGeneratorPanel'),
                'context': {
                    # Provide additional context data to the panel
                    'settings': self.get_settings_dict(),
                    'foo': 'bar'
                }
            })
        
        return panels
    

    
