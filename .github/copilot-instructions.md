# GitHub Copilot Instructions - FlatBOMGenerator Plugin

**Auto-discovered by GitHub Copilot. Last Updated: February 26, 2026**

---

## Before Starting Any Work

1. `git log --oneline -10` and `git status` -- know what's deployed and uncommitted
2. Read [docs/ROADMAP.md](../docs/ROADMAP.md) -- current status, next steps, what's done
3. Read [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) -- module map, API reference, patterns

**Other key docs (consult as needed):**
- [docs/reference/DEPLOYMENT-WORKFLOW.md](../docs/reference/DEPLOYMENT-WORKFLOW.md) -- deploy checklist
- [docs/reference/TEST-WRITING-METHODOLOGY.md](../docs/reference/TEST-WRITING-METHODOLOGY.md) -- code-first test approach
- [flat_bom_generator/tests/TEST-PLAN.md](../flat_bom_generator/tests/TEST-PLAN.md) -- test strategy
- [docs/decisions.md](../docs/decisions.md) -- append-only log of non-obvious choices

---

## Plugin Overview

**Type:** InvenTree UI Plugin (Django REST Framework backend + React/TypeScript/Mantine frontend)  
**Purpose:** Flat BOM analysis with stock tracking, substitute parts, and production planning

**Core capabilities:** Recursive BOM flattening with deduplication, part categorization (TLA/FAB/COML/etc.), stock/allocation/on-order tracking, shortfall calculation, substitute part display, cut-to-length support, warning system, CSV export.

---

## User Context and Communication

- User is a **mechanical engineer** learning software development patterns
- Prefers simple solutions and clear explanations over complex automation
- Explain "why" not just "what"; use plain English for software concepts
- No emoji in code (use ASCII: `[INFO]`, `[OK]`, `[ERROR]`)
- Manual testing on staging is a hard gate -- never assume tests alone prove it works
- Always deploy to staging and get user confirmation before committing

---

## Code Standards

- DRF serializers for all API responses
- Type hints on all functions; docstrings with examples
- Keep functions under 50 lines
- Test edge cases: None values, empty strings, wrong types
- Code-first test methodology: read the code THEN write tests
- Test quality matters more than quantity

---

## Commands

```powershell
# Tests (from toolkit root)
.\scripts\Test-Plugin.ps1 -Plugin "FlatBOMGenerator" -Unit
.\scripts\Test-Plugin.ps1 -Plugin "FlatBOMGenerator" -Integration
.\scripts\Test-Plugin.ps1 -Plugin "FlatBOMGenerator" -All

# Build and deploy
.\scripts\Build-Plugin.ps1 -Plugin "FlatBOMGenerator"
.\scripts\Deploy-Plugin.ps1 -Plugin "FlatBOMGenerator" -Server staging
```

---

## Documentation Principles

Single source of truth -- each doc has ONE purpose. Link, don't duplicate.
- **ARCHITECTURE.md** -- module map, tech stack, API reference
- **ROADMAP.md** -- status, next steps, completed work archive
- **decisions.md** -- append-only non-obvious choices
- **README.md** -- user-facing: features, installation, usage

Keep progress logs brief (3-5 lines, reference git commits).

---

**Plugin Version:** 0.11.51 | **InvenTree Compatibility:** 1.1.6+
