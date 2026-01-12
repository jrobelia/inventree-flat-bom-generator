"""
Integration tests for warning generation in views.py.

Priority 3 (Warning Generation) - Tests view-level warning aggregation loop.
See TEST-PLAN.md for gap closure strategy.

BREAKTHROUGH: Uses programmatic fixture loading to bypass InvenTree Part.check_add_to_bom() validation.

Test Methodology:
- Load fixtures with warning scenarios (inactive parts, empty assemblies, unit mismatches)
- Call FlatBOMView endpoint with fixture data
- Verify warnings are collected and serialized correctly
- Test multiple warnings appearing together

Fixture Loading Pattern (IMPORTANT FOR FUTURE TESTS):
- Standard Django fixtures = ['name'] does NOT work for plugins (not in INSTALLED_APPS)
- Must use call_command('loaddata', absolute_path, verbosity=0) in setUpTestData
- Path calculation: Navigate up from test file to plugin root, then to fixtures/
- This pattern bypasses InvenTree's BOM validation and allows pre-validated test data
"""

import os
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework.test import APIRequestFactory, force_authenticate

from InvenTree.unit_test import InvenTreeTestCase
from part.models import Part

from flat_bom_generator.views import FlatBOMView

User = get_user_model()


class WarningGenerationTests(InvenTreeTestCase):
    """Tests for view-level warning aggregation loop (views.py lines 334-421)."""

    @classmethod
    def setUpTestData(cls):
        """Load fixtures with warning scenarios."""
        super().setUpTestData()

        # Create test user
        cls.user = User.objects.create_user(
            username='test_warning_generation_user',
            password='testpass',
            is_staff=True
        )

        # Load fixtures programmatically (standard fixtures = ['name'] doesn't work for plugins)
        # Calculate absolute path: 2 levels up from test file to tests folder
        test_file_path = Path(__file__)  # .../tests/integration/test_warning_generation.py
        tests_folder = test_file_path.parent.parent  # .../tests/
        fixture_path = tests_folder / 'fixtures' / 'warning_scenarios.yaml'

        if not fixture_path.exists():
            raise FileNotFoundError(f"Fixture not found: {fixture_path}")

        # Load fixture (bypasses InvenTree Part.check_add_to_bom validation)
        call_command('loaddata', str(fixture_path), verbosity=0)

    def setUp(self):
        """Set up each test."""
        self.factory = APIRequestFactory()
        self.view = FlatBOMView.as_view()

    def test_inactive_part_warning_generated(self):
        """
        Test that inactive_part warning is generated and serialized correctly.

        Fixture: Part 9101 (assembly) → Part 9102 (inactive component)
        Expected: 1 warning with type='inactive_part'
        """
        assembly = Part.objects.get(pk=9101)
        self.assertTrue(assembly.assembly, "Test part should be assembly")

        # Make API request
        request = self.factory.get(f'/fake-url/{assembly.pk}/')
        force_authenticate(request, user=self.user)
        response = self.view(request, part_id=assembly.pk)

        # Verify successful response
        self.assertEqual(response.status_code, 200)

        # Verify warnings present in metadata
        self.assertIn('metadata', response.data)
        self.assertIn('warnings', response.data['metadata'])
        warnings = response.data['metadata']['warnings']

        # Find inactive_part warning
        inactive_warnings = [w for w in warnings if w['type'] == 'inactive_part']
        self.assertEqual(len(inactive_warnings), 1, "Should have exactly 1 inactive_part warning")

        # Verify warning structure
        warning = inactive_warnings[0]
        self.assertEqual(warning['part_id'], 9102)
        self.assertIn('inactive', warning['message'].lower())
        self.assertIn('part_name', warning)

    def test_assembly_no_children_warning_generated(self):
        """
        Test that assembly_no_children warning is generated for empty assemblies.

        Fixture: Part 9103 (assembly) → Part 9104 (empty assembly with no BomItems)
        Expected: 1 warning with type='assembly_no_children'
        """
        assembly = Part.objects.get(pk=9103)

        # Make API request
        request = self.factory.get(f'/fake-url/{assembly.pk}/')
        force_authenticate(request, user=self.user)
        response = self.view(request, part_id=assembly.pk)

        # Verify successful response
        self.assertEqual(response.status_code, 200)

        # Verify warnings present in metadata
        self.assertIn('metadata', response.data)
        self.assertIn('warnings', response.data['metadata'])
        warnings = response.data['metadata']['warnings']

        # Find assembly_no_children warning
        empty_warnings = [w for w in warnings if w['type'] == 'assembly_no_children']
        self.assertEqual(len(empty_warnings), 1, "Should have exactly 1 assembly_no_children warning")

        # Verify warning structure
        warning = empty_warnings[0]
        self.assertEqual(warning['part_id'], 9104)
        self.assertIn('no BOM items', warning['message'])

    def test_unit_mismatch_warning_generated(self):
        """
        Test that unit_mismatch warning is generated for conflicting units.

        Fixture: Part 9105 (assembly) → Part 9106 (steel rod, units='m', note='1500mm')
        Expected: 1 warning with type='unit_mismatch'
        """
        assembly = Part.objects.get(pk=9105)

        # Make API request
        request = self.factory.get(f'/fake-url/{assembly.pk}/')
        force_authenticate(request, user=self.user)
        response = self.view(request, part_id=assembly.pk)

        # Verify successful response
        self.assertEqual(response.status_code, 200)

        # Verify warnings present in metadata
        self.assertIn('metadata', response.data)
        self.assertIn('warnings', response.data['metadata'])
        warnings = response.data['metadata']['warnings']

        # Find unit_mismatch warning
        unit_warnings = [w for w in warnings if w['type'] == 'unit_mismatch']
        self.assertEqual(len(unit_warnings), 1, "Should have exactly 1 unit_mismatch warning")

        # Verify warning structure
        warning = unit_warnings[0]
        self.assertEqual(warning['part_id'], 9106)
        # Check message references the unit conflict (contains both unit values)
        self.assertIn('mm', warning['message'].lower())
        self.assertIn('m', warning['message'].lower())

    def test_multiple_warnings_aggregated_correctly(self):
        """
        Test that multiple warning types are aggregated and returned together.

        Fixture: Part 9107 (assembly) with 3 children:
        - Part 9108: Inactive component
        - Part 9109: Empty assembly
        - Part 9110: Unit mismatch

        Expected: 3 warnings (1 of each type)
        """
        assembly = Part.objects.get(pk=9107)

        # Make API request
        request = self.factory.get(f'/fake-url/{assembly.pk}/')
        force_authenticate(request, user=self.user)
        response = self.view(request, part_id=assembly.pk)

        # Verify successful response
        self.assertEqual(response.status_code, 200)

        # Verify warnings present in metadata
        self.assertIn('metadata', response.data)
        self.assertIn('warnings', response.data['metadata'])
        warnings = response.data['metadata']['warnings']
        self.assertGreaterEqual(len(warnings), 3, "Should have at least 3 warnings")

        # Verify all 3 warning types present
        warning_types = [w['type'] for w in warnings]
        self.assertIn('inactive_part', warning_types)
        self.assertIn('assembly_no_children', warning_types)
        self.assertIn('unit_mismatch', warning_types)

        # Verify each warning has correct part_id
        inactive_warning = next(w for w in warnings if w['type'] == 'inactive_part')
        self.assertEqual(inactive_warning['part_id'], 9108)

        empty_warning = next(w for w in warnings if w['type'] == 'assembly_no_children')
        self.assertEqual(empty_warning['part_id'], 9109)

        unit_warning = next(w for w in warnings if w['type'] == 'unit_mismatch')
        self.assertEqual(unit_warning['part_id'], 9110)

    def test_no_warnings_for_clean_bom(self):
        """
        Test that no warnings are generated for valid BOM structure.

        Fixture: Part 9111 (assembly) → Part 9112 (active component, no issues)
        Expected: 0 warnings
        """
        assembly = Part.objects.get(pk=9111)

        # Make API request
        request = self.factory.get(f'/fake-url/{assembly.pk}/')
        force_authenticate(request, user=self.user)
        response = self.view(request, part_id=assembly.pk)

        # Verify successful response
        self.assertEqual(response.status_code, 200)

        # Verify no warnings in metadata
        self.assertIn('metadata', response.data)
        self.assertIn('warnings', response.data['metadata'])
        warnings = response.data['metadata']['warnings']
        self.assertEqual(len(warnings), 0, "Clean BOM should have 0 warnings")

    def test_warning_serialization_structure(self):
        """
        Test that warnings are serialized with correct structure per BOMWarningSerializer.

        Expected fields: type, part_id, part_name, message
        """
        assembly = Part.objects.get(pk=9101)  # Assembly with inactive component

        # Make API request
        request = self.factory.get(f'/fake-url/{assembly.pk}/')
        force_authenticate(request, user=self.user)
        response = self.view(request, part_id=assembly.pk)

        # Verify successful response
        self.assertEqual(response.status_code, 200)

        # Verify warning structure (warnings are nested in metadata)
        self.assertIn('metadata', response.data)
        self.assertIn('warnings', response.data['metadata'])
        warnings = response.data['metadata']['warnings']
        self.assertGreater(len(warnings), 0, "Should have at least 1 warning")

        # Check first warning has all required fields
        warning = warnings[0]
        self.assertIn('type', warning)
        self.assertIn('part_id', warning)
        self.assertIn('part_name', warning)
        self.assertIn('message', warning)

        # Verify field types
        self.assertIsInstance(warning['type'], str)
        self.assertIsInstance(warning['part_id'], int)
        self.assertIsInstance(warning['part_name'], str)
        self.assertIsInstance(warning['message'], str)

    def test_warnings_included_in_response_structure(self):
        """
        Test that warnings array is included in FlatBOMResponse structure.

        Expected response structure:
        {
            "part_id": int,
            "part_name": str,
            "ipn": str,
            "total_unique_parts": int,
            "total_imps_processed": int,
            "bom_items": list,
            "warnings": list  ← Verify this
        }
        """
        assembly = Part.objects.get(pk=9101)

        # Make API request
        request = self.factory.get(f'/fake-url/{assembly.pk}/')
        force_authenticate(request, user=self.user)
        response = self.view(request, part_id=assembly.pk)

        # Verify successful response
        self.assertEqual(response.status_code, 200)

        # Verify response structure
        self.assertIn('part_id', response.data)
        self.assertIn('part_name', response.data)
        self.assertIn('ipn', response.data)
        self.assertIn('total_unique_parts', response.data)
        self.assertIn('total_ifps_processed', response.data)  # Field name is 'ifps' not 'imps'
        self.assertIn('bom_items', response.data)
        self.assertIn('metadata', response.data)
        self.assertIn('warnings', response.data['metadata'])

        # Verify warnings is a list
        self.assertIsInstance(response.data['metadata']['warnings'], list)
