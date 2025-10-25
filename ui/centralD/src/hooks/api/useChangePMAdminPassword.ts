/**
 * Hook for changing PM Admin password
 */

import { useMutation } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';

interface ChangePasswordData {
  current_password: string;
  new_password: string;
}

export function useChangePMAdminPassword() {
  return useMutation({
    mutationFn: async (data: ChangePasswordData) => {
      const response = await apiClient.put('/api/pm-admin/password', data);
      return response.data;
    },
    onSuccess: () => {
      toast.success('Password changed successfully');
    },
    onError: () => {
      toast.error('Failed to change password');
    },
  });
}
