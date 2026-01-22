import {
  Button,
  Group,
  NumberInput,
  Paper,
  Stack,
  Switch,
  Text
} from '@mantine/core';

import type { PluginSettings } from '../types/PluginSettings';

interface SettingsPanelProps {
  title?: string;
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
  title,
  settings,
  cutlistUnits,
  onUpdateSetting,
  onResetToDefaults
}: SettingsPanelProps) {
  return (
    <Paper withBorder p='md' mb='md'>
      <Stack gap='md'>
        {title && (
          <Text size='xs' tt='uppercase' fw={600} c='dimmed'>
            {title}
          </Text>
        )}
        <NumberInput
          label='Maximum Traversal Depth'
          description='0 = unlimited, lower values stop BOM traversal earlier'
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
          label={`Include Internal Fab in Cutlists${cutlistUnits !== 'units' ? ` (${cutlistUnits})` : ''}`}
          description='Show internal fabrication parts expanded in cutlist breakdown'
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
