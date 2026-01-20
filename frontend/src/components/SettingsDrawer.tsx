import {
  Button,
  Drawer,
  Group,
  NumberInput,
  Stack,
  Switch
} from '@mantine/core';

import type { PluginSettings } from '../types/PluginSettings';

interface SettingsDrawerProps {
  opened: boolean;
  onClose: () => void;
  settings: PluginSettings;
  cutlistUnits: string;
  onUpdateSetting: <K extends keyof PluginSettings>(
    key: K,
    value: PluginSettings[K]
  ) => void;
  onResetToDefaults: () => void;
  onApply: () => void;
}

/**
 * Settings drawer component - slides from right after first BOM generation
 *
 * Provides access to backend settings without leaving the panel view.
 * Apply button triggers BOM regeneration with new settings.
 */
export function SettingsDrawer({
  opened,
  onClose,
  settings,
  cutlistUnits,
  onUpdateSetting,
  onResetToDefaults,
  onApply
}: SettingsDrawerProps) {
  return (
    <Drawer
      opened={opened}
      onClose={onClose}
      position='right'
      title='Generation Settings'
      size='md'
    >
      <Stack gap='md'>
        <NumberInput
          label='Maximum Traversal Depth'
          description='0 = unlimited, higher values stop BOM traversal earlier'
          value={settings.maxDepth}
          onChange={(val) =>
            onUpdateSetting('maxDepth', typeof val === 'number' ? val : 0)
          }
          min={0}
          max={20}
          step={1}
        />

        <Switch
          label='Expand Purchased Assemblies'
          description='Include purchased assemblies in the flat BOM (normally filtered as leaf parts)'
          checked={settings.expandPurchasedAssemblies}
          onChange={(event) =>
            onUpdateSetting(
              'expandPurchasedAssemblies',
              event.currentTarget.checked
            )
          }
        />

        <Switch
          label={`Include Ifab in Cutlist (${cutlistUnits})`}
          description='Show internal fabrication parts in cutlist breakdown with units'
          checked={settings.includeInternalFabInCutlist}
          onChange={(event) =>
            onUpdateSetting(
              'includeInternalFabInCutlist',
              event.currentTarget.checked
            )
          }
        />

        <Group justify='space-between' mt='xl'>
          <Button variant='subtle' onClick={onResetToDefaults}>
            Reset to Defaults
          </Button>
          <Button onClick={onApply}>Apply Settings</Button>
        </Group>
      </Stack>
    </Drawer>
  );
}
