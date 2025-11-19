/**
 * Dashboard API Functions
 */

import { apiClient } from '@/lib/api-client';
import type { DashboardStats, TenantUsageStats } from '@/types';

/**
 * Get dashboard statistics
 */
export async function fetchDashboardStats(): Promise<DashboardStats> {
  const response = await apiClient.get<DashboardStats>('/api/portal/dashboard/stats');
  return response.data;
}

/**
 * Get tenant usage stats vs plan limits
 */
export async function fetchTenantUsage(): Promise<TenantUsageStats> {
  const response = await apiClient.get<TenantUsageStats>('/api/portal/dashboard/usage');
  return response.data;
}

/**
 * Get recent activities
 */
export async function fetchRecentActivities(limit: number = 10): Promise<{
  activities: Array<{
    id: number;
    type: string;
    description: string;
    user: string;
    timestamp: string;
  }>;
}> {
  const response = await apiClient.get('/api/portal/dashboard/activities', { params: { limit } });
  return response.data;
}
