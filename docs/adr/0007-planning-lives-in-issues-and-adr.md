# Planning lives in GitHub issues; decisions live in docs/adr/

**Status:** Accepted (issue #11, Nov 2026) — supersedes DEC-007
(`docs/decisions.md`, Feb 2026), archived under `docs/archive/decisions.md`.

**Context:** DEC-007 organized `docs/` into `reference/` (how things work),
`planning/` (future work proposals), and a **gitignored** `archive/`, with
three living docs (`ROADMAP.md`, `ARCHITECTURE.md`, `decisions.md`) at the
`docs/` root. That mirrored the toolkit's transitional model — which the
toolkit itself retired (toolkit ADR-0006): the living docs duplicated
GitHub issues and decisions, and went stale between updates.

**Decision:** Knowledge lives where it stays true:

- `README.md` — durable product direction and user-facing documentation.
- GitHub issues — every planned or proposed work item, priority, and status.
- `docs/adr/` — accepted decisions meeting the ADR threshold
  (hard to reverse, surprising, real trade-off).
- `docs/reference/` — current operational facts (architecture, deployment,
  warning-system patterns).
- `docs/archive/` — non-authoritative history, **committed** rather than
  gitignored so the record is visible and reviewable.
- `docs/internal/` — local-only scratch, still gitignored.

The retired living docs and the `planning/` folder moved to
`docs/archive/` under #11; `decisions.md` entries meeting the threshold
became ADR-0001 through ADR-0009 (this file being 0007).

**Alternatives considered:** Keep the three living docs (rejected — this
ADR records that retirement); keep DEC-007's gitignored archive (rejected —
an invisible archive cannot serve as evidence or hold the retired docs the
migration commits there).

**Why this way:** The retired docs each duplicated a better owner — roadmap
items are issues, decisions are ADRs, operational facts are reference docs —
and recreating a living roadmap or monolithic architecture doc under
another name is a regression, not a simplification.
