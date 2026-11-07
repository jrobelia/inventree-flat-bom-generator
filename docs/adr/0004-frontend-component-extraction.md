# Frontend component extraction over monolith

**Status:** Accepted — migrated from DEC-004 (`docs/decisions.md`, Jan 2026), archived under `docs/archive/decisions.md`.

**Context:** Panel.tsx grew to 950+ lines -- hard to navigate, hard to test,
hard to modify without side effects.

**Decision:** Extract into focused components + custom hooks, organized as
`components/`, `hooks/`, `utils/`, `types/`, `columns/`. Panel.tsx
became a thin orchestrator (306 lines). New frontend work follows the same
folder structure instead of re-growing the monolith.

**Alternatives considered:** Keep monolith with better comments, full rewrite
using InvenTree core patterns.

**Why this way:** Incremental extraction preserves working behavior while
making each piece independently understandable. Full rewrite was too risky
with no frontend test coverage.
