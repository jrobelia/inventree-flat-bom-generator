"""API serializers for the FlatBOMGenerator plugin.

Serializers transform complex data (Django models) to JSON-compatible formats,
define the API contract, and handle validation.

Ref: https://www.django-rest-framework.org/api-guide/serializers/
"""

from rest_framework import serializers


class BOMWarningSerializer(serializers.Serializer):
    """Serializes BOM warning messages for consistent API output.

    Warnings alert users to potential BOM issues that may affect production:
    - Unit mismatches between BOM notes and part definitions
    - Inactive parts that may not be available
    - Assembly parts with no BOM items defined
    - BOM traversal stopped by maximum depth setting

    All warnings include type, part identification, and user-facing message.
    """

    type = serializers.CharField(
        required=True,
        help_text="Warning category: unit_mismatch, inactive_part, assembly_no_children, max_depth_reached",
    )

    part_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Part ID associated with warning (None for summary warnings)",
    )

    part_name = serializers.CharField(
        required=True, help_text="Human-readable part name or summary description"
    )

    message = serializers.CharField(
        required=True, help_text="User-facing warning message explaining the issue"
    )

    class Meta:
        """Meta options for this serializer."""

        fields = ["type", "part_id", "part_name", "message"]
