# Progressive disclosure for settings UI

**Status:** Accepted — migrated from DEC-005 (`docs/decisions.md`, Jan 2026), archived under `docs/archive/decisions.md`.

**Context:** 3 plugin settings were only accessible through the InvenTree
admin panel, which most users never open.

**Decision:** Surface settings in the frontend panel with progressive
disclosure (collapsed by default, expand on demand).

**Alternatives considered:** Always-visible settings bar, separate settings
page, modal dialog.

**Why this way:** Settings are rarely changed after initial setup. Keeping
them collapsed avoids visual clutter while making them discoverable.
