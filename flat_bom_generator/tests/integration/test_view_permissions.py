"""Integration tests for FlatBOMView role-based permission enforcement.

InvenTree 1.4.0 split BOM permissions into a dedicated 'bom' ruleset.
FlatBOMView requires role_required='bom' via InvenTree RolePermission:
GET maps to the 'view' permission.

What We Test:
- A user with the 'bom' view permission gets HTTP 200
- A user with no roles gets HTTP 403
- A user with 'part' view but no 'bom' view gets HTTP 403
  (the bom ruleset is separate from the part ruleset)
- An unauthenticated request gets HTTP 401
  (DRF raises NotAuthenticated when no authenticator succeeded)

DRF Testing Pattern:
- APIRequestFactory + force_authenticate, view invoked via as_view()
  so dispatch() runs the permission checks (unlike direct .get() calls)

Run:
    invoke dev.test -r FlatBOMGenerator.flat_bom_generator.tests.integration.test_view_permissions -v
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIRequestFactory, force_authenticate

from InvenTree.unit_test import InvenTreeTestCase
from part.models import BomItem, Part, PartCategory
from plugin.registry import registry

from flat_bom_generator.views import FlatBOMView

User = get_user_model()


class FlatBOMViewPermissionTests(InvenTreeTestCase):
    """Permission tests for FlatBOMView.get() via full DRF dispatch.

    cls.user (created by InvenTreeTestCase) is granted 'bom.view' via its
    group, matching a deployment user whose role includes BOM access.
    """

    @classmethod
    def setUpTestData(cls):
        """Create test data once for all tests.

        Grants cls.user the 'bom' view ruleset required by FlatBOMView,
        and creates users without it for the negative cases.
        """
        super().setUpTestData()

        # Activate the plugin so registry.get_plugin() resolves it
        registry.set_plugin_state('flat-bom-generator', True)

        # cls.user (from InvenTreeTestCase) is already a member of cls.group
        cls.user.groups.add(cls.group)
        cls.assignRole('bom.view')

        # A user with no roles at all
        cls.no_role_user = User.objects.create_user(
            username='flatbom_no_role_user',
            password='testpass',
        )

        # A user whose group has 'part' view but not 'bom' view —
        # the discriminating case: BOM access is a separate ruleset
        cls.part_only_user = User.objects.create_user(
            username='flatbom_part_only_user',
            password='testpass',
        )
        cls.part_only_group = Group.objects.create(name='flatbom_part_only')
        cls.part_only_user.groups.add(cls.part_only_group)
        cls.assignRole('part.view', group=cls.part_only_group)

        # Minimal assembly with one BOM line
        cls.test_cat = PartCategory.objects.create(
            name='Permission Test Category',
            description='Category for permission tests',
        )
        cls.assembly = Part.objects.create(
            name='Permission Test Assembly',
            IPN='PERM-ASM-001',
            category=cls.test_cat,
            description='Assembly for permission tests',
            active=True,
            assembly=True,
            is_template=False,
        )
        cls.component = Part.objects.create(
            name='Permission Test Component',
            IPN='PERM-CMP-001',
            category=cls.test_cat,
            description='Component for permission tests',
            active=True,
            purchaseable=True,
            is_template=False,
        )
        BomItem.objects.create(
            part=cls.assembly,
            sub_part=cls.component,
            raw_amount='2',
            reference='P1',
        )

    def setUp(self):
        """Set up request factory and view callable for each test."""
        self.factory = APIRequestFactory()
        self.view = FlatBOMView.as_view()

    def test_user_with_bom_view_permission_gets_200(self):
        """A user with the 'bom' view permission gets HTTP 200."""
        request = self.factory.get(
            f'/api/plugin/flat-bom-generator/flat-bom/{self.assembly.pk}/'
        )
        force_authenticate(request, user=self.user)
        response = self.view(request, part_id=self.assembly.pk)

        self.assertEqual(response.status_code, 200)
        self.assertIn('bom_items', response.data)

    def test_user_without_bom_role_gets_403(self):
        """A user with no roles gets HTTP 403."""
        request = self.factory.get(
            f'/api/plugin/flat-bom-generator/flat-bom/{self.assembly.pk}/'
        )
        force_authenticate(request, user=self.no_role_user)
        response = self.view(request, part_id=self.assembly.pk)

        self.assertEqual(response.status_code, 403)

    def test_user_with_part_view_but_no_bom_gets_403(self):
        """A user with 'part' view but no 'bom' view gets HTTP 403.

        Since InvenTree 1.4.0 the bom ruleset is separate from part;
        part-level access alone must not open the flat BOM endpoint.
        """
        request = self.factory.get(
            f'/api/plugin/flat-bom-generator/flat-bom/{self.assembly.pk}/'
        )
        force_authenticate(request, user=self.part_only_user)
        response = self.view(request, part_id=self.assembly.pk)

        self.assertEqual(response.status_code, 403)

    def test_anonymous_request_gets_401(self):
        """An unauthenticated request gets HTTP 401.

        DRF's permission_denied raises NotAuthenticated (401) rather than
        PermissionDenied (403) when the request has no successful
        authenticator; the ticket's 403 criterion covers authenticated users.
        """
        request = self.factory.get(
            f'/api/plugin/flat-bom-generator/flat-bom/{self.assembly.pk}/'
        )
        response = self.view(request, part_id=self.assembly.pk)

        self.assertEqual(response.status_code, 401)
