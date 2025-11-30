/**
 * React Query mutation for reactivating a tenant
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';

export function useReactivateTenant(tenantId: number) {
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
      toast.success(data.message || 'Tenant reactivated successfully');
    },
    onError: (error: any) => {
      const message = error.response?.data?.message || 'Failed to reactivate tenant';
      toast.error(message);
    },
  });
}
