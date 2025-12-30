/**
 * Permissions Hook
 * Check user permissions and roles throughout the application
 */

import { usePortalAuth } from '@/contexts/PortalAuthContext';
import { PERMISSIONS, ROLES } from '@/lib/permissions';
import type { PermissionName, RoleName } from '@/lib/permissions';

export function usePermissions() {
  const { user } = usePortalAuth();

  // Helper to check if user has a specific role
  const hasRole = (roleName: RoleName): boolean => {
    return user?.roles?.some(role => role.name === roleName) || false;
  };

  const isTenantAdmin = hasRole(ROLES.TENANT_ADMIN);
  const isRecruiter = hasRole(ROLES.RECRUITER);
  const isManager = hasRole(ROLES.MANAGER);
  const isTeamLead = hasRole(ROLES.TEAM_LEAD);

  /**
   * Check if user has a specific permission
   */
  const hasPermission = (permissionName: PermissionName | string): boolean => {
    if (!user || !user.roles) return false;

    // Tenant admins have all permissions
    if (isTenantAdmin) return true;
    
    // Check if permission exists in any of the user's roles
    return user.roles.some(role => 
      role.permissions?.some(perm => perm.name === permissionName)
    );
  };

  /**
   * Check if user can manage users
   */
  const canManageUsers = hasPermission(PERMISSIONS.USERS.CREATE) || 
                         hasPermission(PERMISSIONS.USERS.EDIT) || 
                         hasPermission(PERMISSIONS.USERS.DELETE);

  /**
   * Check if user can manage roles
   */
  const canManageRoles = hasPermission(PERMISSIONS.ROLES.CREATE) || 
                         hasPermission(PERMISSIONS.ROLES.EDIT) || 
                         hasPermission(PERMISSIONS.ROLES.DELETE);

  /**
   * Check if user can manage jobs
   */
  const canManageJobs = hasPermission(PERMISSIONS.JOBS.CREATE) || 
                        hasPermission(PERMISSIONS.JOBS.EDIT) || 
                        hasPermission(PERMISSIONS.JOBS.DELETE);

  /**
   * Check if user can view jobs
   */
  const canViewJobs = hasPermission(PERMISSIONS.JOBS.VIEW);

  /**
   * Check if user can manage candidates
   */
  const canManageCandidates = hasPermission(PERMISSIONS.CANDIDATES.CREATE) || 
                              hasPermission(PERMISSIONS.CANDIDATES.EDIT) || 
                              hasPermission(PERMISSIONS.CANDIDATES.DELETE);

  /**
   * Check if user can view candidates
   */
  const canViewCandidates = hasPermission(PERMISSIONS.CANDIDATES.VIEW);

  /**
   * Check if user can manage applications
   */
  const canManageApplications = hasPermission(PERMISSIONS.JOBS.MANAGE_APPLICATIONS);

  /**
   * Check if user can view applications
   */
  const canViewApplications = hasPermission(PERMISSIONS.JOBS.VIEW); // Assuming view jobs includes viewing applications

  /**
   * Check if user can schedule interviews
   */
  const canScheduleInterviews = hasPermission(PERMISSIONS.INTERVIEWS.CREATE);

  /**
   * Check if user can submit interview feedback
   */
  const canSubmitFeedback = hasPermission(PERMISSIONS.INTERVIEWS.FEEDBACK);

  /**
   * Check if user can view settings
   */
  const canViewSettings = hasPermission(PERMISSIONS.SETTINGS.VIEW);

  /**
   * Check if user can manage subscription
   */
  const canManageSubscription = hasPermission(PERMISSIONS.SETTINGS.BILLING);

  /**
   * Check if user can view team
   */
  const canViewTeam = hasPermission(PERMISSIONS.USERS.VIEW_TEAM);

  /**
   * Check if user can assign managers
   */
  const canAssignManager = hasPermission(PERMISSIONS.USERS.ASSIGN_MANAGER);

  /**
   * Check if user can assign candidates
   */
  const canAssignCandidates = hasPermission(PERMISSIONS.CANDIDATES.ASSIGN);

  /**
   * Check if user can view submissions
   */
  const canViewSubmissions = hasPermission(PERMISSIONS.SUBMISSIONS.VIEW);

  /**
   * Check if user can create submissions
   */
  const canCreateSubmissions = hasPermission(PERMISSIONS.SUBMISSIONS.CREATE);

  return {
    // User and roles
    user,
    isTenantAdmin,
    isRecruiter,
    isManager,
    isTeamLead,
    hasRole,
    hasPermission,
    
    // User management
    canManageUsers,
    canManageRoles,
    
    // Job management
    canManageJobs,
    canViewJobs,
    
    // Candidate management
    canManageCandidates,
    canViewCandidates,
    canAssignCandidates,
    
    // Applications
    canManageApplications,
    canViewApplications,
    
    // Interviews
    canScheduleInterviews,
    canSubmitFeedback,
    
    // Settings
    canViewSettings,
    canManageSubscription,
    
    // Team
    canViewTeam,
    canAssignManager,
    
    // Submissions
    canViewSubmissions,
    canCreateSubmissions,
    
    // Re-export constants for convenience
    PERMISSIONS,
    ROLES,
  };
}
