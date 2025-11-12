/**
 * React Query hook for fetching portal users for a tenant
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import type { PortalUser } from '@/types';

export function usePortalUsers(tenantSlug: string | undefined) {
  return useQuery({
    queryKey: ['portal-users', tenantSlug],
    queryFn: async () => {
      const response = await apiClient.get<{ items: PortalUser[] }>( // Changed 'users' to 'items'
        `/api/tenants/${tenantSlug}/users`
      );
      return response.data.items; // Changed 'users' to 'items'
    },
    enabled: !!tenantSlug,
  });
}
