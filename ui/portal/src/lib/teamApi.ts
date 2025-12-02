/**
 * Team Management API Service
 * Handles all team hierarchy and manager assignment API calls
 */

import { apiRequest } from './api-client';
import type {
  TeamHierarchyResponse,
  ManagersListResponse,
  AvailableManagersResponse,
  TeamMembersResponse,
  AssignManagerRequest,
  AssignManagerResponse,
  RemoveManagerRequest,
  RemoveManagerResponse,
} from '@/types';

export const teamApi = {
  /**
   * Get complete team hierarchy for the tenant
   */
  getTeamHierarchy: async (): Promise<TeamHierarchyResponse> => {
    return apiRequest.get<TeamHierarchyResponse>('/api/team/hierarchy');
  },

  /**
   * Get list of all managers (users who have team members)
   * @param roleFilter - Optional role name filter (e.g., TEAM_LEAD, MANAGER)
   */
  getManagersList: async (roleFilter?: string): Promise<ManagersListResponse> => {
    const params = new URLSearchParams();
    if (roleFilter) {
      params.append('role_name', roleFilter);
    }

    const url = `/api/team/managers${params.toString() ? `?${params.toString()}` : ''}`;
    return apiRequest.get<ManagersListResponse>(url);
  },

  /**
   * Get list of users who can be assigned as managers
   * Respects role hierarchy - only returns managers who can manage the target user
   * @param excludeUserId - Optional user ID to exclude from list
   * @param forUserId - Optional target user ID to filter by role hierarchy
   */
  getAvailableManagers: async (excludeUserId?: number, forUserId?: number): Promise<AvailableManagersResponse> => {
    const params = new URLSearchParams();
    if (excludeUserId) {
      params.append('exclude_user_id', excludeUserId.toString());
    }
    if (forUserId) {
      params.append('for_user_id', forUserId.toString());
    }

    const url = `/api/team/available-managers${params.toString() ? `?${params.toString()}` : ''}`;
    return apiRequest.get<AvailableManagersResponse>(url);
  },

  /**
   * Get team members for a specific manager
   * @param userId - Manager's user ID
   * @param includeIndirect - Include indirect reports (default: false)
   */
  getUserTeamMembers: async (
    userId: number,
    includeIndirect: boolean = false
  ): Promise<TeamMembersResponse> => {
    const params = new URLSearchParams();
    params.append('include_indirect', includeIndirect.toString());

    return apiRequest.get<TeamMembersResponse>(
      `/api/team/user/${userId}/team-members?${params.toString()}`
    );
  },

  /**
   * Assign a manager to a user
   * @param data - Assignment data (user_id, manager_id)
   */
  assignManager: async (data: AssignManagerRequest): Promise<AssignManagerResponse> => {
    return apiRequest.post<AssignManagerResponse>('/api/team/assign-manager', data);
  },

  /**
   * Remove manager assignment from a user
   * @param data - User ID to remove manager from
   */
  removeManager: async (data: RemoveManagerRequest): Promise<RemoveManagerResponse> => {
    return apiRequest.post<RemoveManagerResponse>('/api/team/remove-manager', data);
  },
};
