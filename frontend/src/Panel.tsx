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
  Checkbox,
  Divider,
  Group,
  Loader,
  Menu,
  NumberInput,
  Paper,
  Stack,
  Text,
  TextInput,
  Tooltip
} from '@mantine/core';
import {
  IconAdjustments,
  IconAlertCircle,
  IconAlertTriangle,
  IconCornerDownRight,
  IconDownload,
  IconRefresh,
  IconSearch,
  IconX
} from '@tabler/icons-react';
import {
  DataTable,
  type DataTableColumn,
  type DataTableSortStatus
} from 'mantine-datatable';
import { useEffect, useMemo, useState } from 'react';

interface BomItem {
  part_id: number;
  ipn: string;
  part_name: string;
  full_name: string;
  description: string;

  // Categorization
  part_type:
    | 'TLA'
    | 'Coml'
    | 'Fab'
    | 'CtL'
    | 'Purchased Assy'
    | 'Internal Fab'
    | 'Assy'
    | 'Other';
  is_assembly: boolean;
  purchaseable: boolean;
  has_default_supplier: boolean;

  // Quantities (aggregated/deduplicated)
  total_qty: number;
  unit: string;
  cut_list?: Array<{ quantity: number; length: number }> | null; // Cut list details for CtL parts
  internal_fab_cut_list?: Array<{
    count: number;
    piece_qty: number;
    unit: string;
  }> | null; // Cut list for Internal Fab parts
  cut_length?: number | null; // Length for individual cut (child rows only)
  is_cut_list_child?: boolean; // Flag to identify cut list child rows

  // Stock and order information
  in_stock: number;
  on_order: number;
  building?: number;
  allocated: number;
  available: number;

  // Procurement
  default_supplier_name?: string;

  // Display
  image?: string;
  thumbnail?: string;
  link: string;

  // Unit for cut breakdown rows (Internal Fab or CtL)
  cut_unit?: string;
}

interface Warning {
  type: string;
  part_id: number;
  part_name: string;
  message: string;
}

interface FlatBomResponse {
  part_id: number;
  part_name: string;
  ipn: string;
  total_unique_parts: number;
  total_ifps_processed: number;
  max_depth_reached: number;
  bom_items: BomItem[];
  metadata?: {
    warnings?: Warning[];
  };
}

/**
 * Render a custom panel with the provided context.
 * Displays a flattened BOM with background processing and auto-refresh.
 */
function FlatBOMGeneratorPanel({
  context
}: {
  context: InvenTreePluginContext;
}) {
  const [loading, setLoading] = useState(false);
  const [bomData, setBomData] = useState<FlatBomResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [buildQuantity, setBuildQuantity] = useState<number>(1);
  const [includeAllocations, setIncludeAllocations] = useState<boolean>(true);
  const [includeOnOrder, setIncludeOnOrder] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>('');
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

  // Get the part ID from the context
  const partId = useMemo(() => {
    return context?.id || context?.instance?.pk;
  }, [context.id, context.instance]);

  // Get the part name from the context
  const partName = useMemo(() => {
    return context?.instance?.name || 'Unknown Part';
  }, [context.instance]);

  /**
   * Generate flat BOM by calling the plugin API
   */
  const generateFlatBom = async () => {
    if (!partId) {
      setError('No part ID available');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Call the plugin API endpoint with 30 second timeout
      const response = await context.api.get(
        `/plugin/flat-bom-generator/flat-bom/${partId}/`,
        { timeout: 30000 }
      );

      if (response.status === 200) {
        console.log('[FlatBOM] API Response:', response.data);
        console.log('[FlatBOM] Metadata:', response.data.metadata);
        console.log('[FlatBOM] Warnings:', response.data.metadata?.warnings);
        setBomData(response.data);
      } else {
        setError(`API returned status ${response.status}`);
      }
    } catch (err: any) {
      setError(
        err?.response?.data?.error ||
          err.message ||
          'Failed to generate flat BOM'
      );
      console.error('Error generating flat BOM:', err);
    } finally {
      setLoading(false);
    }
  };

  /**
   * Escape CSV field value by:
   * 1. Converting to string
   * 2. Replacing any double quotes with two double quotes (RFC 4180)
   * 3. Wrapping in double quotes if contains comma, quote, or newline
   */
  const escapeCsvField = (value: any): string => {
    const str = String(value ?? '');
    // Escape double quotes by doubling them
    const escaped = str.replace(/"/g, '""');
    // Wrap in quotes if contains comma, quote, or newline
    if (
      escaped.includes(',') ||
      escaped.includes('"') ||
      escaped.includes('\n')
    ) {
      return `"${escaped}"`;
    }
    return escaped;
  };

  /**
   * Export BOM to CSV
   */
  const exportToCsv = () => {
    if (!bomData) return;

    // Always export complete dataset (not filtered)
    const headers = [
      'IPN',
      'Part Name',
      'Description',
      'Part Type',
      'Total Qty',
      'Unit',
      'Cut Length',
      'Cut Unit',
      'In Stock',
      'Allocated',
      'On Order',
      'Build Margin'
    ];
    const rows = filteredAndSortedData.map((item) => {
      // Handle cut list children differently
      if (item.is_cut_list_child) {
        return [
          item.ipn,
          item.part_name,
          item.description,
          item.part_type,
          item.total_qty, // Do not multiply by buildQuantity for child rows
          '',
          item.cut_length || '-',
          item.cut_unit || item.unit || '',
          '-',
          '-',
          '-',
          '-'
        ];
      }

      // Normal row calculation
      const totalRequired = item.total_qty * buildQuantity;
      let stockValue = item.in_stock;
      if (includeAllocations) {
        stockValue -= item.allocated;
      }
      if (includeOnOrder) {
        stockValue += item.on_order;
      }
      const balance = stockValue - totalRequired;
      return [
        item.ipn,
        item.part_name,
        item.description,
        item.part_type,
        totalRequired,
        item.unit,
        '-',
        '',
        item.in_stock,
        item.allocated,
        item.on_order,
        balance
      ];
    });

    const csvContent = [
      headers.map(escapeCsvField).join(','),
      ...rows.map((row) => row.map(escapeCsvField).join(','))
    ].join('\n');

    // Download file with timestamp
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').split('T');
    const dateStr = timestamp[0]; // YYYY-MM-DD
    const timeStr = timestamp[1].split('Z')[0]; // HH-MM-SS
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `flat_bom_${bomData.ipn || partId}_qty${buildQuantity}_${dateStr}_${timeStr}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  // Filter and sort data
  const filteredAndSortedData = useMemo(() => {
    if (!bomData) return [];

    // Flatten data: insert cut list child rows after each CtL parent
    const flattenedData: BomItem[] = [];
    for (const item of bomData.bom_items) {
      // Add parent row
      flattenedData.push(item);

      // Add child rows if cut list exists
      if (item.cut_list && item.cut_list.length > 0) {
        for (const cut of item.cut_list) {
          flattenedData.push({
            ...item,
            total_qty: cut.quantity,
            // CtL children should remain CtL type
            part_type: 'CtL' as any,
            in_stock: null as any,
            on_order: null as any,
            allocated: null as any,
            building: null as any,
            available: null as any,
            default_supplier_name: '',
            cut_length: cut.length,
            is_cut_list_child: true,
            cut_list: null
          });
        }
      }

      // Add Internal Fab cut breakdown child rows if internal_fab_cut_list exists
      if (item.internal_fab_cut_list && item.internal_fab_cut_list.length > 0) {
        for (const piece of item.internal_fab_cut_list) {
          flattenedData.push({
            ...item,
            total_qty: piece.count,
            // Force Internal Fab type for child rows
            part_type: 'Internal Fab' as any,
            in_stock: null as any,
            on_order: null as any,
            allocated: null as any,
            building: null as any,
            available: null as any,
            default_supplier_name: '',
            cut_length: piece.piece_qty, // Use cut_length column for per-use qty
            cut_unit: piece.unit,
            is_cut_list_child: true,
            cut_list: null,
            internal_fab_cut_list: null
          });
        }
      }
    }

    let data = flattenedData;

    // Filter by search query (IPN and Part Name only)
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      data = data.filter(
        (item) =>
          item.ipn.toLowerCase().includes(query) ||
          item.part_name.toLowerCase().includes(query)
      );
    }

    // Sort data
    if (sortStatus.columnAccessor) {
      data.sort((a, b) => {
        let aValue: any;
        let bValue: any;

        // Handle nested accessors and special cases
        switch (sortStatus.columnAccessor) {
          case 'ipn':
            aValue = a.ipn;
            bValue = b.ipn;
            break;
          case 'full_name':
            aValue = a.full_name;
            bValue = b.full_name;
            break;
          case 'part_name':
            aValue = a.part_name;
            bValue = b.part_name;
            break;
          case 'description':
            aValue = a.description;
            bValue = b.description;
            break;
          case 'part_type':
            aValue = a.part_type;
            bValue = b.part_type;
            break;
          case 'total_qty':
            aValue = a.total_qty * buildQuantity;
            bValue = b.total_qty * buildQuantity;
            break;
          case 'in_stock':
            aValue = a.in_stock;
            bValue = b.in_stock;
            break;
          case 'on_order':
            aValue = a.on_order;
            bValue = b.on_order;
            break;
          case 'building':
            aValue = a.building || 0;
            bValue = b.building || 0;
            break;
          case 'allocated':
            aValue = a.allocated;
            bValue = b.allocated;
            break;
          case 'shortfall':
            let aStockValue = a.in_stock;
            let bStockValue = b.in_stock;
            if (includeAllocations) {
              aStockValue -= a.allocated;
              bStockValue -= b.allocated;
            }
            if (includeOnOrder) {
              aStockValue += a.on_order;
              bStockValue += b.on_order;
            }
            aValue = Math.max(0, a.total_qty * buildQuantity - aStockValue);
            bValue = Math.max(0, b.total_qty * buildQuantity - bStockValue);
            break;
          case 'default_supplier_name':
            aValue = a.default_supplier_name || '';
            bValue = b.default_supplier_name || '';
            break;
          default:
            return 0;
        }

        // Handle string vs number comparison
        if (typeof aValue === 'string' && typeof bValue === 'string') {
          return sortStatus.direction === 'asc'
            ? aValue.localeCompare(bValue)
            : bValue.localeCompare(aValue);
        } else {
          return sortStatus.direction === 'asc'
            ? (aValue as number) - (bValue as number)
            : (bValue as number) - (aValue as number);
        }
      });

      // Post-sort: Group children with their parents
      // Separate parents and children, then recombine
      const parents: BomItem[] = [];
      const childrenByParentId = new Map<number, BomItem[]>();

      for (const item of data) {
        if (item.is_cut_list_child) {
          // Children inherit parent's part_id
          const parentId = item.part_id;
          if (!childrenByParentId.has(parentId)) {
            childrenByParentId.set(parentId, []);
          }
          childrenByParentId.get(parentId)!.push(item);
        } else {
          parents.push(item);
        }
      }

      // Rebuild array with children immediately after their parents
      data = [];
      for (const parent of parents) {
        data.push(parent);
        const children = childrenByParentId.get(parent.part_id);
        if (children) {
          data.push(...children);
        }
      }
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
          let color = 'gray';

          // Color code by base type (no suffix)
          switch (baseType) {
            case 'Coml':
              color = 'green';
              break;
            case 'Fab':
              color = 'blue';
              break;
            case 'CtL':
              color = 'teal';
              break;
            case 'Purchased Assy':
              color = 'orange';
              break;
            case 'Internal Fab':
              color = 'cyan';
              break;
            case 'Assy':
              color = 'violet';
              break;
            case 'TLA':
              color = 'grape';
              break;
            case 'Other':
              color = 'gray';
              break;
            default:
              color = 'gray';
          }

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
              <Group gap='xs' justify='space-between' wrap='nowrap'>
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
            <Group gap='xs' justify='space-between' wrap='nowrap'>
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
            <Group gap='xs' justify='space-between' wrap='nowrap'>
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
              <Group gap='xs' justify='space-between' wrap='nowrap'>
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
              <Group gap='xs' justify='space-between' wrap='nowrap'>
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
              <Group gap='xs' justify='space-between' wrap='nowrap'>
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
        render: (record) => {
          const isDimmed = !includeAllocations;
          if (record.is_cut_list_child) {
            return (
              <Text size='sm' c='dimmed'>
                -
              </Text>
            );
          }
          if (record.allocated > 0) {
            return (
              <Group gap='xs' justify='space-between' wrap='nowrap'>
                <Badge
                  color='yellow'
                  variant='light'
                  style={{
                    opacity: isDimmed ? 0.4 : 1,
                    minWidth: 'fit-content'
                  }}
                >
                  {record.allocated.toFixed(2)}
                </Badge>
                {record.unit && (
                  <Text
                    size='xs'
                    c='dimmed'
                    style={{ opacity: isDimmed ? 0.4 : 1 }}
                  >
                    [{record.unit}]
                  </Text>
                )}
              </Group>
            );
          }
          return (
            <Group gap='xs' justify='space-between' wrap='nowrap'>
              <Text
                c='dimmed'
                size='sm'
                style={{ opacity: isDimmed ? 0.4 : 1 }}
              >
                -
              </Text>
              {record.unit && (
                <Text
                  size='xs'
                  c='dimmed'
                  style={{ opacity: isDimmed ? 0.4 : 1 }}
                >
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
        render: (record) => {
          const isDimmed = !includeOnOrder;
          if (record.is_cut_list_child) {
            return (
              <Text size='sm' c='dimmed'>
                -
              </Text>
            );
          }
          if (record.on_order > 0) {
            return (
              <Group gap='xs' justify='space-between' wrap='nowrap'>
                <Badge
                  color='blue'
                  variant='light'
                  style={{
                    opacity: isDimmed ? 0.4 : 1,
                    minWidth: 'fit-content'
                  }}
                >
                  {record.on_order.toFixed(2)}
                </Badge>
                {record.unit && (
                  <Text
                    size='xs'
                    c='dimmed'
                    style={{ opacity: isDimmed ? 0.4 : 1 }}
                  >
                    [{record.unit}]
                  </Text>
                )}
              </Group>
            );
          }
          return (
            <Group gap='xs' justify='space-between' wrap='nowrap'>
              <Text
                c='dimmed'
                size='sm'
                style={{ opacity: isDimmed ? 0.4 : 1 }}
              >
                -
              </Text>
              {record.unit && (
                <Text
                  size='xs'
                  c='dimmed'
                  style={{ opacity: isDimmed ? 0.4 : 1 }}
                >
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
              <Group gap='xs' justify='space-between' wrap='nowrap'>
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
            <Group gap='xs' justify='space-between' wrap='nowrap'>
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

  // Column visibility state - stored in localStorage
  const [hiddenColumns, setHiddenColumns] = useState<Set<string>>(() => {
    const stored = localStorage.getItem('flat-bom-hidden-columns');
    return stored ? new Set(JSON.parse(stored)) : new Set();
  });

  // Auto-manage cut_length column visibility
  useEffect(() => {
    if (bomData) {
      const hasCtLParts = bomData.bom_items.some(
        (item) => item.cut_list && item.cut_list.length > 0
      );

      setHiddenColumns((prev) => {
        const newSet = new Set(prev);
        if (hasCtLParts) {
          newSet.delete('cut_length');
        } else {
          newSet.add('cut_length');
        }
        localStorage.setItem(
          'flat-bom-hidden-columns',
          JSON.stringify([...newSet])
        );
        return newSet;
      });
    }
  }, [bomData]);

  // Toggle column visibility
  const toggleColumn = (accessor: string) => {
    setHiddenColumns((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(accessor)) {
        newSet.delete(accessor);
      } else {
        newSet.add(accessor);
      }
      localStorage.setItem(
        'flat-bom-hidden-columns',
        JSON.stringify([...newSet])
      );
      return newSet;
    });
  };

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

      {error && (
        <Alert
          icon={<IconAlertCircle size={16} />}
          title='Error'
          color='red'
          withCloseButton
          onClose={() => setError(null)}
        >
          {error}
        </Alert>
      )}

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
          {bomData?.metadata?.warnings &&
            bomData.metadata.warnings.length > 0 && (
              <Alert
                icon={<IconAlertTriangle size={16} />}
                title={`${bomData.metadata.warnings.length} Warning${bomData.metadata.warnings.length > 1 ? 's' : ''} Found`}
                color='yellow'
                withCloseButton
                onClose={() => {
                  // Clear warnings from bomData to hide the alert
                  setBomData((prev) =>
                    prev
                      ? {
                          ...prev,
                          metadata: { ...prev.metadata, warnings: [] }
                        }
                      : null
                  );
                }}
              >
                <Stack gap='xs'>
                  {bomData.metadata.warnings.map((warning, idx) => (
                    <Text key={idx} size='sm'>
                      <strong>{warning.part_name}</strong>: {warning.message}
                    </Text>
                  ))}
                </Stack>
              </Alert>
            )}

          <Paper p='sm' withBorder>
            <Group justify='space-between' align='flex-start' wrap='wrap'>
              <Group gap='md' wrap='wrap'>
                <div style={{ minWidth: '70px' }}>
                  <Text size='xs' c='dimmed' style={{ lineHeight: 1.2 }}>
                    Total
                    <br />
                    Parts
                  </Text>
                  <Text size='lg' fw={700}>
                    {bomData.total_unique_parts}
                  </Text>
                </div>
                <div style={{ minWidth: '70px' }}>
                  <Text size='xs' c='dimmed' style={{ lineHeight: 1.2 }}>
                    BOM
                    <br />
                    Depth
                  </Text>
                  <Text size='lg' fw={700} c='violet'>
                    {bomData.max_depth_reached}
                  </Text>
                </div>
                <div style={{ minWidth: '80px' }}>
                  <Text size='xs' c='dimmed' style={{ lineHeight: 1.2 }}>
                    Internal Fab
                    <br />
                    Processed
                  </Text>
                  <Text size='lg' fw={700} c='cyan'>
                    {bomData.total_ifps_processed}
                  </Text>
                </div>
                <div style={{ minWidth: '70px' }}>
                  <Text size='xs' c='dimmed' style={{ lineHeight: 1.2 }}>
                    Out of
                    <br />
                    Stock
                  </Text>
                  <Text size='lg' fw={700} c='red'>
                    {
                      bomData.bom_items.filter((item) => item.in_stock <= 0)
                        .length
                    }
                  </Text>
                </div>
                <div style={{ minWidth: '70px' }}>
                  <Text size='xs' c='dimmed' style={{ lineHeight: 1.2 }}>
                    On
                    <br />
                    Order
                  </Text>
                  <Text size='lg' fw={700} c='blue'>
                    {
                      bomData.bom_items.filter((item) => item.on_order > 0)
                        .length
                    }
                  </Text>
                </div>
                <div style={{ minWidth: '70px' }}>
                  <Text size='xs' c='dimmed' style={{ lineHeight: 1.2 }}>
                    Need to
                    <br />
                    Order
                  </Text>
                  <Text size='lg' fw={700} c='orange'>
                    {
                      bomData.bom_items.filter((item) => {
                        const totalRequired = item.total_qty * buildQuantity;
                        let stockValue = item.in_stock;
                        if (includeAllocations) {
                          stockValue -= item.allocated;
                        }
                        if (includeOnOrder) {
                          stockValue += item.on_order;
                        }
                        return totalRequired > stockValue;
                      }).length
                    }
                  </Text>
                </div>
              </Group>
              <Group gap='xs' align='flex-end' wrap='wrap'>
                <NumberInput
                  label='Build Quantity'
                  value={buildQuantity}
                  onChange={(value) =>
                    setBuildQuantity(typeof value === 'number' ? value : 1)
                  }
                  min={1}
                  step={1}
                  style={{ width: 150 }}
                />
                <Stack gap='xs'>
                  <Checkbox
                    label='Include Allocations in Build Margin (-)'
                    checked={includeAllocations}
                    onChange={(e) =>
                      setIncludeAllocations(e.currentTarget.checked)
                    }
                  />
                  <Checkbox
                    label='Include On Order in Build Margin (+)'
                    checked={includeOnOrder}
                    onChange={(e) => setIncludeOnOrder(e.currentTarget.checked)}
                  />
                </Stack>
                <Button
                  leftSection={<IconRefresh size={16} />}
                  onClick={generateFlatBom}
                  loading={loading}
                >
                  Refresh
                </Button>
                <Button
                  variant='light'
                  leftSection={<IconDownload size={16} />}
                  onClick={exportToCsv}
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
                  <Menu.Dropdown
                    style={{ maxHeight: '400px', overflowY: 'auto' }}
                  >
                    <Menu.Label>Select Columns</Menu.Label>
                    <Divider />
                    {columns
                      .filter((col: any) => col.switchable !== false)
                      .map((col: any) => (
                        <Menu.Item key={col.accessor}>
                          <Checkbox
                            checked={!hiddenColumns.has(col.accessor)}
                            label={col.title || col.accessor}
                            onChange={() => toggleColumn(col.accessor)}
                            radius='sm'
                          />
                        </Menu.Item>
                      ))}
                  </Menu.Dropdown>
                </Menu>
              </Group>
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
