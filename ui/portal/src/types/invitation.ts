/**
 * Invitation Types for Candidate Self-Onboarding
 * Matches backend schemas from server/app/schemas/
 */

export type InvitationStatus =
  | 'sent'
  | 'pending_review'
  | 'approved'
  | 'rejected'
  | 'cancelled'
  | 'expired'
  | 'opened'
  | 'in_progress';

export type OnboardingType =
  | 'email_invitation'
  | 'self_signup'
  | 'import';

export interface CandidateInvitation {
  id: number;
  tenant_id: number;
  email: string;
  first_name?: string;
  last_name?: string;
  token: string;
  expires_at: string;
  status: InvitationStatus;
  invited_by_id: number;
  invited_at: string;
  invitation_data?: Record<string, unknown>;
  submitted_at?: string;
  reviewed_by_id?: number;
  reviewed_at?: string;
  review_notes?: string;
  rejection_reason?: string;
  candidate_id?: number;
  position?: string; // Added
  recruiter_notes?: string; // Added
  created_at: string;
  updated_at: string;
}

export interface InvitationWithRelations extends CandidateInvitation {
  is_valid?: boolean; // Added
  invited_by?: {
    id: number;
    email: string;
    first_name?: string;
    last_name?: string;
  };
  reviewed_by?: {
    id: number;
    email: string;
    first_name?: string;
    last_name?: string;
  };
  candidate?: {
    id: number;
    email: string;
    first_name: string;
    last_name?: string;
  };
}

export interface InvitationAuditLog {
  id: number;
  invitation_id: number;
  action: string;
  performed_by_id?: number;
  performed_at: string;
  ip_address?: string;
  user_agent?: string;
  extra_data?: Record<string, unknown>;
  created_at: string;
}

export interface CandidateDocument {
  id: number;
  tenant_id: number;
  candidate_id?: number;
  invitation_id?: number;
  document_type: string;
  file_name: string;
  file_path: string;
  file_size: number;
  mime_type: string;
  uploaded_by_id?: number;
  uploaded_at: string;
  is_verified: boolean;
  verified_by_id?: number;
  verified_at?: string;
  verification_notes?: string;
  created_at: string;
  updated_at: string;
}

// Request/Response Types

export interface InvitationCreateRequest {
  email: string;
  first_name?: string;
  last_name?: string;
  position?: string;
  recruiter_notes?: string;
  expiry_hours?: number; // Hours until expiry (backend expects this)
  invitation_data?: Record<string, unknown>;
}

export interface InvitationUpdateRequest {
  email?: string;
  first_name?: string;
  last_name?: string;
  invitation_data?: Record<string, unknown>;
  position?: string; // Added
  recruiter_notes?: string; // Added
}

export interface InvitationListParams {
  page?: number;
  per_page?: number;
  status?: InvitationStatus;
  search?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface InvitationListResponse {
  items: InvitationWithRelations[]; // Changed from 'invitations' to match backend
  total: number;
  page: number;
  per_page: number;
  pages: number; // Changed from 'total_pages' to match backend
}

export interface InvitationStatsResponse {
  total: number;
  by_status: {
    approved: number;
    cancelled: number;
    expired: number;
    in_progress: number;
    invited: number;
    opened: number;
    rejected: number;
    submitted: number;
  };
}

export interface InvitationReviewRequest {
  action: 'approve' | 'reject';
  notes?: string;
  rejection_reason?: string;
  edited_data?: Record<string, any>;  // HR can edit candidate data during approval
}

// Candidate Onboarding Submission

export interface OnboardingSubmissionRequest {
  first_name: string;
  last_name: string;
  email: string;
  phone?: string;
  location?: string;
  position?: string;
  experience_years?: number;
  expected_salary: string;
  visa_type?: string;
  skills?: string[];
  preferred_roles?: string[];
  preferred_locations?: string[];
  education?: string;
  work_experience?: string;
  summary?: string;
  linkedin_url?: string;
  github_url?: string;
  portfolio_url?: string;
  parsed_resume_data?: Record<string, unknown>;
  additional_data?: Record<string, unknown>;
}

export interface OnboardingSubmissionResponse {
  success: boolean;
  message: string;
  invitation: CandidateInvitation;
}

// Document Upload

export interface DocumentUploadResponse {
  success: boolean;
  document: CandidateDocument;
  message?: string;
}

export interface BulkInvitationRequest {
  invitations: InvitationCreateRequest[];
  expires_in_days?: number;
}

export interface BulkInvitationResponse {
  success: boolean;
  created: number;
  failed: number;
  errors?: Array<{
    email: string;
    error: string;
  }>;
}

// Filter/Sort helpers
export interface InvitationFilters {
  status?: InvitationStatus[];
  dateRange?: {
    start: string;
    end: string;
  };
  invitedBy?: number[];
  search?: string;
}

export interface InvitationSort {
  field: 'invited_at' | 'expires_at' | 'submitted_at' | 'email' | 'status';
  order: 'asc' | 'desc';
}
