/**
 * React Query mutation for deleting a tenant
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import type { TenantDeleteRequest, TenantDeleteResponse } from '@/types';
import { toast } from 'sonner';

export function useDeleteTenant(tenantId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: TenantDeleteRequest) => {
      const response = await apiClient.delete<TenantDeleteResponse>(
        `/api/tenants/${tenantId}`,
        { data }
      );
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] });
      toast.success(data.message || 'Tenant deleted successfully');
    },
    onError: (error: any) => {
      const message = error.response?.data?.message || 'Failed to delete tenant';
      toast.error(message);
    },
  });
}
