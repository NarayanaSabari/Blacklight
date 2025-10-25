/**
 * React Query hook for fetching single subscription plan
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import type { SubscriptionPlan } from '@/types';

export function usePlan(planId: number | undefined) {
  return useQuery({
    queryKey: ['subscription-plan', planId],
    queryFn: async () => {
      const response = await apiClient.get<{ plan: SubscriptionPlan }>(
        `/api/subscription-plans/${planId}`
      );
      return response.data.plan;
    },
    enabled: !!planId,
  });
}
