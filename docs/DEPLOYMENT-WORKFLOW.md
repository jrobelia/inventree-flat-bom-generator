# Deployment & Testing Workflow

**Purpose:** Checklist for deploying code changes safely  
**Audience:** Human developer + AI agents  
**Philosophy:** Test each change before stacking more changes

**Related Documentation:**
- [ROADMAP.md](ROADMAP.md) - Current refactoring status and priorities
- [TEST-PLAN.md](../../flat_bom_generator/tests/TEST-PLAN.md) - Testing strategy
- [TEST-WRITING-METHODOLOGY.md](TEST-WRITING-METHODOLOGY.md) - Code-first testing approach

---

## Before Starting Work

**Check Project State:**

```powershell
# 1. What's been deployed?
git log --oneline -10
# Look for version tags (e.g., v0.9.2) - that's last deployed version

# 2. What's uncommitted?
git status
# Any WIP files? Unfinished work?

# 3. What branch are we on?
git branch
# Should be refactor/flatbom-2025 for plugin work
```

**Questions to Answer:**
- What version is on staging/production servers?
- Is there uncommitted code? Is it working or broken?
- Are we building on verified code or unverified code?

---

## Pre-Deployment Checklist

**Before deploying ANY changes, verify:**

### Code-Test Synchronization

- [ ] **Frontend calculation changes?** If Panel.tsx shortfall calculation modified (lines 881-889), update `test_shortfall_calculation.py` to match
- [ ] **Serializer changes?** If serializer fields change, update corresponding tests
- [ ] **BOM traversal logic changes?** If `bom_traversal.py` modified, update integration tests

### Frontend-Backend Contracts

**Files with Synchronized Logic** (must stay in sync):

| Frontend File | Backend Test | Sync Point | Last Synced |
|--------------|--------------|------------|-------------|
| Panel.tsx (lines 881-889) | test_shortfall_calculation.py | Shortfall calculation | Jan 9, 2026 |

**Why this matters:**
- Frontend (TypeScript) and tests (Python) can't share code
- Logic is intentionally duplicated for fast testing
- Tests verify frontend behavior expectations
- Drift between files = bugs in production

**When updating synced files:**
1. Identify which files need sync (check table above)
2. Update frontend code
3. Update corresponding test
4. Run tests to verify logic matches
5. Update "Last Synced" date in table above
6. Commit both files together

---

## Workflow: Making Changes

### Step 1: Plan & Discuss

**Before writing code:**

1. **Explain the approach** - "We need to X because Y"
2. **Discuss trade-offs** - "Approach A is simpler, Approach B is more maintainable"
3. **Get approval** - Wait for "yes, do it" before proceeding
4. **Educational framing** - Help human understand WHY, not just WHAT

**Example:**
> "We need to add a serializer for the API response. This will:
> - Replace manual dict construction (200 lines → 50 lines)
> - Add type validation automatically
> - Make API contract explicit
>
> Trade-off: Requires learning DRF serializers, but that's industry standard.
> Should we proceed?"

---

### Step 2: Implement with Tests

**For refactoring existing code:**

```
1. Check if tests exist
2. Evaluate test quality
3. Improve/create tests FIRST
4. Refactor code
5. Verify tests pass
```

**For new features:**

```
1. Write test for expected behavior
2. Implement feature
3. Verify test passes
4. Add edge case tests
```

**Commit after each logical step:**
```powershell
git add <files>
git commit -m "feat: add X" -m "Explain WHY and WHAT changed"
```

---

### Step 3: Deploy & Verify

**CRITICAL: Don't stack unverified changes**

After implementing a feature/refactor:

```powershell
# 1. Build the plugin
cd 'C:\PythonProjects\Inventree Plugin Creator\inventree-plugin-ai-toolkit'
.\scripts\Build-Plugin.ps1 -Plugin "FlatBOMGenerator"

# 2. Deploy to staging
.\scripts\Deploy-Plugin.ps1 -Plugin "FlatBOMGenerator" -Server staging

# 3. Test in browser
# - Open staging server
# - Navigate to part with BOM
# - Click "Flat BOM" tab
# - Click "Generate Flat BOM"
# - Check browser console (F12) for errors
# - Verify data displays correctly
```

**Manual Test Checklist:**
- [ ] Panel loads without errors
- [ ] "Generate Flat BOM" button works
- [ ] Data displays in table
- [ ] Console shows no errors (F12 → Console)
- [ ] All columns populate correctly
- [ ] Pagination works
- [ ] Export CSV works

**If anything fails:**
- Fix it immediately
- Don't commit more changes on top of broken code
- Document what broke and why

---

## Workflow: Phase-Based Refactoring

**Example: Serializer refactoring (3 phases)**

### Phase 1: BOMWarningSerializer

```
1. Implement serializer
2. Write 7 tests
3. Commit: "feat: add BOMWarningSerializer"
4. Build → Deploy → Test on staging
5. Verify warnings still display correctly
6. ✅ Phase 1 complete and verified
```

### Phase 2: FlatBOMItemSerializer

```
1. Implement serializer
2. Write 16 tests
3. Commit: "feat: add FlatBOMItemSerializer"
4. Build → Deploy → Test on staging
5. Verify BOM items display correctly
6. ✅ Phase 2 complete and verified
```

### Phase 3: FlatBOMResponseSerializer

```
1. Implement serializer
2. Write 8 tests
3. Commit: "feat: add FlatBOMResponseSerializer"
4. Build → Deploy → Test on staging  ⬅️ **WE SKIPPED THIS**
5. Verify API response structure intact
6. ⚠️ Phase 3 NOT VERIFIED
```

**Lesson:** Always complete the verification step before moving to next phase.

---

## What Went Wrong: December 16, 2025

### The Mistake

**What happened:**
- Completed Phase 3 serializer (commit f9c6963)
- Committed code with tests passing
- Moved directly to "add integration tests" (critical priority #1)
- Created new test file without checking for existing tests
- Never deployed Phase 3 to verify it works on server

**Why it's a problem:**
- Phase 3 changes API response structure (nested serializers)
- If it breaks, we won't know until much later
- Stacking more changes on unverified code = compound errors
- User loses confidence in "tests passing" meaning "code works"

**What we should have done:**
1. After Phase 3 commit: Build → Deploy → Test
2. Verify API response in browser console
3. Test with real data (100+ BOM items)
4. Only then move to next priority

---

## Testing Philosophy

### Unit Tests (Fast)

**Purpose:** Test individual functions in isolation  
**When:** Every time you change a function  
**Run:** `.\scripts\Test-Plugin.ps1 -Plugin "FlatBOMGenerator" -Unit`

**What they DO test:**
- Pure function logic
- Serializer validation
- Calculation correctness
- Edge cases

**What they DON'T test:**
- API endpoints (plugin URLs not accessible in tests)
- Database interactions
- Frontend/backend integration
- Real InvenTree environment

### Integration Tests (Slower)

**Purpose:** Test with real InvenTree models  
**When:** After unit tests pass and before deployment  
**Run:** `.\scripts\Test-Plugin.ps1 -Plugin "FlatBOMGenerator" -Integration`

**What they DO test:**
- BOM traversal with real Part/BomItem objects
- Stock calculations with real StockItem objects
- Serializer output with real data
- Business logic end-to-end

**What they DON'T test:**
- HTTP layer (plugin URLs not accessible)
- URL routing
- Authentication
- Frontend UI

### Manual Testing (Essential)

**Purpose:** Verify actual user experience  
**When:** After every deployment  
**How:** Use the UI on staging server

**What only manual testing catches:**
- Frontend rendering issues
- API response format problems
- Browser compatibility issues
- Real-world performance with large datasets
- User workflow problems

**Truth:** A feature isn't done until it works in the browser.

---

## Quick Reference: Commands

```powershell
# Build plugin
.\scripts\Build-Plugin.ps1 -Plugin "FlatBOMGenerator"

# Deploy to staging
.\scripts\Deploy-Plugin.ps1 -Plugin "FlatBOMGenerator" -Server staging

# Run unit tests
.\scripts\Test-Plugin.ps1 -Plugin "FlatBOMGenerator" -Unit

# Run integration tests
.\scripts\Test-Plugin.ps1 -Plugin "FlatBOMGenerator" -Integration

# Check git history
git log --oneline -10

# Check uncommitted changes
git status

# Check current branch
git branch
```

---

## Recovery Plan: Current Situation

**Status (December 16, 2025):**
- ✅ Phase 1 & 2 serializers: Deployed and verified (v0.9.2)
- ⚠️ Phase 3 serializer: Committed but NOT deployed or tested
- ⚠️ test_view_function.py: WIP file that can't run (Django validation error)
- ⚠️ test_internal_fab_cut_rollup.py: Fixed but not committed

**Next Steps:**
1. **Commit the fixed test** (skipped test now works)
2. **Delete test_view_function.py** (duplicate of working tests)
3. **Deploy Phase 3 to staging** (verify serializers work)
4. **Manual test in browser** (verify API response structure)
5. **Document results** (did it work? any issues?)
6. **Then** move to next refactoring priority

---

## Remember

**Code isn't done until:**
- ✅ Tests pass
- ✅ Deployed to staging
- ✅ Manually tested in browser
- ✅ No errors in console
- ✅ User-facing features work correctly

**Avoid:**
- ❌ Assuming "tests pass" = "code works"
- ❌ Stacking changes without verification
- ❌ Creating duplicate code without checking for existing
- ❌ Moving fast without explaining or getting approval

**Philosophy:**
> "Slow is smooth, smooth is fast. One verified change is worth ten untested commits."

---

_Last Updated: December 16, 2025_
