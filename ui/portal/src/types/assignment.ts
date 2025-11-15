/**
 * Candidate Assignment Types
 * Type definitions for candidate assignments and notifications
 */

import type { Candidate } from './candidate';

/**
 * User info (for assignments)
 */
export interface UserInfo {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
}

/**
 * Assignment types
 */
export type AssignmentType = 'ASSIGNMENT' | 'REASSIGNMENT';

/**
 * Assignment status
 */
export type AssignmentStatus = 'ACTIVE' | 'COMPLETED' | 'CANCELLED';

/**
 * Candidate assignment
 */
export interface CandidateAssignment {
  id: number;
  tenant_id: number;
  candidate_id: number;
  assigned_to_user_id: number;
  assigned_by_user_id: number;
  assignment_type: AssignmentType;
  status: AssignmentStatus;
  assignment_reason: string | null;
  completed_at: string | null;
  previous_assignee_id: number | null;
  created_at: string;
  updated_at: string;
  // Optional related objects
  assigned_to?: UserInfo;
  assigned_by?: UserInfo;
  previous_assignee?: UserInfo;
  candidate?: Candidate;
}

/**
 * Assignment notification
 */
export interface AssignmentNotification {
  id: number;
  tenant_id: number;
  user_id: number;
  assignment_id: number;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
  // Optional related assignment
  assignment?: CandidateAssignment;
}

/**
 * Assign candidate request
 */
export interface AssignCandidateRequest {
  candidate_id: number;
  assigned_to_user_id: number;
  assignment_reason?: string;
}

/**
 * Assign candidate response
 */
export interface AssignCandidateResponse {
  message: string;
  assignment: CandidateAssignment;
  notification_id: number;
}

/**
 * Reassign candidate request
 */
export interface ReassignCandidateRequest {
  candidate_id: number;
  new_assigned_to_user_id: number;
  assignment_reason?: string;
}

/**
 * Reassign candidate response
 */
export interface ReassignCandidateResponse {
  message: string;
  old_assignment: {
    id: number;
    status: AssignmentStatus;
    completed_at: string;
  };
  new_assignment: CandidateAssignment;
}

/**
 * Unassign candidate request
 */
export interface UnassignCandidateRequest {
  candidate_id: number;
}

/**
 * Unassign candidate response
 */
export interface UnassignCandidateResponse {
  message: string;
  assignment_id: number;
  candidate_id: number;
  previous_assignee_id: number;
  unassigned_at: string;
}

/**
 * Candidate assignments response
 */
export interface CandidateAssignmentsResponse {
  assignments: CandidateAssignment[];
  total: number;
  candidate_id: number;
}

/**
 * Candidate info for assignment list
 */
export interface CandidateInfo {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  phone: string | null;
  onboarding_status: string;
  current_assignment?: CandidateAssignment;
}

/**
 * User assigned candidates response
 */
export interface UserAssignedCandidatesResponse {
  candidates: CandidateInfo[];
  total: number;
  user_id: number;
  filters: {
    status: string | null;
    include_completed: boolean;
  };
}

/**
 * Assignment history response
 */
export interface AssignmentHistoryResponse {
  assignments: CandidateAssignment[];
  total: number;
  limit: number;
}

/**
 * Notifications response
 */
export interface NotificationsResponse {
  notifications: AssignmentNotification[];
  total: number;
  unread_count: number;
}

/**
 * Mark notification read request
 */
export interface MarkNotificationReadRequest {
  notification_id: number;
}

/**
 * Mark notification read response
 */
export interface MarkNotificationReadResponse {
  message: string;
  notification_id: number;
}

/**
 * Mark all notifications read response
 */
export interface MarkAllNotificationsReadResponse {
  message: string;
  count: number;
}

/**
 * Query filters for user candidates
 */
export interface UserCandidatesFilters {
  status?: AssignmentStatus;
  include_completed?: boolean;
}

/**
 * Query filters for assignment history
 */
export interface AssignmentHistoryFilters {
  limit?: number;
  assigned_to_user_id?: number;
  assigned_by_user_id?: number;
}

/**
 * Query filters for notifications
 */
export interface NotificationsFilters {
  unread_only?: boolean;
  limit?: number;
}
