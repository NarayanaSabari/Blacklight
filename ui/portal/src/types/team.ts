/**
 * Team Management Types
 * Type definitions for team hierarchy and manager assignments
 */

/**
 * Role object structure
 */
export interface Role {
  id: number;
  name: string;
  display_name: string;
  description?: string;
}

/**
 * User basic info (used in team context)
 */
export interface UserBasicInfo {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  roles: (string | Role)[];
}

/**
 * Team member with hierarchy information
 */
export interface TeamMember extends UserBasicInfo {
  manager_id: number | null;
  hierarchy_level: number;
  team_members: TeamMember[];
}

/**
 * Manager with team count
 */
export interface ManagerWithCount extends UserBasicInfo {
  team_count: number;
}

/**
 * Team hierarchy response
 */
export interface TeamHierarchyResponse {
  top_level_users: TeamMember[];
  total_users: number;
}

/**
 * Available managers response
 */
export interface AvailableManagersResponse {
  managers: UserBasicInfo[];
  total: number;
}

/**
 * Managers list response
 */
export interface ManagersListResponse {
  managers: ManagerWithCount[];
  total: number;
}

/**
 * Team members response
 */
export interface TeamMembersResponse {
  team_members: TeamMember[];
  total: number;
  manager_id: number;
  include_indirect: boolean;
}

/**
 * Assign manager request
 */
export interface AssignManagerRequest {
  user_id: number;
  manager_id: number;
}

/**
 * Assign manager response
 */
export interface AssignManagerResponse {
  message: string;
  user_id: number;
  manager_id: number;
  assigned_by_user_id: number;
  assigned_at: string;
}

/**
 * Remove manager request
 */
export interface RemoveManagerRequest {
  user_id: number;
}

/**
 * Remove manager response
 */
export interface RemoveManagerResponse {
  message: string;
  user_id: number;
  previous_manager_id: number | null;
  removed_by_user_id: number;
  removed_at: string;
}
