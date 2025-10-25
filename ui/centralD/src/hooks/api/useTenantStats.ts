/**
 * React Query hook for fetching tenant statistics
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import type { TenantStats } from '@/types';

export function useTenantStats(tenantSlug: string | undefined) {
  return useQuery({
    queryKey: ['tenant-stats', tenantSlug],
    queryFn: async () => {
      const response = await apiClient.get<TenantStats>(
        `/api/tenants/${tenantSlug}/stats`
      );
      return response.data;
    },
    enabled: !!tenantSlug,
  });
}
