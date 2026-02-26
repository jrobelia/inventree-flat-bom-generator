# FlatBOMGenerator -- Decision Log

Append-only. Newest entries at the bottom. Record non-obvious choices so
future-you (or an AI agent) understands *why*, not just *what*.

---

## Template

```
### DEC-NNN -- Short title (YYYY-MM-DD)
**Context:** What situation prompted this decision?
**Decision:** What was chosen?
**Alternatives considered:** What else was on the table?
**Why this way:** The deciding factor.
```

---

## Decisions

### DEC-001 -- Fixture-based integration testing (Jan 2026)
**Context:** Django model validation rejects programmatic test data that
would be valid in a real InvenTree database (e.g., Part objects without
all required related objects).
**Decision:** Use fixture JSON files loaded directly into the test database,
bypassing Django model validation entirely.
**Alternatives considered:** Factory Boy factories, raw SQL, mocking ORM calls.
**Why this way:** Fixtures let us represent real InvenTree data shapes
(including edge cases) without fighting Django's validation layer. Factory
Boy would still hit the same validators.

### DEC-002 -- DRF serializers for all API responses (Dec 2025)
**Context:** Views originally returned hand-built dicts. This made it hard
to validate response shape and easy to introduce inconsistencies.
**Decision:** BOMWarningSerializer, FlatBOMItemSerializer, and
FlatBOMResponseSerializer wrap every API response.
**Alternatives considered:** Keep raw dicts, use Pydantic, use dataclasses.
**Why this way:** DRF serializers are the Django-native pattern, give
automatic validation/coercion, and generate browsable API docs. Found 2
bugs during the serializer migration, proving the value immediately.

### DEC-003 -- Code-first test methodology (Dec 2025)
**Context:** Early test rewrites assumed how code *should* work. Several
tests passed but validated fantasy behavior. User caught it: "you are
doing it backwards."
**Decision:** Always read the implementation code first, trace real data
through it, then write tests that match actual behavior.
**Alternatives considered:** Strict TDD (write tests before reading code).
**Why this way:** When refactoring existing code, you need to understand
current behavior before asserting anything. TDD is better for greenfield
features. Documented in
[TEST-WRITING-METHODOLOGY.md](reference/TEST-WRITING-METHODOLOGY.md).

### DEC-004 -- Frontend component extraction over monolith (Jan 2026)
**Context:** Panel.tsx grew to 950+ lines -- hard to navigate, hard to test,
hard to modify without side effects.
**Decision:** Extract into 5 focused components + 5 custom hooks. Panel.tsx
became a thin orchestrator (306 lines).
**Alternatives considered:** Keep monolith with better comments, full rewrite
using InvenTree core patterns.
**Why this way:** Incremental extraction preserves working behavior while
making each piece independently understandable. Full rewrite was too risky
with no frontend test coverage.

### DEC-005 -- Progressive disclosure for settings UI (Jan 2026)
**Context:** 3 plugin settings were only accessible through the InvenTree
admin panel, which most users never open.
**Decision:** Surface settings in the frontend panel with progressive
disclosure (collapsed by default, expand on demand).
**Alternatives considered:** Always-visible settings bar, separate settings
page, modal dialog.
**Why this way:** Settings are rarely changed after initial setup. Keeping
them collapsed avoids visual clutter while making them discoverable.

### DEC-006 -- Smart flag aggregation for optional/consumable (Jan 2026)
**Context:** A part can appear multiple times in a BOM tree -- sometimes
marked optional, sometimes not. How should the flat BOM represent this?
**Decision:** Flag = True only if ALL instances have the flag. If any
instance is required, the part shows as required.
**Alternatives considered:** Flag = True if ANY instance has it, separate
rows per flag state, majority-wins.
**Known limitation:** Mixed flags (3 optional + 2 required) lose the
distinction -- user sees "required" with no indication some paths are
optional.
**Why this way:** Safer default -- a production planner should not skip a
part that is required in at least one BOM path.

### DEC-007 -- docs/ subfolder structure: reference, planning, archive (Feb 2026)
**Context:** Plugin docs folder had grown flat with a mix of how-to guides,
future plans, and superseded documents. Hard to tell what's current.
**Decision:** Organize into `reference/` (stable how-to guides),
`planning/` (future work proposals), and `archive/` (gitignored, superseded).
Living docs (ROADMAP, ARCHITECTURE, decisions) stay at `docs/` root.
**Alternatives considered:** Keep flat, use only archive/ for cleanup.
**Why this way:** Mirrors the toolkit-level pattern. Separating reference
from planning makes it obvious whether a doc describes how things *are*
versus how they *might be*.
