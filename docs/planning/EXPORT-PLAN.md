# Export Integration Plan

**Status:** ON HOLD  
**Created:** January 19, 2026  
**Last Updated:** February 26, 2026  
**Estimated Time:** 3-4 hours (2 phases)

---

## Summary

Replace client-side CSV generation with a server-side export endpoint
supporting CSV, JSON, and XLSX formats.

**Decision:** Use a custom endpoint with tablib (not DataExportMixin).
DataExportMixin is designed for generic list exports; our plugin takes a
single assembly as input and generates a custom flat BOM -- a simple
endpoint is a better fit.

---

## Open Decisions

| Decision | Options | Leaning |
|---|---|---|
| Build quantity in export | A) Always buildQuantity=1 (raw BOM) / B) Pass as query param | Option A (simpler, reusable) |
| Warnings in export | A) Separate XLSX sheet / B) Header section / C) Skip | Option C (skip for now) |
| Column set | Match current 12 CSV columns / Expand to all API fields | Match current 12 first |

---

## Phase 1: Backend Export Endpoint (~2 hours)

**Goal:** `GET /plugin/flat-bom-generator/flat-bom/{id}/export/?format=csv`

**Approach:**
- Create `FlatBOMExportView` in views.py
- Reuse `FlatBOMView` logic (leverages existing serializers and enrichment)
- Convert response to tablib Dataset
- Return file with Content-Disposition header

**Key pattern:**
```python
class FlatBOMExportView(APIView):
    def get(self, request, part_id):
        export_format = request.query_params.get('format', 'csv')
        # Reuse FlatBOMView for data generation
        # Convert to tablib Dataset
        # Return HttpResponse with attachment header
```

**Files changed:** `views.py`, `core.py` (URL registration)

**Considerations:**
- tablib is already available in InvenTree (verify openpyxl for XLSX)
- Cutlist rows must be preserved correctly
- Empty IPN uses fallback: `Part_{id}`
- Filename pattern: `FlatBOM_{IPN}_{YYYYMMDD}.{ext}`

---

## Phase 2: Frontend Integration (~1-2 hours)

**Goal:** Replace client-side CSV generation with export dropdown

**Approach:**
- Add Mantine Menu dropdown next to Generate/Refresh buttons
- Format options: CSV, JSON, XLSX
- Remove old `escapeCsvField()` and CSV generation logic
- Add loading state during export

**UI layout:**
```
[Generate Flat BOM]  [Refresh]  [Export v]
                                  +-- CSV
                                  +-- JSON
                                  +-- XLSX
```

---

## Testing Checklist

- [ ] All 3 formats download correctly
- [ ] Filenames include IPN and date
- [ ] Content matches current CSV export
- [ ] Special characters handled (commas, quotes, unicode)
- [ ] Large BOMs work (100+ parts)
- [ ] Cutlist parts appear correctly
- [ ] Empty fields don't crash
- [ ] Existing panel functionality unaffected

---

## InvenTree DataExportMixin Reference

For future reference, DataExportMixin uses this pattern:
- Plugin declares `supports_export()`, `generate_filename()`, `update_headers()`, `export_data()`
- API views use `DataExportViewMixin` to detect `?export=True&export_plugin=slug`
- System generates file via tablib

We chose NOT to use this because our plugin is part-specific (single
assembly input), not a generic list exporter. If InvenTree's export
system evolves to support single-item exports, revisit this decision.
