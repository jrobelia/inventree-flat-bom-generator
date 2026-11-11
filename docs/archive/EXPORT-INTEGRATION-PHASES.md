# InvenTree Export Integration - Phased Implementation Plan

**Created:** January 19, 2026  
**Updated:** January 19, 2026  
**Status:** ⏸️ **ON HOLD** - Paused for other feature development  
**Approach:** Simple export endpoint (InvenTree standard pattern)  
**Decision:** No DataExportMixin - Use custom endpoint with tablib (simpler, fits use case)

---

## Project Overview

Replace client-side CSV generation with server-side export endpoint supporting multiple formats (CSV/JSON/XLSX). Leverage existing serializer refactoring work by reusing FlatBOMView logic.

**Estimated Time:** 3-4 hours total (2 phases)

---

## Critical Considerations Before Implementation

### 1. Dependencies ✅
**tablib is already in InvenTree** - Used by DataExportMixin system  
- No need to add to pyproject.toml  
- Safe to import directly
- ⚠️ Verify openpyxl available for XLSX support

### 2. Warnings in Export ⚠️
**Current plan doesn't include warnings in export file**

**Options:**
- **A. Add warnings as separate sheet** (XLSX only) - More complex
- **B. Add warnings section at top of file** - Works for CSV/JSON/XLSX
- **C. Skip warnings entirely** - Simpler, warnings visible in UI

**Recommendation:** Start with Option C (skip), add later if users request

### 3. Cutlist Parts 🔍 **CRITICAL**
**Must handle cutlist rows correctly**

Current CSV export behavior:
- Includes `is_cut_list_child` flag
- Includes `cut_length` and `cut_unit` fields
- Child rows NOT multiplied by buildQuantity (shows raw cut length)

**Export must preserve this behavior!** Test carefully with cutlist BOMs.

### 4. Column Selection 📊
**Current CSV exports 12 columns, but API response has more fields**

**Current CSV columns (12):**
```
IPN, Part Name, Description, Part Type, Total Qty, Unit,
Cut Length, Cut Unit, In Stock, Allocated, On Order, Build Margin
```

**Available in API but NOT currently exported:**
```
available, building, level, reference, note, image, 
thumbnail, link, default_supplier_name
```

**Decision:** Match current 12 columns first (less disruptive to users), expand later if requested

### 5. Build Quantity in Export 🔢 **NEEDS DECISION**
**Should export include buildQuantity calculations?**

**Current CSV behavior:**
- Multiplies `Total Qty` by buildQuantity (from frontend state)
- Calculates `Build Margin` based on buildQuantity

**Options:**
- **A. Export uses buildQuantity=1 always** - Raw BOM quantities (user multiplies in Excel)
- **B. Pass buildQuantity as query param** - Flexible but more complex
- **C. Calculate in frontend before calling export** - Matches current behavior

**Recommendation:** Option A (buildQuantity=1) - Export shows raw BOM, users can multiply in Excel

**Trade-offs:**
- ✅ Simpler backend (no query param handling)
- ✅ Export file is reusable (not tied to specific build qty)
- ❌ Breaks parity with current CSV export
- ❌ Users lose "Build Margin" calculated column

**Alternative (Option B):**
- Pass `?format=csv&build_qty=5` in URL
- Backend multiplies quantities before export
- Maintains current behavior
- More complex but better UX

### 6. Empty IPN Handling 📝
**Filename generation needs fallback**

```python
ipn = data.get('ipn', '') or f"Part_{part_id}"
date_str = datetime.now().strftime('%Y%m%d')
filename = f"FlatBOM_{ipn}_{date_str}.{extension}"
```

### 7. Format-Specific Considerations

**CSV:**
- ✅ Works great with tablib
- ✅ Excel auto-opens
- ⚠️ Loses type info (numbers become strings if formatted wrong)

**JSON:**
- ✅ Preserves types perfectly
- ✅ Easy to parse programmatically
- ❌ Not human-readable in text editor

**XLSX:**
- ✅ Preserves types and formatting
- ✅ Can add multiple sheets (future: warnings sheet)
- ⚠️ Larger file size
- ⚠️ Requires openpyxl library (verify InvenTree has it)

### 8. Testing Strategy ✅

**No unit tests planned** - Acceptable because:
- Simple view wrapper (reuses FlatBOMView)
- Tablib is well-tested library
- Manual testing sufficient for 3 formats

**Manual testing checklist:**
- ✅ All 3 formats download
- ✅ Filenames correct (IPN + date)
- ✅ Content matches current CSV export
- ✅ Special characters handled (commas, quotes, unicode)
- ✅ Large BOMs (100+ parts) work
- ✅ Cutlist parts appear correctly
- ✅ Empty fields don't crash
- ✅ Empty IPN uses fallback filename

---

## Why Not DataExportMixin?

**DataExportMixin is for generic list exports:**
- Export many items from list views (Parts, BOM, Stock, etc.)
- Shows in InvenTree's standard export dialog
- User selects which plugin to use

**Our plugin is part-specific:**
- Takes ONE assembly as input
- Generates custom flat BOM for that assembly
- Meant to be used from custom panel (after generating)
- DataExportMixin doesn't fit this workflow

**Solution:** Simple export endpoint (same pattern as existing `/flat-bom/{id}/` endpoint)

---

## Implementation Phases

### Phase 1: Backend Export Endpoint (2 hours)
**Goal:** Add export endpoint that returns files in multiple formats

**What We'll Do:**
1. Create `FlatBOMExportView` in views.py
2. **REUSE FlatBOMView logic** (calls existing view, leverages serializers)
3. Convert serialized response to tablib Dataset
4. Use tablib library for format conversion (InvenTree standard)
5. Return HttpResponse with proper headers
6. Register URL: `/plugin/flat-bom-generator/flat-bom/{id}/export/`

**Key Pattern (Leverages Refactoring):**
```python
import tablib
from django.http import HttpResponse
from datetime import datetime

class FlatBOMExportView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, part_id):
        # Get format from query params
        export_format = request.query_params.get('format', 'csv').lower()
        
        # REUSE EXISTING VIEW (leverages serializers, enrichment, warnings!)
        flat_bom_view = FlatBOMView()
        flat_bom_view.request = request  # Pass request context
        response = flat_bom_view.get(request, part_id)
        
        # Check for errors
        if response.status_code != 200:
            return response  # Return error response as-is
        
        # Extract validated data (already serialized!)
        data = response.data
        bom_items = data['bom_items']
        
        # Convert to tablib Dataset
        dataset = tablib.Dataset()
        dataset.headers = [
            'IPN', 'Part Name', 'Description', 'Type', 'Total Qty', 'Unit',
            'In Stock', 'On Order', 'Allocated', 'Available', 'Level', 'Reference', 'Note'
        ]
        
        for item in bom_items:
            dataset.append([
                item.get('ipn', ''),
                item.get('part_name', ''),
                item.get('description', ''),
                item.get('part_type', ''),
                item.get('total_qty', 0),
                item.get('unit', ''),
                item.get('in_stock', 0),
                item.get('on_order', 0),
                item.get('allocated', 0),
                item.get('available', 0),
                item.get('level', 0),
                item.get('reference', ''),
                item.get('note', ''),
            ])
        
        # Export in requested format
        if export_format == 'csv':
            content = dataset.export('csv')
            content_type = 'text/csv'
            extension = 'csv'
        elif export_format == 'json':
            content = dataset.export('json')
            content_type = 'application/json'
            extension = 'json'
        elif export_format == 'xlsx':
            content = dataset.export('xlsx')
            content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            extension = 'xlsx'
        else:
            return Response(
                {'error': f'Unsupported format: {export_format}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate filename
        ipn = data.get('ipn', part_id)
        date_str = datetime.now().strftime('%Y%m%d')
        filename = f"FlatBOM_{ipn}_{date_str}.{extension}"
        
        # Return file (InvenTree pattern)
        response = HttpResponse(content, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
```

**Why This Approach:**
- ✅ **Reuses serializer refactoring** (FlatBOMItemSerializer, FlatBOMResponseSerializer)
- ✅ **Reuses enrichment logic** (stock, warnings, images)
- ✅ **Reuses settings loading** (max_depth, category mappings, etc.)
- ✅ **Single source of truth** - FlatBOMView is canonical logic
- ✅ **Maintains consistency** - Export matches Panel.tsx exactly
- ✅ **Easy to maintain** - Changes to FlatBOMView automatically apply to export

**Testing:**
- ✅ GET `/flat-bom/123/export/?format=csv` downloads CSV
- ✅ GET `/flat-bom/123/export/?format=json` downloads JSON  
- ✅ GET `/flat-bom/123/export/?format=xlsx` downloads XLSX
- ✅ Verify filename: `FlatBOM_{IPN}_{date}.{ext}`
- ✅ Compare CSV with current export (should match)
- ✅ Test with cutlist parts (multiple rows)
- ✅ Test with special characters (commas, quotes)

**Files Changed:**
- `flat_bom_generator/views.py` (add FlatBOMExportView class)
- `flat_bom_generator/core.py` (register export URL in setup_urls)
- `pyproject.toml` (add tablib dependency if not present)

**Commit:** "feat: Add export endpoint with CSV/JSON/XLSX support via tablib"

**Verification:**
- Deploy to staging
- Test in browser: `https://staging/api/plugin/flat-bom-generator/flat-bom/123/export/?format=csv`
- Verify download triggers
- Open CSV in Excel
- Compare data with current export
- Test all 3 formats

---

### Phase 2: Frontend Integration (1-2 hours)
**Goal:** Replace client-side CSV generation with server-side export endpoint

**What We'll Do:**
1. Update Panel.tsx: Replace client-side CSV generation
2. Add format selector dropdown (CSV/JSON/XLSX)
3. Call export endpoint instead of generating CSV
4. Remove old `escapeCsvField()` and CSV generation logic
5. Add loading state during export
6. Update frontend tests

**Testing:**
- ✅ Export button appears in correct location
- ✅ Format selector works (CSV/JSON/XLSX)
- ✅ Loading indicator shows during export
- ✅ File downloads with correct name
- ✅ CSV content matches old export (verification test)
- Code Pattern:**
```typescript
// Before: Client-side CSV generation
const handleExportCSV = () => {
  const csv = generateCSV(bomData);  // Custom logic
  downloadFile(csv, 'flat_bom.csv');
};

// After: Call export endpoint
const handleExport = (format: 'csv' | 'json' | 'xlsx') => {
  const url = `/api/plugin/flat-bom-generator/flat-bom/${partId}/export/`;
  window.open(`${url}?format=${format}`, '_blank');
};Navigate to part with BOM
- Open Flat BOM panel
- Generate flat BOM
- Test export:
  - Click export dropdown
  - Select CSV → Verify download
  - Select JSON → Verify download
  - Select XLSX → Verify download
- Open CSV in Excel, compare with old export
- Test with large BOM (100+ parts)
- Check mobile/tablet view

---

## Export Button Design

### Placement
**Inline with Generate/Refresh buttons (Option A):**
```
[Generate Flat BOM]  [Refresh]  [Export ▼]
                                  ├─ CSV
                                  ├─ JSON
                                  └─ XLSX
```
**Why:** All controls in one place, users expect export near generate

### Component (Mantine Menu)
```typescript
<Menu>
  <Menu.Target>
    <Button leftIcon={<IconDownload />} loading={exporting}>
      Export
    </Button>
  </Menu.Target>
  <Menu.Dropdown>
    <Menu.Item onClick={() => handleExport('csv')}>CSV</Menu.Item>
    <Menu.Item onClick={() => handleExport('json')}>JSON</Menu.Item>
    <Menu.Item onClick={() => handleExport('xlsx')}>XLSX</Menu.Item>
  </Menu.Dropdown>
</Menu>
```
- IMP Processed: 12            ├─ JSON
- Need to Order: 8             └─ XLSX
```
**Pros:** Separate from generation controls  
**Cons:** Far from related actions

**Option C: Above Table (Header Bar)**
```
Search [___________]  |  [Checkboxes]  |  [Export ▼]
---------------------------------------------------
| Component | IPN | Description | ... |
```
**Pros:** Common pattern for data tables  
**Cons:** May conflict with existing controls

**Recommendation:** Option A - Inline with Generate button

### Export Button Component

```typescript
// Simple approach - use Mantine Menu
<Menu>
  <Menu.Target>
    <Button leftIcon={<IconDownload />} loading={exporting}>
      Export
    </Button>
  </Menu.Target>
  <Menu.Dropdown>
    <Menu.Item onClick={() => handleExport('csv')}>
      CSV (Spreadsheet)
    </Menu.Item>
    <Menu.Item onClick={() => handleExport('json')}>
      JSON (Data)
    </Menu.Item>
    <Menu.Item onClick={() => handleExport('xlsx')}>
      XLSX (Excel)
    </Menu.Item>
  </Menu.Dropdown>
</Menu>
```

### Loading States

```typescript
const [exporting, setExporting] = useState(false);

const handleExport = async (format: 'csv' | 'json' | 'xlsx') => {
  setExporting(true);
  try {
    const url = `/plugin/flat-bom-generator/flat-bom/${partId}/export/`;
    window.open(`${url}?export=True&format=${format}`, '_blank');
  } finally {
    // Reset after short delay (export initiates download)
    setTimeout(() => setExporting(false), 1000);
  }
};
```

### Mobile Considerations

- Export button should work on tablets (touch targets)
- Dropdown menu needs adequate spacing
- File downloads should work on mobile browsers

---

## Testing Strategy

### After Each Phase

**Backend Tests (Phase 1):**
```powershell
# No unit tests needed for simple endpoint
# Test manually via browser/API
```

**Frontend Tests (Phase 2):**
```powershell
# Run frontend tests
.\scripts\Test-Frontend.ps1 -Plugin "FlatBOMGenerator"
```

**Deployment (Both Phases):**
```powershell
# Deploy to staging after each phase
.\scripts\Deploy-Plugin.ps1 -Plugin "FlatBOMGenerator" -Server staging
```

### Manual Verification Checklist (Phase 2)

**Basic Functionality:**
- [ ] Export button appears
- [ ] Format dropdown opens
- [ ] CSV exports and downloads
- [ ] JSON exports and downloads
- [ ] XLSX exports and downloads
- [ ] Filenames are descriptive (include IPN and date)

**Data Verification:**
- [ ] CSV has all columns from old export
- [ ] Shortfall calculations correct
- [ ] Cutlist rows present (if applicable)
- [ ] Stock levels accurate
- [ ] All parts included (compare counts)

**Edge Cases:**
- [ ] Export empty BOM (assembly with no children)
- [ ] Export very large BOM (100+ parts)
- [ ] Export with special characters (part names with commas, quotes)
- [ ] Export with cutlist parts (multiple rows)

**UI/UX:**
- [ ] Loading indicator shows
- [ ] Button disabled during export
- [ ] Works on tablet view
- [ ] Dropdown menu readable

**Regression:**
- [ ] Existing panel functionality works
- [ ] Generate button still works
- [ ] Refresh button still works
- [ ] All existing features intact

---

## Rollback Plan

**If Phase Fails:**
1. Revert last commit: `git revert HEAD`
2. Redeploy previous version to staging
3. Fix issue locally
4. Re-test
5. Deploy again

**Critical Issues:**
- Export endpoint crashes → Revert Phase 1
- Frontend broken → Revert Phase 2

---

## Success Criteria

**Phase 1 Complete When:**
- ✅ Export endpoint returns CSV/JSON/XLSX files
- ✅ Files download with correct names
- ✅ Content matches current export
- ✅ Existing flat BOM generation still works

**Phase 2 Complete When:**
- ✅ Old CSV export logic removed
- ✅ New export dropdown works
- ✅ All 3 formats download correctly
- ✅ Frontend tests pass
- ✅ Manual testing complete

**Project Complete When:**
- ✅ Both phases deployed to staging
- ✅ Frontend tests passing
- ✅ Manual testing complete
- ✅ Documentation updated (README, ARCHITECTURE)
- ✅ User approves for production deployment

---

## Timeline Estimate

- **Phase 1:** 2 hours (backend export endpoint)
- **Phase 2:** 1-2 hours (frontend integration)

**Total:** 3-4 hours over 2 deployments

**Spread:** Can be done in one session or split across 2 days

---

## Ready to Start?

Let me know when you're ready and I'll begin **Phase 1: Backend Foundation**!

We'll go step-by-step, testing and verifying each phase before moving to the next.
