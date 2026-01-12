"""
Integration tests for stock enrichment error handling in views.py.

Gap #6 (Stock Enrichment Error Handling) - Tests for Part.DoesNotExist during enrichment.
See TEST-PLAN.md for gap closure strategy.

Test Methodology:
- Tests verify view's error handling when Part model is deleted AFTER get_flat_bom but BEFORE enrichment
- Uses real Django models to simulate production scenario
- Validates that missing parts are logged and response continues with partial data
"""

import logging
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, force_authenticate

from company.models import Company
from InvenTree.unit_test import InvenTreeTestCase
from part.models import Part, PartCategory

from flat_bom_generator.views import FlatBOMView

User = get_user_model()


class StockEnrichmentErrorHandlingTests(InvenTreeTestCase):
    """Tests for Part.DoesNotExist exception handling during stock enrichment."""

    @classmethod
    def setUpTestData(cls):
        """Create test data once for all tests."""
        super().setUpTestData()

        # Create test user (unique username to avoid conflicts)
        cls.user = User.objects.create_user(
            username='test_stock_enrichment_user', 
            password='testpass',
            is_staff=True
        )

        # Create test category
        cls.test_cat = PartCategory.objects.create(
            name='Electronics',
            description='Electronic components'
        )

        # Create test company
        cls.test_company = Company.objects.create(
            name='Test Supplier',
            is_supplier=True
        )

        # Create assembly part (will be used in get_flat_bom mock)
        cls.assembly = Part.objects.create(
            name='Test Assembly',
            description='Assembly for testing',
            category=cls.test_cat,
            assembly=True,
            active=True
        )

    def setUp(self):
        """Set up each test."""
        self.factory = APIRequestFactory()
        self.view = FlatBOMView.as_view()

    @patch('flat_bom_generator.views.get_flat_bom')
    def test_part_deleted_between_get_flat_bom_and_enrichment(self, mock_get_flat_bom):
        """
        Test that view handles Part.DoesNotExist gracefully when part is deleted
        between get_flat_bom call and enrichment loop.
        
        Scenario:
        1. get_flat_bom returns valid part_id
        2. Part is deleted (or ID is invalid)
        3. Enrichment loop tries to fetch Part
        4. Part.DoesNotExist is raised
        5. View logs warning and continues with original item data
        """
        # Create a part to use in mock (will simulate deletion by using non-existent ID)
        nonexistent_part_id = 999999

        # Mock get_flat_bom to return BOM with non-existent part
        mock_get_flat_bom.return_value = (
            [
                {
                    'part_id': nonexistent_part_id,
                    'ipn': 'TEST-001',
                    'part_name': 'Deleted Part',
                    'description': 'Part that was deleted',
                    'part_type': 'Coml',
                    'total_qty': 10.0,
                    'unit': 'pcs',
                    'is_assembly': False,
                    'purchaseable': True,
                    'has_default_supplier': False,
                    'note': '',
                    'level': 1,
                }
            ],
            0,  # total_ifps_processed
            [],  # ctl_warnings
            0   # max_depth_reached
        )

        # Make request
        request = self.factory.get(f'/fake-url/{self.assembly.pk}/')
        force_authenticate(request, user=self.user)

        # Capture logs to verify warning message
        with self.assertLogs('inventree', level=logging.WARNING) as cm:
            response = self.view(request, part_id=self.assembly.pk)

        # Verify response is successful (doesn't raise exception)
        self.assertEqual(response.status_code, 200)

        # Verify warning was logged
        log_output = '\n'.join(cm.output)
        self.assertIn(f'Part {nonexistent_part_id} not found during enrichment', log_output)

        # Verify response includes the original item (without enrichment)
        response_data = response.data
        self.assertIn('bom_items', response_data)
        self.assertEqual(len(response_data['bom_items']), 1)

        # Verify item data is present (original data from get_flat_bom)
        item = response_data['bom_items'][0]
        self.assertEqual(item['part_id'], nonexistent_part_id)
        self.assertEqual(item['ipn'], 'TEST-001')
        self.assertEqual(item['part_name'], 'Deleted Part')

    @patch('flat_bom_generator.views.get_flat_bom')
    def test_multiple_parts_deleted_partial_enrichment(self, mock_get_flat_bom):
        """
        Test that view continues enriching remaining parts when some parts are missing.
        
        Scenario:
        1. get_flat_bom returns 3 parts
        2. Part 1: Valid (exists in database)
        3. Part 2: Invalid (doesn't exist)
        4. Part 3: Valid (exists in database)
        5. View enriches parts 1 and 3, logs warning for part 2, returns all 3
        """
        # Create valid parts
        part1 = Part.objects.create(
            name='Valid Part 1',
            description='This part exists',
            category=self.test_cat,
            assembly=False,
            active=True,
            purchaseable=True
        )

        part3 = Part.objects.create(
            name='Valid Part 3',
            description='This part also exists',
            category=self.test_cat,
            assembly=False,
            active=True,
            purchaseable=True
        )

        nonexistent_part_id = 888888

        # Mock get_flat_bom to return mix of valid and invalid parts
        mock_get_flat_bom.return_value = (
            [
                {
                    'part_id': part1.pk,
                    'ipn': 'VALID-001',
                    'part_name': part1.name,
                    'description': part1.description,
                    'part_type': 'Coml',
                    'total_qty': 5.0,
                    'unit': 'pcs',
                    'is_assembly': False,
                    'purchaseable': True,
                    'has_default_supplier': False,
                    'note': '',
                    'level': 1,
                },
                {
                    'part_id': nonexistent_part_id,
                    'ipn': 'MISSING-002',
                    'part_name': 'Missing Part',
                    'description': 'This part is missing',
                    'part_type': 'Coml',
                    'total_qty': 3.0,
                    'unit': 'pcs',
                    'is_assembly': False,
                    'purchaseable': True,
                    'has_default_supplier': False,
                    'note': '',
                    'level': 1,
                },
                {
                    'part_id': part3.pk,
                    'ipn': 'VALID-003',
                    'part_name': part3.name,
                    'description': part3.description,
                    'part_type': 'Coml',
                    'total_qty': 8.0,
                    'unit': 'pcs',
                    'is_assembly': False,
                    'purchaseable': True,
                    'has_default_supplier': False,
                    'note': '',
                    'level': 1,
                },
            ],
            0,  # total_ifps_processed
            [],  # ctl_warnings
            0   # max_depth_reached
        )

        # Make request
        request = self.factory.get(f'/fake-url/{self.assembly.pk}/')
        force_authenticate(request, user=self.user)

        # Capture logs
        with self.assertLogs('inventree', level=logging.WARNING) as cm:
            response = self.view(request, part_id=self.assembly.pk)

        # Verify response is successful
        self.assertEqual(response.status_code, 200)

        # Verify warning was logged for missing part only
        log_output = '\n'.join(cm.output)
        self.assertIn(f'Part {nonexistent_part_id} not found during enrichment', log_output)

        # Verify all 3 parts are in response
        response_data = response.data
        self.assertEqual(len(response_data['bom_items']), 3)

        # Verify part 1 was enriched (has stock fields)
        part1_item = next(item for item in response_data['bom_items'] if item['part_id'] == part1.pk)
        self.assertIn('in_stock', part1_item)
        self.assertIn('allocated', part1_item)
        self.assertIn('available', part1_item)
        self.assertIn('full_name', part1_item)

        # Verify part 2 was NOT enriched (original data only)
        part2_item = next(item for item in response_data['bom_items'] if item['part_id'] == nonexistent_part_id)
        self.assertEqual(part2_item['part_name'], 'Missing Part')
        # Should still have original data but may not have enriched fields

        # Verify part 3 was enriched
        part3_item = next(item for item in response_data['bom_items'] if item['part_id'] == part3.pk)
        self.assertIn('in_stock', part3_item)
        self.assertIn('allocated', part3_item)
        self.assertIn('available', part3_item)
        self.assertIn('full_name', part3_item)
