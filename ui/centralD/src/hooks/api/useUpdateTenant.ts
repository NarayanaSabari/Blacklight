/**
 * React Query mutation for updating a tenant
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import type { TenantUpdateRequest, Tenant } from '@/types';
import { toast } from 'sonner';

export function useUpdateTenant(tenantId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: TenantUpdateRequest) => {
      const response = await apiClient.put<{ tenant: Tenant; message: string }>(
        `/api/tenants/${tenantId}`,
        data
      );
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] });
      queryClient.invalidateQueries({ queryKey: ['tenant', tenantId] });
      toast.success(data.message || 'Tenant updated successfully');
    },
    onError: (error: any) => {
      const message = error.response?.data?.message || 'Failed to update tenant';
      toast.error(message);
    },
  });
}
