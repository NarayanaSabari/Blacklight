/**
 * Permissions Hook
 * Check user permissions and roles throughout the application
 */

import { usePortalAuth } from '@/contexts/PortalAuthContext';

export function usePermissions() {
  const { user } = usePortalAuth();

  const isTenantAdmin = user?.role?.name === 'TENANT_ADMIN';
  const isRecruiter = user?.role?.name === 'RECRUITER';
  const isHiringManager = user?.role?.name === 'HIRING_MANAGER';

  /**
   * Check if user has a specific permission
   */
  const hasPermission = (): boolean => {
    if (!user || !user.role) return false;
    // Tenant admins have all permissions
    if (isTenantAdmin) return true;
    
    // Check if permission exists in user's role
    // This would require the permissions array to be included in the user object
    // For now, we'll implement role-based checks
    return false;
  };

  /**
   * Check if user can manage users
   * Only TENANT_ADMIN can create/edit/delete users
   */
  const canManageUsers = isTenantAdmin;

  /**
   * Check if user can manage jobs
   * TENANT_ADMIN and RECRUITER can manage jobs
   */
  const canManageJobs = isTenantAdmin || isRecruiter;

  /**
   * Check if user can view jobs
   * All roles can view jobs
   */
  const canViewJobs = !!user;

  /**
   * Check if user can manage candidates
   * TENANT_ADMIN and RECRUITER can manage candidates
   */
  const canManageCandidates = isTenantAdmin || isRecruiter;

  /**
   * Check if user can view candidates
   * All roles can view candidates
   */
  const canViewCandidates = !!user;

  /**
   * Check if user can manage applications
   * TENANT_ADMIN and RECRUITER can manage applications
   */
  const canManageApplications = isTenantAdmin || isRecruiter;

  /**
   * Check if user can view applications
   * All roles can view applications
   */
  const canViewApplications = !!user;

  /**
   * Check if user can schedule interviews
   * TENANT_ADMIN, RECRUITER, and HIRING_MANAGER can schedule interviews
   */
  const canScheduleInterviews = isTenantAdmin || isRecruiter || isHiringManager;

  /**
   * Check if user can submit interview feedback
   * All roles can submit feedback for interviews they're assigned to
   */
  const canSubmitFeedback = !!user;

  /**
   * Check if user can manage custom roles
   * Only TENANT_ADMIN can manage roles
   */
  const canManageRoles = isTenantAdmin;

  /**
   * Check if user can view settings
   * All users can view settings
   */
  const canViewSettings = !!user;

  /**
   * Check if user can change subscription plan
   * Only TENANT_ADMIN can manage subscription
   */
  const canManageSubscription = isTenantAdmin;

  return {
    user,
    isTenantAdmin,
    isRecruiter,
    isHiringManager,
    hasPermission,
    canManageUsers,
    canManageJobs,
    canViewJobs,
    canManageCandidates,
    canViewCandidates,
    canManageApplications,
    canViewApplications,
    canScheduleInterviews,
    canSubmitFeedback,
    canManageRoles,
    canViewSettings,
    canManageSubscription,
  };
}
