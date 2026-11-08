# Fixture-based integration testing

**Status:** Accepted — migrated from DEC-001 (`docs/decisions.md`, Jan 2026), archived under `docs/archive/decisions.md`.

**Context:** Django model validation rejects programmatic test data that
would be valid in a real InvenTree database (e.g., Part objects without
all required related objects).

**Decision:** Use fixture JSON files loaded directly into the test database,
bypassing Django model validation entirely.

**Alternatives considered:** Factory Boy factories, raw SQL, mocking ORM calls.

**Why this way:** Fixtures let us represent real InvenTree data shapes
(including edge cases) without fighting Django's validation layer. Factory
Boy would still hit the same validators.
