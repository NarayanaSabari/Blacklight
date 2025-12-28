/**
 * Dashboard API Service
 * Handles dashboard statistics and activity API calls
 */

import { apiRequest } from './api-client';

// Types
export interface MyStats {
  assigned_candidates: number;
  by_status: Record<string, number>;
  recent_assignments: number;
}

export interface TenantStats {
  total_candidates: number;
  by_status: Record<string, number>;
  pending_invitations: number;
  pending_review: number;
  new_candidates_7d: number;
  approved_7d: number;
}

export interface TeamStats {
  team_members: number;
  team_candidates: number;
}

export interface DashboardStatsResponse {
  my_stats: MyStats;
  tenant_stats: TenantStats;
  team_stats?: TeamStats;
  user_role: string;
  is_admin: boolean;
  is_manager: boolean;
}

export interface RecentCandidate {
  id: number;
  name: string;
  email: string | null;
  status: string;
  created_at: string | null;
}

export interface RecentAssignment {
  id: number;
  candidate_id: number;
  candidate_name: string;
  assigned_by: string;
  assigned_at: string | null;
  status: string;
}

export interface RecentActivityResponse {
  recent_candidates: RecentCandidate[];
  my_recent_assignments: RecentAssignment[];
}

export const dashboardApi = {
  /**
   * Get comprehensive dashboard statistics
   */
  getStats: async (): Promise<DashboardStatsResponse> => {
    return apiRequest.get<DashboardStatsResponse>('/api/dashboard/stats');
  },

  /**
   * Get recent activity (candidates and assignments)
   */
  getRecentActivity: async (): Promise<RecentActivityResponse> => {
    return apiRequest.get<RecentActivityResponse>('/api/dashboard/recent-activity');
  },
};
