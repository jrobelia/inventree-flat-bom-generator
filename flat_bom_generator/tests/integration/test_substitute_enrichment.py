"""
Integration tests for substitute part enrichment in FlatBOMView.

Tests verify that substitute parts are correctly queried from BomItemSubstitute
relationships, enriched with stock data, validated with SubstitutePartSerializer,
and included in API responses when SHOW_SUBSTITUTE_PARTS setting is enabled.

Test Coverage:
- Substitutes included when setting enabled
- Substitutes excluded when setting disabled
- Stock data accuracy for substitutes
- Parts without substitutes have null substitute_parts

Fixture-Based Testing:
This module uses Django fixtures loaded programmatically to bypass InvenTree's
Part.check_add_to_bom() validation which rejects dynamic BOM creation in tests.

Fixture: substitute_enrichment.yaml
- Assembly (pk=8001) → Primary part (pk=8002) with 2 substitutes (pk=8003, 8004)
- StockItems: Primary=50 (allocated=10), Sub1=100, Sub2=25
- BomItemSubstitute relationships linking substitutes to BomItem

Usage Pattern:
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        fixture_path = Path(__file__).parent.parent / 'fixtures' / 'substitute_enrichment.yaml'
        call_command('loaddata', str(fixture_path.absolute()), verbosity=0)
        cls.assembly = Part.objects.get(pk=8001)
        cls.primary_part = Part.objects.get(pk=8002)
"""

from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework.test import APIRequestFactory, force_authenticate

from InvenTree.unit_test import InvenTreeTestCase
from part.models import BomItem, Part, PartCategory

from flat_bom_generator.views import FlatBOMView

User = get_user_model()


class SubstituteEnrichmentTests(InvenTreeTestCase):
    """Integration tests for substitute part enrichment.
    
    Uses fixture-based approach to bypass InvenTree's Part.check_add_to_bom()
    validation which rejects dynamic BOM creation in tests.
    """

    @classmethod
    def setUpTestData(cls):
        """Load test data from fixture."""
        super().setUpTestData()

        # Load fixture programmatically (bypasses InvenTree validation)
        fixture_path = Path(__file__).parent.parent / 'fixtures' / 'substitute_enrichment.yaml'
        call_command('loaddata', str(fixture_path.absolute()), verbosity=0)

        # Get or create test user (avoid UNIQUE constraint conflict)
        cls.user, _ = User.objects.get_or_create(
            username='testuser',
            defaults={'password': 'testpass'}
        )

        # Get parts from fixture
        cls.assembly = Part.objects.get(pk=8001)
        cls.primary_part = Part.objects.get(pk=8002)
        cls.substitute1 = Part.objects.get(pk=8003)
        cls.substitute2 = Part.objects.get(pk=8004)

    def setUp(self):
        """Set up each test."""
        self.factory = APIRequestFactory()
        self.view = FlatBOMView.as_view()

    @patch('plugin.registry.registry')
    def test_substitutes_included_when_setting_enabled(self, mock_registry):
        """Test substitutes appear in API response when SHOW_SUBSTITUTE_PARTS=True."""
        # Create mock plugin with setting enabled
        mock_plugin = type('MockPlugin', (), {
            'get_setting': lambda self, key, default=None: {
                'SHOW_SUBSTITUTE_PARTS': True,
                'SHOW_PURCHASED_ASSEMBLIES': False,
                'ENABLE_INTERNAL_FAB_CUT_BREAKDOWN': False,
                'PRIMARY_INTERNAL_SUPPLIER': None,
                'ADDITIONAL_INTERNAL_SUPPLIERS': '',
                'FABRICATION_CATEGORY': None,
                'COMMERCIAL_CATEGORY': None,
                'CUT_TO_LENGTH_CATEGORY': None,
                'CUTLIST_UNITS_FOR_INTERNAL_FAB': 'mm',
            }.get(key, default)
        })()
        mock_registry.get_plugin.return_value = mock_plugin

        # Make API request
        request = self.factory.get(f'/api/plugin/flat-bom-generator/flat-bom/{self.assembly.pk}/')
        force_authenticate(request, user=self.user)
        response = self.view(request, part_id=self.assembly.pk)

        # Verify response structure
        self.assertEqual(response.status_code, 200)
        self.assertIn('bom_items', response.data)
        self.assertGreater(len(response.data['bom_items']), 0)

        # Find primary part in response
        primary_item = next(
            (item for item in response.data['bom_items'] if item['part_id'] == self.primary_part.pk),
            None
        )
        self.assertIsNotNone(primary_item, "Primary part not found in flat BOM")

        # Verify substitute fields exist
        self.assertIn('has_substitutes', primary_item)
        self.assertIn('substitute_parts', primary_item)

        # Verify has_substitutes flag
        self.assertTrue(primary_item['has_substitutes'])

        # Verify substitute_parts list
        self.assertIsNotNone(primary_item['substitute_parts'])
        self.assertEqual(len(primary_item['substitute_parts']), 2)

        # Verify substitute data structure (serialized by SubstitutePartSerializer)
        sub1_data = next(
            (sub for sub in primary_item['substitute_parts'] if sub['part_id'] == self.substitute1.pk),
            None
        )
        self.assertIsNotNone(sub1_data, "Substitute1 not found in substitute_parts list")

        # Verify all SubstitutePartSerializer fields present
        required_fields = [
            'substitute_id', 'part_id', 'ipn', 'part_name', 'full_name',
            'in_stock', 'on_order', 'allocated', 'available', 'link'
        ]
        for field in required_fields:
            self.assertIn(field, sub1_data, f"Field '{field}' missing from substitute data")

        # Verify stock values are correct
        self.assertEqual(sub1_data['in_stock'], 100.0)
        self.assertEqual(sub1_data['part_name'], 'Resistor 10k - Alt1')
        self.assertEqual(sub1_data['ipn'], 'R-10K-ALT1')

    @patch('plugin.registry.registry')
    def test_substitutes_excluded_when_setting_disabled(self, mock_registry):
        """Test substitutes NOT in response when SHOW_SUBSTITUTE_PARTS=False."""
        # Create mock plugin with setting disabled
        mock_plugin = type('MockPlugin', (), {
            'get_setting': lambda self, key, default=None: {
                'SHOW_SUBSTITUTE_PARTS': False,  # Setting disabled
                'SHOW_PURCHASED_ASSEMBLIES': False,
                'ENABLE_INTERNAL_FAB_CUT_BREAKDOWN': False,
                'PRIMARY_INTERNAL_SUPPLIER': None,
                'ADDITIONAL_INTERNAL_SUPPLIERS': '',
                'FABRICATION_CATEGORY': None,
                'COMMERCIAL_CATEGORY': None,
                'CUT_TO_LENGTH_CATEGORY': None,
                'CUTLIST_UNITS_FOR_INTERNAL_FAB': 'mm',
            }.get(key, default)
        })()
        mock_registry.get_plugin.return_value = mock_plugin

        # Make API request
        request = self.factory.get(f'/api/plugin/flat-bom-generator/flat-bom/{self.assembly.pk}/')
        force_authenticate(request, user=self.user)
        response = self.view(request, part_id=self.assembly.pk)

        # Verify response structure
        self.assertEqual(response.status_code, 200)

        # Find primary part
        primary_item = next(
            (item for item in response.data['bom_items'] if item['part_id'] == self.primary_part.pk),
            None
        )
        self.assertIsNotNone(primary_item)

        # Verify substitutes NOT included (or fields not set)
        # When setting disabled, fields should either be absent or have default False/None values
        has_subs = primary_item.get('has_substitutes', False)
        sub_parts = primary_item.get('substitute_parts', None)

        self.assertFalse(has_subs)
        self.assertIsNone(sub_parts)

    @patch('plugin.registry.registry')
    def test_substitute_stock_data_correct(self, mock_registry):
        """Test substitute stock values match Part model calculations."""
        # Create mock plugin with setting enabled
        mock_plugin = type('MockPlugin', (), {
            'get_setting': lambda self, key, default=None: {
                'SHOW_SUBSTITUTE_PARTS': True,
                'SHOW_PURCHASED_ASSEMBLIES': False,
                'ENABLE_INTERNAL_FAB_CUT_BREAKDOWN': False,
                'PRIMARY_INTERNAL_SUPPLIER': None,
                'ADDITIONAL_INTERNAL_SUPPLIERS': '',
                'FABRICATION_CATEGORY': None,
                'COMMERCIAL_CATEGORY': None,
                'CUT_TO_LENGTH_CATEGORY': None,
                'CUTLIST_UNITS_FOR_INTERNAL_FAB': 'mm',
            }.get(key, default)
        })()
        mock_registry.get_plugin.return_value = mock_plugin

        # Make API request
        request = self.factory.get(f'/api/plugin/flat-bom-generator/flat-bom/{self.assembly.pk}/')
        force_authenticate(request, user=self.user)
        response = self.view(request, part_id=self.assembly.pk)

        # Get primary part item
        primary_item = next(
            (item for item in response.data['bom_items'] if item['part_id'] == self.primary_part.pk),
            None
        )

        # Get substitutes from response
        sub1_data = next(
            (sub for sub in primary_item['substitute_parts'] if sub['part_id'] == self.substitute1.pk),
            None
        )
        sub2_data = next(
            (sub for sub in primary_item['substitute_parts'] if sub['part_id'] == self.substitute2.pk),
            None
        )

        # Verify substitute1 stock values
        self.assertEqual(sub1_data['in_stock'], 100.0, "Substitute1 in_stock incorrect")
        self.assertEqual(sub1_data['available'], 100.0, "Substitute1 available incorrect (no allocations)")

        # Verify substitute2 stock values
        self.assertEqual(sub2_data['in_stock'], 25.0, "Substitute2 in_stock incorrect")
        self.assertEqual(sub2_data['available'], 25.0, "Substitute2 available incorrect (no allocations)")

    @patch('plugin.registry.registry')
    def test_part_without_substitutes_has_null_substitute_parts(self, mock_registry):
        """Test parts with no substitutes have has_substitutes=False and substitute_parts=None."""
        # Get category from fixture
        test_cat = PartCategory.objects.get(pk=8001)
        
        # Create a second BOM item without substitutes
        part_no_subs = Part.objects.create(
            name='Capacitor 100uF',
            description='Part with no substitutes',
            category=test_cat,
            component=True,
            active=True,
            IPN='C-100UF',
            units='pcs'
        )

        BomItem.objects.create(
            part=self.assembly,
            sub_part=part_no_subs,
            quantity=5,
            validated=True
        )

        # Create mock plugin with setting enabled
        mock_plugin = type('MockPlugin', (), {
            'get_setting': lambda self, key, default=None: {
                'SHOW_SUBSTITUTE_PARTS': True,
                'SHOW_PURCHASED_ASSEMBLIES': False,
                'ENABLE_INTERNAL_FAB_CUT_BREAKDOWN': False,
                'PRIMARY_INTERNAL_SUPPLIER': None,
                'ADDITIONAL_INTERNAL_SUPPLIERS': '',
                'FABRICATION_CATEGORY': None,
                'COMMERCIAL_CATEGORY': None,
                'CUT_TO_LENGTH_CATEGORY': None,
                'CUTLIST_UNITS_FOR_INTERNAL_FAB': 'mm',
            }.get(key, default)
        })()
        mock_registry.get_plugin.return_value = mock_plugin

        # Make API request
        request = self.factory.get(f'/api/plugin/flat-bom-generator/flat-bom/{self.assembly.pk}/')
        force_authenticate(request, user=self.user)
        response = self.view(request, part_id=self.assembly.pk)

        # Find part without substitutes
        part_item = next(
            (item for item in response.data['bom_items'] if item['part_id'] == part_no_subs.pk),
            None
        )
        self.assertIsNotNone(part_item)

        # Verify substitute fields have expected null/false values
        self.assertFalse(part_item.get('has_substitutes', False))
        self.assertIsNone(part_item.get('substitute_parts'))
