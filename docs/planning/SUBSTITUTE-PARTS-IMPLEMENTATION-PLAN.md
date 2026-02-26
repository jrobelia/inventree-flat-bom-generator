# Substitute Parts Support - Implementation Plan

**Status:** Planning Phase  
**Created:** January 22, 2026  
**Estimated Time:** 3.75-4.25 hours (ADJUSTED - comprehensive file updates)  
**Priority:** HIGH  
**Pattern:** Extend cutlist infrastructure with generic child row system

---

## Overview

Add support for displaying BOM item substitute parts as expandable child rows, showing individual stock availability for each substitute. This helps users see which substitute has best availability at a glance.

**Design Philosophy:** Reuse the successful cutlist breakdown pattern (proven infrastructure, minimal risk).

---

## InvenTree Substitute Parts System

### Database Model

**`BomItemSubstitute` Model:**
```python
class BomItemSubstitute:
    bom_item: ForeignKey(BomItem)      # Parent BOM line item
    part: ForeignKey(Part)              # Substitute part (must be component=True)
    
    # Relations:
    # BomItem.substitutes → QuerySet[BomItemSubstitute]
    # Part.substitute_items → QuerySet[BomItemSubstitute] (reverse lookup)
```

**Key Relationships:**
- Each `BomItem` can have 0-N substitute parts via `bom_item.substitutes.all()`
- Substitutes are alternative parts that can fulfill the same BOM requirement
- Substitutes must be `component=True` parts
- Substitute cannot be same as the BOM item's `sub_part` (enforced by model validation)

### API Access

**Existing InvenTree API:**
```
GET /api/bom/substitute/?bom_item=123
Response: [
  {
    "pk": 456,
    "bom_item": 123,
    "part": 789,
    "part_detail": { /* PartBriefSerializer */ }
  }
]
```

**BomItem Serializer** (when `substitutes=True`):
```json
{
  "pk": 123,
  "substitutes": [ /* array of BomItemSubstituteSerializer */ ],
  "available_substitute_stock": 5000  // Total stock across all substitutes
}
```

### Stock Allocation Behavior

**`BomItem.get_valid_parts_for_allocation()`:**
- Returns list of parts that can fulfill this BOM item
- Includes: sub_part, substitutes, variants (if allow_variants=True)
- InvenTree's build allocation logic considers all these parts

**Our Plugin's Scope:**
- We show information only (read-only)
- Don't allocate stock (InvenTree handles that)
- Display availability so user can make informed decisions

---

## Clean Migration Strategy

**Philosophy:** No backward compatibility, no dead code. Refactor cutlists to generic system FIRST, then add substitutes.

**Why Clean Migration?**
- ✅ Eliminates dead code (`is_cut_list_child` flag removed)
- ✅ One grouping function works for all child row types
- ✅ Easy to add variants/mixed-flags later (just add `child_row_type`)
- ✅ Clear semantics: `is_child_row` + `child_row_type` + `parent_row_part_id`
- ✅ Works for different part_ids (substitutes, variants) AND same part_id (cutlists)

**Generic Child Row System:**
```typescript
export interface BomItem {
  // Generic child row fields (replaces is_cut_list_child)
  is_child_row?: boolean;              // True if cutlist/substitute/variant child
  child_row_type?: 'cutlist_ctl' | 'cutlist_ifab' | 'substitute' | 'variant';
  parent_row_part_id?: number;         // Parent ROW's part_id (not assembly parent!)
}
```

**Key Innovation:** `parent_row_part_id` enables different part_id children
- Cutlists: `parent_row_part_id: 123` (same as child `part_id: 123`)
- Substitutes: `parent_row_part_id: 123` (different child `part_id: 456`) ✅ Works!
- Future variants: Same pattern, just add `child_row_type: 'variant'`

**Implementation Approach:**
- **Phase 3.1:** Migrate cutlists to generic system (0.5 hrs)
- **Phase 3.2:** Add substitutes using generic system (0.5 hrs)
- **Result:** Clean architecture ready for future expansion

---

## Visual Design for Substitute Rows

**Validated:** January 23, 2026 via prototype testing

**Approach:** Flat-row insertion (insert substitute rows immediately after parent in flat array)

### Visual Elements

**Row Styling:**
```typescript
rowStyle={(record) => {
  if (record.is_substitute_part) {
    return {
      backgroundColor: 'var(--mantine-color-blue-0)',      // Light blue tint
      borderLeft: '4px solid var(--mantine-color-blue-5)',  // Blue left border
      boxShadow: 'inset 0 1px 3px rgba(0, 0, 0, 0.05)'     // Subtle depth
    };
  }
}}
```

**Component Column:**
- **Icon:** "↳" symbol (gray, bold)
- **Indent:** 2rem padding-left

**Flags Column:**
- **Badge:** Blue filled "Substitute" badge (most prominent)
- **Order:** Substitute badge → Optional → Consumable

### Flag Inheritance

Substitute parts inherit parent's `optional` and `consumable` flags (they're alternatives for same requirement).

```typescript
// In flattenBomData():
flattenedData.push({
  ...item,
  ...sub,
  is_substitute_part: true,
  optional: item.optional,      // Inherit from parent
  consumable: item.consumable   // Inherit from parent
} as BomItem);
```

---

## Implementation Phases

### Phase 0: Backend Serializer (Test-First) (0.5 hours)

**Goal:** Create proper DRF serializer for substitute parts (follows FlatBOMItemSerializer pattern).

**Files:**
- `flat_bom_generator/serializers.py`
- `flat_bom_generator/tests/unit/test_serializers.py`

**Test-First Workflow:**

1. **Write Tests First** (20 min)
   ```python
   # test_serializers.py
   class SubstitutePartSerializerTests(TestCase):
       def test_serializer_validates_required_fields(self):
           """Test serializer requires substitute_id, part_id, etc."""
           
       def test_serializer_handles_none_values(self):
           """Test serializer handles None for optional fields."""
           
       def test_serializer_output_structure(self):
           """Test serialized output matches expected structure."""
   ```

2. **Implement Serializer** (20 min)
   ```python
   # serializers.py
   class SubstitutePartSerializer(serializers.Serializer):
       """Serializes substitute part data with stock information.
       
       Substitutes are alternative parts that can fulfill the same BOM requirement.
       Each substitute includes its own stock, allocation, and availability data.
       """
       
       substitute_id = serializers.IntegerField(
           required=True,
           help_text="BomItemSubstitute primary key"
       )
       
       part_id = serializers.IntegerField(
           required=True,
           help_text="Substitute Part primary key"
       )
       
       ipn = serializers.CharField(
           required=False,
           allow_blank=True,
           help_text="Internal Part Number"
       )
       
       part_name = serializers.CharField(
           required=True,
           help_text="Part name"
       )
       
       full_name = serializers.CharField(
           required=True,
           help_text="Full display name with variant info"
       )
       
       description = serializers.CharField(
           required=False,
           allow_blank=True,
           help_text="Part description"
       )
       
       # Stock data
       in_stock = serializers.FloatField(
           required=True,
           help_text="Total inventory"
       )
       
       on_order = serializers.FloatField(
           required=True,
           help_text="Quantity on incomplete purchase orders"
       )
       
       allocated = serializers.FloatField(
           required=True,
           help_text="Stock reserved for builds/sales"
       )
       
       available = serializers.FloatField(
           required=True,
           help_text="in_stock - allocated"
       )
       
       # Display metadata
       image = serializers.CharField(
           required=False,
           allow_null=True,
           help_text="Full-size image URL"
       )
       
       thumbnail = serializers.CharField(
           required=False,
           allow_null=True,
           help_text="Thumbnail image URL"
       )
       
       link = serializers.CharField(
           required=True,
           help_text="URL to part detail page"
       )
       
       class Meta:
           fields = [
               'substitute_id', 'part_id', 'ipn', 'part_name', 'full_name',
               'description', 'in_stock', 'on_order', 'allocated', 'available',
               'image', 'thumbnail', 'link'
           ]
   ```

3. **Run Tests** (10 min)
   ```bash
   python -m unittest flat_bom_generator.tests.unit.test_serializers.SubstitutePartSerializerTests -v
   ```

4. **Update FlatBOMItemSerializer** (10 min)
   ```python
   class FlatBOMItemSerializer(serializers.Serializer):
       # ... existing fields ...
       
       # NEW: Substitute parts support
       has_substitutes = serializers.BooleanField(
           required=False,
           default=False,
           help_text="True if this part has substitute options"
       )
       
       substitute_parts = SubstitutePartSerializer(
           many=True,
           required=False,
           allow_null=True,
           help_text="List of substitute parts with individual stock data"
       )
   ```

**Testing:** All serializer tests pass before moving to Phase 1

**Estimated Time:** 0.5 hours (follows proper DRF pattern)

---

### Phase 1: Backend Data Enrichment (Test-First) (1-1.5 hours)

**Goal:** Query substitute parts and enrich with stock data using serializer.

**File:** `flat_bom_generator/views.py`

**Test-First Workflow:**

1. **Write Integration Tests First** (30 min)
   ```python
   # tests/integration/test_substitute_enrichment.py
   class SubstituteEnrichmentTests(InvenTreeTestCase):
       @classmethod
       def setUpTestData(cls):
           """Create fixture: Part with 3 substitutes."""
           
       def test_substitutes_included_when_setting_enabled(self):
           """Test substitutes appear in API response when setting enabled."""
           
       def test_substitutes_excluded_when_setting_disabled(self):
           """Test substitutes not in response when setting disabled."""
           
       def test_substitute_stock_data_correct(self):
           """Test substitute stock values match Part model."""
   ```

2. **Implement Enrichment** (40-60 min)
   ```python
   # In FlatBOMView.get() method, during enrichment loop:
   
   # Import at top of file
   from part.models import BomItemSubstitute
   from .serializers import SubstitutePartSerializer
   
   # Current enrichment (lines 334-500)
   for item_dict in flat_bom:
       part_obj = part_dict.get(item_dict["part_id"])
       # ... existing enrichment ...
       
       # NEW: Query substitutes if plugin setting enabled
       if include_substitutes:  # From plugin setting
           substitutes = BomItemSubstitute.objects.filter(
               bom_item__part_id=original_part_id,  # Need to track this
               bom_item__sub_part_id=item_dict["part_id"]
           ).select_related('part')
           
           if substitutes.exists():
               item_dict['has_substitutes'] = True
               substitute_data = []
               
               for sub in substitutes:
                   sub_part = sub.part
                   # Build raw data dict
                   sub_raw = {
                       'substitute_id': sub.pk,
                       'part_id': sub_part.pk,
                       'ipn': sub_part.IPN or '',
                       'part_name': sub_part.name,
                       'full_name': sub_part.full_name,
                       'description': sub_part.description or '',
                       # Stock data
                       'in_stock': float(sub_part.total_stock),
                       'on_order': float(sub_part.on_order),
                       'allocated': float(sub_part.allocation_count()),
                       'available': float(sub_part.available_stock),
                       # Display metadata
                       'image': sub_part.image.url if sub_part.image else None,
                       'thumbnail': sub_part.image.thumbnail.url if sub_part.image else None,
                       'link': f'/part/{sub_part.pk}/',
                   }
                   substitute_data.append(sub_raw)
               
               # Validate with serializer (ensures API contract)
               serializer = SubstitutePartSerializer(data=substitute_data, many=True)
               if serializer.is_valid(raise_exception=True):
                   item_dict['substitute_parts'] = serializer.validated_data
           else:
               item_dict['has_substitutes'] = False
               item_dict['substitute_parts'] = None
   ```

3. **Run Integration Tests** (10 min)
   ```bash
   .\scripts\Test-Plugin.ps1 -Plugin "FlatBOMGenerator" -Integration
   ```

2. **Track Original BomItem Context**
   - **Problem:** After deduplication, we lose which BomItem(s) a part came from
   - **Current:** `deduplicate_and_sum()` only keeps `part_id` + aggregated quantities
   - **Solution:** Pass through `bom_item_ids` list during traversal
   
   ```python
   # In bom_traversal.py traverse_bom():
   item_data = {
       "part_id": bom_item.sub_part.pk,
       "bom_item_id": bom_item.pk,  # NEW: Track BomItem ID
       # ... existing fields ...
   }
   
   # In deduplicate_and_sum():
   grouped[part_id]["bom_item_ids"].append(item["bom_item_id"])  # NEW
   ```

3. **Add Plugin Setting**
   ```python
   # In core.py SETTINGS:
   SHOW_SUBSTITUTE_PARTS = {
       'name': _('Show Substitute Parts'),
       'description': _('Display substitute parts as expandable rows'),
       'validator': bool,
       'default': False,  # Default OFF (new feature)
   }
   ```

**Testing:**
- Unit test: Mock BomItemSubstitute query, verify enrichment
- Integration test: Create fixture with BomItem + 3 substitutes, verify API response

**Estimated Time:** 1-1.5 hours

---

### Phase 2: Frontend Data Structure (0.5 hours)

**Goal:** Update TypeScript types to include substitute support.

**File:** `frontend/src/types/BomTypes.ts`

**Changes:**

```typescript
export interface BomItem {
  // ... existing fields ...
  
  // NEW: Substitute parts support (from API)
  has_substitutes?: boolean;
  substitute_parts?: SubstitutePart[];  // Enriched from backend
}

export interface SubstitutePart {
  substitute_id: number;
  part_id: number;
  ipn: string;
  part_name: string;
  full_name: string;
  description: string;
  
  // Stock data
  in_stock: number;
  on_order: number;
  allocated: number;
  available: number;
  
  // Display metadata
  image: string | null;
  thumbnail: string | null;
  link: string;
}
```

**Note:** Generic child row fields (`is_child_row`, `child_row_type`, `parent_row_part_id`) added in Phase 3.1.

**Testing:** TypeScript compilation passes

**Estimated Time:** 0.5 hours

---

### Phase 3: Generic Child Row System - Clean Migration (1 hour)

**Goal:** Migrate cutlists to generic child row system, then add substitutes using same infrastructure.

**Philosophy:** Clean break - no backward compatibility, no dead code. Refactor cutlists FIRST, then add substitutes.

**Files:**
- `frontend/src/types/BomTypes.ts` (update interface)
- `frontend/src/utils/bomDataProcessing.ts` (migrate cutlists + add substitutes)
- `frontend/src/columns/bomTableColumns.tsx` (update rendering)
- `frontend/src/utils/csvExport.ts` (update export)
- `frontend/src/components/ControlBar.tsx` (checkbox)
- `frontend/src/Panel.tsx` (state + options)

**Phase 3.1: Migrate Cutlists to Generic System (45 min)**

**CRITICAL:** This phase touches **6 source files + 1 test file with 39 total references**. All cutlist functionality must continue working.

**Scope Summary:**
- 1 interface definition (BomTypes.ts)
- 3 function implementations (bomDataProcessing.ts)
- 8 column rendering conditionals (bomTableColumns.tsx)
- 3 filter/statistics references (Panel.tsx)
- 1 CSV export conditional (csvExport.ts)
- 23+ test fixtures and assertions (bomDataProcessing.test.ts)

**Migration Pattern:** Replace `is_cut_list_child` boolean with generic child row system (`is_child_row`, `child_row_type`, `parent_row_part_id`)

**Step 1: Update BomItem Interface (5 min)**
   ```typescript
   // types/BomTypes.ts
   export interface BomItem {
     // ... existing fields ...
     
     // Generic child row system (replaces is_cut_list_child)
     is_child_row?: boolean;              // True if cutlist/substitute/variant child
     child_row_type?: 'cutlist_ctl' | 'cutlist_ifab' | 'substitute' | 'variant';
     parent_row_part_id?: number;         // Parent ROW's part_id (not assembly parent!)
     
     // REMOVE these (clean break):
     // is_cut_list_child?: boolean;  // DELETE
   }
   ```

**Step 2: Migrate flattenBomData() Cutlist Logic (10 min)**

   ```typescript
   // utils/bomDataProcessing.ts
   
   export function flattenBomData(items: BomItem[], options?: {
     includeCutlists?: boolean;
     includeSubstitutes?: boolean;  // NEW
   }): BomItem[] {
     const flattenedData: BomItem[] = [];
     const { includeCutlists = true, includeSubstitutes = false } = options || {};

     for (const item of items) {
       flattenedData.push(item); // Parent row

       // MIGRATED: CtL cutlist children (use generic fields)
       if (includeCutlists && item.cut_list?.length > 0) {
         for (const cut of item.cut_list) {
           flattenedData.push({
             ...item,
             total_qty: cut.quantity,
             cut_length: cut.length,
             // NEW: Generic child row fields
             is_child_row: true,
             child_row_type: 'cutlist_ctl',
             parent_row_part_id: item.part_id,
             cut_list: null
           });
         }
       }

       // MIGRATED: Internal Fab cutlist children (use generic fields)
       if (includeCutlists && item.internal_fab_cut_list?.length > 0) {
         for (const piece of item.internal_fab_cut_list) {
           flattenedData.push({
             ...item,
             total_qty: piece.count,
             cut_length: piece.piece_qty,
             cut_unit: piece.unit,
             // NEW: Generic child row fields
             is_child_row: true,
             child_row_type: 'cutlist_ifab',
             parent_row_part_id: item.part_id,
             internal_fab_cut_list: null
           });
         }
       }
       
       // NOTE: Substitutes added in Phase 3.2
     }

     return flattenedData;
   }
   ```

**Step 3: Rename and Update groupChildrenWithParents() → groupChildRowsWithParents() (5 min)**

   ```typescript
   // utils/bomDataProcessing.ts
   
   // RENAME: groupChildrenWithParents → groupChildRowsWithParents
   // (clarifies it works with generic child row system)
   
   export function groupChildRowsWithParents(items: BomItem[]): BomItem[] {
     const parents: BomItem[] = [];
     const childrenByParentId = new Map<number, BomItem[]>();

     // Separate parent rows and child rows
     for (const item of items) {
       if (item.is_child_row) {  // CLEAN - single flag
         const parentId = item.parent_row_part_id!;  // Parent ROW's part_id
         
         if (!childrenByParentId.has(parentId)) {
           childrenByParentId.set(parentId, []);
         }
         childrenByParentId.get(parentId)!.push(item);
       } else {
         parents.push(item);
       }
     }

     // Rebuild with child rows after parent rows
     const result: BomItem[] = [];
     for (const parent of parents) {
       result.push(parent);
       const children = childrenByParentId.get(parent.part_id);
       if (children) {
         result.push(...children);
       }
     }

     return result;
   }
   ```
   
   **Also update function call in Panel.tsx:**
   ```typescript
   // OLD: data = groupChildrenWithParents(data);
   // NEW: data = groupChildRowsWithParents(data);
   ```

**Step 4: Update Column Rendering (5 min)**

   ```typescript
   // columns/bomTableColumns.tsx
   // Component column: Check is_child_row instead of is_cut_list_child
   render: (record) => {
     if (record.is_child_row) {
       const badgeText = 
         record.child_row_type === 'cutlist_ctl' ? 'Cut Length' :
         record.child_row_type === 'cutlist_ifab' ? 'Piece' :
         'Child';
       
       return (
         <Group gap="xs" ml="lg">
           <Badge color="cyan" size="xs">{badgeText}</Badge>
           {/* ... existing thumbnail + name ... */}
         </Group>
       );
     }
     // ... normal rendering ...
   }
   ```

**Step 5: Find and Replace All is_cut_list_child References (20 min)**

   **Files requiring updates:**
   - ✅ `types/BomTypes.ts` - Interface updated in Step 1
   - ✅ `utils/bomDataProcessing.ts` - Functions updated in Steps 2-3
   - ⚠️ `columns/bomTableColumns.tsx` - **8 references** to update
   - ⚠️ `Panel.tsx` - **3 references** to update (filter, comment, count)
   - ⚠️ `utils/csvExport.ts` - **1 reference** to update
   - ⚠️ `utils/bomDataProcessing.test.ts` - **23+ test references** to update
   
   **Update pattern for all files:**
   ```typescript
   // OLD
   if (record.is_cut_list_child) { ... }
   
   // NEW
   if (record.is_child_row && record.child_row_type?.startsWith('cutlist')) { ... }
   // OR more specific:
   if (record.is_child_row) { ... }  // If applies to all child types
   ```

   **Details by file:**
   
   **columns/bomTableColumns.tsx (8 occurrences):**
   - Line 36: Component column rendering (indentation + badge)
   - Line 101: Flags column hiding logic
   - Line 138: Total Qty column (blank for cutlist children)
   - Line 194: Cut Length column (only show for cutlist children)
   - Line 269: In Stock column (hide for cutlist children)
   - Line 338: Allocated column (hide for cutlist children)
   - Line 392: On Order column (hide for cutlist children)
   - Line 439: Build Margin column (hide for cutlist children)
   
   **Panel.tsx (3 occurrences):**
   - Line 165: Filter to hide cutlist rows when checkbox disabled
   - Line 375: Comment explaining child row counting
   - Line 377: Count of cutlist child rows for statistics
   
   **utils/csvExport.ts (1 occurrence):**
   - Line 73: Skip cutlist children in CSV export when needed
   
   **utils/bomDataProcessing.test.ts (23+ occurrences):**
   - All test fixtures using `is_cut_list_child: true/false`
   - All test assertions checking `is_cut_list_child` value
   - Need to update to use `is_child_row`, `child_row_type`, `parent_row_part_id`

**Step 6: Validation Checklist (Before Testing)**

   **CRITICAL:** Verify ALL files updated before manual testing:

   ```bash
   # This grep search MUST return ZERO results:
   cd frontend/src
   grep -r "is_cut_list_child" .
   ```

   **If grep finds ANY matches, migration is INCOMPLETE - do NOT proceed to testing.**

   **Manual File Verification:**
   - [ ] `types/BomTypes.ts` - `is_cut_list_child` removed, new fields added
   - [ ] `utils/bomDataProcessing.ts` - All 3 references updated (lines 41, 62, 118)
   - [ ] `columns/bomTableColumns.tsx` - All 8 references updated
     - [ ] Line 36: Component column (indentation/badge)
     - [ ] Line 101: Flags column
     - [ ] Line 138: Total Qty column
     - [ ] Line 194: Cut Length column
     - [ ] Line 269: In Stock column
     - [ ] Line 338: Allocated column
     - [ ] Line 392: On Order column
     - [ ] Line 439: Build Margin column
   - [ ] `Panel.tsx` - All 3 references updated
     - [ ] Line 165: Filter logic
     - [ ] Line 375: Comment
     - [ ] Line 377: Statistics count
   - [ ] `utils/csvExport.ts` - 1 reference updated (line 73)
   - [ ] `utils/bomDataProcessing.test.ts` - All 23+ test references updated
     - [ ] Test fixtures use `is_child_row`, `child_row_type`, `parent_row_part_id`
     - [ ] Test assertions check new fields
     - [ ] No remaining `is_cut_list_child` references

**Test Phase 3.1:** Toggle cutlist checkbox, verify cutlists still work, no console errors

---

**Phase 3.2: Add Substitutes Using Generic System (30 min)**

**Step 1: Add Substitute Expansion to flattenBomData() (15 min)**

   ```typescript
   // utils/bomDataProcessing.ts (continue from Phase 3.1)
   
   export function flattenBomData(items: BomItem[], options?: {
     includeCutlists?: boolean;
     includeSubstitutes?: boolean;
   }): BomItem[] {
     // ... existing cutlist logic ...
     
     // NEW: Substitute children (uses SAME generic system)
     if (includeSubstitutes && item.substitute_parts?.length > 0) {
       for (const sub of item.substitute_parts) {
         flattenedData.push({
           ...sub,  // Substitute has DIFFERENT part_id!
           // Generic child row fields (same as cutlists)
           is_child_row: true,
           child_row_type: 'substitute',
           parent_row_part_id: item.part_id,  // Parent ROW's part_id
           // Context from parent
           total_qty: item.total_qty,
           unit: item.unit,
         } as BomItem);
       }
     }
   }
   ```

**Step 2: Update Column Rendering for Substitutes (10 min)**

   ```typescript
   // columns/bomTableColumns.tsx
   render: (record) => {
     if (record.is_child_row) {
       const badgeText = 
         record.child_row_type === 'cutlist_ctl' ? 'Cut Length' :
         record.child_row_type === 'cutlist_ifab' ? 'Piece' :
         record.child_row_type === 'substitute' ? 'Substitute' :  // NEW
         'Child';
       
       const badgeColor = 
         record.child_row_type === 'substitute' ? 'blue' : 'cyan';  // NEW
       
       return (
         <Group gap="xs" ml="lg">
           <Badge color={badgeColor} size="xs">{badgeText}</Badge>
           {/* ... */}
         </Group>
       );
     }
   }
   ```

**Step 3: Add State and Options to Panel.tsx (5 min)**

   ```typescript
   // Panel.tsx
   export default function Panel({ context }: { context: InvenTreePluginContext }) {
     // ... existing state ...
     const [showCutlistRows, setShowCutlistRows] = useState<boolean>(true);
     const [showSubstitutes, setShowSubstitutes] = useState<boolean>(false);  // NEW
     
     // ... existing logic ...
     
     // Update flattenBomData call with new options
     const flattened = useMemo(
       () => flattenBomData(filtered, {
         includeCutlists: showCutlistRows,
         includeSubstitutes: showSubstitutes  // NEW
       }),
       [filtered, showCutlistRows, showSubstitutes]
     );
   }
   ```

**Step 4: Add Checkbox to ControlBar (5 min)**

   ```typescript
   // ControlBar.tsx - add new prop and checkbox
   <Checkbox
     label="Show Substitute Parts"
     checked={showSubstitutes}
     onChange={(e) => setShowSubstitutes(e.currentTarget.checked)}
     disabled={!bomData?.bom_items?.some(item => item.has_substitutes)}
   />
   ```

**Test Phase 3.2:** Enable substitutes checkbox, verify substitutes appear with blue badge, grouped with parent

**Benefits of Clean Migration:**
- ✅ No dead code (`is_cut_list_child` deleted)
- ✅ One grouping function works for all child types
- ✅ Easy to add variants/mixed-flags later (just add `child_type`)
- ✅ Clear semantics: `is_child_row` + `child_type` + `parent_part_id`
- ✅ Works for different part_ids (substitutes) and same part_id (cutlists)

**Estimated Time:** 1.25 hours (0.75 cutlist migration + 0.5 substitute addition)

---

### Phase 4: Polish Column Rendering (0.5 hours)

**Goal:** Add any additional column-specific rendering for child rows (if needed beyond Phase 3).

**Files:**
- `frontend/src/columns/bomTableColumns.tsx`

**Changes:**

1. **Review All Columns for Child Row Handling**
   ```typescript
   // In bomTableColumns.tsx
   
   // Component column: Indent substitute rows
   render: (record) => {
     const isSubstitute = record.is_substitute;
     return (
       <Group gap="xs">
         {isSubstitute && (
           <Box ml="lg">
             <Badge color="blue" size="xs">Substitute</Badge>
           </Box>
         )}
         {/* ... existing thumbnail + name ... */}
       </Group>
     );
   }
   
   // Type column: Show "Substitute" badge
   render: (record) => {
     if (record.is_substitute) {
       return <Badge color="blue">Substitute</Badge>;
     }
     // ... existing type badges ...
   }
   ```

**Consider:** If rendering logic becomes complex (>30 lines), extract `SubstituteRow` component:
```typescript
// components/SubstituteRow.tsx
interface SubstituteRowProps {
  record: BomItem;
}

export function SubstituteRow({ record }: SubstituteRowProps) {
  return (
    <Group gap="xs">
      <Box ml="lg">
        <Badge color="blue" size="xs">Substitute</Badge>
      </Box>
      {/* ... rendering logic ... */}
    </Group>
  );
}
```

**Testing:**
- Enable checkbox, verify substitutes appear as child rows
- Disable checkbox, verify substitutes hidden
- Verify "Substitute" badge displays
- Verify indentation shows parent/child relationship

**Estimated Time:** 0.5 hours (most work done in Phase 3)

**Note:** Sorting and filtering already work! `groupChildRowsWithParents()` handles all child row types automatically.

---

### Phase 5: CSV Export & Final Polish (0.5 hours)

**Goal:** Update CSV export to handle child rows cleanly.

**File:** `frontend/src/utils/csvExport.ts`

**Changes:**

```typescript
// In generateCsvContent():

// Add "Child Type" column
const headers = [
  'IPN',
  'Part Name',
  'Description',
  'Type',
  'Child Type',  // NEW
  // ... existing columns ...
];

// Generate rows including child rows
const rows = expandedData.map(item => [
  item.ipn,
  item.part_name,
  item.description,
  item.part_type,
  item.is_child_row ? item.child_row_type : '',  // NEW: Shows cutlist_ctl, substitute, etc.
  // ... existing columns ...
]);
```

**Testing:** Export with cutlists and substitutes enabled, verify CSV includes all rows with clear child row type indication

**Estimated Time:** 0.5 hours

**Note:** Sorting and filtering already work! The `groupChildRowsWithParents()` function handles all child row types automatically via `parent_row_part_id` matching. No additional sort/filter work needed.

---

## Testing Strategy (Test-First Workflow)

**Critical:** Write tests BEFORE implementing each phase. This ensures:
- Clear requirements (test defines expected behavior)
- No regressions (tests catch breaking changes)
- Confidence in refactoring (tests verify correctness)

**Test Order:**
1. Phase 0: Serializer tests → Implement serializer → Tests pass
2. Phase 1: Enrichment tests → Implement enrichment → Tests pass  
3. Phase 3: TypeScript compilation → Verify types and hooks work
4. Phase 4-5: Manual UI testing → Implement → Verify

### Unit Tests (Backend)

**File:** `flat_bom_generator/tests/unit/test_serializers.py` (Phase 0)

```python
class SubstitutePartSerializerTests(TestCase):
    """Test SubstitutePartSerializer validation and output."""
    
    def test_serializer_validates_required_fields(self):
        """Test serializer requires substitute_id, part_id, etc."""
        
    def test_serializer_handles_none_values(self):
        """Test optional fields accept None."""
        
    def test_serializer_output_structure(self):
        """Test serialized output matches API contract."""
        
    def test_serializer_rejects_invalid_data(self):
        """Test serializer raises ValidationError for bad data."""
```

**File:** `flat_bom_generator/tests/unit/test_substitute_enrichment.py` (if helper functions)

```python
class SubstituteEnrichmentHelpersTests(TestCase):
    """Test helper functions for substitute enrichment (if any)."""
    
    def test_substitute_query_construction(self):
        """Test query filters correctly by bom_item and sub_part."""
```

### Integration Tests

**File:** `flat_bom_generator/tests/integration/test_substitute_parts.py`

```python
class SubstitutePartsIntegrationTests(InvenTreeTestCase):
    @classmethod
    def setUpTestData(cls):
        """Create fixture: Assembly → Part with 3 substitutes."""
        
    def test_api_returns_substitute_parts(self):
        """Test FlatBOMView returns substitute data when enabled."""
        
    def test_substitute_stock_calculation(self):
        """Test substitute stock values correct."""
        
    def test_substitutes_respect_setting(self):
        """Test substitutes only appear when setting enabled."""
```

### Manual UI Testing

**10-Minute Checklist:**
- [ ] Enable setting, verify substitutes appear
- [ ] Disable setting, verify substitutes hidden
- [ ] Check substitute badge displays
- [ ] Verify stock values correct for substitutes
- [ ] Sort table, substitutes stay with parent
- [ ] Search parent, substitutes shown
- [ ] Search substitute, parent+sub shown
- [ ] Export CSV, substitutes included
- [ ] Pagination works with substitutes
- [ ] Console has no errors

---

## Risks & Mitigation

### Risk 1: BomItem Context Lost After Deduplication
**Problem:** After `deduplicate_and_sum()`, we only have `part_id`, not original `BomItem` IDs  
**Impact:** Can't query substitutes (need `bom_item_id`)  
**Mitigation:** Pass through `bom_item_ids` list during traversal  
**Estimated Time:** +0.5 hours if issue arises

### Risk 2: Multiple BomItems for Same Part
**Problem:** Part appears in BOM 3 times, each with different substitutes  
**Impact:** Which substitutes do we show?  
**Solution:** Show union of all substitutes (all possible alternatives)  
**Estimated Time:** Already handled by passing `bom_item_ids` list

### Risk 3: Performance with Many Substitutes
**Problem:** 100 parts × 5 substitutes = 500 extra rows  
**Impact:** Slow rendering, pagination issues  
**Mitigation:**
- Default setting OFF (opt-in feature)
- Pagination handles 500+ rows fine (tested with cutlist)
- Only query when setting enabled (no performance hit if disabled)

### Risk 4: Sorting/Filtering Complexity
**Problem:** Substitutes must stay grouped with parent during sort  
**Impact:** Complex filtering logic  
**Mitigation:** Reuse cutlist pattern (already proven to work)

---

## Definition of Done

**Architecture:**
- [ ] `SubstitutePartSerializer` created (follows DRF pattern)
- [ ] Backend uses serializer (no manual dict building)
- [ ] Generic child row system implemented (`is_child_row`, `child_row_type`, `parent_row_part_id`)
- [ ] `is_cut_list_child` flag REMOVED (clean break, no dead code)
- [ ] `flattenBomData()` extended with options (reuses existing infrastructure)
- [ ] `groupChildRowsWithParents()` works for all child row types
- [ ] Panel.tsx stays small (<350 lines)
- [ ] ControlBar.tsx updated with checkbox
- [ ] Column rendering uses `is_child_row` check
- [ ] SubstituteRow component extracted (if rendering >30 lines)

**Functionality:**
- [ ] Backend queries substitutes and enriches with stock data
- [ ] Plugin setting `SHOW_SUBSTITUTE_PARTS` controls feature
- [ ] Frontend displays substitutes as child rows with indentation
- [ ] "Substitute" badge shows clearly
- [ ] Checkbox controls substitute visibility
- [ ] Substitutes stay grouped with parent during sort/filter
- [ ] CSV export includes substitutes

**Testing (Test-First):**
- [ ] 4+ serializer unit tests pass (Phase 0)
- [ ] 3+ enrichment integration tests pass (Phase 1)
- [ ] TypeScript compilation passes (Phase 3)
- [ ] Manual UI checklist complete (10 items)
- [ ] No console errors

**Documentation:**
- [ ] ARCHITECTURE.md updated (serializer, hook, API response)
- [ ] ROADMAP.md updated (move to completed)
- [ ] Inline code comments explain WHY, not WHAT

---

## Documentation Updates

**ARCHITECTURE.md:**
- Add `has_substitutes` to BomItem interface
- Add `substitute_parts` array to API response
- Document substitute display pattern
- Add checkbox to Testing Checklist

**ROADMAP.md:**
- Move "Substitute Parts Support" from Planned Features to Completed Work Archive
- Add completion date and lessons learned

**README.md:**
- Add "Substitute Parts" to Features list
- Add screenshot if UI significant

---

## Open Questions

1. **Should substitutes inherit parent's optional/consumable flags?**
   - Leaning: No, substitutes are independent parts with own properties
   - Decision: Show substitute's actual flags, not inherited

2. **Should we show substitute availability in parent row?**
   - InvenTree API provides `available_substitute_stock` field
   - Could add "(+5000 in substitutes)" to parent row stock display
   - Decision: Defer to Phase 6 (out of scope for MVP)

3. **Should Build Margin column account for substitute stock?**
   - Currently: `shortfall = required - (in_stock + on_order)`
   - With substitutes: Should we add substitute stock to calculation?
   - Decision: No for MVP (user can see substitute stock separately)

4. **What if substitute is also in the flat BOM as a regular item?**
   - Part "Resistor" is in BOM at top level AND as substitute for "Capacitor"
   - Do we show it twice?
   - Decision: Yes, show in both contexts (different roles in BOM)

---

## Next Steps

1. **Review this plan with user** - Get approval on approach
2. **Create feature branch** - `git checkout -b feature/substitute-parts`
3. **Phase 0: Serializer** - Test-first serializer implementation
4. **Phase 1: Backend** - Query + enrichment with serializer validation
5. **Test Phase 1** - Verify API returns correct data
6. **Phase 2-3: Frontend** - Types + generic child row migration + display
7. **Test Phase 2-3** - Manual UI testing (cutlists + substitutes)
8. **Phase 4-5: Polish** - Column rendering + CSV export
9. **Write additional tests** - Unit + integration (beyond test-first)
10. **Deploy to staging** - Manual verification
11. **Documentation updates** - ARCHITECTURE, ROADMAP, README
12. **Merge to main** - Deploy to production

---

## Summary

**Estimated Total Time:** 3.75-4.25 hours (ADJUSTED - comprehensive file updates)  
- Phase 0 (Serializer): 0.5 hrs
- Phase 1 (Enrichment): 1-1.5 hrs  
- Phase 2 (Types): 0.5 hrs
- Phase 3 (Clean Migration): 1.25 hrs (0.75 cutlist refactor + 0.5 substitute addition)
- Phase 4 (Polish): 0.5 hrs
- Phase 5 (CSV): 0.5 hrs

**Architecture Principles Followed:**
✅ DRF serializers for API responses (not manual dicts)  
✅ Test-first workflow (write tests before code)  
✅ **Clean break - no backward compatibility, no dead code**  
✅ Generic child row system (cutlists, substitutes, variants use same infrastructure)  
✅ Reuse existing utilities (`flattenBomData()`, `groupChildRowsWithParents()`)  
✅ Component extraction for complex rendering (>30 lines)  
✅ `parent_row_part_id` enables different part_id children (substitutes, variants)  

**Key Innovation:** Generic child row system with `parent_row_part_id` tracking
- Cutlists: `parent_row_part_id: 123` (same as child `part_id: 123`)
- Substitutes: `parent_row_part_id: 123` (different child `part_id: 456`) ✅ Works!
- Future variants: Same pattern, just add `child_row_type: 'variant'`

**Confidence Level:** Very High (clean migration + reusing proven infrastructure)  
**Risk Level:** Very Low (minimal new code, test-first workflow, proven patterns)

---

_Last Updated: January 23, 2026 (revised for row-focused naming clarity)_

