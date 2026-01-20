import {
  Button,
  Group,
  NumberInput,
  Paper,
  Stack,
  Switch
} from '@mantine/core';

import type { PluginSettings } from '../types/PluginSettings';

interface SettingsPanelProps {
  settings: PluginSettings;
  cutlistUnits: string;
  onUpdateSetting: <K extends keyof PluginSettings>(
    key: K,
    value: PluginSettings[K]
  ) => void;
  onResetToDefaults: () => void;
}

/**
 * Settings panel component - shown before first BOM generation
 *
 * Displays backend settings in expanded Paper component for initial configuration.
 * Progressive disclosure: collapses to gear icon after first successful generation.
 */
export function SettingsPanel({
  settings,
  cutlistUnits,
  onUpdateSetting,
  onResetToDefaults
}: SettingsPanelProps) {
  return (
    <Paper withBorder p='md' mb='md'>
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

        <Group justify='flex-end'>
          <Button variant='subtle' onClick={onResetToDefaults}>
            Reset to Defaults
          </Button>
        </Group>
      </Stack>
    </Paper>
  );
}
