# All-instances aggregation for optional/consumable flags

**Status:** Accepted — migrated from DEC-006 (`docs/decisions.md`, Jan 2026), archived under `docs/archive/decisions.md`. **Amended 2026-11-11 (#30) — see Amendment section.**

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

## Amendment (ticket #30)

The flag collapse stays as decided, but it is no longer the only signal.
Each merged row now carries `optional_qty` -- the share of `total_qty`
contributed by optional-demand occurrences -- and the flag cell renders
`mixed (X opt / Y req)` when a row holds both. An occurrence counts as
optional when its own BOM line is optional OR any ancestor line on its
path was, so the partition equals exactly the demand the new
`include_optional` toggle (query param / INCLUDE_OPTIONAL_PARTS setting /
panel switch, all defaulting on) removes when switched off. `consumable`
is unchanged: all-instances collapse, no partition, outside the toggle's
scope. The partition and toggle add the complementary answer ("what must
I buy if we don't exercise the options?") without splitting rows.
