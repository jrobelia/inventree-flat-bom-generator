# Merged rows null disagreeing per-line scalars

**Status:** Accepted — migrated from DEC-009 (`docs/decisions.md`, Nov 2026), archived under `docs/archive/decisions.md`.

**Context:** The flat-BOM merge (`deduplicate_and_sum`) grouped occurrences of
the same part but displayed first-seen `piece_count` and `inherited_from`.
A merge of `500x4` + `500x2` rendered "Pieces: 4" beside a truthful
"500 x 6" cut-list row -- the scalar lied about its siblings.

**Decision:** Track every occurrence's `piece_count`/`inherited_from` during
the merge; emit the scalar only when the set is uniform, else null. The cut
list is unaffected (it aggregates by part+size, not by line scalar), and
single-occurrence rows are untouched. Extends the ADR-0006 all-instances
aggregation idea from flags to scalars.

**Alternatives considered:** First-seen wins (the bug), a "mixed" marker
string, splitting merged rows by scalar value.

**Why this way:** Maintainer ruling R-025 (adjudication of #14 R1-F10,
2026-11-05): blank is honest -- a planner must not read one occurrence's
count as the whole story. Null also feeds #24's CSV blank semantics.
