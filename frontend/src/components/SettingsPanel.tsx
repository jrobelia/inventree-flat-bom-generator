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
          description='Show components of external-supplier assemblies instead of the assembly row'
          checked={settings.expandPurchasedAssemblies}
          onChange={(event) =>
            onUpdateSetting(
              'expandPurchasedAssemblies',
              event.currentTarget.checked
            )
          }
        />

        <Switch
          label='Include Substitute Parts'
          description='Fetch and display substitute part options with individual stock data'
          checked={settings.includeSubstitutes}
          onChange={(event) =>
            onUpdateSetting('includeSubstitutes', event.currentTarget.checked)
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
