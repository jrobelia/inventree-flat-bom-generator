# GitHub Copilot Instructions - FlatBOMGenerator Plugin

**Audience:** AI Agents (GitHub Copilot) | **Category:** Quick Reference | **Purpose:** Auto-discovered entry point for GitHub Copilot agents | **Last Updated:** 2025-12-15

**This file is automatically read by GitHub Copilot to provide context about this plugin.**

---

## Quick Start for AI Agents

When working in this plugin workspace, **always review these files first**:

1. **[ARCHITECTURE.md](../ARCHITECTURE.md)** - Plugin architecture, tech stack, API reference, development patterns
2. **[docs/internal/REFAC-PANEL-PLAN.md](../docs/internal/REFAC-PANEL-PLAN.md)** - Current refactoring status and plan
3. **[docs/internal/TEST-QUALITY-REVIEW.md](../docs/internal/TEST-QUALITY-REVIEW.md)** - Test quality analysis and improvement roadmap
4. **[flat_bom_generator/tests/TEST-PLAN.md](../flat_bom_generator/tests/TEST-PLAN.md)** - Testing strategy and execution guide

---

## Plugin Overview

**Type:** InvenTree UI Plugin with Custom API Endpoints  
**Purpose:** Advanced flat BOM analysis with stock tracking and production planning

**Key Features:**
- Recursive BOM flattening with deduplication
- Intelligent part categorization (TLA, FAB, COML, etc.)
- Stock availability and allocation tracking
- Shortfall calculation for production planning
- Warning system for BOM structure issues
- React/TypeScript frontend with Mantine UI

---

## Current Work Status

**Phase:** Serializer refactoring (Phase 2 complete)
- ✅ Phase 1: BOMWarningSerializer (4 fields)
- ✅ Phase 2: FlatBOMItemSerializer (24 fields)
- 📋 Phase 3: FlatBOMResponseSerializer (planned)

**Test Status:** 106 tests (105 passing, 1 skipped), grade C+

**Recent Changes:**
- Implemented Django REST Framework serializers for API responses
- Replaced manual dictionary construction with validated serializers
- Created comprehensive test suite (23 serializer tests)
- Production validated on staging server

See [docs/internal/REFAC-PANEL-PLAN.md](../docs/internal/REFAC-PANEL-PLAN.md) for detailed status.

---

## Documentation Organization

This plugin follows **single source of truth** principle:

**Each document has ONE focused purpose:**
- **ARCHITECTURE.md** → Plugin architecture, tech stack, API reference, patterns, backend/frontend structure
- **docs/TEST-PLAN.md** → Testing strategy, workflow, test-first approach, CI/CD
- **docs/TEST-QUALITY-REVIEW.md** → Test quality analysis, gaps, prioritized improvements
- **docs/REFAC-PANEL-PLAN.md** → What to refactor, how to refactor, current status, next steps
- **README.md** → User-facing: features, installation, usage

**Key Principles:**
- Link between docs instead of duplicating content
- Keep progress logs brief (3-5 lines per session, reference git commits)
- Reorganize when documents exceed 500 lines
- Focus on "what's next" rather than historical narrative

---

## Toolkit Context

For toolkit-level guidance (deployment, build commands, general patterns):

**In workspace root:**
- `.github/copilot-instructions.md` - Toolkit quick reference
- `copilot/PROJECT-CONTEXT.md` - Toolkit architecture and InvenTree patterns
- `copilot/AGENT-BEHAVIOR.md` - Communication style and code generation rules
- `docs/toolkit/WORKFLOWS.md` - How-to guides for common tasks
- `docs/toolkit/QUICK-REFERENCE.md` - Command cheat sheet

---

## Common Commands

**Testing:**
```powershell
# Run unit tests (fast, no database)
python -m unittest discover -s flat_bom_generator/tests/unit -v

# Run integration tests (requires InvenTree dev setup)
cd ..\..\inventree-dev\InvenTree
& .venv\Scripts\Activate.ps1
invoke dev.test -r FlatBOMGenerator.tests.integration -v

# Or use toolkit script (recommended)
cd ..\..  # Back to toolkit root
.\scripts\Test-Plugin.ps1 -Plugin "FlatBOMGenerator" -Unit
.\scripts\Test-Plugin.ps1 -Plugin "FlatBOMGenerator" -Integration
.\scripts\Test-Plugin.ps1 -Plugin "FlatBOMGenerator" -All
```

**Integration Testing Setup (one-time):**
```powershell
# From toolkit root
.\scripts\Setup-InvenTreeDev.ps1
.\scripts\Link-PluginToDev.ps1 -Plugin "FlatBOMGenerator"
```

**Build & Deploy:**
```powershell
# Build plugin (compiles frontend)
cd 'C:\PythonProjects\Inventree Plugin Creator\inventree-plugin-ai-toolkit'
.\scripts\Build-Plugin.ps1 -Plugin "FlatBOMGenerator"

# Deploy to staging
.\scripts\Deploy-Plugin.ps1 -Plugin "FlatBOMGenerator" -Server staging
```

**Development:**
```powershell
# Activate virtual environment
& ".venv\Scripts\Activate.ps1"

# Run frontend dev server
cd frontend
npm run dev
```

---

## Key Guidelines

### User Context
- User is a mechanical engineer with intermediate Python skills
- Learning software development patterns (test-first, refactoring)
- Prefers simple solutions over complex automation
- Values clear explanations and complete examples

### Communication
- Use plain English for software concepts
- Provide step-by-step instructions
- **No emoji in code** (use ASCII: `[INFO]`, `[OK]`, `[ERROR]`)
- Explain "why" not just "what"

### Code Generation
- Follow test-first workflow: write tests → implement → verify
- Use Django REST Framework serializers for API responses
- Add docstrings with examples
- Type hints on all functions
- Keep functions under 50 lines

### Testing
- Write tests for what you refactor, not just what's easy
- Test edge cases: None values, empty strings, wrong types
- All 106 tests should pass (1 known skip)
- Test quality matters more than test quantity

---

## Architecture Quick Reference

**Backend (Django REST Framework):**
- `core.py` - Main plugin class with mixins (SettingsMixin, UrlsMixin, UserInterfaceMixin)
- `views.py` - FlatBOMView API endpoint
- `serializers.py` - BOMWarningSerializer, FlatBOMItemSerializer
- `bom_traversal.py` - Core BOM algorithms (get_flat_bom, deduplicate_and_sum)
- `categorization.py` - Part type classification logic

**Frontend (React 19 + TypeScript + Mantine 8):**
- `frontend/src/Panel.tsx` - Main UI panel component
- `frontend/src/locale.tsx` - i18n translations
- Uses mantine-datatable for BOM display
- Vite 6 for build tooling

**Testing:**
- 106 tests across 9 test files
- Uses Django's unittest.TestCase
- Some tests use CSV data files in test_data/

See [ARCHITECTURE.md](../ARCHITECTURE.md) for complete architecture details.

---

## Critical Gaps & Priorities

**From TEST-QUALITY-REVIEW.md:**
- 🔴 **ZERO tests for views.py** (API endpoint completely untested)
- 🔴 **ZERO tests for core BOM traversal** (get_flat_bom, deduplicate_and_sum)
- ⚠️ 1 test skipped for months (test_piece_qty_times_count_rollup)
- ⚠️ Some tests validate stub functions, not real code

---

## Remember

This plugin is under active refactoring. Always:
1. Check if tests exist before refactoring
2. Evaluate test quality, not just quantity
3. Write/improve tests BEFORE refactoring
4. Keep documentation focused (single source of truth)
5. Update progress logs briefly (git has full details)

**Your goal:** Help make this plugin maintainable, well-tested, and production-ready while teaching software engineering best practices.

---

**Last Updated:** December 15, 2025  
**Plugin Version:** 0.9.2  
**InvenTree Compatibility:** 1.1.6+
