/**
 * React Query hook for resetting tenant admin password
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import type { ResetTenantAdminPasswordRequest } from '@/types';
import { toast } from 'sonner';

export function useResetTenantAdminPassword() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: ResetTenantAdminPasswordRequest) => {
      const response = await apiClient.post<{ message: string }>(
        '/api/pm-admin/reset-tenant-admin-password',
        data
      );
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['portal-users'] });
      toast.success(data.message || 'Password reset successfully');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to reset password');
    },
  });
}
