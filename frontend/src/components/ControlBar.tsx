import {
  ActionIcon,
  Badge,
  Button,
  Checkbox,
  Divider,
  Group,
  Menu,
  NumberInput,
  Stack,
  Tooltip
} from '@mantine/core';
import {
  IconAdjustments,
  IconDownload,
  IconRefresh,
  IconSettings
} from '@tabler/icons-react';
import type { DataTableColumn } from 'mantine-datatable';

interface ControlBarProps {
  buildQuantity: number;
  onBuildQuantityChange: (value: number) => void;
  includeAllocations: boolean;
  onIncludeAllocationsChange: (checked: boolean) => void;
  includeOnOrder: boolean;
  onIncludeOnOrderChange: (checked: boolean) => void;
  onRefresh: () => void;
  loading: boolean;
  onExport: () => void;
  columns: DataTableColumn<any>[];
  hiddenColumns: Set<string>;
  onToggleColumn: (accessor: string) => void;
  hasCustomSettings?: boolean;
  onOpenSettings?: () => void;
}

/**
 * Control bar with build quantity, checkboxes, and action buttons
 */
export function ControlBar({
  buildQuantity,
  onBuildQuantityChange,
  includeAllocations,
  onIncludeAllocationsChange,
  includeOnOrder,
  onIncludeOnOrderChange,
  onRefresh,
  loading,
  onExport,
  columns,
  hiddenColumns,
  onToggleColumn,
  hasCustomSettings = false,
  onOpenSettings
}: ControlBarProps) {
  return (
    <Group gap='xs' align='flex-end' wrap='wrap'>
      <NumberInput
        label='Build Quantity'
        value={buildQuantity}
        onChange={(value) =>
          onBuildQuantityChange(typeof value === 'number' ? value : 1)
        }
        min={1}
        step={1}
        style={{ width: 150 }}
      />
      <Stack gap='xs'>
        <Checkbox
          label='Include Allocations in Build Margin (-)'
          checked={includeAllocations}
          onChange={(e) => onIncludeAllocationsChange(e.currentTarget.checked)}
        />
        <Checkbox
          label='Include On Order in Build Margin (+)'
          checked={includeOnOrder}
          onChange={(e) => onIncludeOnOrderChange(e.currentTarget.checked)}
        />
      </Stack>
      {onOpenSettings && (
        <ActionIcon
          variant='light'
          size='lg'
          onClick={onOpenSettings}
          aria-label='open-settings'
        >
          <Tooltip label='Generation Settings' position='top'>
            {hasCustomSettings ? (
              <Badge
                size='xs'
                circle
                color='blue'
                style={{ position: 'absolute', top: -4, right: -4 }}
              >
                ●
              </Badge>
            ) : null}
            <IconSettings />
          </Tooltip>
        </ActionIcon>
      )}
      <Button
        leftSection={<IconRefresh size={16} />}
        onClick={onRefresh}
        loading={loading}
      >
        Refresh
      </Button>
      <Button
        variant='light'
        leftSection={<IconDownload size={16} />}
        onClick={onExport}
      >
        Export CSV
      </Button>
      <Menu shadow='xs' closeOnItemClick={false}>
        <Menu.Target>
          <ActionIcon
            variant='light'
            size='lg'
            aria-label='table-select-columns'
          >
            <Tooltip label='Select Columns' position='top-end'>
              <IconAdjustments />
            </Tooltip>
          </ActionIcon>
        </Menu.Target>
        <Menu.Dropdown style={{ maxHeight: '400px', overflowY: 'auto' }}>
          <Menu.Label>Select Columns</Menu.Label>
          <Divider />
          {columns
            .filter((col: any) => col.toggleable !== false)
            .map((col: any) => (
              <Menu.Item key={col.accessor}>
                <Checkbox
                  checked={!hiddenColumns.has(col.accessor)}
                  label={col.title || col.accessor}
                  onChange={() => onToggleColumn(col.accessor)}
                  radius='sm'
                />
              </Menu.Item>
            ))}
        </Menu.Dropdown>
      </Menu>
    </Group>
  );
}
