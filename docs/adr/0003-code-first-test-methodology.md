# Code-first test methodology

**Status:** Accepted — migrated from DEC-003 (`docs/decisions.md`, Dec 2025), archived under `docs/archive/decisions.md`.

**Context:** Early test rewrites assumed how code *should* work. Several
tests passed but validated fantasy behavior. User caught it: "you are
doing it backwards."

**Decision:** Always read the implementation code first, trace real data
through it, then write tests that match actual behavior.

**Alternatives considered:** Strict TDD (write tests before reading code).

**Why this way:** When refactoring existing code, you need to understand
current behavior before asserting anything. TDD is better for greenfield
features. The full case study is preserved at
`docs/archive/TEST-WRITING-METHODOLOGY.md` (non-authoritative).
