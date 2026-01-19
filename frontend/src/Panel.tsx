// Import for type checking
import {
  checkPluginVersion,
  type InvenTreePluginContext
} from '@inventreedb/ui';
import {
  ActionIcon,
  Alert,
  Anchor,
  Badge,
  Button,
  Group,
  Loader,
  Paper,
  Stack,
  Text,
  TextInput,
  Tooltip
} from '@mantine/core';
import {
  IconCornerDownRight,
  IconRefresh,
  IconSearch,
  IconX
} from '@tabler/icons-react';
import {
  DataTable,
  type DataTableColumn,
  type DataTableSortStatus
} from 'mantine-datatable';
import { useMemo, useState } from 'react';

// Import components
import { ControlBar } from './components/ControlBar';
import { ErrorAlert } from './components/ErrorAlert';
import { StatisticsPanel } from './components/StatisticsPanel';
import { WarningsAlert } from './components/WarningsAlert';

// Import custom hooks
import { useBuildQuantity } from './hooks/useBuildQuantity';
import { useColumnVisibility } from './hooks/useColumnVisibility';
import { useFlatBom } from './hooks/useFlatBom';
import { useShortfallCalculation } from './hooks/useShortfallCalculation';

// Import types
import type { BomItem } from './types/BomTypes';

// Import utilities
import {
  filterBomData,
  flattenBomData,
  groupChildrenWithParents,
  sortBomData
} from './utils/bomDataProcessing';
import { getDimmedOpacity, getPartTypeColor } from './utils/colorUtils';
import {
  downloadCsv,
  generateCsvContent,
  generateFilename
} from './utils/csvExport';

/**
 * Render a custom panel with the provided context.
 * Displays a flattened BOM with background processing and auto-refresh.
 */
function FlatBOMGeneratorPanel({
  context
}: {
  context: InvenTreePluginContext;
}) {
  // Get the part ID from the context
  const partId = useMemo(() => {
    return context?.id || context?.instance?.pk;
  }, [context.id, context.instance]);

  // Get the part name from the context
  const partName = useMemo(() => {
    return context?.instance?.name || 'Unknown Part';
  }, [context.instance]);

  // Local UI state (must be declared before hooks that use them)
  const [includeAllocations, setIncludeAllocations] = useState<boolean>(true);
  const [includeOnOrder, setIncludeOnOrder] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [warningsDismissed, setWarningsDismissed] = useState<boolean>(false);
  const [sortStatus, setSortStatus] = useState<DataTableSortStatus<BomItem>>({
    columnAccessor: 'ipn',
    direction: 'asc'
  });
  const [page, setPage] = useState(1);
  // Records per page state - persisted in localStorage
  const [recordsPerPage, setRecordsPerPage] = useState<number | 'All'>(() => {
    const stored = localStorage.getItem('flat-bom-records-per-page');
    if (stored === 'All') return 'All';
    const num = Number(stored);
    return num > 0 ? num : 50;
  });

  // Custom hooks for flat BOM functionality
  const { bomData, loading, error, generateFlatBom, clearError } = useFlatBom(
    partId,
    context
  );
  const { buildQuantity, setBuildQuantity } = useBuildQuantity(1);
  const { hiddenColumns, toggleColumn } = useColumnVisibility(bomData);
  const { countNeedToOrder, countOutOfStock, countOnOrder } =
    useShortfallCalculation(buildQuantity, includeAllocations, includeOnOrder);

  /**
   * Export BOM to CSV using utility functions
   */
  const exportToCsv = () => {
    if (!bomData) return;

    // Generate CSV content from filtered data
    const csvContent = generateCsvContent(
      filteredAndSortedData,
      buildQuantity,
      includeAllocations,
      includeOnOrder
    );

    // Generate filename and download
    const filename = generateFilename(bomData.ipn, partId, buildQuantity);
    downloadCsv(csvContent, filename);
  };

  // Filter and sort data using utility functions
  const filteredAndSortedData = useMemo(() => {
    if (!bomData) return [];

    // Step 1: Flatten data (insert cut list child rows)
    let data = flattenBomData(bomData.bom_items);

    // Step 2: Filter by search query
    data = filterBomData(data, searchQuery);

    // Step 3: Sort data
    if (sortStatus.columnAccessor) {
      data = sortBomData(
        data,
        sortStatus.columnAccessor,
        sortStatus.direction,
        buildQuantity,
        includeAllocations,
        includeOnOrder
      );

      // Step 4: Group children with parents after sorting
      data = groupChildrenWithParents(data);
    }

    return data;
  }, [
    bomData,
    searchQuery,
    sortStatus,
    buildQuantity,
    includeAllocations,
    includeOnOrder
  ]);

  // Define DataTable columns matching InvenTree BomTable style
  const columns: DataTableColumn<BomItem>[] = useMemo(
    () => [
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

          // Use CSS ellipsis and always show tooltip for now (like InvenTree ellipsis 'Actions')
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
            // Cut list children: multiply pieces by buildQuantity
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
        sortable: false, // Disable sorting and arrow
        switchable: false, // Prevent hiding to clarify intent
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
        // Fixed-layout table requires pixel minWidth (max-content ignored)
        // Content: Badge (70-80px) + spacer (8px min) + unit text (30-35px) ≈ 125px
        // Matches InvenTree core standard for badge/progress columns
        minWidth: 125,
        cellsStyle: () => ({ minWidth: 125 }),
        titleStyle: () => ({ minWidth: 125 }),
        render: (record) => {
          // Show dash for cut list children
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
        // Fixed-layout table requires pixel minWidth (max-content ignored)
        // Content: Badge (70-80px) + spacer (8px min) + unit text (30-35px) ≈ 125px
        // Matches InvenTree core standard for badge/progress columns
        minWidth: 125,
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
        // Fixed-layout table requires pixel minWidth (max-content ignored)
        // Content: Badge (70-80px) + spacer (8px min) + unit text (30-35px) ≈ 125px
        // Matches InvenTree core standard for badge/progress columns
        minWidth: 125,
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
        // Fixed-layout table requires pixel minWidth (max-content ignored)
        // Content: Badge (70-80px) + spacer (8px min) + unit text (30-35px) ≈ 125px
        // Matches InvenTree core standard for badge/progress columns
        minWidth: 125,
        cellsStyle: () => ({ minWidth: 125 }),
        titleStyle: () => ({ minWidth: 125 }),
        render: (record) => {
          // No shortfall for cut list children
          if (record.is_cut_list_child) {
            return (
              <Text size='sm' c='dimmed'>
                -
              </Text>
            );
          }

          const totalRequired = record.total_qty * buildQuantity;
          let stockValue = record.in_stock;
          if (includeAllocations) {
            stockValue -= record.allocated;
          }
          if (includeOnOrder) {
            stockValue += record.on_order;
          }
          const balance = stockValue - totalRequired;
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
    ],
    [buildQuantity, includeAllocations, includeOnOrder]
  );

  // Filter columns based on visibility
  const visibleColumns = useMemo(
    () => columns.filter((col) => !hiddenColumns.has(col.accessor as string)),
    [columns, hiddenColumns]
  );

  const handleRecordsPerPageChange = (value: number | 'All') => {
    setRecordsPerPage(value);
    setPage(1);
    localStorage.setItem('flat-bom-records-per-page', value.toString());
  };

  return (
    <Stack gap='md'>
      {!bomData && !loading && (
        <Group justify='flex-end'>
          <Button
            leftSection={<IconRefresh size={16} />}
            onClick={generateFlatBom}
            loading={loading}
            disabled={!partId}
          >
            Generate Flat BOM
          </Button>
        </Group>
      )}

      {error && <ErrorAlert error={error} onClose={clearError} />}

      {loading && (
        <Paper p='xl' withBorder>
          <Stack align='center' gap='md'>
            <Loader size='lg' />
            <Text c='dimmed'>
              Traversing BOM hierarchy for <strong>{partName}</strong>...
            </Text>
            <Text size='xs' c='dimmed'>
              This may take a few moments for complex assemblies
            </Text>
          </Stack>
        </Paper>
      )}

      {bomData && !loading && (
        <Stack gap='sm'>
          {/* Warnings Section */}
          {!warningsDismissed && bomData?.metadata?.warnings && (
            <WarningsAlert
              warnings={bomData.metadata.warnings}
              onClose={() => setWarningsDismissed(true)}
            />
          )}

          <Paper p='sm' withBorder>
            <Group justify='space-between' align='flex-start' wrap='wrap'>
              <StatisticsPanel
                totalUniqueParts={bomData.total_unique_parts}
                maxDepthReached={bomData.max_depth_reached}
                totalIfpsProcessed={bomData.total_ifps_processed}
                outOfStockCount={countOutOfStock(bomData.bom_items)}
                onOrderCount={countOnOrder(bomData.bom_items)}
                needToOrderCount={countNeedToOrder(bomData.bom_items)}
              />

              <ControlBar
                buildQuantity={buildQuantity}
                onBuildQuantityChange={setBuildQuantity}
                includeAllocations={includeAllocations}
                onIncludeAllocationsChange={setIncludeAllocations}
                includeOnOrder={includeOnOrder}
                onIncludeOnOrderChange={setIncludeOnOrder}
                onRefresh={generateFlatBom}
                loading={loading}
                onExport={exportToCsv}
                columns={columns}
                hiddenColumns={hiddenColumns}
                onToggleColumn={toggleColumn}
              />
            </Group>
          </Paper>

          <Paper p='xs' withBorder>
            <TextInput
              placeholder='Search by IPN or Part Name...'
              leftSection={<IconSearch size={16} />}
              rightSection={
                searchQuery && (
                  <ActionIcon
                    variant='subtle'
                    onClick={() => setSearchQuery('')}
                    aria-label='Clear search'
                  >
                    <IconX size={16} />
                  </ActionIcon>
                )
              }
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.currentTarget.value)}
              mb='xs'
            />
          </Paper>

          <DataTable
            withTableBorder
            withColumnBorders
            striped
            highlightOnHover
            columns={visibleColumns}
            records={
              recordsPerPage === 'All'
                ? filteredAndSortedData
                : filteredAndSortedData.slice(
                    (page - 1) * recordsPerPage,
                    page * recordsPerPage
                  )
            }
            totalRecords={filteredAndSortedData.length}
            recordsPerPage={
              recordsPerPage === 'All'
                ? filteredAndSortedData.length
                : recordsPerPage
            }
            page={page}
            onPageChange={setPage}
            recordsPerPageOptions={[10, 25, 50, 100, 'All'] as any}
            onRecordsPerPageChange={handleRecordsPerPageChange}
            sortStatus={sortStatus}
            onSortStatusChange={setSortStatus}
            minHeight={200}
            noRecordsText='No parts found'
            paginationText={({ from, to, totalRecords }) => {
              // Count child/cut parts (rows with is_cut_list_child true)
              const cutParts = filteredAndSortedData.filter(
                (row) => row.is_cut_list_child
              ).length;
              return cutParts > 0
                ? `Showing ${from} to ${to} of ${totalRecords} parts (including ${cutParts} cut parts)`
                : `Showing ${from} to ${to} of ${totalRecords} parts`;
            }}
          />
        </Stack>
      )}

      {!bomData && !loading && !error && (
        <Alert color='blue' variant='light'>
          <Text size='sm'>
            Click <strong>"Generate Flat BOM"</strong> to traverse the complete
            bill of materials hierarchy for <strong>{partName}</strong> and
            calculate cumulative quantities.
          </Text>
        </Alert>
      )}
    </Stack>
  );
}

// This is the function which is called by InvenTree to render the actual panel component
export function renderFlatBOMGeneratorPanel(context: InvenTreePluginContext) {
  checkPluginVersion(context);

  return <FlatBOMGeneratorPanel context={context} />;
}
