/**
 * Candidate Assignment API Service
 * Handles all candidate assignment and notification API calls
 */

import { apiRequest } from './api-client';
import type {
  AssignCandidateRequest,
  AssignCandidateResponse,
  ReassignCandidateRequest,
  ReassignCandidateResponse,
  UnassignCandidateRequest,
  UnassignCandidateResponse,
  CandidateAssignmentsResponse,
  UserAssignedCandidatesResponse,
  AssignmentHistoryResponse,
  NotificationsResponse,
  MarkNotificationReadRequest,
  MarkNotificationReadResponse,
  MarkAllNotificationsReadResponse,
  UserCandidatesFilters,
  AssignmentHistoryFilters,
  NotificationsFilters,
} from '@/types';

export const candidateAssignmentApi = {
  /**
   * Assign a candidate to a recruiter or manager
   * @param data - Assignment data (candidate_id, assigned_to_user_id, optional reason)
   */
  assignCandidate: async (data: AssignCandidateRequest): Promise<AssignCandidateResponse> => {
    return apiRequest.post<AssignCandidateResponse>(
      '/api/candidates/assignments/assign',
      data
    );
  },

  /**
   * Broadcast assign a candidate to ALL managers and recruiters in the tenant
   * Sets is_visible_to_all_team=True, making the candidate visible to all current AND future team members
   * @param candidateId - Candidate ID to broadcast assign
   * @param reason - Optional reason for assignment
   */
  broadcastAssignCandidate: async (
    candidateId: number,
    reason?: string
  ): Promise<{
    message: string;
    candidate_id: number;
    is_visible_to_all_team: boolean;
    current_team_count: number;
    previous_assignments_cancelled: number;
  }> => {
    return apiRequest.post('/api/candidates/assignments/broadcast', {
      candidate_id: candidateId,
      assignment_reason: reason,
    });
  },

  /**
   * Set the tenant-wide visibility flag for a candidate
   * @param candidateId - Candidate ID
   * @param isVisibleToAllTeam - Whether candidate should be visible to all team members
   */
  setCandidateVisibility: async (
    candidateId: number,
    isVisibleToAllTeam: boolean
  ): Promise<{
    message: string;
    candidate_id: number;
    is_visible_to_all_team: boolean;
  }> => {
    return apiRequest.put(`/api/candidates/assignments/visibility/${candidateId}`, {
      is_visible_to_all_team: isVisibleToAllTeam,
    });
  },

  /**
   * Reassign a candidate from current assignee to a new assignee
   * @param data - Reassignment data (candidate_id, new_assigned_to_user_id, optional reason)
   */
  reassignCandidate: async (data: ReassignCandidateRequest): Promise<ReassignCandidateResponse> => {
    return apiRequest.post<ReassignCandidateResponse>(
      '/api/candidates/assignments/reassign',
      data
    );
  },

  /**
   * Unassign a candidate from their current assignee
   * @param data - Candidate ID to unassign
   */
  unassignCandidate: async (data: UnassignCandidateRequest): Promise<UnassignCandidateResponse> => {
    return apiRequest.post<UnassignCandidateResponse>(
      '/api/candidates/assignments/unassign',
      data
    );
  },

  /**
   * Get assignment history for a specific candidate
   * @param candidateId - Candidate ID
   * @param includeNotifications - Include related notifications (default: false)
   */
  getCandidateAssignments: async (
    candidateId: number,
    includeNotifications: boolean = false
  ): Promise<CandidateAssignmentsResponse> => {
    const params = new URLSearchParams();
    params.append('include_notifications', includeNotifications.toString());

    return apiRequest.get<CandidateAssignmentsResponse>(
      `/api/candidates/assignments/candidate/${candidateId}?${params.toString()}`
    );
  },

  /**
   * Get candidates assigned to the current user
   * @param filters - Optional filters (status, include_completed)
   */
  getMyAssignedCandidates: async (
    filters: UserCandidatesFilters = {}
  ): Promise<UserAssignedCandidatesResponse> => {
    const params = new URLSearchParams();
    
    if (filters.status) {
      params.append('status', filters.status);
    }
    if (filters.include_completed !== undefined) {
      params.append('include_completed', filters.include_completed.toString());
    }

    const url = `/api/candidates/assignments/my-candidates${
      params.toString() ? `?${params.toString()}` : ''
    }`;
    return apiRequest.get<UserAssignedCandidatesResponse>(url);
  },

  /**
   * Get recent assignment history for the tenant
   * @param filters - Optional filters (limit, assigned_to_user_id, assigned_by_user_id)
   */
  getAssignmentHistory: async (
    filters: AssignmentHistoryFilters = {}
  ): Promise<AssignmentHistoryResponse> => {
    const params = new URLSearchParams();
    
    if (filters.limit) {
      params.append('limit', filters.limit.toString());
    }
    if (filters.assigned_to_user_id) {
      params.append('assigned_to_user_id', filters.assigned_to_user_id.toString());
    }
    if (filters.assigned_by_user_id) {
      params.append('assigned_by_user_id', filters.assigned_by_user_id.toString());
    }

    const url = `/api/candidates/assignments/history${
      params.toString() ? `?${params.toString()}` : ''
    }`;
    return apiRequest.get<AssignmentHistoryResponse>(url);
  },

  /**
   * Get assignment notifications for the current user
   * @param filters - Optional filters (unread_only, limit)
   */
  getUserNotifications: async (
    filters: NotificationsFilters = {}
  ): Promise<NotificationsResponse> => {
    const params = new URLSearchParams();
    
    if (filters.unread_only !== undefined) {
      params.append('unread_only', filters.unread_only.toString());
    }
    if (filters.limit) {
      params.append('limit', filters.limit.toString());
    }

    const url = `/api/candidates/assignments/notifications${
      params.toString() ? `?${params.toString()}` : ''
    }`;
    return apiRequest.get<NotificationsResponse>(url);
  },

  /**
   * Mark a notification as read
   * @param data - Notification ID to mark as read
   */
  markNotificationAsRead: async (
    data: MarkNotificationReadRequest
  ): Promise<MarkNotificationReadResponse> => {
    return apiRequest.post<MarkNotificationReadResponse>(
      '/api/candidates/assignments/notifications/read',
      data
    );
  },

  /**
   * Mark all notifications as read for the current user
   */
  markAllNotificationsAsRead: async (): Promise<MarkAllNotificationsReadResponse> => {
    return apiRequest.post<MarkAllNotificationsReadResponse>(
      '/api/candidates/assignments/notifications/mark-all-read',
      {}
    );
  },
};
