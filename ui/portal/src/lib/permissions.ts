/**
 * Centralized Permission Constants
 * 
 * These constants match the permission names defined in the backend
 * at server/app/seeds/roles_and_permissions.py
 * 
 * Use these constants instead of hardcoding permission strings to:
 * - Avoid typos
 * - Enable IDE autocomplete
 * - Make refactoring easier
 * - Keep frontend/backend in sync
 */

// =============================================================================
// PERMISSION CONSTANTS
// =============================================================================

export const PERMISSIONS = {
  // Candidates
  CANDIDATES: {
    VIEW: 'candidates.view',
    CREATE: 'candidates.create',
    EDIT: 'candidates.edit',
    UPDATE: 'candidates.update',
    DELETE: 'candidates.delete',
    UPLOAD_RESUME: 'candidates.upload_resume',
    EXPORT: 'candidates.export',
    ASSIGN: 'candidates.assign',
    VIEW_ALL: 'candidates.view_all',
    VIEW_ASSIGNED: 'candidates.view_assigned',
    UNASSIGN: 'candidates.unassign',
    VIEW_HISTORY: 'candidates.view_history',
    REASSIGN: 'candidates.reassign',
    APPROVE: 'candidates.approve',
    REVIEW: 'candidates.review',
    REJECT: 'candidates.reject',
  },

  // Jobs
  JOBS: {
    VIEW: 'jobs.view',
    CREATE: 'jobs.create',
    EDIT: 'jobs.edit',
    DELETE: 'jobs.delete',
    PUBLISH: 'jobs.publish',
    MANAGE_APPLICATIONS: 'jobs.manage_applications',
  },

  // Interviews
  INTERVIEWS: {
    VIEW: 'interviews.view',
    CREATE: 'interviews.create',
    EDIT: 'interviews.edit',
    DELETE: 'interviews.delete',
    FEEDBACK: 'interviews.feedback',
  },

  // Clients
  CLIENTS: {
    VIEW: 'clients.view',
    CREATE: 'clients.create',
    EDIT: 'clients.edit',
    DELETE: 'clients.delete',
    COMMUNICATE: 'clients.communicate',
  },

  // Users (Portal Users)
  USERS: {
    VIEW: 'users.view',
    CREATE: 'users.create',
    EDIT: 'users.edit',
    DELETE: 'users.delete',
    MANAGE_ROLES: 'users.manage_roles',
    RESET_PASSWORD: 'users.reset_password',
    VIEW_TEAM: 'users.view_team',
    ASSIGN_MANAGER: 'users.assign_manager',
  },

  // Roles (Custom Role Management)
  ROLES: {
    VIEW: 'roles.view',
    CREATE: 'roles.create',
    EDIT: 'roles.edit',
    DELETE: 'roles.delete',
  },

  // Settings
  SETTINGS: {
    VIEW: 'settings.view',
    EDIT: 'settings.edit',
    BILLING: 'settings.billing',
  },

  // Reports
  REPORTS: {
    VIEW: 'reports.view',
    EXPORT: 'reports.export',
    ADVANCED: 'reports.advanced',
  },

  // Documents
  DOCUMENTS: {
    VIEW: 'documents.view',
    UPLOAD: 'documents.upload',
    DOWNLOAD: 'documents.download',
    DELETE: 'documents.delete',
  },

  // Invitations
  INVITATIONS: {
    VIEW: 'invitations.view',
    SEND: 'invitations.send',
    RESEND: 'invitations.resend',
    CANCEL: 'invitations.cancel',
    MANAGE: 'invitations.manage',
  },

  // Onboarding
  ONBOARDING: {
    VIEW: 'onboarding.view',
    MANAGE: 'onboarding.manage',
    REVIEW_SUBMISSIONS: 'onboarding.review_submissions',
    APPROVE: 'onboarding.approve',
  },

  // Candidate Assignments
  ASSIGNMENTS: {
    VIEW: 'assignments.view',
    CREATE: 'assignments.create',
    REMOVE: 'assignments.remove',
    MANAGE: 'assignments.manage',
  },

  // Job Matching (AI)
  JOB_MATCHES: {
    VIEW: 'job_matches.view',
    GENERATE: 'job_matches.generate',
    EXPORT: 'job_matches.export',
  },

  // Submissions (Candidate to Job Submissions)
  SUBMISSIONS: {
    VIEW: 'submissions.view',
    CREATE: 'submissions.create',
    EDIT: 'submissions.edit',
    DELETE: 'submissions.delete',
    MANAGE_STATUS: 'submissions.manage_status',
    VIEW_ALL: 'submissions.view_all',
  },

  // Audit Logs
  AUDIT: {
    VIEW: 'audit.view',
    EXPORT: 'audit.export',
  },
} as const;

// =============================================================================
// ROLE CONSTANTS
// =============================================================================

export const ROLES = {
  TENANT_ADMIN: 'TENANT_ADMIN',
  MANAGER: 'MANAGER',
  TEAM_LEAD: 'TEAM_LEAD',
  RECRUITER: 'RECRUITER',
} as const;

// =============================================================================
// ROLE HIERARCHY
// =============================================================================

/**
 * Role hierarchy levels (lower number = higher authority)
 * Matches backend ROLE_HIERARCHY in team_management_service.py
 */
export const ROLE_HIERARCHY = {
  [ROLES.TENANT_ADMIN]: 1,
  [ROLES.MANAGER]: 2,
  [ROLES.TEAM_LEAD]: 3,
  [ROLES.RECRUITER]: 4,
} as const;

// =============================================================================
// TYPE EXPORTS
// =============================================================================

export type PermissionName = 
  | typeof PERMISSIONS.CANDIDATES[keyof typeof PERMISSIONS.CANDIDATES]
  | typeof PERMISSIONS.JOBS[keyof typeof PERMISSIONS.JOBS]
  | typeof PERMISSIONS.INTERVIEWS[keyof typeof PERMISSIONS.INTERVIEWS]
  | typeof PERMISSIONS.CLIENTS[keyof typeof PERMISSIONS.CLIENTS]
  | typeof PERMISSIONS.USERS[keyof typeof PERMISSIONS.USERS]
  | typeof PERMISSIONS.ROLES[keyof typeof PERMISSIONS.ROLES]
  | typeof PERMISSIONS.SETTINGS[keyof typeof PERMISSIONS.SETTINGS]
  | typeof PERMISSIONS.REPORTS[keyof typeof PERMISSIONS.REPORTS]
  | typeof PERMISSIONS.DOCUMENTS[keyof typeof PERMISSIONS.DOCUMENTS]
  | typeof PERMISSIONS.INVITATIONS[keyof typeof PERMISSIONS.INVITATIONS]
  | typeof PERMISSIONS.ONBOARDING[keyof typeof PERMISSIONS.ONBOARDING]
  | typeof PERMISSIONS.ASSIGNMENTS[keyof typeof PERMISSIONS.ASSIGNMENTS]
  | typeof PERMISSIONS.JOB_MATCHES[keyof typeof PERMISSIONS.JOB_MATCHES]
  | typeof PERMISSIONS.SUBMISSIONS[keyof typeof PERMISSIONS.SUBMISSIONS]
  | typeof PERMISSIONS.AUDIT[keyof typeof PERMISSIONS.AUDIT];

export type RoleName = typeof ROLES[keyof typeof ROLES];
