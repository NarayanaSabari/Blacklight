/**
 * React Query hook for fetching tenants with filters
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import type { Tenant, TenantListResponse, TenantFilterParams } from '@/types';

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

export function useTenant(tenantId: number) {
  return useQuery({
    queryKey: ['tenant', tenantId],
    queryFn: async () => {
      const response = await apiClient.get<Tenant>(`/api/tenants/${tenantId}`);
      return response.data;
    },
    enabled: !!tenantId,
  });
}
