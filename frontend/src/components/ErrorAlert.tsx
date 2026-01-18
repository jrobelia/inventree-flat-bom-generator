import { Alert } from '@mantine/core';
import { IconAlertCircle } from '@tabler/icons-react';

interface ErrorAlertProps {
  error: string;
  onClose: () => void;
}

/**
 * Error alert component for displaying API or validation errors
 */
export function ErrorAlert({ error, onClose }: ErrorAlertProps) {
  return (
    <Alert
      icon={<IconAlertCircle size={16} />}
      title='Error'
      color='red'
      withCloseButton
      onClose={onClose}
    >
      {error}
    </Alert>
  );
}
