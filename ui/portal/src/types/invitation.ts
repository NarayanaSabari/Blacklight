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
  | 'expired';

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
  created_at: string;
  updated_at: string;
}

export interface InvitationWithRelations extends CandidateInvitation {
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
  expiry_hours?: number; // Hours until expiry (backend expects this)
  invitation_data?: Record<string, unknown>;
}

export interface InvitationUpdateRequest {
  email?: string;
  first_name?: string;
  last_name?: string;
  invitation_data?: Record<string, unknown>;
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
  sent: number;
  pending_review: number;
  approved: number;
  rejected: number;
  cancelled: number;
  expired: number;
}

export interface InvitationReviewRequest {
  notes?: string;
  rejection_reason?: string;
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
  skills?: string[];
  education?: string;
  summary?: string;
  linkedin_url?: string;
  github_url?: string;
  portfolio_url?: string;
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
