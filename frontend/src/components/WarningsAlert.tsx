import { Alert, Stack, Text } from '@mantine/core';
import { IconAlertTriangle } from '@tabler/icons-react';
import type { Warning } from '../types/BomTypes';

interface WarningsAlertProps {
  warnings: Warning[];
  onClose: () => void;
}

/**
 * Warnings alert component for displaying BOM validation warnings
 */
export function WarningsAlert({ warnings, onClose }: WarningsAlertProps) {
  if (!warnings || warnings.length === 0) {
    return null;
  }

  return (
    <Alert
      icon={<IconAlertTriangle size={16} />}
      title={`${warnings.length} Warning${warnings.length > 1 ? 's' : ''} Found`}
      color='yellow'
      withCloseButton
      onClose={onClose}
    >
      <Stack gap='xs'>
        {warnings.map((warning, idx) => (
          <Text key={idx} size='sm'>
            <strong>{warning.part_name}</strong>: {warning.message}
          </Text>
        ))}
      </Stack>
    </Alert>
  );
}
