# Settings UI/UX Implementation Plan

**Feature Branch:** `feature/settings-ui`  
**Estimated Time:** 5-8 hours  
**Status:** Planning Phase  
**Last Updated:** January 20, 2026

---

## Overview

Move 3 plugin settings from admin panel to frontend UI, add 1 new frontend-only filter. Follow v0.10.0 refactoring patterns for clean, maintainable code.

**Settings Being Moved:**
1. MAX_DEPTH → Frontend UI (hardcoded default: 0, persisted to localStorage)
2. SHOW_PURCHASED_ASSEMBLIES → Frontend UI (hardcoded default: false, persisted to localStorage)
3. INCLUDE_INTERNAL_FAB_IN_CUTLIST → Frontend UI (hardcoded default: false, persisted to localStorage)

**New Frontend Filter:**
4. Show Cutlist Rows → ControlBar checkbox (default: true)
   - Note: Managed as regular `useState` in Panel.tsx, NOT in PluginSettings
   - Grouped with other frontend filters (includeAllocations, includeOnOrder)

**Settings Staying in Plugin Admin:**
- All category mappings (FABRICATION_CATEGORY, COMMERCIAL_CATEGORY, etc.)
- CUTLIST_UNITS_FOR_INTERNAL_FAB (used for dynamic label display)

---

## Architecture Overview

### Backend Changes
```
flat_bom_generator/
├── core.py              # Remove 3 settings from SETTINGS dict
├── views.py             # Use query params, hardcoded defaults, add units to response
└── serializers.py       # Add cutlist_units_for_ifab to metadata
```

### Frontend Changes
```
frontend/src/
├── types/
│   └── PluginSettings.ts          # NEW: PluginSettings interface (3 backend settings only)
├── hooks/
│   └── usePluginSettings.ts       # NEW: Backend settings state + localStorage
├── components/
│   ├── SettingsPanel.tsx          # NEW: Before-first-gen expanded settings
│   ├── SettingsDrawer.tsx         # NEW: After-first-gen drawer
│   └── ControlBar.tsx             # MODIFY: Add showCutlistRows checkbox (useState)
└── Panel.tsx                      # MODIFY: Add showCutlistRows useState + orchestration
```

**State Management Strategy:**
- **PluginSettings (via usePluginSettings hook):** Backend generation settings that require API call
- **Regular useState in Panel.tsx:** Frontend display filters (allocations, on-order, cutlists)

---

## Phase 1: Backend Changes (1-1.5 hours)

### 1.1 Remove Settings from core.py

**File:** `flat_bom_generator/core.py`

**Remove:**
```python
"MAX_DEPTH": {...},
"SHOW_PURCHASED_ASSEMBLIES": {...},
"INCLUDE_INTERNAL_FAB_IN_CUTLIST": {...},
```

**Keep:**
- All category mappings
- CUTLIST_UNITS_FOR_INTERNAL_FAB

**Testing:** Verify plugin loads without errors

---

### 1.2 Update views.py Query Parameter Handling

**File:** `flat_bom_generator/views.py`

**Current Behavior:**
```python
# Lines ~255-270
max_depth_setting = plugin.get_setting("MAX_DEPTH", 0)
expand_purchased_assemblies = plugin.get_setting("SHOW_PURCHASED_ASSEMBLIES", False)
enable_ifab_cuts = plugin.get_setting("INCLUDE_INTERNAL_FAB_IN_CUTLIST", False)
```

**New Behavior:**
```python
# Hardcoded defaults (no plugin.get_setting())
max_depth = 0
expand_purchased_assemblies = False
enable_ifab_cuts = False

# Override with query parameters if provided
max_depth_param = request.query_params.get('max_depth', None)
if max_depth_param is not None:
    try:
        max_depth = int(max_depth_param)
    except ValueError:
        return Response(
            {"error": "max_depth must be an integer"},
            status=status.HTTP_400_BAD_REQUEST
        )

expand_param = request.query_params.get('expand_purchased_assemblies', None)
if expand_param is not None:
    expand_purchased_assemblies = expand_param.lower() in ['true', '1', 'yes']

include_ifab_param = request.query_params.get('include_internal_fab_in_cutlist', None)
if include_ifab_param is not None:
    enable_ifab_cuts = include_ifab_param.lower() in ['true', '1', 'yes']
```

**Backward Compatibility:** Defaults remain the same (0, False, False)

**Testing:** 
- Verify API works without query params (uses defaults)
- Verify query params override defaults
- Verify invalid max_depth returns 400 error

---

### 1.3 Add cutlist_units_for_ifab to API Response

**File:** `flat_bom_generator/views.py`

**Current metadata structure** (lines ~405-420):
```python
metadata = {
    "part_id": part_id,
    "part_name": part.name if part else None,
    "ipn": part.IPN if part else None,
    "total_unique_parts": len(flat_bom),
    "total_imps_processed": imp_count,
    "warnings": warnings_data,
}
```

**Add to metadata:**
```python
metadata = {
    "part_id": part_id,
    "part_name": part.name if part else None,
    "ipn": part.IPN if part else None,
    "total_unique_parts": len(flat_bom),
    "total_imps_processed": imp_count,
    "warnings": warnings_data,
    "cutlist_units_for_ifab": plugin.get_setting("CUTLIST_UNITS_FOR_INTERNAL_FAB", "mm,in,cm") if plugin else "mm,in,cm",
}
```

**Testing:**
- Verify metadata includes cutlist_units_for_ifab
- Verify default is "mm,in,cm" when plugin not available

---

### 1.4 Update FlatBOMResponseSerializer

**File:** `flat_bom_generator/serializers.py`

**Current MetadataSerializer** (lines ~140-150):
```python
class FlatBOMMetadataSerializer(serializers.Serializer):
    part_id = serializers.IntegerField()
    part_name = serializers.CharField(allow_null=True)
    ipn = serializers.CharField(allow_null=True)
    total_unique_parts = serializers.IntegerField()
    total_imps_processed = serializers.IntegerField()
    warnings = BOMWarningSerializer(many=True)
```

**Add field:**
```python
class FlatBOMMetadataSerializer(serializers.Serializer):
    part_id = serializers.IntegerField()
    part_name = serializers.CharField(allow_null=True)
    ipn = serializers.CharField(allow_null=True)
    total_unique_parts = serializers.IntegerField()
    total_imps_processed = serializers.IntegerField()
    warnings = BOMWarningSerializer(many=True)
    cutlist_units_for_ifab = serializers.CharField()  # NEW
```

**Testing:**
- Verify serializer validates cutlist_units_for_ifab field
- Run serializer tests to ensure no regressions

---

### 1.5 Backend Testing Checklist

**Unit Tests:**
- [ ] Plugin loads without removed settings
- [ ] FlatBOMMetadataSerializer includes cutlist_units_for_ifab

**Integration Tests:**
- [ ] API works without query params (defaults)
- [ ] max_depth query param overrides default
- [ ] expand_purchased_assemblies query param overrides default
- [ ] include_internal_fab_in_cutlist query param overrides default
- [ ] Invalid max_depth returns 400 error
- [ ] Response includes cutlist_units_for_ifab in metadata

**Manual Testing:**
- [ ] Generate BOM without query params (should work)
- [ ] Add `?max_depth=5` to URL (should limit depth)
- [ ] Check response metadata for cutlist_units_for_ifab

---

## Phase 2: Frontend Types & Interfaces (0.5 hours)

### 2.1 Create PluginSettings Interface

**File:** `frontend/src/types/PluginSettings.ts` (NEW)

```typescript
/**
 * Plugin generation settings (moved from admin panel to UI)
 * These settings are persisted to localStorage and sent as query params to backend.
 * They trigger BOM regeneration when changed.
 */
export interface PluginSettings {
  /** Maximum BOM traversal depth (0 = unlimited) */
  maxDepth: number;
  
  /** Expand assemblies with default suppliers */
  expandPurchasedAssemblies: boolean;
  
  /** Include Internal Fab parts in cutlist processing */
  includeInternalFabInCutlist: boolean;
}

/**
 * Default plugin settings (hardcoded)
 */
export const DEFAULT_PLUGIN_SETTINGS: PluginSettings = {
  maxDepth: 0,
  expandPurchasedAssemblies: false,
  includeInternalFabInCutlist: false,
};

/**
 * Note: Frontend-only display filters (includeAllocations, includeOnOrder, showCutlistRows)
 * are managed as regular useState in Panel.tsx. They don't need persistence or backend
 * communication, so they're kept separate from PluginSettings.
 */

/**
 * Units for Internal Fab cutlist processing (from plugin config)
 */
export interface CutlistUnits {
  units: string; // e.g., "mm, in, cm"
}
```

**Testing:**
- TypeScript compiles without errors
- Defaults match backend defaults

---

### 2.2 Update FlatBomResponse Type

**File:** `frontend/src/types/FlatBomTypes.ts`

**Current metadata type** (approximate location):
```typescript
interface FlatBomMetadata {
  part_id: number;
  part_name: string | null;
  ipn: string | null;
  total_unique_parts: number;
  total_imps_processed: number;
  warnings: BOMWarning[];
}
```

**Add field:**
```typescript
interface FlatBomMetadata {
  part_id: number;
  part_name: string | null;
  ipn: string | null;
  total_unique_parts: number;
  total_imps_processed: number;
  warnings: BOMWarning[];
  cutlist_units_for_ifab: string;  // NEW
}
```

**Testing:**
- TypeScript compiles without errors
- API response matches type definition

---

## Phase 3: Frontend State Management (1-1.5 hours)

### 3.1 Create usePluginSettings Hook

**File:** `frontend/src/hooks/usePluginSettings.ts` (NEW)

```typescript
import { useState, useEffect, useCallback } from 'react';
import { DEFAULT_PLUGIN_SETTINGS, PluginSettings } from '../types/PluginSettings';

const STORAGE_KEY = 'flatbom_plugin_settings';
const HAS_GENERATED_KEY = 'flatbom_has_generated';

export function usePluginSettings() {
  // Load from localStorage or use defaults
  const [settings, setSettings] = useState<PluginSettings>(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? JSON.parse(stored) : DEFAULT_PLUGIN_SETTINGS;
  });

  const [hasGeneratedOnce, setHasGeneratedOnce] = useState<boolean>(() => {
    return localStorage.getItem(HAS_GENERATED_KEY) === 'true';
  });

  // Persist settings to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
  }, [settings]);

  // Persist hasGeneratedOnce to localStorage
  useEffect(() => {
    localStorage.setItem(HAS_GENERATED_KEY, hasGeneratedOnce.toString());
  }, [hasGeneratedOnce]);

  // Update individual setting
  const updateSetting = useCallback(<K extends keyof PluginSettings>(
    key: K,
    value: PluginSettings[K]
  ) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
  }, []);

  // Reset to defaults
  const resetToDefaults = useCallback(() => {
    setSettings(DEFAULT_PLUGIN_SETTINGS);
  }, []);

  // Check if settings differ from defaults
  const hasCustomSettings = useCallback(() => {
    return (
      settings.maxDepth !== DEFAULT_PLUGIN_SETTINGS.maxDepth ||
      settings.expandPurchasedAssemblies !== DEFAULT_PLUGIN_SETTINGS.expandPurchasedAssemblies ||
      settings.includeInternalFabInCutlist !== DEFAULT_PLUGIN_SETTINGS.includeInternalFabInCutlist
    );
  }, [settings]);

  // Mark as generated (triggers progressive disclosure)
  const markAsGenerated = useCallback(() => {
    setHasGeneratedOnce(true);
  }, []);

  return {
    settings,
    updateSetting,
    resetToDefaults,
    hasCustomSettings: hasCustomSettings(),
    hasGeneratedOnce,
    markAsGenerated,
  };
}
```

**Testing:**
- localStorage read/write works
- Settings persist across page reloads
- resetToDefaults restores defaults
- hasCustomSettings detects changes

---

### 3.2 Update useFlatBom Hook

**File:** `frontend/src/hooks/useFlatBom.ts`

**Add settings parameter** to fetchBom function:

```typescript
const fetchBom = useCallback(
  async (settings?: PluginSettings) => {  // PluginSettings has 3 backend fields only
    if (!partId) return;

    setLoading(true);
    setError(null);

    try {
      // Build query params from backend settings (not frontend filters)
      const params = new URLSearchParams();
      if (settings) {
        if (settings.maxDepth > 0) {
          params.append('max_depth', settings.maxDepth.toString());
        }
        if (settings.expandPurchasedAssemblies) {
          params.append('expand_purchased_assemblies', 'true');
        }
        if (settings.includeInternalFabInCutlist) {
          params.append('include_internal_fab_in_cutlist', 'true');
        }
        // Note: showCutlistRows NOT sent to backend (frontend-only filter)
      }

      const url = `/plugin/flat-bom-generator/flat-bom/${partId}/?${params.toString()}`;
      const response = await api.get(url);
      
      setBomData(response.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  },
  [partId, api]
);
```

**Testing:**
- Query params correctly appended to URL
- Backend receives parameters
- BOM generation respects settings

---

## Phase 4: Frontend Components (2-3 hours)

### 4.1 Create SettingsPanel Component

**File:** `frontend/src/components/SettingsPanel.tsx` (NEW)

```typescript
import { Paper, NumberInput, Switch, Group, Button, Text, Stack } from '@mantine/core';
import { PluginSettings } from '../types/PluginSettings';

interface SettingsPanelProps {
  settings: PluginSettings;
  cutlistUnits: string;
  onUpdate: <K extends keyof PluginSettings>(key: K, value: PluginSettings[K]) => void;
  onApply: () => void;
  onReset: () => void;
}

export function SettingsPanel({
  settings,
  cutlistUnits,
  onUpdate,
  onApply,
  onReset,
}: SettingsPanelProps) {
  return (
    <Paper withBorder p="md" mb="md">
      <Text size="lg" fw={500} mb="sm">
        📋 Generation Settings
      </Text>

      <Stack gap="sm">
        <NumberInput
          label="Maximum Traversal Depth"
          description="0 = unlimited"
          value={settings.maxDepth}
          onChange={(value) => onUpdate('maxDepth', Number(value) || 0)}
          min={0}
        />

        <Switch
          label="Expand Purchased Assemblies"
          description="Expand assemblies with default suppliers"
          checked={settings.expandPurchasedAssemblies}
          onChange={(e) => onUpdate('expandPurchasedAssemblies', e.currentTarget.checked)}
        />

        <Switch
          label={`Include Ifab in Cutlist (${cutlistUnits})`}
          description="Process Internal Fab parts as cutlist items"
          checked={settings.includeInternalFabInCutlist}
          onChange={(e) => onUpdate('includeInternalFabInCutlist', e.currentTarget.checked)}
        />
      </Stack>

      <Group mt="md">
        <Button onClick={onApply}>Apply Settings</Button>
        <Button variant="subtle" onClick={onReset}>
          Reset to Defaults
        </Button>
      </Group>
    </Paper>
  );
}
```

**Testing:**
- Renders without errors
- Switch toggles update state
- NumberInput updates maxDepth
- Apply/Reset buttons call handlers

---

### 4.2 Create SettingsDrawer Component

**File:** `frontend/src/components/SettingsDrawer.tsx` (NEW)

```typescript
import { Drawer, NumberInput, Switch, Group, Button, Text, Stack, Divider } from '@mantine/core';
import { PluginSettings } from '../types/PluginSettings';

interface SettingsDrawerProps {
  opened: boolean;
  onClose: () => void;
  settings: PluginSettings;
  cutlistUnits: string;
  onUpdate: <K extends keyof PluginSettings>(key: K, value: PluginSettings[K]) => void;
  onApply: () => void;
  onReset: () => void;
}

export function SettingsDrawer({
  opened,
  onClose,
  settings,
  cutlistUnits,
  onUpdate,
  onApply,
  onReset,
}: SettingsDrawerProps) {
  const handleApply = () => {
    onApply();
    onClose();
  };

  return (
    <Drawer
      opened={opened}
      onClose={onClose}
      title="Generation Settings"
      position="right"
      size="md"
    >
      <Stack gap="md">
        <div>
          <Text size="sm" fw={500} c="dimmed" mb="xs">
            Backend Settings
          </Text>
          <Text size="xs" c="dimmed" mb="sm">
            (triggers auto-refresh on Apply)
          </Text>
          <Divider mb="sm" />

          <Stack gap="sm">
            <NumberInput
              label="Max Depth"
              description="0 = unlimited"
              value={settings.maxDepth}
              onChange={(value) => onUpdate('maxDepth', Number(value) || 0)}
              min={0}
            />

            <Switch
              label="Expand Assemblies"
              description="Expand assemblies with default suppliers"
              checked={settings.expandPurchasedAssemblies}
              onChange={(e) => onUpdate('expandPurchasedAssemblies', e.currentTarget.checked)}
            />

            <Switch
              label="Include Ifab in Cutlist"
              description={`Process Internal Fab parts (${cutlistUnits})`}
              checked={settings.includeInternalFabInCutlist}
              onChange={(e) => onUpdate('includeInternalFabInCutlist', e.currentTarget.checked)}
            />
          </Stack>
        </div>

        <Group mt="md">
          <Button onClick={handleApply}>Apply</Button>
          <Button variant="subtle" onClick={onReset}>
            Reset to Defaults
          </Button>
        </Group>
      </Stack>
    </Drawer>
  );
}
```

**Testing:**
- Drawer opens/closes correctly
- Settings update in state
- Apply closes drawer and triggers regeneration
- Reset restores defaults

---

### 4.3 Update ControlBar Component

**File:** `frontend/src/components/ControlBar.tsx`

**Add showCutlistRows checkbox** alongside allocations/on-order:

```typescript
// Add to props interface
interface ControlBarProps {
  // ... existing props
  showCutlistRows: boolean;           // NEW - same pattern as includeAllocations
  onShowCutlistRowsChange: (value: boolean) => void;
}

// Add checkbox to JSX (after On Order checkbox)
<Checkbox
  label="Cutlists"
  checked={showCutlistRows}
  onChange={(e) => onShowCutlistRowsChange(e.currentTarget.checked)}
/>
```

**Testing:**
- Checkbox renders
- Toggling updates state
- Table filters cutlist rows correctly

---

### 4.4 Update Panel.tsx Orchestration

**File:** `frontend/src/Panel.tsx`

**Add at top:**
```typescript
import { usePluginSettings } from './hooks/usePluginSettings';
import { SettingsPanel } from './components/SettingsPanel';
import { SettingsDrawer } from './components/SettingsDrawer';
```

**Add state management:**
```typescript
const {
  settings,
  updateSetting,
  resetToDefaults,
  hasCustomSettings,
  hasGeneratedOnce,
  markAsGenerated,
} = usePluginSettings();

const [settingsDrawerOpen, setSettingsDrawerOpen] = useState(false);
```

**Update fetchBom calls:**
```typescript
const handleGenerate = () => {
  fetchBom(settings);
  markAsGenerated();
};

const handleApplySettings = () => {
  fetchBom(settings);
  markAsGenerated();
};
```

**Conditional rendering:**
```typescript
{!hasGeneratedOnce && (
  <SettingsPanel
    settings={settings}
    cutlistUnits={bomData?.metadata?.cutlist_units_for_ifab || 'mm,in,cm'}
    onUpdate={updateSetting}
    onApply={handleApplySettings}
    onReset={resetToDefaults}
  />
)}

<SettingsDrawer
  opened={settingsDrawerOpen}
  onClose={() => setSettingsDrawerOpen(false)}
  settings={settings}
  cutlistUnits={bomData?.metadata?.cutlist_units_for_ifab || 'mm,in,cm'}
  onUpdate={updateSetting}
  onApply={handleApplySettings}
  onReset={resetToDefaults}
/>
```

**Add gear icon to ControlBar:**
```typescript
<ActionIcon
  variant={hasCustomSettings ? 'filled' : 'subtle'}
  color={hasCustomSettings ? 'blue' : 'gray'}
  onClick={() => setSettingsDrawerOpen(true)}
>
  <IconSettings size={18} />
</ActionIcon>
```

**Testing:**
- Settings panel shows before first generation
- Panel hides after first generation
- Gear icon appears after first generation
- Gear icon is blue when settings are custom
- Drawer opens when clicking gear icon

---

## Phase 5: Table Filtering (0.5-1 hour)

### 5.1 Implement showCutlistRows Filter

**File:** `frontend/src/utils/filterCutlistRows.ts` (NEW)

```typescript
import { BomItem } from '../types/FlatBomTypes';

/**
 * Filter cutlist child rows based on showCutlistRows setting
 * 
 * Cutlist rows are identified by having cut_list or internal_fab_cut_list data
 * and being inserted after their parent part in the table.
 */
export function filterCutlistRows(
  items: BomItem[],
  showCutlistRows: boolean
): BomItem[] {
  if (showCutlistRows) {
    return items; // Show all rows
  }

  // Hide rows that are cutlist children
  // (These would have been inserted by expansion logic)
  return items.filter((item) => {
    // Keep parent rows (they have cut_list/internal_fab_cut_list but are not children themselves)
    // This logic depends on how cutlist expansion works in your current implementation
    // You may need to adjust based on actual row structure
    
    // Simple approach: Filter out rows that ARE cutlist data
    // (Assumes cutlist children are marked somehow - check current implementation)
    return !item.is_cutlist_child; // Adjust based on actual property
  });
}
```

**Note:** This implementation depends on how cutlist rows are currently identified. Check existing cutlist expansion logic to determine the correct filter condition.

**Testing:**
- Toggle showCutlistRows on/off
- Verify cutlist rows hide when OFF
- Verify parent rows still show when OFF
- Verify all rows show when ON

---

### 5.2 Apply Filter in Panel.tsx

**Update filteredAndSortedData useMemo:**

```typescript
const filteredAndSortedData = useMemo(() => {
  if (!bomData?.bom_items) return [];

  let data = [...bomData.bom_items];

  // Apply search filter
  if (searchQuery) {
    data = data.filter(
      (item) =>
        item.ipn.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.part_name.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }

  // Apply cutlist row filter
  data = filterCutlistRows(data, showCutlistRows);

  // Apply sorting
  // ... existing sort logic

  return data;
}, [bomData, searchQuery, showCutlistRows, sortStatus]);
```

**Testing:**
- Cutlist filter works with search
- Cutlist filter works with sorting
- Stats update correctly when filtered

---

## Phase 6: Testing Strategy (1-2 hours)

### 6.1 Backend Integration Tests

**File:** `flat_bom_generator/tests/integration/test_settings_ui_migration.py` (NEW)

```python
"""Integration tests for Settings UI migration."""

from InvenTree.unit_test import InvenTreeAPITestCase
from part.models import Part, PartCategory


class SettingsUIMigrationTests(InvenTreeAPITestCase):
    """Test that removed settings work via query params."""
    
    def setUp(self):
        super().setUp()
        self.test_cat = PartCategory.objects.create(name='TestCat')
        self.test_part = Part.objects.create(
            name='TestPart',
            category=self.test_cat,
            assembly=True,
        )
    
    def test_api_works_without_query_params(self):
        """Verify API uses defaults when no query params provided."""
        url = f'/plugin/flat-bom-generator/flat-bom/{self.test_part.pk}/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Should use defaults: max_depth=0, expand=False, include_ifab=False
    
    def test_max_depth_query_param(self):
        """Verify max_depth query param overrides default."""
        url = f'/plugin/flat-bom-generator/flat-bom/{self.test_part.pk}/?max_depth=5'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Backend should limit traversal to depth 5
    
    def test_expand_query_param(self):
        """Verify expand_purchased_assemblies query param works."""
        url = f'/plugin/flat-bom-generator/flat-bom/{self.test_part.pk}/?expand_purchased_assemblies=true'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
    
    def test_include_ifab_query_param(self):
        """Verify include_internal_fab_in_cutlist query param works."""
        url = f'/plugin/flat-bom-generator/flat-bom/{self.test_part.pk}/?include_internal_fab_in_cutlist=true'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
    
    def test_invalid_max_depth_returns_400(self):
        """Verify invalid max_depth returns error."""
        url = f'/plugin/flat-bom-generator/flat-bom/{self.test_part.pk}/?max_depth=invalid'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 400)
    
    def test_response_includes_cutlist_units(self):
        """Verify response metadata includes cutlist_units_for_ifab."""
        url = f'/plugin/flat-bom-generator/flat-bom/{self.test_part.pk}/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('cutlist_units_for_ifab', response.data['metadata'])
        self.assertIsInstance(response.data['metadata']['cutlist_units_for_ifab'], str)
```

**Run:**
```powershell
.\scripts\Test-Plugin.ps1 -Plugin "FlatBOMGenerator" -Integration
```

---

### 6.2 Frontend Component Tests

**File:** `frontend/src/components/SettingsPanel.test.tsx` (NEW)

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { SettingsPanel } from './SettingsPanel';
import { DEFAULT_PLUGIN_SETTINGS } from '../types/PluginSettings';

describe('SettingsPanel', () => {
  const mockOnUpdate = jest.fn();
  const mockOnApply = jest.fn();
  const mockOnReset = jest.fn();

  it('renders with default settings', () => {
    render(
      <SettingsPanel
        settings={DEFAULT_PLUGIN_SETTINGS}
        cutlistUnits="mm, in, cm"
        onUpdate={mockOnUpdate}
        onApply={mockOnApply}
        onReset={mockOnReset}
      />
    );

    expect(screen.getByText('Generation Settings')).toBeInTheDocument();
  });

  it('calls onUpdate when switch toggled', () => {
    render(
      <SettingsPanel
        settings={DEFAULT_PLUGIN_SETTINGS}
        cutlistUnits="mm, in, cm"
        onUpdate={mockOnUpdate}
        onApply={mockOnApply}
        onReset={mockOnReset}
      />
    );

    const expandSwitch = screen.getByLabelText('Expand Purchased Assemblies');
    fireEvent.click(expandSwitch);

    expect(mockOnUpdate).toHaveBeenCalledWith('expandPurchasedAssemblies', true);
  });

  it('calls onApply when Apply button clicked', () => {
    render(
      <SettingsPanel
        settings={DEFAULT_PLUGIN_SETTINGS}
        cutlistUnits="mm, in, cm"
        onUpdate={mockOnUpdate}
        onApply={mockOnApply}
        onReset={mockOnReset}
      />
    );

    const applyButton = screen.getByText('Apply Settings');
    fireEvent.click(applyButton);

    expect(mockOnApply).toHaveBeenCalled();
  });
});
```

**Run:**
```bash
cd frontend
npm test
```

---

### 6.3 Manual Testing Checklist

**Before First Generation:**
- [ ] Settings panel visible
- [ ] All 3 settings displayed with defaults
- [ ] Units displayed correctly (from plugin config)
- [ ] Apply button triggers BOM generation
- [ ] Reset button restores defaults

**After First Generation:**
- [ ] Settings panel hides
- [ ] Gear icon appears in ControlBar
- [ ] Gear icon is gray (default settings)
- [ ] Cutlist checkbox visible in ControlBar
- [ ] Cutlist checkbox ON by default

**Settings Drawer:**
- [ ] Clicking gear icon opens drawer
- [ ] Drawer slides from right
- [ ] All 3 settings displayed
- [ ] Units displayed correctly for Include Ifab setting
- [ ] Apply button triggers regeneration (drawer stays open)
- [ ] X button closes drawer without regenerating
- [ ] Reset button restores defaults

**Custom Settings:**
- [ ] Change max_depth to 5 → Gear icon turns blue
- [ ] Toggle expand assemblies → Gear icon stays blue
- [ ] Reset → Gear icon returns to gray
- [ ] Settings persist after page reload (localStorage)

**Cutlist Row Filtering:**
- [ ] Toggle cutlist checkbox OFF → Cutlist rows hide
- [ ] Toggle cutlist checkbox ON → Cutlist rows show
- [ ] Parent rows always visible
- [ ] Stats update correctly when filtered

**Query Parameters:**
- [ ] Add `?max_depth=5` to URL → BOM limited to depth 5
- [ ] Add `?expand_purchased_assemblies=true` → Assemblies expanded
- [ ] Add `?include_internal_fab_in_cutlist=true` → Internal Fab cutlist generated

---

## Phase 7: Deployment & Verification (0.5-1 hour)

### 7.1 Pre-Deployment Checklist

- [ ] All backend tests pass
- [ ] All frontend tests pass
- [ ] TypeScript compiles without errors
- [ ] Frontend builds successfully
- [ ] Manual testing complete
- [ ] Documentation updated

### 7.2 Build & Deploy

```powershell
# Build plugin
cd 'C:\PythonProjects\Inventree Plugin Creator\inventree-plugin-ai-toolkit'
.\scripts\Build-Plugin.ps1 -Plugin "FlatBOMGenerator"

# Deploy to staging
.\scripts\Deploy-Plugin.ps1 -Plugin "FlatBOMGenerator" -Server staging
```

### 7.3 Staging Verification

- [ ] Plugin loads without errors
- [ ] Generate BOM without settings (uses defaults)
- [ ] Change settings and regenerate
- [ ] Verify query params in network tab
- [ ] Check browser console for errors
- [ ] Test cutlist row filtering
- [ ] Test progressive disclosure (first gen → hide panel)

### 7.4 Commit & Push

```bash
git add -A
git commit -m "feat: migrate settings from admin panel to frontend UI

- Remove MAX_DEPTH, SHOW_PURCHASED_ASSEMBLIES, INCLUDE_INTERNAL_FAB_IN_CUTLIST from plugin settings
- Accept query params in views.py with hardcoded defaults
- Add cutlist_units_for_ifab to API response metadata
- Create SettingsPanel component (before-first-gen expanded view)
- Create SettingsDrawer component (after-first-gen drawer)
- Add usePluginSettings hook with localStorage persistence
- Add showCutlistRows toggle to ControlBar
- Implement progressive disclosure (panel → drawer)
- Add gear icon with blue indicator for custom settings

BREAKING CHANGE: Plugin settings removed from admin panel, now UI-only"

git push origin feature/settings-ui
```

---

## Documentation Updates

### README.md

**Remove from Plugin Settings table:**
- Maximum Traversal Depth
- Expand Purchased Assemblies
- Include Internal Fab Parts in Cutlist

**Add to Usage section:**
```markdown
### Generation Settings

Settings are configured directly in the panel UI:

**Before First Generation:**
Settings panel is visible to guide configuration.

**After First Generation:**
Settings collapse to a gear icon (⚙️). Click to open settings drawer.

**Available Settings:**
- **Max Depth** - Limit BOM traversal depth (0 = unlimited)
- **Expand Purchased Assemblies** - Expand assemblies with default suppliers
- **Include Ifab in Cutlist** - Process Internal Fab parts as cutlist items

**Display Filters (ControlBar):**
- **Build Quantity** - Multiply requirements
- **Allocations** - Use available vs total stock
- **On Order** - Include incoming in shortfall
- **Cutlists** - Show/hide cutlist child rows

Settings persist per browser via localStorage.
```

### ARCHITECTURE.md

**Update API Endpoint section:**
```markdown
**Query Parameters:**
- `max_depth` (optional): Maximum BOM traversal depth (default: 0 = unlimited)
- `expand_purchased_assemblies` (optional): Expand purchased assemblies (default: false)
- `include_internal_fab_in_cutlist` (optional): Include Internal Fab cutlist processing (default: false)
```

**Update Response Fields:**
```markdown
**Metadata Fields:**
- `cutlist_units_for_ifab`: Units for Internal Fab cutlist processing (e.g., "mm,in,cm")
```

### ROADMAP.md

**Mark Settings UI/UX as COMPLETE:**
```markdown
### ✅ Settings UI/UX Improvement (COMPLETE)
**Status:** Deployed v0.11.0

**Implementation:**
- Removed 3 settings from plugin admin panel
- Progressive disclosure: Panel before first gen, drawer after
- localStorage persistence
- Frequency-based grouping (ControlBar vs Drawer)
- Dynamic units display for Include Ifab setting
```

---

## Rollback Plan

If critical issues arise in production:

### Emergency Rollback Steps

1. **Revert to v0.10.0:**
```bash
git checkout main
```

2. **Quick fix option:** Add settings back to core.py
```python
"MAX_DEPTH": {
    "name": "Maximum Traversal Depth",
    "validator": int,
    "default": 0,
},
# ... restore other settings
```

3. **Deploy previous version:**
```powershell
.\scripts\Deploy-Plugin.ps1 -Plugin "FlatBOMGenerator" -Server staging
```

### Partial Rollback

If only frontend issues:
- Keep backend changes (query params)
- Temporarily disable frontend settings UI
- Users can still use query params manually

---

## Success Criteria

**Backend:**
- [ ] Plugin loads without removed settings
- [ ] API accepts query params
- [ ] Backward compatible (defaults match old behavior)
- [ ] Response includes cutlist_units_for_ifab

**Frontend:**
- [ ] Progressive disclosure works (panel → drawer)
- [ ] Settings persist in localStorage
- [ ] Gear icon indicates custom settings
- [ ] Cutlist row filtering works
- [ ] All controls in correct locations (ControlBar vs Drawer)

**User Experience:**
- [ ] First-time users see settings panel (guided)
- [ ] Repeat users see clean UI (drawer hidden)
- [ ] Settings changes trigger regeneration
- [ ] No page navigation required
- [ ] Matches InvenTree UI patterns

**Performance:**
- [ ] No regression in BOM generation time
- [ ] localStorage operations fast
- [ ] UI remains responsive

---

## Estimated Timeline

| Phase | Task | Time | Status |
|-------|------|------|--------|
| 1 | Backend Changes | 1-1.5h | Not Started |
| 2 | Frontend Types | 0.5h | Not Started |
| 3 | State Management | 1-1.5h | Not Started |
| 4 | UI Components | 2-3h | Not Started |
| 5 | Table Filtering | 0.5-1h | Not Started |
| 6 | Testing | 1-2h | Not Started |
| 7 | Deployment | 0.5-1h | Not Started |
| **Total** | | **5-8h** | |

---

## Next Steps

1. Review and approve this plan
2. Start Phase 1: Backend Changes
3. Test backend changes on staging
4. Proceed to Phase 2: Frontend implementation
5. Incremental testing after each phase
6. Final verification before merge to main

**Ready to begin?**

---

## Implementation Decisions (January 20, 2026)

Key decisions made during planning phase:

1. **Default Values:** Match existing plugin defaults (0, false, false) ✅
2. **Migration Strategy:** No migration - use hardcoded defaults, users reconfigure in UI
3. **localStorage Key:** `flatbom_plugin_settings` (global per-browser)
4. **Error Handling:** Graceful degradation - settings work in-memory if localStorage unavailable
5. **Query Parameter Naming:** `include_internal_fab_in_cutlist` (matches setting name)
6. **Apply Button Behavior:** Triggers refresh but doesn't close drawer (InvenTree filter pattern). Drawer closes only via X button.
7. **Progressive Disclosure:** Option C - Settings expanded on initial page load, collapse to gear icon after first BOM generation (remembered in localStorage)
8. **Documentation Approach:** Clean removal, no deprecation notices
9. **Backward Compatibility:** No support for old parameter names (small install base)
10. **Frontend Validation:** Simple validation (maxDepth >= 0) in UI before sending to backend

---

*Last Updated: January 20, 2026*
