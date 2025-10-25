/**
 * React Query hook for fetching subscription plans
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import type { SubscriptionPlan } from '@/types';

export function usePlans() {
  return useQuery({
    queryKey: ['subscription-plans'],
    queryFn: async () => {
      const response = await apiClient.get<{ plans: SubscriptionPlan[] }>(
        '/api/subscription-plans'
      );
      return response.data.plans;
    },
  });
}
