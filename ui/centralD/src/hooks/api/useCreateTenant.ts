/**
 * React Query mutation for creating a tenant
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import type { TenantCreateRequest, Tenant } from '@/types';
import { toast } from 'sonner';

export function useCreateTenant() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: TenantCreateRequest) => {
      const response = await apiClient.post<{ tenant: Tenant; message: string }>(
        '/api/tenants',
        data
      );
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] });
      toast.success(data.message || 'Tenant created successfully');
    },
    onError: (error: any) => {
      const message = error.response?.data?.message || 'Failed to create tenant';
      toast.error(message);
    },
  });
}
