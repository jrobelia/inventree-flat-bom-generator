# docs/archive — non-authoritative history

Everything in this directory is **retained for provenance only**. Nothing
here is authoritative — it describes how the plugin *was planned or
understood* at the time it was written, not what is true now.

Current sources of truth:

- **Planned and proposed work** → [GitHub issues](https://github.com/jrobelia/inventree-flat-bom-generator/issues)
- **Accepted decisions** → `docs/adr/` (ADR-0007 explains this ownership model)
- **Operational docs** → `docs/reference/` (`ARCHITECTURE.md`, `DEPLOYMENT-WORKFLOW.md`, `ARCHITECTURE-WARNINGS.md`)
- **User-facing docs** → `README.md`

## What's here

| File | Retired under | Was |
|---|---|---|
| `ROADMAP.md` | #11 (2026-11-07) | Living roadmap — open items migrated to issues #30–#39 |
| `ARCHITECTURE.md` | #11 | Living architecture guide — current content lives at `docs/reference/ARCHITECTURE.md` |
| `decisions.md` | #11 | Append-only decision log — DEC-001…009 migrated to `docs/adr/` 0001–0009 |
| `planning/` | #11 | Future-work proposals (9 docs) — open items migrated to issues #30–#40 |
| `TEST-WRITING-METHODOLOGY.md` | `d8d9b99` | Code-first test case study — deliberately archived earlier; still cited as background |

Do not edit files in this directory to "fix" them — the point of the
archive is that it is frozen. If a fact here is needed today, carry it into
a live document and cite this file as the source.
