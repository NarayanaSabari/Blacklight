/**
 * React Query hook for fetching single tenant
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import type { Tenant } from '@/types';

export function useTenant(identifier: number | string | undefined) {
  return useQuery({
    queryKey: ['tenant', identifier],
    queryFn: async () => {
      const response = await apiClient.get<{ tenant: Tenant }>(
        `/api/tenants/${identifier}`
      );
      return response.data.tenant;
    },
    enabled: !!identifier,
  });
}
