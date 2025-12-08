import { useState, useMemo } from 'react';
import {
    Alert,
    Button,
    Group,
    Loader,
    Stack,
    Text,
    Paper,
    Badge,
    NumberInput,
    TextInput,
    Anchor,
    Checkbox
} from '@mantine/core';
import { IconRefresh, IconDownload, IconAlertCircle, IconSearch } from '@tabler/icons-react';
import { DataTable, type DataTableColumn, type DataTableSortStatus } from 'mantine-datatable';

// Import for type checking
import { checkPluginVersion, type InvenTreePluginContext } from '@inventreedb/ui';

interface BomItem {
    part_id: number;
    ipn: string;
    part_name: string;
    description: string;

    // Categorization
    part_type: 'Fab Part' | 'Coml Part' | 'Purchaseable Assembly';
    is_assembly: boolean;
    purchaseable: boolean;
    has_default_supplier: boolean;

    // Quantities (aggregated/deduplicated)
    total_qty: number;
    unit: string;

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
}

interface FlatBomResponse {
    part_id: number;
    part_name: string;
    ipn: string;
    total_unique_parts: number;
    bom_items: BomItem[];
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
    const [recordsPerPage, setRecordsPerPage] = useState(50);

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
            // Call the plugin API endpoint
            const response = await context.api.get(
                `/plugin/flat-bom-generator/flat-bom/${partId}/`
            );

            if (response.status === 200) {
                setBomData(response.data);
            } else {
                setError(`API returned status ${response.status}`);
            }
        } catch (err: any) {
            setError(err?.response?.data?.error || err.message || 'Failed to generate flat BOM');
            console.error('Error generating flat BOM:', err);
        } finally {
            setLoading(false);
        }
    };

    /**
     * Export BOM to CSV
     */
    const exportToCsv = () => {
        if (!bomData) return;

        // Always export complete dataset (not filtered)
        const headers = ['IPN', 'Part Name', 'Description', 'Part Type', 'Total Qty', 'Unit', 'In Stock', 'Allocated', 'Available', 'On Order', 'Building', 'Net Shortfall', 'Supplier'];
        const rows = bomData.bom_items.map(item => {
            const totalRequired = item.total_qty * buildQuantity;
            const stockToUse = includeAllocations ? item.available : item.in_stock;
            const onOrderToUse = includeOnOrder ? item.on_order : 0;
            const netShortfall = Math.max(0, totalRequired - stockToUse - onOrderToUse);
            return [
                item.ipn,
                item.part_name,
                item.description,
                item.part_type,
                totalRequired,
                item.unit,
                item.in_stock,
                item.allocated,
                item.available,
                item.on_order,
                item.building || 0,
                netShortfall,
                item.default_supplier_name || ''
            ];
        });

        const csvContent = [
            headers.join(','),
            ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
        ].join('\n');

        // Download file
        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `flat_bom_${bomData.ipn || partId}_qty${buildQuantity}.csv`;
        a.click();
        window.URL.revokeObjectURL(url);
    };

    // Filter and sort data
    const filteredAndSortedData = useMemo(() => {
        if (!bomData) return [];

        let data = [...bomData.bom_items];

        // Filter by search query (IPN and Part Name only)
        if (searchQuery) {
            const query = searchQuery.toLowerCase();
            data = data.filter(
                item =>
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
                    case 'available':
                        aValue = a.available;
                        bValue = b.available;
                        break;
                    case 'shortfall':
                        const aStock = includeAllocations ? a.available : a.in_stock;
                        const bStock = includeAllocations ? b.available : b.in_stock;
                        const aOnOrder = includeOnOrder ? a.on_order : 0;
                        const bOnOrder = includeOnOrder ? b.on_order : 0;
                        aValue = Math.max(0, a.total_qty * buildQuantity - aStock - aOnOrder);
                        bValue = Math.max(0, b.total_qty * buildQuantity - bStock - bOnOrder);
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
        }

        return data;
    }, [bomData, searchQuery, sortStatus, buildQuantity, includeAllocations, includeOnOrder]);

    // Define DataTable columns matching InvenTree BomTable style
    const columns: DataTableColumn<BomItem>[] = useMemo(() => [
        {
            accessor: 'part_name',
            title: 'Part',
            sortable: true,
            render: (record) => (
                <Group gap="xs" wrap="nowrap">
                    {record.thumbnail && (
                        <img
                            src={record.thumbnail}
                            alt={record.part_name}
                            style={{ width: 40, height: 40, objectFit: 'contain' }}
                        />
                    )}
                    <Anchor
                        href={record.link}
                        target="_blank"
                        size="sm"
                        style={{ textDecoration: 'none' }}
                    >
                        {record.part_name}
                    </Anchor>
                </Group>
            )
        },
        {
            accessor: 'ipn',
            title: 'IPN',
            sortable: true,
            render: (record) => (
                <Text size="sm" style={{ fontFamily: 'monospace' }}>
                    {record.ipn}
                </Text>
            )
        },
        {
            accessor: 'description',
            title: 'Description',
            sortable: true,
            render: (record) => (
                <Text size="sm" lineClamp={2} title={record.description}>
                    {record.description}
                </Text>
            )
        },
        {
            accessor: 'part_type',
            title: 'Type',
            sortable: true,
            render: (record) => (
                <Badge
                    size="sm"
                    color={
                        record.part_type === 'Fab Part' ? 'blue' :
                            record.part_type === 'Coml Part' ? 'green' :
                                'orange'
                    }
                    variant="light"
                >
                    {record.part_type}
                </Badge>
            )
        },
        {
            accessor: 'total_qty',
            title: 'Total Qty',
            sortable: true,
            render: (record) => {
                const totalRequired = record.total_qty * buildQuantity;
                return (
                    <Group gap="xs" justify="space-between" wrap="nowrap">
                        <Text size="sm" fw={700}>
                            {totalRequired.toFixed(2)}
                        </Text>
                        {record.unit && (
                            <Text size="xs" c="dimmed">[{record.unit}]</Text>
                        )}
                    </Group>
                );
            }
        },
        {
            accessor: 'in_stock',
            title: 'In Stock',
            sortable: true,
            render: (record) => {
                const totalRequired = record.total_qty * buildQuantity;
                if (record.in_stock <= 0) {
                    return <Text c="red" fs="italic" size="sm">No stock</Text>;
                } else if (record.in_stock < totalRequired) {
                    return (
                        <Badge color="orange" variant="light">
                            {record.in_stock.toFixed(2)}
                        </Badge>
                    );
                } else {
                    return (
                        <Badge color="green" variant="filled">
                            {record.in_stock.toFixed(2)}
                        </Badge>
                    );
                }
            }
        },
        {
            accessor: 'on_order',
            title: 'On Order',
            sortable: true,
            render: (record) => {
                if (record.on_order > 0) {
                    return (
                        <Badge color="blue" variant="light">
                            {record.on_order.toFixed(2)}
                        </Badge>
                    );
                }
                return <Text c="dimmed" size="sm">-</Text>;
            }
        },
        {
            accessor: 'building',
            title: 'Building',
            sortable: true,
            render: (record) => {
                const building = record.building || 0;
                if (building > 0) {
                    return (
                        <Badge color="cyan" variant="light">
                            {building.toFixed(2)}
                        </Badge>
                    );
                }
                return <Text c="dimmed" size="sm">-</Text>;
            }
        },
        {
            accessor: 'allocated',
            title: 'Allocated',
            sortable: true,
            render: (record) => {
                if (record.allocated > 0) {
                    return (
                        <Badge color="yellow" variant="light">
                            {record.allocated.toFixed(2)}
                        </Badge>
                    );
                }
                return <Text c="dimmed" size="sm">-</Text>;
            }
        },
        {
            accessor: 'available',
            title: 'Available',
            sortable: true,
            render: (record) => {
                const totalRequired = record.total_qty * buildQuantity;
                if (record.available <= 0) {
                    return <Text c="red" fs="italic" size="sm">None</Text>;
                } else if (record.available < totalRequired) {
                    return (
                        <Badge color="orange" variant="light">
                            {record.available.toFixed(2)}
                        </Badge>
                    );
                } else {
                    return (
                        <Badge color="green" variant="filled">
                            {record.available.toFixed(2)}
                        </Badge>
                    );
                }
            }
        },
        {
            accessor: 'shortfall',
            title: 'Shortfall',
            sortable: true,
            render: (record) => {
                const totalRequired = record.total_qty * buildQuantity;
                const stockToUse = includeAllocations ? record.available : record.in_stock;
                const onOrderToUse = includeOnOrder ? record.on_order : 0;
                const netShortfall = Math.max(0, totalRequired - stockToUse - onOrderToUse);
                if (netShortfall > 0) {
                    return (
                        <Badge color="red" variant="filled">
                            -{netShortfall.toFixed(2)}
                        </Badge>
                    );
                }
                return <Text c="green" fw={700}>✓</Text>;
            }
        },
        {
            accessor: 'default_supplier_name',
            title: 'Supplier',
            sortable: true,
            render: (record) => {
                if (record.default_supplier_name) {
                    return <Text size="sm">{record.default_supplier_name}</Text>;
                }
                return <Text size="sm" c="dimmed" fs="italic">No supplier</Text>;
            }
        }
    ], [buildQuantity, includeAllocations, includeOnOrder]);

    return (
        <Stack gap="md">
            {!bomData && !loading && (
                <Group justify="flex-end">
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
                    title="Error"
                    color="red"
                    withCloseButton
                    onClose={() => setError(null)}
                >
                    {error}
                </Alert>
            )}

            {loading && (
                <Paper p="xl" withBorder>
                    <Stack align="center" gap="md">
                        <Loader size="lg" />
                        <Text c="dimmed">
                            Traversing BOM hierarchy for <strong>{partName}</strong>...
                        </Text>
                        <Text size="xs" c="dimmed">
                            This may take a few moments for complex assemblies
                        </Text>
                    </Stack>
                </Paper>
            )}

            {bomData && !loading && (
                <Stack gap="sm">
                    <Paper p="sm" withBorder>
                        <Group justify="space-between" align="flex-start">
                            <Group gap="xl">
                                <div>
                                    <Text size="xs" c="dimmed">Total Parts</Text>
                                    <Text size="lg" fw={700}>{bomData.total_unique_parts}</Text>
                                </div>
                                <div>
                                    <Text size="xs" c="dimmed">Out of Stock</Text>
                                    <Text size="lg" fw={700} c="red">
                                        {bomData.bom_items.filter(item => item.in_stock <= 0).length}
                                    </Text>
                                </div>
                                <div>
                                    <Text size="xs" c="dimmed">On Order</Text>
                                    <Text size="lg" fw={700} c="blue">
                                        {bomData.bom_items.filter(item => item.on_order > 0).length}
                                    </Text>
                                </div>
                                <div>
                                    <Text size="xs" c="dimmed">Need to Order</Text>
                                    <Text size="lg" fw={700} c="orange">
                                        {bomData.bom_items.filter(item => {
                                            const totalRequired = item.total_qty * buildQuantity;
                                            const stockToUse = includeAllocations ? item.available : item.in_stock;
                                            const onOrderToUse = includeOnOrder ? item.on_order : 0;
                                            return totalRequired > (stockToUse + onOrderToUse);
                                        }).length}
                                    </Text>
                                </div>
                            </Group>
                            <Group gap="xs" align="flex-end">
                                <NumberInput
                                    label="Build Quantity"
                                    value={buildQuantity}
                                    onChange={(value) => setBuildQuantity(typeof value === 'number' ? value : 1)}
                                    min={1}
                                    step={1}
                                    style={{ width: 150 }}
                                />
                                <Stack gap="xs">
                                    <Checkbox
                                        label="Include Allocations in Shortfall"
                                        checked={includeAllocations}
                                        onChange={(e) => setIncludeAllocations(e.currentTarget.checked)}
                                    />
                                    <Checkbox
                                        label="Include On Order in Shortfall"
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
                                    variant="light"
                                    leftSection={<IconDownload size={16} />}
                                    onClick={exportToCsv}
                                >
                                    Export CSV
                                </Button>
                            </Group>
                        </Group>
                    </Paper>

                    <Paper p="xs" withBorder>
                        <TextInput
                            placeholder="Search by IPN or Part Name..."
                            leftSection={<IconSearch size={16} />}
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.currentTarget.value)}
                            mb="xs"
                        />
                    </Paper>

                    <DataTable
                        withTableBorder
                        withColumnBorders
                        striped
                        highlightOnHover
                        columns={columns}
                        records={filteredAndSortedData.slice((page - 1) * recordsPerPage, page * recordsPerPage)}
                        totalRecords={filteredAndSortedData.length}
                        recordsPerPage={recordsPerPage}
                        page={page}
                        onPageChange={setPage}
                        recordsPerPageOptions={[10, 25, 50, 100]}
                        onRecordsPerPageChange={setRecordsPerPage}
                        sortStatus={sortStatus}
                        onSortStatusChange={setSortStatus}
                        minHeight={200}
                        noRecordsText="No parts found"
                        paginationText={({ from, to, totalRecords }) =>
                            `Showing ${from} to ${to} of ${totalRecords} parts`
                        }
                    />
                </Stack>
            )}

            {!bomData && !loading && !error && (
                <Alert color="blue" variant="light">
                    <Text size="sm">
                        Click <strong>"Generate Flat BOM"</strong> to traverse the complete bill of materials
                        hierarchy for <strong>{partName}</strong> and calculate cumulative quantities.
                    </Text>
                </Alert>
            )}
        </Stack>
    );
}


// This is the function which is called by InvenTree to render the actual panel component
export function renderFlatBOMGeneratorPanel(context: InvenTreePluginContext) {
    checkPluginVersion(context);

    return (
        <FlatBOMGeneratorPanel context={context} />
    );
}
