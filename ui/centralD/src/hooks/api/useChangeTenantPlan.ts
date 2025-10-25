/**
 * React Query mutation for changing tenant subscription plan
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import type { TenantChangePlanRequest } from '@/types';
import { toast } from 'sonner';

export function useChangeTenantPlan(tenantId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: TenantChangePlanRequest) => {
      const response = await apiClient.post<{ message: string }>(
        `/api/tenants/${tenantId}/change-plan`,
        data
      );
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] });
      queryClient.invalidateQueries({ queryKey: ['tenant', tenantId] });
      toast.success(data.message || 'Subscription plan changed successfully');
    },
    onError: (error: any) => {
      const message = error.response?.data?.message || 'Failed to change plan';
      toast.error(message);
    },
  });
}
