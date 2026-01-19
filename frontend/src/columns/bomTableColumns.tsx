import { Anchor, Badge, Group, Text, Tooltip } from '@mantine/core';
import { IconCornerDownRight } from '@tabler/icons-react';
import type { DataTableColumn } from 'mantine-datatable';
import type { BomItem } from '../types/BomTypes';
import { getDimmedOpacity, getPartTypeColor } from '../utils/colorUtils';

// Extend DataTableColumn to include switchable property (exists at runtime)
type ExtendedColumn<T> = DataTableColumn<T> & { switchable?: boolean };

interface BomTableColumnOptions {
  buildQuantity: number;
  includeAllocations: boolean;
  includeOnOrder: boolean;
  calculateShortfall: (item: BomItem) => number;
}

/**
 * Generate DataTable column definitions for BOM display
 */
export function createBomTableColumns({
  buildQuantity,
  includeAllocations,
  includeOnOrder,
  calculateShortfall
}: BomTableColumnOptions): ExtendedColumn<BomItem>[] {
  return [
    {
      accessor: 'full_name',
      title: 'Component',
      sortable: true,
      switchable: false,
      render: (record) => {
        if (record.is_cut_list_child) {
          return (
            <Group gap='xs' wrap='nowrap' justify='flex-end'>
              <IconCornerDownRight
                size={40}
                stroke={1.5}
                style={{ color: 'var(--mantine-color-blue-5)' }}
              />
            </Group>
          );
        }
        return (
          <Group gap='xs' wrap='nowrap'>
            {record.thumbnail && (
              <img
                src={record.thumbnail}
                alt={record.full_name}
                style={{ width: 40, height: 40, objectFit: 'contain' }}
              />
            )}
            <Anchor
              href={record.link}
              target='_blank'
              size='sm'
              style={{ textDecoration: 'none' }}
            >
              {record.full_name}
            </Anchor>
          </Group>
        );
      }
    },
    {
      accessor: 'ipn',
      title: 'IPN',
      sortable: true,
      switchable: true,
      render: (record) => (
        <Text size='sm' style={{ fontFamily: 'monospace' }}>
          {record.ipn}
        </Text>
      )
    },
    {
      accessor: 'description',
      title: 'Description',
      sortable: true,
      switchable: true,
      render: (record) => (
        <Text size='sm' lineClamp={2} title={record.description}>
          {record.description}
        </Text>
      )
    },
    {
      accessor: 'part_type',
      title: 'Type',
      sortable: true,
      switchable: true,
      render: (record) => {
        const baseType = record.part_type;
        const color = getPartTypeColor(baseType);

        // Internal Fab and CtL child rows get the CUT suffix
        const display =
          record.is_cut_list_child &&
          (baseType === 'Internal Fab' || baseType === 'CtL')
            ? `${baseType} - CUT`
            : baseType;

        return (
          <Tooltip label={display} withArrow>
            <Badge
              size='sm'
              color={color}
              variant='light'
              style={{
                maxWidth: 90,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                cursor: 'pointer',
                display: 'inline-block',
                verticalAlign: 'middle'
              }}
              tabIndex={0}
              aria-label={display}
            >
              {display}
            </Badge>
          </Tooltip>
        );
      }
    },
    {
      accessor: 'total_qty',
      title: 'Total Qty',
      sortable: true,
      switchable: true,
      render: (record) => {
        const totalRequired = record.total_qty * buildQuantity;
        if (record.is_cut_list_child) {
          const totalPieces = record.total_qty * buildQuantity;
          return (
            <Group
              gap='xs'
              justify='space-between'
              wrap='nowrap'
              style={{ maxWidth: '100%' }}
            >
              <Text size='sm' fw={700}>
                {totalPieces.toFixed(0)}
              </Text>
              <Text size='xs' c='dimmed'>
                pieces
              </Text>
            </Group>
          );
        }
        return (
          <Group
            gap='xs'
            justify='space-between'
            wrap='nowrap'
            style={{ maxWidth: '100%' }}
          >
            <Text size='sm' fw={700}>
              {totalRequired.toFixed(2)}
            </Text>
            {record.unit && (
              <Text size='xs' c='dimmed'>
                [{record.unit}]
              </Text>
            )}
          </Group>
        );
      }
    },
    {
      accessor: 'cut_length',
      title: 'Cut Length',
      sortable: false,
      switchable: false,
      render: (record) => {
        if (!record.cut_length) {
          return (
            <Text size='sm' c='dimmed'>
              -
            </Text>
          );
        }
        return (
          <Group
            gap='xs'
            justify='space-between'
            wrap='nowrap'
            style={{ maxWidth: '100%' }}
          >
            <Text size='sm'>{record.cut_length.toFixed(2)}</Text>
            {(record.cut_unit || record.unit) && (
              <Text size='xs' c='dimmed'>
                [{record.cut_unit || record.unit}]
              </Text>
            )}
          </Group>
        );
      }
    },
    {
      accessor: 'in_stock',
      title: 'In Stock',
      sortable: true,
      switchable: true,
      cellsStyle: () => ({ minWidth: 125 }),
      titleStyle: () => ({ minWidth: 125 }),
      render: (record) => {
        if (record.is_cut_list_child) {
          return (
            <Text size='sm' c='dimmed'>
              -
            </Text>
          );
        }

        const totalRequired = record.total_qty * buildQuantity;
        if (record.in_stock <= 0) {
          return (
            <Group gap='xs' wrap='nowrap' justify='space-between'>
              <Text c='red' fs='italic' size='sm'>
                No stock
              </Text>
              {record.unit && (
                <Text size='xs' c='dimmed'>
                  [{record.unit}]
                </Text>
              )}
            </Group>
          );
        } else if (record.in_stock < totalRequired) {
          return (
            <Group gap='xs' wrap='nowrap' justify='space-between'>
              <Badge
                color='orange'
                variant='light'
                style={{ minWidth: 'fit-content' }}
              >
                {record.in_stock.toFixed(2)}
              </Badge>
              {record.unit && (
                <Text size='xs' c='dimmed'>
                  [{record.unit}]
                </Text>
              )}
            </Group>
          );
        } else {
          return (
            <Group gap='xs' wrap='nowrap' justify='space-between'>
              <Badge
                color='green'
                variant='filled'
                style={{ minWidth: 'fit-content' }}
              >
                {record.in_stock.toFixed(2)}
              </Badge>
              {record.unit && (
                <Text size='xs' c='dimmed'>
                  [{record.unit}]
                </Text>
              )}
            </Group>
          );
        }
      }
    },
    {
      accessor: 'allocated',
      title: 'Allocated',
      sortable: true,
      switchable: true,
      cellsStyle: () => ({ minWidth: 125 }),
      titleStyle: () => ({ minWidth: 125 }),
      render: (record) => {
        const isDimmed = !includeAllocations;
        const opacity = getDimmedOpacity(isDimmed);
        if (record.is_cut_list_child) {
          return (
            <Text size='sm' c='dimmed'>
              -
            </Text>
          );
        }
        if (record.allocated > 0) {
          return (
            <Group gap='xs' wrap='nowrap' justify='space-between'>
              <Badge
                color='yellow'
                variant='light'
                style={{ opacity, minWidth: 'fit-content' }}
              >
                {record.allocated.toFixed(2)}
              </Badge>
              {record.unit && (
                <Text size='xs' c='dimmed' style={{ opacity }}>
                  [{record.unit}]
                </Text>
              )}
            </Group>
          );
        }
        return (
          <Group
            gap='xs'
            wrap='nowrap'
            justify='space-between'
            style={{ overflow: 'hidden' }}
          >
            <Text c='dimmed' size='sm' style={{ opacity }}>
              -
            </Text>
            {record.unit && (
              <Text size='xs' c='dimmed' style={{ opacity }}>
                [{record.unit}]
              </Text>
            )}
          </Group>
        );
      }
    },
    {
      accessor: 'on_order',
      title: 'On Order',
      sortable: true,
      switchable: true,
      cellsStyle: () => ({ minWidth: 125 }),
      titleStyle: () => ({ minWidth: 125 }),
      render: (record) => {
        const isDimmed = !includeOnOrder;
        const opacity = getDimmedOpacity(isDimmed);
        if (record.is_cut_list_child) {
          return (
            <Text size='sm' c='dimmed'>
              -
            </Text>
          );
        }
        if (record.on_order > 0) {
          return (
            <Group gap='xs' wrap='nowrap' justify='space-between'>
              <Badge
                color='blue'
                variant='light'
                style={{ opacity, minWidth: 'fit-content' }}
              >
                {record.on_order.toFixed(2)}
              </Badge>
              {record.unit && (
                <Text size='xs' c='dimmed' style={{ opacity }}>
                  [{record.unit}]
                </Text>
              )}
            </Group>
          );
        }
        return (
          <Group gap='xs' wrap='nowrap' justify='space-between'>
            <Text c='dimmed' size='sm' style={{ opacity }}>
              -
            </Text>
            {record.unit && (
              <Text size='xs' c='dimmed' style={{ opacity }}>
                [{record.unit}]
              </Text>
            )}
          </Group>
        );
      }
    },
    {
      accessor: 'shortfall',
      title: 'Build Margin',
      sortable: true,
      switchable: true,
      cellsStyle: () => ({ minWidth: 125 }),
      titleStyle: () => ({ minWidth: 125 }),
      render: (record) => {
        if (record.is_cut_list_child) {
          return (
            <Text size='sm' c='dimmed'>
              -
            </Text>
          );
        }

        const balance = calculateShortfall(record);

        if (balance < 0) {
          return (
            <Group gap='xs' wrap='nowrap' justify='space-between'>
              <Badge
                color='red'
                variant='filled'
                style={{ minWidth: 'fit-content' }}
              >
                {balance.toFixed(2)}
              </Badge>
              {record.unit && (
                <Text size='xs' c='dimmed'>
                  [{record.unit}]
                </Text>
              )}
            </Group>
          );
        }
        return (
          <Group gap='xs' wrap='nowrap' justify='space-between'>
            <Badge
              color='green'
              variant='filled'
              style={{ minWidth: 'fit-content' }}
            >
              +{balance.toFixed(2)}
            </Badge>
            {record.unit && (
              <Text size='xs' c='dimmed'>
                [{record.unit}]
              </Text>
            )}
          </Group>
        );
      }
    }
  ];
}
