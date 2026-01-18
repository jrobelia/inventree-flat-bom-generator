import { Group, Paper, Text } from '@mantine/core';

interface StatisticsPanelProps {
  totalUniqueParts: number;
  maxDepthReached: number;
  totalIfpsProcessed: number;
  outOfStockCount: number;
  onOrderCount: number;
  needToOrderCount: number;
}

interface StatProps {
  label: string;
  value: number;
  color?: string;
  minWidth?: string;
}

function Stat({ label, value, color, minWidth = '70px' }: StatProps) {
  return (
    <div style={{ minWidth }}>
      <Text size='xs' c='dimmed' style={{ lineHeight: 1.2 }}>
        {label.split('\n').map((line, idx) => (
          <span key={idx}>
            {line}
            {idx < label.split('\n').length - 1 && <br />}
          </span>
        ))}
      </Text>
      <Text size='lg' fw={700} c={color}>
        {value}
      </Text>
    </div>
  );
}

/**
 * Statistics panel displaying BOM metrics
 */
export function StatisticsPanel({
  totalUniqueParts,
  maxDepthReached,
  totalIfpsProcessed,
  outOfStockCount,
  onOrderCount,
  needToOrderCount
}: StatisticsPanelProps) {
  return (
    <Paper p='sm' withBorder>
      <Group gap='md' wrap='wrap'>
        <Stat label='Total\nParts' value={totalUniqueParts} />
        <Stat label='BOM\nDepth' value={maxDepthReached} color='violet' />
        <Stat
          label='Internal Fab\nProcessed'
          value={totalIfpsProcessed}
          color='cyan'
          minWidth='80px'
        />
        <Stat label='Out of\nStock' value={outOfStockCount} color='red' />
        <Stat label='On\nOrder' value={onOrderCount} color='blue' />
        <Stat label='Need to\nOrder' value={needToOrderCount} color='orange' />
      </Group>
    </Paper>
  );
}
