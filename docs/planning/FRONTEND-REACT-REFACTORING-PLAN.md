# Frontend Refactoring Plan: InvenTree Pattern Alignment

**Status:** Analysis Complete - Awaiting Decision  
**Created:** February 12, 2026  
**Priority:** LOW (Current implementation functional)

---

## Overview

This document outlines the technical work required to refactor the FlatBOMGenerator frontend to align with [InvenTree React Frontend patterns](https://docs.inventree.org/en/stable/develop/react-frontend/) as documented in `.github/instructions/frontend.react.instructions.md`.

**Key Question:** Should we invest 7-10 hours to align with InvenTree standards, or prioritize user-facing features?

---

## Current State Assessment

### ✅ What's Already Good

- **TypeScript with strict typing** - All interfaces defined, no `any` types
- **Mantine UI components** - Uses `Stack`, `Group`, `Paper` for layouts
- **Custom hooks** - Separation of concerns (`useFlatBom`, `usePluginSettings`)
- **i18n infrastructure** - `locale.tsx` setup, just not used
- **Loading/error states** - Handled with proper UI feedback
- **Component extraction** - Panel.tsx reduced from 1250 → 306 lines

### ⚠️ What Needs Refactoring

1. **API State Management** - Manual `useState` instead of React Query
2. **Internationalization** - Hard-coded English strings (~72 total)
3. **Loading States** - Inline styles instead of Mantine components
4. **Error Messages** - Not internationalized

---

## Refactoring Tasks

### Task 1: Migrate to React Query
**Priority:** MEDIUM | **Effort:** 4-6 hours | **Impact:** HIGH

#### Current Problem

**File:** `frontend/src/hooks/useFlatBom.ts`

```typescript
// Manual state management (lines 35-105)
const [loading, setLoading] = useState(false);
const [bomData, setBomData] = useState<FlatBomResponse | null>(null);
const [error, setError] = useState<string | null>(null);

const generateFlatBom = async (settings: PluginSettings) => {
  setLoading(true);
  setError(null);
  try {
    const response = await context.api.get(url, { timeout: 30000 });
    setBomData(response.data);
  } catch (err) {
    setError(err.message);
  } finally {
    setLoading(false);
  }
};
```

**Issues:**
- No caching - every generation makes fresh API call
- Manual error/loading state management
- No automatic refetch when dependencies change
- Inconsistent with InvenTree core patterns

#### Refactored Solution

```typescript
import { useQuery } from '@tanstack/react-query';

export function useFlatBom(
  partId: number | undefined,
  context: InvenTreePluginContext,
  settings: PluginSettings
) {
  return useQuery({
    queryKey: ['flatbom', partId, settings],  // Auto-refetch when settings change
    queryFn: async () => {
      if (!partId) throw new Error('No part ID available');
      
      // Build query params from settings
      const queryParams = new URLSearchParams();
      if (settings.maxDepth > 0) {
        queryParams.append('max_depth', settings.maxDepth.toString());
      }
      if (settings.expandPurchasedAssemblies) {
        queryParams.append('expand_purchased_assemblies', 'true');
      }
      if (settings.includeInternalFabInCutlist) {
        queryParams.append('include_internal_fab_in_cutlist', 'true');
      }
      queryParams.append(
        'include_substitutes',
        settings.includeSubstitutes ? 'true' : 'false'
      );
      
      const url = `/plugin/flat-bom-generator/flat-bom/${partId}/?${queryParams}`;
      const response = await context.api.get(url, { timeout: 30000 });
      return response.data as FlatBomResponse;
    },
    enabled: !!partId,
    refetchOnWindowFocus: false,
    staleTime: 30000  // Cache for 30 seconds
  });
}
```

#### Files to Change

1. **`frontend/src/hooks/useFlatBom.ts`** (REFACTOR)
   - Remove `useState` for loading/error/data
   - Remove manual `generateFlatBom` function
   - Return `{ data, isLoading, error, refetch }` from useQuery
   - Remove ~30 lines of boilerplate

2. **`frontend/src/Panel.tsx`** (UPDATE USAGE)
   ```typescript
   // BEFORE
   const { bomData, loading, error, generateFlatBom, clearError } = useFlatBom(
     partId,
     context
   );
   
   const handleGenerate = async () => {
     await generateFlatBom(settings);
   };
   
   // AFTER
   const { data: bomData, isLoading, error, refetch } = useFlatBom(
     partId,
     context,
     settings
   );
   
   const handleGenerate = () => {
     refetch();  // React Query handles everything
   };
   ```

#### Benefits

- ✅ **Automatic caching** - Toggling checkboxes doesn't refetch data
- ✅ **Automatic refetch** - Changing settings triggers new fetch
- ✅ **Built-in states** - No manual loading/error management
- ✅ **InvenTree consistency** - Matches core frontend patterns
- ✅ **Less code** - Remove ~30 lines of boilerplate

#### Testing Checklist

- [ ] Generate BOM on fresh load
- [ ] Change settings → Apply → Verify refetch
- [ ] Toggle checkboxes → Verify NO refetch (client-side filter)
- [ ] Click Refresh button → Verify refetch
- [ ] Error handling still works
- [ ] Loading spinner displays correctly
- [ ] All 151 tests still pass

---

### Task 2: Add Internationalization (i18n)
**Priority:** LOW | **Effort:** 2-3 hours | **Impact:** MEDIUM

#### Current Problem

All user-facing text is hard-coded English across 12 components (~72 strings total).

**Examples:**

```typescript
// SettingsPanel.tsx
<NumberInput label='Maximum Traversal Depth' />
<Switch
  label='Expand Purchased Assemblies'
  description='Include purchased assemblies in the flat BOM'
/>
<Button>Reset to Defaults</Button>

// ControlBar.tsx  
<Checkbox label='Show Cutlist Rows' />
<Checkbox label='Show Substitutes' />
<Button>Export to CSV</Button>

// Panel.tsx
<Button>Generate Flat BOM</Button>
<Alert>Click "Generate Flat BOM" to traverse the bill of materials...</Alert>
```

#### Refactored Solution

```typescript
import { t } from '@lingui/macro';

// SettingsPanel.tsx
<NumberInput label={t`Maximum Traversal Depth`} />
<Switch
  label={t`Expand Purchased Assemblies`}
  description={t`Include purchased assemblies in the flat BOM`}
/>
<Button>{t`Reset to Defaults`}</Button>

// ControlBar.tsx
<Checkbox label={t`Show Cutlist Rows`} />
<Checkbox label={t`Show Substitutes`} />
<Button>{t`Export to CSV`}</Button>

// Panel.tsx
<Button>{t`Generate Flat BOM`}</Button>
<Alert>{t`Click "Generate Flat BOM" to traverse the bill of materials...`}</Alert>
```

#### Implementation Steps

1. **Add import to each component:**
   ```typescript
   import { t } from '@lingui/macro';
   ```

2. **Wrap all string literals:**
   - Replace `'text'` with `` t`text` ``
   - Replace `"text"` with `` t`text` ``
   - For template literals: `` t`Total: ${count}` ``

3. **Extract translations:**
   ```bash
   cd frontend
   npm run extract
   ```

4. **Add English translations:**
   - Edit `frontend/src/locales/en/messages.po`
   - Translations auto-generated for English

#### Files to Change (12 files)

| File | String Count | Lines to Change |
|------|--------------|-----------------|
| `Panel.tsx` | ~10 | ~10 |
| `SettingsPanel.tsx` | ~15 | ~15 |
| `SettingsDrawer.tsx` | ~15 | ~15 |
| `ControlBar.tsx` | ~8 | ~8 |
| `StatisticsPanel.tsx` | ~10 | ~10 |
| `WarningsAlert.tsx` | ~8 | ~8 |
| `ErrorAlert.tsx` | ~2 | ~2 |
| `bomTableColumns.tsx` | ~25 | ~25 |
| `useFlatBom.ts` | ~6 | ~6 |
| `csvExport.ts` | ~25 | ~25 |
| **TOTAL** | **~124** | **~124** |

#### Benefits

- ✅ Enables translations for international users
- ✅ Consistent with InvenTree core patterns
- ✅ Professional localization support
- ⚠️ Minimal benefit for English-only deployments

#### Testing Checklist

- [ ] All UI text still displays correctly
- [ ] No TypeScript errors
- [ ] `npm run extract` generates translations
- [ ] English locale file created
- [ ] Plugin loads without errors

---

### Task 3: Improve Loading States
**Priority:** LOW | **Effort:** 1 hour | **Impact:** LOW

#### Current Code

```typescript
// Panel.tsx (lines 286-288)
{loading && (
  <div style={{ textAlign: 'center', padding: '2rem' }}>
    <Loader size='lg' />
  </div>
)}
```

#### Refactored Code

```typescript
import { Center, Loader, Alert } from '@mantine/core';
import { t } from '@lingui/macro';

{isLoading && (
  <Center h={200}>
    <Loader />
  </Center>
)}

{!bomData && !isLoading && (
  <Alert color="blue" title={t`No data`}>
    {t`Generate a BOM to see results.`}
  </Alert>
)}
```

#### Changes

- Replace inline styles with Mantine `Center` component
- Add explicit empty state message
- Use semantic height (`h={200}`)

#### Files to Change

- `frontend/src/Panel.tsx` (1 loading state)

---

### Task 4: Internationalize Error Messages
**Priority:** LOW | **Effort:** 30 minutes | **Impact:** LOW

#### Current Code

```typescript
// ErrorAlert.tsx
<Alert color="red" title="Error" onClose={onClose}>
  {error}
</Alert>
```

#### Refactored Code

```typescript
import { t } from '@lingui/macro';

<Alert color="red" title={t`Error`} onClose={onClose}>
  {error}
</Alert>
```

#### Files to Change

- `frontend/src/components/ErrorAlert.tsx`

---

## Tasks NOT Needed

### ✅ DataTable Pattern - Already Compliant

**Current implementation is correct:**

```typescript
<DataTable
  columns={columns}
  records={filteredAndSortedData}
  fetching={loading}
  sortStatus={sortStatus}
  onSortStatusChange={setSortStatus}
/>
```

**Checklist:**
- ✅ Uses `fetching` prop for loading overlay
- ✅ Implements sorting with state
- ✅ Right-aligns numeric columns
- ✅ Columns are sortable
- ✅ Uses `minWidth` with `cellsStyle`/`titleStyle` callbacks

**No changes needed.**

### ✅ Form Handling - Not Applicable

Plugin doesn't use form submission (only switches/inputs with direct `onChange` handlers). No need for Mantine `useForm` hook.

**No changes needed.**

---

## Summary

### Total Effort Estimate: 7-10 hours

| Task | Priority | Effort | Impact | Files | Status |
|------|----------|--------|--------|-------|--------|
| React Query migration | MEDIUM | 4-6 hrs | HIGH | 2 | Not Started |
| Add i18n (Lingui) | LOW | 2-3 hrs | MEDIUM | 12 | Not Started |
| Loading/empty states | LOW | 1 hr | LOW | 1 | Not Started |
| Error i18n | LOW | 30 min | LOW | 1 | Not Started |
| **TOTAL** | | **7.5-10.5 hrs** | | **16** | |

---

## Recommended Approach

### Option A: Phased Refactoring

**Phase 1: React Query (High Value)**
- **When:** When caching becomes performance issue
- **Effort:** 4-6 hours
- **Benefit:** Eliminate redundant API calls, better UX

**Phase 2: Internationalization (Optional)**
- **When:** If supporting non-English users
- **Effort:** 2-3 hours  
- **Benefit:** Professional localization support

**Phase 3: Minor Polish (Optional)**
- **When:** After Phase 1-2 complete
- **Effort:** 1.5 hours
- **Benefit:** Marginally better UI consistency

### Option B: Defer Indefinitely

**Current implementation is functional:**
- ✅ 150/151 tests passing
- ✅ All features working on production
- ✅ No user complaints about performance
- ✅ English-only deployment sufficient

**Higher priority tasks on roadmap:**
1. Variant parts support (user-requested feature)
2. Filter consolidation UX (scaling concern)
3. Export integration (replaces unmaintained code)

---

## Risk Assessment

### Low Risk Refactoring

- React Query is well-documented pattern
- i18n changes are additive (don't break existing code)
- Can deploy incrementally
- Each phase is independent and reversible

### Testing Requirements

After each phase:
- [ ] Generate BOM on fresh load
- [ ] Change settings and regenerate
- [ ] Toggle checkboxes (should not refetch)
- [ ] Refresh button works
- [ ] Error handling still works
- [ ] Loading states display correctly
- [ ] All 151 tests still pass
- [ ] Deploy to staging, verify in browser

### Rollback Plan

- **Phase 1:** Revert to manual state management (git history)
- **Phase 2:** Remove `` t`...` `` macro, restore string literals
- Each phase is independent and fully reversible

---

## Decision Framework

### Arguments FOR Refactoring

- ✅ React Query eliminates redundant API calls (performance)
- ✅ Aligns with InvenTree core patterns (consistency)
- ✅ Future-proofs for i18n requirements
- ✅ Cleaner code, less boilerplate

### Arguments AGAINST Refactoring

- ✅ Current code works reliably (150/151 tests passing)
- ✅ i18n not needed for English-only deployment
- ✅ 7-10 hours effort for marginal user-facing benefit
- ✅ Risk of introducing regressions
- ✅ Other roadmap items have higher business value

### Recommendation

**DEFER** pending:
1. User-reported performance issues with API calls
2. Request for non-English language support
3. InvenTree requirement for plugin approval
4. Completion of higher-priority roadmap items

Current implementation is **good enough** for production use.

---

## References

- [InvenTree React Frontend Docs](https://docs.inventree.org/en/stable/develop/react-frontend/)
- [Toolkit React Instructions](../../.github/instructions/frontend.react.instructions.md)
- [TanStack Query Docs](https://tanstack.com/query/latest/docs/react/overview)
- [Lingui i18n Docs](https://lingui.dev/tutorials/react)

---

**Last Updated:** February 12, 2026  
**Next Review:** After completing variant parts + filter consolidation
