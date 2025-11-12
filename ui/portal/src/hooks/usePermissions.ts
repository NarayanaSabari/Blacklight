/**
 * Permissions Hook
 * Check user permissions and roles throughout the application
 */

import { usePortalAuth } from '@/contexts/PortalAuthContext';

export function usePermissions() {
  const { user } = usePortalAuth();

  // Helper to check if user has a specific role
  const hasRole = (roleName: string): boolean => {
    return user?.roles?.some(role => role.name === roleName) || false;
  };

  const isTenantAdmin = hasRole('TENANT_ADMIN');
  const isRecruiter = hasRole('RECRUITER');
  const isHiringManager = hasRole('HIRING_MANAGER');
  const isManager = hasRole('MANAGER'); // New Manager role check

  /**
   * Check if user has a specific permission
   */
  const hasPermission = (permissionName: string): boolean => {
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
  const canManageUsers = hasPermission('users.create') || hasPermission('users.edit') || hasPermission('users.delete');

  /**
   * Check if user can manage roles
   */
  const canManageRoles = hasPermission('roles.create') || hasPermission('roles.edit') || hasPermission('roles.delete');

  /**
   * Check if user can manage jobs
   */
  const canManageJobs = hasPermission('jobs.create') || hasPermission('jobs.edit') || hasPermission('jobs.delete');

  /**
   * Check if user can view jobs
   */
  const canViewJobs = hasPermission('jobs.view');

  /**
   * Check if user can manage candidates
   */
  const canManageCandidates = hasPermission('candidates.create') || hasPermission('candidates.edit') || hasPermission('candidates.delete');

  /**
   * Check if user can view candidates
   */
  const canViewCandidates = hasPermission('candidates.view');

  /**
   * Check if user can manage applications
   */
  const canManageApplications = hasPermission('jobs.manage_applications');

  /**
   * Check if user can view applications
   */
  const canViewApplications = hasPermission('jobs.view'); // Assuming view jobs includes viewing applications

  /**
   * Check if user can schedule interviews
   */
  const canScheduleInterviews = hasPermission('interviews.create');

  /**
   * Check if user can submit interview feedback
   */
  const canSubmitFeedback = hasPermission('interviews.feedback');

  /**
   * Check if user can view settings
   */
  const canViewSettings = hasPermission('settings.view');

  /**
   * Check if user can manage subscription
   */
  const canManageSubscription = hasPermission('settings.billing');

  return {
    user,
    isTenantAdmin,
    isRecruiter,
    isHiringManager,
    isManager,
    hasPermission,
    canManageUsers,
    canManageRoles,
    canManageJobs,
    canViewJobs,
    canManageCandidates,
    canViewCandidates,
    canManageApplications,
    canViewApplications,
    canScheduleInterviews,
    canSubmitFeedback,
    canViewSettings,
    canManageSubscription,
  };
}
