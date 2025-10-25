/**
 * React Query hook for fetching subscription plan usage
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import type { SubscriptionPlanUsageResponse } from '@/types';

export function usePlanUsage(planId: number | undefined) {
  return useQuery({
    queryKey: ['subscription-plan-usage', planId],
    queryFn: async () => {
      const response = await apiClient.get<SubscriptionPlanUsageResponse>(
        `/api/subscription-plans/${planId}/usage`
      );
      return response.data;
    },
    enabled: !!planId,
  });
}
