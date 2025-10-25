/**
 * React Query mutation for suspending a tenant
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import type { TenantSuspendRequest } from '@/types';
import { toast } from 'sonner';

export function useSuspendTenant(tenantId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: TenantSuspendRequest) => {
      const response = await apiClient.post<{ message: string }>(
        `/api/tenants/${tenantId}/suspend`,
        data
      );
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] });
      queryClient.invalidateQueries({ queryKey: ['tenant', tenantId] });
      toast.success(data.message || 'Tenant suspended successfully');
    },
    onError: (error: any) => {
      const message = error.response?.data?.message || 'Failed to suspend tenant';
      toast.error(message);
    },
  });
}
