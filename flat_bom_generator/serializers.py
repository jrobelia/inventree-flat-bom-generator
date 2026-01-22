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


class FlatBOMItemSerializer(serializers.Serializer):
    """Serializes enriched flat BOM item data for frontend display.

    Combines data from BOM traversal (part_id, quantities, flags) with
    Part model fields (names, images, stock) for complete UI representation.

    Fields are organized into categories:
    - Core identifiers (part_id, ipn, part_name)
    - Quantities (total_qty, in_stock, allocated, on_order, available)
    - Display metadata (full_name, description, image, thumbnail, link)
    - Part properties (units, is_assembly, purchaseable, part_type)
    - BOM data (note, cut_list, internal_fab_cut_list)
    - Warning flags (assembly_no_children, max_depth_exceeded)
    """

    # Core identifiers
    part_id = serializers.IntegerField(
        required=True, help_text="InvenTree Part ID (primary key)"
    )

    ipn = serializers.CharField(
        required=True, allow_blank=True, help_text="Internal Part Number"
    )

    part_name = serializers.CharField(
        required=True, help_text="Short part name from Part model"
    )

    # Quantities
    total_qty = serializers.FloatField(
        required=True, help_text="Total quantity required (deduplicated and summed)"
    )

    in_stock = serializers.FloatField(
        required=True, help_text="Total stock available across all locations"
    )

    allocated = serializers.FloatField(
        required=True,
        help_text="Stock allocated to builds and sales orders (unavailable)",
    )

    on_order = serializers.FloatField(
        required=True, help_text="Stock on order from incomplete purchase orders"
    )

    available = serializers.FloatField(
        required=True, help_text="Stock available for use (in_stock - allocated)"
    )

    # Display metadata
    full_name = serializers.CharField(
        required=True, help_text="Full part name including IPN"
    )

    description = serializers.CharField(
        required=True, allow_blank=True, help_text="Part description"
    )

    image = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="Full-size part image URL (None if no image)",
    )

    thumbnail = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="Thumbnail image URL (None if no image)",
    )

    link = serializers.CharField(
        required=True, help_text="Relative URL to part detail page"
    )

    unit = serializers.CharField(
        required=True, allow_blank=True, help_text="Part unit (mm, pcs, etc.)"
    )

    # Part properties
    is_assembly = serializers.BooleanField(
        required=True, help_text="Whether part is an assembly"
    )

    purchaseable = serializers.BooleanField(
        required=True, help_text="Whether part can be purchased"
    )

    default_supplier_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Default supplier ID (None if no supplier)",
    )

    part_type = serializers.CharField(
        required=True,
        help_text="Categorized part type (TLA, Fab, Coml, Internal Fab, etc.)",
    )

    optional = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Whether part is optional in BOM (can be excluded from builds)",
    )

    consumable = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Whether part is consumable (not tracked in build orders)",
    )

    # BOM data
    note = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="BOM item notes (may contain cut-to-length specifications)",
    )

    cut_list = serializers.ListField(
        required=False,
        allow_null=True,
        child=serializers.DictField(),
        help_text="Cut-to-length breakdown for CtL parts (None if not applicable)",
    )

    internal_fab_cut_list = serializers.ListField(
        required=False,
        allow_null=True,
        child=serializers.DictField(),
        help_text="Internal Fab cut breakdown for Internal Fab parents (None if not applicable)",
    )

    # Warning flags
    assembly_no_children = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Assembly part has no BOM items defined (BOM structure issue)",
    )

    max_depth_exceeded = serializers.BooleanField(
        required=False,
        default=False,
        help_text="BOM traversal stopped at max depth (assembly not fully expanded)",
    )

    class Meta:
        """Meta options for this serializer."""

        fields = [
            # Core identifiers
            "part_id",
            "ipn",
            "part_name",
            # Quantities
            "total_qty",
            "in_stock",
            "allocated",
            "on_order",
            "available",
            # Display metadata
            "full_name",
            "description",
            "image",
            "thumbnail",
            "link",
            "unit",
            # Part properties
            "is_assembly",
            "purchaseable",
            "default_supplier_id",
            "part_type",
            "optional",
            "consumable",
            # BOM data
            "note",
            "cut_list",
            "internal_fab_cut_list",
            # Warning flags
            "assembly_no_children",
            "max_depth_exceeded",
        ]


class FlatBOMResponseSerializer(serializers.Serializer):
    """Serializes complete flat BOM API response structure.

    Wraps the entire API response including root part info, flattened BOM items,
    statistics, and warnings. This serializer defines the complete API contract
    and ensures consistent response structure.

    Response structure:
    {
        "part_id": 123,
        "part_name": "Assembly Name",
        "ipn": "ASM-001",
        "total_unique_parts": 45,
        "total_ifps_processed": 12,
        "max_depth_reached": 5,
        "bom_items": [...],  # List of FlatBOMItemSerializer
        "metadata": {
            "warnings": [...],  # List of BOMWarningSerializer
            "cutlist_units_for_ifab": "mm,in,cm"  # Units for Internal Fab cutlist display
        }
    }
    """

    # Root part identification
    part_id = serializers.IntegerField(
        required=True, help_text="Database ID of root part (top-level assembly)"
    )

    part_name = serializers.CharField(
        required=True, help_text="Name of root part (top-level assembly)"
    )

    ipn = serializers.CharField(
        required=True,
        allow_blank=True,
        help_text="Internal Part Number (IPN) of root part, empty string if not set",
    )

    # Statistics
    total_unique_parts = serializers.IntegerField(
        required=True,
        help_text="Count of unique leaf parts in flattened BOM (after deduplication)",
    )

    total_ifps_processed = serializers.IntegerField(
        required=True,
        help_text="Count of Internal Fab Parts (IFP) processed for cut list generation",
    )

    max_depth_reached = serializers.IntegerField(
        required=True, help_text="Maximum BOM depth reached during traversal"
    )

    # Flattened BOM data
    bom_items = FlatBOMItemSerializer(
        many=True,
        required=True,
        help_text="List of enriched flat BOM items (leaf parts only)",
    )

    # Metadata with warnings
    metadata = serializers.DictField(
        required=True,
        help_text="Additional response metadata including warnings and cutlist units",
    )

    def validate_metadata(self, value):
        """Validate metadata structure and warning serialization.

        Metadata must contain:
        - 'warnings': list of valid BOMWarningSerializer objects
        - Other keys: must have list values (not strings or other types)

        Raises:
            ValidationError: If warnings are invalid or values are wrong type
        """
        if not isinstance(value, dict):
            raise serializers.ValidationError("Metadata must be a dictionary")

        # Validate warnings list
        if "warnings" in value:
            warnings = value["warnings"]
            if not isinstance(warnings, list):
                raise serializers.ValidationError("metadata.warnings must be a list")

            # Validate each warning object
            for i, warning in enumerate(warnings):
                warning_serializer = BOMWarningSerializer(data=warning)
                if not warning_serializer.is_valid():
                    raise serializers.ValidationError(
                        f"Invalid warning at index {i}: {warning_serializer.errors}"
                    )

        # Validate other metadata values are lists
        for key, val in value.items():
            if key != "warnings" and not isinstance(val, list):
                raise serializers.ValidationError(
                    f"metadata.{key} must be a list, got {type(val).__name__}"
                )

        return value

    class Meta:
        """Meta options for this serializer."""

        fields = [
            "part_id",
            "part_name",
            "ipn",
            "total_unique_parts",
            "total_ifps_processed",
            "max_depth_reached",
            "bom_items",
            "metadata",
        ]
