/**
 * Submission API Service
 * Handles all submission-related API calls for the ATS functionality
 */

import { apiRequest } from './api-client';
import type {
  Submission,
  SubmissionListResponse,
  SubmissionCreateInput,
  ExternalSubmissionCreateInput,
  SubmissionUpdateInput,
  SubmissionStatusUpdateInput,
  SubmissionInterviewScheduleInput,
  SubmissionActivityCreateInput,
  SubmissionFilters,
  SubmissionStats,
  SubmissionActivity,
} from '@/types/submission';

// Response types for specific endpoints
interface MySubmissionsResponse {
  submissions: Submission[];
  total: number;
}

interface CandidateSubmissionsResponse {
  candidate_id: number;
  submissions: Submission[];
  total: number;
}

interface JobSubmissionsResponse {
  job_posting_id: number;
  submissions: Submission[];
  total: number;
}

interface ActivitiesResponse {
  submission_id: number;
  activities: SubmissionActivity[];
  total: number;
}

interface FollowUpsResponse {
  upcoming: Submission[];
  overdue: Submission[];
  total_upcoming: number;
  total_overdue: number;
}

interface DuplicateCheckResponse {
  exists: boolean;
  submission: Submission | null;
}

interface DeleteResponse {
  message: string;
  submission_id: number;
  already_deleted?: boolean;
}

interface Submitter {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  submission_count: number;
}

interface SubmittersResponse {
  submitters: Submitter[];
}

export const submissionApi = {
  // ==================== CRUD Operations ====================

  /**
   * Create a new submission (submit candidate to job)
   */
  createSubmission: async (data: SubmissionCreateInput): Promise<Submission> => {
    return apiRequest.post<Submission>('/api/submissions', data);
  },

  /**
   * Create a submission to an external job (not in portal)
   * Use this when the job is from LinkedIn, Dice, company websites, etc.
   */
  createExternalSubmission: async (data: ExternalSubmissionCreateInput): Promise<Submission> => {
    return apiRequest.post<Submission>('/api/submissions/external', data);
  },

  /**
   * Get a submission by ID
   */
  getSubmission: async (
    id: number,
    includeActivities: boolean = false
  ): Promise<Submission> => {
    const params = includeActivities ? '?include_activities=true' : '';
    return apiRequest.get<Submission>(`/api/submissions/${id}${params}`);
  },

  /**
   * List submissions with filters and pagination
   */
  listSubmissions: async (
    filters: SubmissionFilters = {}
  ): Promise<SubmissionListResponse> => {
    const params = new URLSearchParams();

    // Single status
    if (filters.status) params.append('status', filters.status);

    // Multiple statuses
    if (filters.statuses && filters.statuses.length > 0) {
      params.append('statuses', filters.statuses.join(','));
    }

    // ID filters
    if (filters.candidate_id)
      params.append('candidate_id', filters.candidate_id.toString());
    if (filters.job_posting_id)
      params.append('job_posting_id', filters.job_posting_id.toString());
    if (filters.submitted_by_user_id)
      params.append('submitted_by_user_id', filters.submitted_by_user_id.toString());

    // Text filters
    if (filters.vendor_company) params.append('vendor_company', filters.vendor_company);
    if (filters.client_company) params.append('client_company', filters.client_company);

    // Priority and flags
    if (filters.priority) params.append('priority', filters.priority);
    if (filters.is_hot !== undefined)
      params.append('is_hot', filters.is_hot.toString());
    if (filters.is_active !== undefined)
      params.append('is_active', filters.is_active.toString());

    // Date filters
    if (filters.submitted_after)
      params.append('submitted_after', filters.submitted_after);
    if (filters.submitted_before)
      params.append('submitted_before', filters.submitted_before);
    if (filters.interview_after)
      params.append('interview_after', filters.interview_after);
    if (filters.interview_before)
      params.append('interview_before', filters.interview_before);

    // Pagination
    if (filters.page) params.append('page', filters.page.toString());
    if (filters.per_page) params.append('per_page', filters.per_page.toString());

    // Sorting
    if (filters.sort_by) params.append('sort_by', filters.sort_by);
    if (filters.sort_order) params.append('sort_order', filters.sort_order);

    const queryString = params.toString();
    const url = queryString ? `/api/submissions?${queryString}` : '/api/submissions';

    return apiRequest.get<SubmissionListResponse>(url);
  },

  /**
   * Update a submission
   */
  updateSubmission: async (
    id: number,
    data: SubmissionUpdateInput
  ): Promise<Submission> => {
    return apiRequest.put<Submission>(`/api/submissions/${id}`, data);
  },

  /**
   * Update submission status with activity logging
   */
  updateStatus: async (
    id: number,
    data: SubmissionStatusUpdateInput
  ): Promise<Submission> => {
    return apiRequest.put<Submission>(`/api/submissions/${id}/status`, data);
  },

  /**
   * Delete a submission
   */
  deleteSubmission: async (id: number): Promise<DeleteResponse> => {
    return apiRequest.delete<DeleteResponse>(`/api/submissions/${id}`);
  },

  // ==================== Activity Operations ====================

  /**
   * Get activity log for a submission
   */
  getActivities: async (
    submissionId: number,
    options: { limit?: number; activity_type?: string } = {}
  ): Promise<ActivitiesResponse> => {
    const params = new URLSearchParams();
    if (options.limit) params.append('limit', options.limit.toString());
    if (options.activity_type) params.append('activity_type', options.activity_type);

    const queryString = params.toString();
    const url = queryString
      ? `/api/submissions/${submissionId}/activities?${queryString}`
      : `/api/submissions/${submissionId}/activities`;

    return apiRequest.get<ActivitiesResponse>(url);
  },

  /**
   * Add a note/activity to a submission
   */
  addActivity: async (
    submissionId: number,
    data: SubmissionActivityCreateInput
  ): Promise<SubmissionActivity> => {
    return apiRequest.post<SubmissionActivity>(
      `/api/submissions/${submissionId}/activities`,
      data
    );
  },

  // ==================== Interview Operations ====================

  /**
   * Schedule an interview for a submission
   */
  scheduleInterview: async (
    submissionId: number,
    data: SubmissionInterviewScheduleInput
  ): Promise<Submission> => {
    return apiRequest.post<Submission>(
      `/api/submissions/${submissionId}/interview`,
      data
    );
  },

  // ==================== Relationship Queries ====================

  /**
   * Get submissions made by the current user
   */
  getMySubmissions: async (
    isActiveOnly: boolean = false
  ): Promise<MySubmissionsResponse> => {
    const url = isActiveOnly
      ? '/api/submissions/my?is_active_only=true'
      : '/api/submissions/my';
    return apiRequest.get<MySubmissionsResponse>(url);
  },

  /**
   * Get all submissions for a specific candidate
   */
  getCandidateSubmissions: async (
    candidateId: number
  ): Promise<CandidateSubmissionsResponse> => {
    return apiRequest.get<CandidateSubmissionsResponse>(
      `/api/submissions/by-candidate/${candidateId}`
    );
  },

  /**
   * Get all submissions for a specific job posting
   */
  getJobSubmissions: async (
    jobPostingId: number
  ): Promise<JobSubmissionsResponse> => {
    return apiRequest.get<JobSubmissionsResponse>(
      `/api/submissions/by-job/${jobPostingId}`
    );
  },

  // ==================== Statistics & Follow-ups ====================

  /**
   * Get submission statistics
   */
  getStats: async (options: { userId?: number; daysBack?: number } = {}): Promise<SubmissionStats> => {
    const params = new URLSearchParams();
    if (options.userId) params.append('user_id', options.userId.toString());
    if (options.daysBack) params.append('days_back', options.daysBack.toString());

    const queryString = params.toString();
    const url = queryString ? `/api/submissions/stats?${queryString}` : '/api/submissions/stats';

    return apiRequest.get<SubmissionStats>(url);
  },

  /**
   * Get list of users who have made submissions (for filter dropdown)
   */
  getSubmitters: async (): Promise<SubmittersResponse> => {
    return apiRequest.get<SubmittersResponse>('/api/submissions/submitters');
  },

  /**
   * Get submissions with upcoming or overdue follow-ups
   */
  getFollowUps: async (
    options: { userId?: number; daysAhead?: number; includeOverdue?: boolean } = {}
  ): Promise<FollowUpsResponse> => {
    const params = new URLSearchParams();
    if (options.userId) params.append('user_id', options.userId.toString());
    if (options.daysAhead) params.append('days_ahead', options.daysAhead.toString());
    if (options.includeOverdue !== undefined)
      params.append('include_overdue', options.includeOverdue.toString());

    const queryString = params.toString();
    const url = queryString
      ? `/api/submissions/follow-ups?${queryString}`
      : '/api/submissions/follow-ups';

    return apiRequest.get<FollowUpsResponse>(url);
  },

  // ==================== Utility Operations ====================

  /**
   * Check if a submission already exists for candidate-job pair
   */
  checkDuplicate: async (
    candidateId: number,
    jobPostingId: number
  ): Promise<DuplicateCheckResponse> => {
    return apiRequest.get<DuplicateCheckResponse>(
      `/api/submissions/check-duplicate?candidate_id=${candidateId}&job_posting_id=${jobPostingId}`
    );
  },

  /**
   * Health check for submission service
   */
  healthCheck: async (): Promise<{ status: string; service: string; message: string }> => {
    return apiRequest.get('/api/submissions/health');
  },
};
