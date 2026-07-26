## Agent skills

- **Issue tracker:** Track issues/PRDs in GitHub. See `docs/agents/issue-tracker.md`.
- **Triage labels:** Use the five canonical labels. See `docs/agents/triage-labels.md`.
- **Domain docs:** Maintain one `CONTEXT.md` and `docs/adr/`. See `docs/agents/domain.md`.

## Plugin context

- This is the InvenTree Flat BOM Generator plugin.
- Purpose: flatten nested BOMs into a single-level, purchaseable-parts view with quantity aggregation, stock/allocation awareness, and production planning.
- Key docs: `README.md`, `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, `docs/decisions.md`.
- Backend package: `flat_bom_generator/`.
- Frontend: `frontend/src/` (React/TypeScript/Mantine).
- Tests: `flat_bom_generator/tests/unit/`, `flat_bom_generator/tests/integration/`, `frontend/` (Vitest/Playwright).
- Shared domain language also lives in the toolkit root `CONTEXT-MAP.md` and `C:\Software Projects\inventree-plugin-ai-toolkit\docs\reference\inventree-bom-build-buy-suite\`.
- When this plugin is opened inside the toolkit, the toolkit root `AGENTS.md` is also active for cross-plugin discipline.
