/**
 * React Query hook for fetching tenants with filters
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import type { TenantListResponse, TenantFilterParams } from '@/types';

export function useTenants(filters?: TenantFilterParams) {
  return useQuery({
    queryKey: ['tenants', filters],
    queryFn: async () => {
      const response = await apiClient.get<TenantListResponse>('/api/tenants', {
        params: filters,
      });
      return response.data;
    },
  });
}
