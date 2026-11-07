# Variant parts support is out of scope

**Status:** Accepted — migrated from DEC-008 (`docs/decisions.md`, Feb 2026), archived under `docs/archive/decisions.md`.

**Context:** InvenTree supports template parts (`is_template=True`) with
variants (`variant_of`) and a per-BomItem `allow_variants` flag that controls
whether variant stock counts toward the parent part's availability. Correctly
supporting this in the Flat BOM Generator would require tracking the
`allow_variants` flag separately through BOM traversal, deduplication, and all
stock/build-margin calculations.

**Decision:** Variant parts are explicitly out of scope. The plugin ignores
`allow_variants` and treats all parts as non-variant. The `allow_variants`
flag is excluded from the deduplication key.

**Alternatives considered:** Full implementation (8-10 hour estimate), partial
support (flag passthrough only, no stock changes), warning badge when
`allow_variants=True` is detected.

**Why this way:** The use case for this plugin (mechanical engineer doing
purchasing/build planning) does not require variant-aware stock aggregation.
Full implementation would interact with every stock column and the build margin
calculation, creating a large surface for subtle bugs. InvenTree's built-in BOM
view and build order system handles variants natively for users who need it.
The effort-to-value ratio is poor for this plugin's audience.
