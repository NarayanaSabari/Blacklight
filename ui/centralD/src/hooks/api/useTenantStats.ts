/**
 * React Query hook for fetching tenant statistics
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import type { TenantStats } from '@/types';

export function useTenantStats(tenantId: number | undefined) {
  return useQuery({
    queryKey: ['tenant-stats', tenantId],
    queryFn: async () => {
      const response = await apiClient.get<TenantStats>(
        `/api/tenants/${tenantId}/stats`
      );
      return response.data;
    },
    enabled: !!tenantId,
  });
}
