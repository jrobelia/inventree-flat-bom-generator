# InvenTree Export System Integration - Review & Implementation Plan

**Created:** January 19, 2026  
**Purpose:** Document InvenTree's export system for implementing DataExportMixin in FlatBOMGenerator

---

## InvenTree Export System Overview

### Two-Part Architecture

**1. DataExportMixin (Plugin Side)**
- Plugin mixin that provides export capabilities
- Located: `InvenTree/plugin/base/integration/DataExport.py`
- Defines what models the plugin can export
- Customizes headers, filters data, generates filenames
- Returns list of dict objects (serialized data)

**2. DataExportViewMixin (API View Side)**
- Added to API list views (e.g., `PartList`, `BomList`)
- Handles export requests: `GET /api/endpoint/?export=True&export_plugin=slug`
- Orchestrates plugin execution
- Generates file (CSV/JSON/XLSX via tablib)
- Returns download link

---

## Key Patterns from BOM Exporter Reference

### Plugin Structure (bom_exporter.py)

```python
from plugin import InvenTreePlugin
from plugin.mixins import DataExportMixin

class BomExporterPlugin(DataExportMixin, InvenTreePlugin):
    """Builtin plugin for performing multi-level BOM exports."""

    NAME = 'BOM Exporter'
    SLUG = 'bom-exporter'
    TITLE = _('Multi-Level BOM Exporter')
    DESCRIPTION = _('Provides support for exporting multi-level BOMs')
    VERSION = '1.1.0'

    # Optional: Custom options for user to configure export
    ExportOptionsSerializer = BomExporterOptionsSerializer

    def supports_export(self, model_class: type, user, *args, **kwargs) -> bool:
        """This exported only supports the BomItem model."""
        return model_class == BomItem  # ← Limit to specific model

    def generate_filename(self, model_class, export_format: str) -> str:
        """Generate a filename for the exported data."""
        model = model_class.__name__
        date = current_date().isoformat()
        return f'InvenTree_{model}_{date}.{export_format}'

    def update_headers(self, headers: OrderedDict, context: dict, **kwargs) -> OrderedDict:
        """Modify the headers for the data export."""
        # Add custom headers
        headers['level'] = _('BOM Level')
        headers['total_quantity'] = _('Total Quantity')
        return headers

    def export_data(
        self,
        queryset: QuerySet,
        serializer_class,
        headers: OrderedDict,
        context: dict,
        output: DataOutput,
        **kwargs
    ) -> list:
        """Export data from the queryset."""
        # Custom data generation logic
        data = []
        for item in queryset:
            row = serializer_class(item, exporting=True).data
            row['level'] = 1  # ← Add custom fields
            row['total_quantity'] = calculate_total(item)
            data.append(row)
        
        return data  # ← Return list of dicts
```

### Custom Export Options (Optional)

```python
class BomExporterOptionsSerializer(serializers.Serializer):
    """Custom export options for the BOM exporter plugin."""

    export_levels = serializers.IntegerField(
        default=0,
        label=_('Levels'),
        help_text=_('Number of levels to export - set to zero to export all BOM levels'),
        min_value=0,
    )

    export_stock_data = serializers.BooleanField(
        default=True,
        label=_('Stock Data'),
        help_text=_('Include part stock data')
    )
```

---

## FlatBOMGenerator Implementation Plan

### Answers to Your Questions

**1. Should we start implementation now?**
- Yes, after this review we have all the information needed

**2. Export file naming**
- Use descriptive name with part info and timestamp
- Pattern: `FlatBOM_{part_ipn}_{timestamp}.{format}`
- Example: `FlatBOM_ASM-001_2026-01-19.csv`

**3. Column selection**
- Export all columns (no custom options)
- InvenTree's DataExportViewMixin supports this by default
- Keep it simple - users can filter in Excel/CSV viewer

**4. Backward compatibility**
- Switch completely to new system
- Remove old CSV export button
- Cleaner user experience

---

## Implementation Steps

### Step 1: Add DataExportMixin to Core Plugin (core.py)

**Current mixins:**
```python
class FlatBOMGeneratorPlugin(SettingsMixin, UrlsMixin, UserInterfaceMixin, InvenTreePlugin):
```

**Add DataExportMixin:**
```python
from plugin.mixins import DataExportMixin

class FlatBOMGeneratorPlugin(
    DataExportMixin,      # ← Add this
    SettingsMixin,
    UrlsMixin,
    UserInterfaceMixin,
    InvenTreePlugin
):
```

### Step 2: Implement DataExportMixin Methods (core.py)

```python
def supports_export(self, model_class: type, user, *args, **kwargs) -> bool:
    """Support exporting Part data (for flat BOM context)."""
    from part.models import Part
    return model_class == Part

def generate_filename(self, model_class, export_format: str) -> str:
    """Generate descriptive filename for flat BOM export."""
    from InvenTree.helpers import current_date
    
    # Try to get part context from kwargs
    context = kwargs.get('context', {})
    part_ipn = context.get('part_ipn', 'Part')
    part_name = context.get('part_name', '')
    
    date = current_date().isoformat()
    
    # Clean filename (remove special characters)
    safe_ipn = part_ipn.replace('/', '-').replace(' ', '_')
    
    return f'FlatBOM_{safe_ipn}_{date}.{export_format}'

def update_headers(self, headers: OrderedDict, context: dict, **kwargs) -> OrderedDict:
    """Customize headers for flat BOM export."""
    # Reorder headers to match current CSV export order
    # Keep all existing headers from serializer
    return headers

def export_data(
    self,
    queryset: QuerySet,
    serializer_class,
    headers: OrderedDict,
    context: dict,
    output: DataOutput,
    **kwargs
) -> list:
    """Export flat BOM data.
    
    Note: queryset will be a Part queryset (single part)
    We need to generate flat BOM data from that part.
    """
    from flat_bom_generator.bom_traversal import get_flat_bom
    
    # Get the part ID from queryset (should be single part)
    if not queryset.exists():
        return []
    
    part = queryset.first()
    
    # Generate flat BOM using existing function
    flat_bom, imp_count, warnings, max_depth = get_flat_bom(
        part.pk,
        max_depth=self.get_setting('MAX_DEPTH', 0) or None,
        # ... other settings
    )
    
    # Enrich with stock data (reuse existing logic from views.py)
    enriched_data = self._enrich_bom_data(flat_bom, part)
    
    # Add part context for filename generation
    context['part_ipn'] = part.IPN or part.name
    context['part_name'] = part.name
    
    return enriched_data
```

### Step 3: Create Export URL Endpoint (views.py)

**Option A: Add to existing FlatBOMView**
```python
class FlatBOMView(APIView):
    """Existing view for flat BOM generation."""
    
    # Keep existing GET method for JSON response
    
    def get_export(self, request, part_id):
        """Export endpoint for DataExportMixin."""
        # This would be called by InvenTree export system
        pass
```

**Option B: Create separate export view (RECOMMENDED)**
```python
from data_exporter.mixins import DataExportViewMixin
from InvenTree.mixins import ListAPI

class FlatBOMExportView(DataExportViewMixin, ListAPI):
    """Export endpoint for flat BOM data."""
    
    serializer_class = FlatBOMItemSerializer
    
    def get_queryset(self):
        """Return Part queryset for export."""
        from part.models import Part
        part_id = self.kwargs.get('part_id')
        return Part.objects.filter(pk=part_id)
```

### Step 4: Register Export URL (core.py)

```python
def setup_urls(self):
    from django.urls import path
    from .views import FlatBOMView, FlatBOMExportView
    
    return [
        path('flat-bom/<int:part_id>/', FlatBOMView.as_view(), name='flat-bom'),
        path('flat-bom/<int:part_id>/export/', FlatBOMExportView.as_view(), name='flat-bom-export'),  # ← New
    ]
```

### Step 5: Update Frontend (Panel.tsx)

**Current (custom CSV export):**
```typescript
<Button onClick={handleExportCSV}>Export CSV</Button>
```

**New (InvenTree export integration):**
```typescript
import { ActionButton } from '@inventreedb/ui';

<ActionButton
  icon="download"
  tooltip="Export Flat BOM"
  onClick={() => {
    const exportUrl = `/plugin/flat-bom-generator/flat-bom/${partId}/export/`;
    window.open(`${exportUrl}?export=True&format=csv`, '_blank');
  }}
/>
```

**Or use InvenTree's DataTable export integration:**
- Check if InvenTree DataTable component has built-in export button
- May auto-detect export endpoint and show format selector (CSV/JSON/XLSX)

---

## Benefits Summary

**What We Get:**
✅ CSV, JSON, XLSX formats automatically  
✅ Consistent with InvenTree UI patterns  
✅ Better encoding/escaping (InvenTree handles)  
✅ Server-side generation (no browser limits)  
✅ ~30 lines less code to maintain  
✅ Descriptive filenames with timestamp  

**What We Remove:**
❌ Custom `escapeCsvField()` function  
❌ Client-side CSV generation logic  
❌ Manual file download trigger  

---

## Testing Checklist

**After Implementation:**
- [ ] Export CSV from frontend panel
- [ ] Verify filename format: `FlatBOM_{IPN}_{date}.csv`
- [ ] Verify all columns present (match current CSV)
- [ ] Verify special characters handled (commas, quotes, newlines)
- [ ] Test JSON export
- [ ] Test XLSX export
- [ ] Test with large BOM (100+ parts)
- [ ] Verify shortfall calculations in export
- [ ] Verify cutlist rows in export
- [ ] Compare exported data with current CSV export

---

## Questions/Decisions Still Needed

1. **Export endpoint design:**
   - Option A: Extend existing `/flat-bom/{id}/` with `?export=True`
   - Option B: Separate `/flat-bom/{id}/export/` endpoint (RECOMMENDED)

2. **Serializer approach:**
   - Reuse existing FlatBOMItemSerializer?
   - Create dedicated export serializer?

3. **Context passing:**
   - How to pass part IPN to generate_filename()?
   - Store in context dict during export_data()?

4. **Frontend integration:**
   - Simple link/button?
   - Use InvenTree ActionButton component?
   - Integrate with DataTable export if available?

---

## Next Steps

1. ✅ Review InvenTree export system (COMPLETE - this document)
2. ⏭️ Decide on implementation approach (endpoint design, serializer)
3. ⏭️ Implement backend (DataExportMixin methods, export view)
4. ⏭️ Update frontend (replace CSV button with export integration)
5. ⏭️ Test all export formats
6. ⏭️ Deploy to staging
7. ⏭️ Update documentation (README.md, ARCHITECTURE.md)

---

**Ready to proceed with implementation?**

Let me know which options you prefer and I'll start implementing!
