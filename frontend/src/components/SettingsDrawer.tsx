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
          label='Include Internal Fab in Cutlists'
          description='Show cut-list rows for children of internal-supplier assemblies'
          checked={settings.includeInternalFabInCutlist}
          onChange={(event) =>
            onUpdateSetting(
              'includeInternalFabInCutlist',
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
