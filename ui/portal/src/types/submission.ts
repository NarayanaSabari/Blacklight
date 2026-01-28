/**
 * Submission tracking types for the ATS functionality.
 * Handles candidate submissions to job postings.
 */

// ==================== Constants ====================

export const SUBMISSION_STATUSES = [
  'SUBMITTED',
  'CLIENT_REVIEW',
  'INTERVIEW_SCHEDULED',
  'INTERVIEWED',
  'OFFERED',
  'PLACED',
  'REJECTED',
  'WITHDRAWN',
  'ON_HOLD',
] as const;

export type SubmissionStatus = (typeof SUBMISSION_STATUSES)[number];

export const RATE_TYPES = ['HOURLY', 'DAILY', 'WEEKLY', 'MONTHLY', 'ANNUAL'] as const;
export type RateType = (typeof RATE_TYPES)[number];

export const INTERVIEW_TYPES = ['PHONE', 'VIDEO', 'ONSITE', 'TECHNICAL', 'HR', 'PANEL'] as const;
export type InterviewType = (typeof INTERVIEW_TYPES)[number];

export const PRIORITY_LEVELS = ['HIGH', 'MEDIUM', 'LOW'] as const;
export type PriorityLevel = (typeof PRIORITY_LEVELS)[number];

export const ACTIVITY_TYPES = [
  'CREATED',
  'STATUS_CHANGE',
  'NOTE',
  'EMAIL_SENT',
  'EMAIL_RECEIVED',
  'CALL_LOGGED',
  'INTERVIEW_SCHEDULED',
  'INTERVIEW_COMPLETED',
  'INTERVIEW_CANCELLED',
  'RATE_UPDATED',
  'VENDOR_UPDATED',
  'PRIORITY_CHANGED',
  'FOLLOW_UP_SET',
  'RESUME_SENT',
  'CLIENT_FEEDBACK',
] as const;

export type ActivityType = (typeof ACTIVITY_TYPES)[number];

// Status display labels and colors
export const STATUS_LABELS: Record<SubmissionStatus, string> = {
  SUBMITTED: 'Submitted',
  CLIENT_REVIEW: 'Client Review',
  INTERVIEW_SCHEDULED: 'Interview Scheduled',
  INTERVIEWED: 'Interviewed',
  OFFERED: 'Offered',
  PLACED: 'Placed',
  REJECTED: 'Rejected',
  WITHDRAWN: 'Withdrawn',
  ON_HOLD: 'On Hold',
};

export const STATUS_COLORS: Record<SubmissionStatus, string> = {
  SUBMITTED: 'bg-blue-100 text-blue-800',
  CLIENT_REVIEW: 'bg-yellow-100 text-yellow-800',
  INTERVIEW_SCHEDULED: 'bg-purple-100 text-purple-800',
  INTERVIEWED: 'bg-indigo-100 text-indigo-800',
  OFFERED: 'bg-emerald-100 text-emerald-800',
  PLACED: 'bg-green-100 text-green-800',
  REJECTED: 'bg-red-100 text-red-800',
  WITHDRAWN: 'bg-gray-100 text-gray-800',
  ON_HOLD: 'bg-orange-100 text-orange-800',
};

export const PRIORITY_COLORS: Record<PriorityLevel, string> = {
  HIGH: 'bg-red-100 text-red-800',
  MEDIUM: 'bg-yellow-100 text-yellow-800',
  LOW: 'bg-gray-100 text-gray-800',
};

// Terminal statuses (no further transitions)
export const TERMINAL_STATUSES: SubmissionStatus[] = ['PLACED', 'REJECTED', 'WITHDRAWN'];

// Active statuses (in progress)
export const ACTIVE_STATUSES: SubmissionStatus[] = [
  'SUBMITTED',
  'CLIENT_REVIEW',
  'INTERVIEW_SCHEDULED',
  'INTERVIEWED',
  'OFFERED',
  'ON_HOLD',
];

// ==================== Nested Response Types ====================

export interface SubmissionCandidate {
  id: number;
  first_name: string;
  last_name?: string;
  email?: string;
  phone?: string;
  current_title?: string;
  skills?: string[];
  location?: string;
  visa_type?: string; // Visa/work authorization type
}

export interface SubmissionJob {
  id?: number | null; // Null for external jobs
  title: string;
  company: string;
  location?: string;
  job_type?: string;
  is_remote?: boolean;
  platform?: string; // 'external' for external jobs
  job_url?: string;
}

export interface SubmissionUser {
  id: number;
  email: string;
  first_name?: string;
  last_name?: string;
}

// ==================== Activity Types ====================

export interface SubmissionActivity {
  id: number;
  submission_id: number;
  activity_type: ActivityType;
  content?: string;
  old_value?: string;
  new_value?: string;
  metadata?: Record<string, unknown>;
  created_at: string;
  created_by_id?: number;
  created_by?: SubmissionUser;
}

// ==================== Main Submission Type ====================

export interface Submission {
  id: number;
  candidate_id: number;
  job_posting_id?: number | null; // Nullable for external jobs
  submitted_by_user_id?: number;
  tenant_id: number;

  // External Job Info
  is_external_job?: boolean;
  external_job_title?: string;
  external_job_company?: string;
  external_job_location?: string;
  external_job_url?: string;
  external_job_description?: string;

  // Status
  status: SubmissionStatus;
  status_changed_at?: string;

  // Vendor info
  vendor_company?: string;
  vendor_contact_name?: string;
  vendor_contact_email?: string;
  vendor_contact_phone?: string;
  client_company?: string;

  // Rates
  bill_rate?: number;
  pay_rate?: number;
  rate_type?: RateType;
  currency?: string;
  margin?: number;
  margin_percentage?: number;

  // Notes
  submission_notes?: string;
  cover_letter?: string;
  tailored_resume_id?: number;

  // Interview
  interview_scheduled_at?: string;
  interview_type?: InterviewType;
  interview_location?: string;
  interview_notes?: string;
  interview_feedback?: string;

  // Outcome
  rejection_reason?: string;
  rejection_stage?: string;
  withdrawal_reason?: string;

  // Placement
  placement_start_date?: string;
  placement_end_date?: string;
  placement_duration_months?: number;

  // Priority
  priority?: PriorityLevel;
  is_hot?: boolean;
  follow_up_date?: string;

  // Timestamps
  submitted_at: string;
  created_at: string;
  updated_at: string;

  // Computed fields
  days_since_submitted?: number;
  is_active?: boolean;

  // Nested objects (optional, included based on endpoint)
  candidate?: SubmissionCandidate;
  job?: SubmissionJob;
  submitted_by?: SubmissionUser;
  activities?: SubmissionActivity[];
}

// ==================== Request Types ====================

export interface SubmissionCreateInput {
  candidate_id: number;
  job_posting_id: number;

  vendor_company: string;
  vendor_contact_name: string;
  vendor_contact_email: string;
  vendor_contact_phone: string;
  client_company: string;

  bill_rate: number;
  pay_rate: number;
  rate_type?: RateType;
  currency?: string;

  submission_notes: string;
  cover_letter?: string;
  tailored_resume_id?: number;

  priority?: PriorityLevel;
  is_hot?: boolean;
  follow_up_date?: string;
}

export interface ExternalSubmissionCreateInput {
  // Required
  candidate_id: number;

  // External job info (required)
  external_job_title: string;
  external_job_company: string;
  external_job_location?: string;
  external_job_url?: string;
  external_job_description?: string;

  // Vendor/Client info
  vendor_company?: string;
  vendor_contact_name?: string;
  vendor_contact_email?: string;
  vendor_contact_phone?: string;
  client_company?: string;

  // Rate information
  bill_rate?: number;
  pay_rate?: number;
  rate_type?: RateType;
  currency?: string;

  // Submission details
  submission_notes?: string;

  // Priority
  priority?: PriorityLevel;
  is_hot?: boolean;
  follow_up_date?: string;
}

export interface SubmissionUpdateInput {
  // Vendor/Client info
  vendor_company?: string;
  vendor_contact_name?: string;
  vendor_contact_email?: string;
  vendor_contact_phone?: string;
  client_company?: string;

  // Rate information
  bill_rate?: number;
  pay_rate?: number;
  rate_type?: RateType;
  currency?: string;

  // Submission details
  submission_notes?: string;
  cover_letter?: string;
  tailored_resume_id?: number;

  // Interview info
  interview_scheduled_at?: string;
  interview_type?: InterviewType;
  interview_location?: string;
  interview_notes?: string;
  interview_feedback?: string;

  // Priority
  priority?: PriorityLevel;
  is_hot?: boolean;
  follow_up_date?: string;
}

export interface SubmissionStatusUpdateInput {
  status: SubmissionStatus;
  note?: string;

  // Status-specific fields
  rejection_reason?: string;
  rejection_stage?: string;
  withdrawal_reason?: string;

  // For placement status
  placement_start_date?: string;
  placement_end_date?: string;
  placement_duration_months?: number;
}

export interface SubmissionInterviewScheduleInput {
  interview_scheduled_at: string;
  interview_type: InterviewType;
  interview_location?: string;
  interview_notes?: string;
}

export interface SubmissionActivityCreateInput {
  activity_type?: ActivityType;
  content: string;
  metadata?: Record<string, unknown>;
}

// ==================== Filter Types ====================

export interface SubmissionFilters {
  status?: SubmissionStatus;
  statuses?: SubmissionStatus[];
  candidate_id?: number;
  job_posting_id?: number;
  submitted_by_user_id?: number;
  vendor_company?: string;
  client_company?: string;
  priority?: PriorityLevel;
  is_hot?: boolean;
  is_active?: boolean;

  // Date filters
  submitted_after?: string;
  submitted_before?: string;
  interview_after?: string;
  interview_before?: string;

  // Pagination
  page?: number;
  per_page?: number;

  // Sorting
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

// ==================== Response Types ====================

export interface SubmissionListResponse {
  items: Submission[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface SubmissionStats {
  total: number;
  by_status: Record<SubmissionStatus, number>;
  submitted_this_week: number;
  submitted_this_month: number;
  interviews_scheduled: number;
  placements_this_month: number;
  average_days_to_placement?: number;
  interview_rate?: number;
  placement_rate?: number;
}

export interface SubmissionFollowUp {
  id: number;
  candidate_name: string;
  job_title: string;
  company: string;
  follow_up_date: string;
  status: SubmissionStatus;
  is_overdue: boolean;
}

export interface SubmissionFollowUpsResponse {
  upcoming: SubmissionFollowUp[];
  overdue: SubmissionFollowUp[];
}

// ==================== Utility Types ====================

// For the submission dialog / quick submit
export interface QuickSubmitData {
  candidate_id: number;
  job_posting_id: number;
  candidate_name?: string;
  job_title?: string;
  company?: string;
}

// Status transition validation
export const VALID_STATUS_TRANSITIONS: Record<SubmissionStatus, SubmissionStatus[]> = {
  SUBMITTED: ['CLIENT_REVIEW', 'INTERVIEW_SCHEDULED', 'REJECTED', 'WITHDRAWN', 'ON_HOLD'],
  CLIENT_REVIEW: ['INTERVIEW_SCHEDULED', 'REJECTED', 'WITHDRAWN', 'ON_HOLD'],
  INTERVIEW_SCHEDULED: ['INTERVIEWED', 'REJECTED', 'WITHDRAWN', 'ON_HOLD'],
  INTERVIEWED: ['OFFERED', 'REJECTED', 'WITHDRAWN', 'ON_HOLD'],
  OFFERED: ['PLACED', 'REJECTED', 'WITHDRAWN', 'ON_HOLD'],
  PLACED: [], // Terminal
  REJECTED: [], // Terminal
  WITHDRAWN: [], // Terminal
  ON_HOLD: ['SUBMITTED', 'CLIENT_REVIEW', 'INTERVIEW_SCHEDULED', 'INTERVIEWED', 'OFFERED', 'WITHDRAWN'],
};

// Helper to check if a status transition is valid
export function isValidStatusTransition(
  currentStatus: SubmissionStatus,
  newStatus: SubmissionStatus
): boolean {
  return VALID_STATUS_TRANSITIONS[currentStatus]?.includes(newStatus) ?? false;
}

// Helper to get next valid statuses
export function getNextValidStatuses(currentStatus: SubmissionStatus): SubmissionStatus[] {
  return VALID_STATUS_TRANSITIONS[currentStatus] ?? [];
}

// Helper to check if status is terminal
export function isTerminalStatus(status: SubmissionStatus): boolean {
  return TERMINAL_STATUSES.includes(status);
}

// Helper to check if status is active
export function isActiveStatus(status: SubmissionStatus): boolean {
  return ACTIVE_STATUSES.includes(status);
}
