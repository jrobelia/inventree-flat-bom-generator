# All-instances aggregation for optional/consumable flags

**Status:** Accepted — migrated from DEC-006 (`docs/decisions.md`, Jan 2026), archived under `docs/archive/decisions.md`.

**Context:** A part can appear multiple times in a BOM tree -- sometimes
marked optional, sometimes not. How should the flat BOM represent this?

**Decision:** Flag = True only if ALL instances have the flag. If any
instance is required, the part shows as required.

**Alternatives considered:** Flag = True if ANY instance has it, separate
rows per flag state, majority-wins.

**Known limitation:** Mixed flags (3 optional + 2 required) lose the
distinction -- user sees "required" with no indication some paths are
optional. Splitting these rows is tracked as issue #30. ADR-0009 extends
the same all-instances idea from flags to per-line scalars.

**Why this way:** Safer default -- a production planner should not skip a
part that is required in at least one BOM path.
