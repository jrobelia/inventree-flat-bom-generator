# Archived Documentation

This folder contains completed planning documents that are no longer actively maintained but preserved for historical reference.

---

## Archive Organization

Documents are organized by completion date and feature area.

---

## Archived Projects

### 2026-01: Frontend Refactoring (Phase 6)

**Completed:** January 18, 2026  
**Duration:** ~8-12 hours  
**Outcome:** Panel.tsx reduced from 950 → 306 lines (68% reduction)

**Files:**
- [FRONTEND-REFACTORING-GUIDE.md](2026-01-frontend-refactoring/FRONTEND-REFACTORING-GUIDE.md) - Comprehensive step-by-step refactoring guide

**Key Achievements:**
- Extracted 5 custom hooks (useBuildQuantity, useColumnVisibility, useFlatBom, usePluginSettings, useShortfallCalculation)
- Extracted 5 components (ErrorAlert, WarningsAlert, StatisticsPanel, ControlBar, SettingsDrawer/SettingsPanel)
- Extracted column definitions to separate file (bomTableColumns.tsx)
- Clean architecture enabled faster feature development (Settings UI: 3-5 hrs vs estimated 8-10 hrs)

---

### 2026-01: Settings UI Implementation (Phase 7)

**Completed:** January 21, 2026  
**Duration:** ~3-5 hours  
**Outcome:** Moved 3 plugin settings from admin panel to frontend with progressive disclosure

**Files:**
- [SETTINGS-UI-IMPLEMENTATION-PLAN.md](2026-01-settings-ui/SETTINGS-UI-IMPLEMENTATION-PLAN.md) - Settings UI/UX design and implementation plan

**Key Achievements:**
- Maximum Traversal Depth, Expand Purchased Assemblies, Include Internal Fab in Cutlist moved to UI
- Progressive disclosure pattern (settings panel before first generation, drawer after)
- localStorage persistence for per-session settings
- "Show Cutlist Rows" frontend filter added
- All changes tested on staging server (v0.11.6-v0.11.18)

---

## Why Archive?

**Benefits:**
1. **Focus:** Keeps active docs/ focused on current priorities
2. **History:** Preserves "how did we do it?" for future similar work
3. **Clarity:** AI agents won't think incomplete work needs doing
4. **Standards:** Common practice in software development

**Archiving Criteria:**
- Feature/refactoring is complete and deployed
- Document is no longer referenced for active work
- No planned future changes to the documented feature
- Historical value only (reference for similar future work)

---

## Accessing Archives

All archived documents remain searchable in the repository and can be referenced via relative links from active documentation.

**Example Reference from ROADMAP.md:**
```markdown
✅ Frontend Refactoring (COMPLETE) - See [archive](internal/archive/2026-01-frontend-refactoring/FRONTEND-REFACTORING-GUIDE.md)
```

---

_Last Updated: January 21, 2026_
