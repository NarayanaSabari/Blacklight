/**
 * React Query mutation for activating a suspended tenant
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';

export function useActivateTenant(tenantId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const response = await apiClient.post<{ message: string }>(
        `/api/tenants/${tenantId}/activate`
      );
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] });
      queryClient.invalidateQueries({ queryKey: ['tenant', tenantId] });
      toast.success(data.message || 'Tenant activated successfully');
    },
    onError: (error: unknown) => {
      const err = error as { response?: { data?: { message?: string } } };
      const message = err.response?.data?.message || 'Failed to activate tenant';
      toast.error(message);
    },
  });
}
