// Import for type checking
import {
  checkPluginVersion,
  type InvenTreePluginContext
} from '@inventreedb/ui';
import {
  ActionIcon,
  Alert,
  Button,
  Group,
  Loader,
  Paper,
  Stack,
  Text,
  TextInput
} from '@mantine/core';
import {
  IconInfoCircle,
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
// Import column definitions
import { createBomTableColumns } from './columns/bomTableColumns';
// Import components
import { ControlBar } from './components/ControlBar';
import { ErrorAlert } from './components/ErrorAlert';
import { SettingsDrawer } from './components/SettingsDrawer';
import { SettingsPanel } from './components/SettingsPanel';
import { StatisticsPanel } from './components/StatisticsPanel';
import { WarningsAlert } from './components/WarningsAlert';

// Import custom hooks
import { useBuildQuantity } from './hooks/useBuildQuantity';
import { useColumnVisibility } from './hooks/useColumnVisibility';
import { useFlatBom } from './hooks/useFlatBom';
import { usePluginSettings } from './hooks/usePluginSettings';
import { useShortfallCalculation } from './hooks/useShortfallCalculation';

// Import types
import type { BomItem } from './types/BomTypes';

// Import utilities
import {
  filterBomData,
  flattenBomData,
  groupChildRowsWithParents,
  sortBomData
} from './utils/bomDataProcessing';
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
  const [showCutlistRows, setShowCutlistRows] = useState<boolean>(true);
  const [showSubstitutes, setShowSubstitutes] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>('');

  const [warningsDismissed, setWarningsDismissed] = useState<boolean>(false);
  const [settingsDrawerOpen, setSettingsDrawerOpen] = useState<boolean>(false);
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
  const { settings, updateSetting, resetToDefaults } = usePluginSettings();
  const { bomData, loading, error, generateFlatBom, clearError } = useFlatBom(
    partId,
    context
  );
  const { buildQuantity, setBuildQuantity } = useBuildQuantity(1);
  const { hiddenColumns, toggleColumn } = useColumnVisibility(bomData);
  const {
    calculateShortfall,
    countNeedToOrder,
    countOutOfStock,
    countOnOrder
  } = useShortfallCalculation(
    buildQuantity,
    includeAllocations,
    includeOnOrder
  );

  // Extract cutlist units from BOM metadata
  const cutlistUnits = useMemo(() => {
    return bomData?.metadata?.cutlist_units_for_ifab || 'units';
  }, [bomData?.metadata?.cutlist_units_for_ifab]);

  // True when at least one item in the BOM has substitute parts available
  const hasSubstitutes = useMemo(() => {
    return bomData?.bom_items?.some((item) => item.has_substitutes) ?? false;
  }, [bomData?.bom_items]);

  // Handle initial generation
  const handleGenerate = async () => {
    await generateFlatBom(settings);
    // Auto-show substitute rows when substitutes are included
    if (settings.includeSubstitutes) {
      setShowSubstitutes(true);
    }
  };

  // Handle settings apply from drawer (regenerates BOM)
  const handleApplySettings = async () => {
    setSettingsDrawerOpen(false);
    await generateFlatBom(settings);
    // Sync substitute row visibility with the generation setting
    setShowSubstitutes(settings.includeSubstitutes);
  };

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

    // Step 2: Filter cutlist rows if checkbox unchecked
    if (!showCutlistRows) {
      data = data.filter(
        (item) =>
          !item.is_child_row || !item.child_row_type?.startsWith('cutlist')
      );
    }

    // Step 2.5: Filter substitute rows if checkbox unchecked
    if (!showSubstitutes) {
      data = data.filter(
        (item) => !item.is_child_row || item.child_row_type !== 'substitute'
      );
    }

    // Step 3: Filter by search query
    data = filterBomData(data, searchQuery);

    // Step 4: Sort data
    if (sortStatus.columnAccessor) {
      data = sortBomData(
        data,
        sortStatus.columnAccessor,
        sortStatus.direction,
        buildQuantity,
        includeAllocations,
        includeOnOrder
      );

      // Step 5: Group children with parents after sorting
      data = groupChildRowsWithParents(data);
    }

    return data;
  }, [
    bomData,
    showCutlistRows,
    showSubstitutes,
    searchQuery,
    sortStatus,
    buildQuantity,
    includeAllocations,
    includeOnOrder
  ]);

  // Define DataTable columns matching InvenTree BomTable style
  const columns: DataTableColumn<BomItem>[] = useMemo(
    () =>
      createBomTableColumns({
        buildQuantity,
        includeAllocations,
        includeOnOrder,
        calculateShortfall
      }),
    [buildQuantity, includeAllocations, includeOnOrder, calculateShortfall]
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
    <Stack gap='lg'>
      {/* Settings Drawer - shown after first generation */}
      <SettingsDrawer
        opened={settingsDrawerOpen}
        onClose={() => setSettingsDrawerOpen(false)}
        settings={settings}
        cutlistUnits={cutlistUnits}
        onUpdateSetting={updateSetting}
        onResetToDefaults={resetToDefaults}
        onApply={handleApplySettings}
      />

      {/* Pre-generation UI - shown before first generation */}
      {!bomData && !loading && (
        <>
          <div>
            <Button
              leftSection={<IconRefresh size={16} />}
              onClick={handleGenerate}
              loading={loading}
              disabled={!partId}
            >
              Generate Flat BOM
            </Button>
          </div>

          <Alert color='blue' variant='light' icon={<IconInfoCircle />}>
            <Text size='sm'>
              Click <strong>"Generate Flat BOM"</strong> to traverse the bill of
              materials hierarchy for OpenCPC and calculate cumulative
              quantities.
            </Text>
          </Alert>

          <SettingsPanel
            title='Generation Settings'
            settings={settings}
            cutlistUnits={cutlistUnits}
            onUpdateSetting={updateSetting}
            onResetToDefaults={resetToDefaults}
          />
        </>
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
                showCutlistRows={showCutlistRows}
                onShowCutlistRowsChange={setShowCutlistRows}
                showSubstitutes={showSubstitutes}
                onShowSubstitutesChange={setShowSubstitutes}
                substituteSettingOn={settings.includeSubstitutes}
                hasSubstitutes={hasSubstitutes}
                onRefresh={handleGenerate}
                loading={loading}
                onExport={exportToCsv}
                columns={columns}
                hiddenColumns={hiddenColumns}
                onToggleColumn={toggleColumn}
                onOpenSettings={
                  bomData ? () => setSettingsDrawerOpen(true) : undefined
                }
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
            rowStyle={(record) => {
              if (
                record.is_child_row &&
                record.child_row_type === 'substitute'
              ) {
                return {
                  // light: subtle blue-0 tint; dark: blue at 18% opacity — stands out against dark-7/8 table rows
                  backgroundColor:
                    'light-dark(var(--mantine-color-blue-0), rgba(34, 139, 230, 0.18))',
                  borderLeft:
                    '4px solid light-dark(var(--mantine-color-blue-4), var(--mantine-color-blue-6))'
                };
              }
            }}
            paginationText={({ from, to, totalRecords }) => {
              // Count child/cut parts (rows with is_child_row true)
              const cutParts = filteredAndSortedData.filter(
                (row) =>
                  row.is_child_row && row.child_row_type?.startsWith('cutlist')
              ).length;
              return cutParts > 0
                ? `Showing ${from} to ${to} of ${totalRecords} parts (including ${cutParts} cut parts)`
                : `Showing ${from} to ${to} of ${totalRecords} parts`;
            }}
          />
        </Stack>
      )}
    </Stack>
  );
}

// This is the function which is called by InvenTree to render the actual panel component
export function renderFlatBOMGeneratorPanel(context: InvenTreePluginContext) {
  checkPluginVersion(context);

  return <FlatBOMGeneratorPanel context={context} />;
}
