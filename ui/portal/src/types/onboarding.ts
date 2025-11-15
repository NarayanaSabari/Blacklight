/**
 * Candidate Onboarding Types
 * Type definitions for onboarding workflow
 */

/**
 * Onboarding status
 */
export type OnboardingStatus = 
  | 'PENDING_ASSIGNMENT'
  | 'ASSIGNED'
  | 'PENDING_ONBOARDING'
  | 'ONBOARDED'
  | 'APPROVED'
  | 'REJECTED';

/**
 * User info for onboarding context
 */
export interface OnboardingUserInfo {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
}

/**
 * Candidate with onboarding information
 */
export interface CandidateOnboardingInfo {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  phone: string | null;
  onboarding_status: OnboardingStatus;
  manager_id: number | null;
  recruiter_id: number | null;
  onboarded_by_user_id: number | null;
  onboarded_at: string | null;
  approved_by_user_id: number | null;
  approved_at: string | null;
  rejected_by_user_id: number | null;
  rejected_at: string | null;
  rejection_reason: string | null;
  created_at: string;
  updated_at: string;
  // Optional related users
  manager?: OnboardingUserInfo;
  recruiter?: OnboardingUserInfo;
  onboarded_by?: OnboardingUserInfo;
  approved_by?: OnboardingUserInfo;
  rejected_by?: OnboardingUserInfo;
}

/**
 * Onboard candidate request
 */
export interface OnboardCandidateRequest {
  candidate_id: number;
}

/**
 * Onboard candidate response
 */
export interface OnboardCandidateResponse {
  message: string;
  candidate_id: number;
  onboarding_status: OnboardingStatus;
  onboarded_at: string | null;
  onboarded_by_user_id: number;
}

/**
 * Approve candidate request
 */
export interface ApproveCandidateRequest {
  candidate_id: number;
}

/**
 * Approve candidate response
 */
export interface ApproveCandidateResponse {
  message: string;
  candidate_id: number;
  onboarding_status: OnboardingStatus;
  approved_at: string | null;
  approved_by_user_id: number;
}

/**
 * Reject candidate request
 */
export interface RejectCandidateRequest {
  candidate_id: number;
  rejection_reason: string;
}

/**
 * Reject candidate response
 */
export interface RejectCandidateResponse {
  message: string;
  candidate_id: number;
  onboarding_status: OnboardingStatus;
  rejected_at: string | null;
  rejected_by_user_id: number;
  rejection_reason: string;
}

/**
 * Update onboarding status request
 */
export interface UpdateOnboardingStatusRequest {
  candidate_id: number;
  new_status: OnboardingStatus;
}

/**
 * Update onboarding status response
 */
export interface UpdateOnboardingStatusResponse {
  message: string;
  candidate_id: number;
  onboarding_status: OnboardingStatus;
}

/**
 * Query filters for onboarding candidates
 */
export interface OnboardingCandidatesFilters {
  page?: number;
  per_page?: number;
  status?: OnboardingStatus;
  assigned_to_user_id?: number;
}

/**
 * Onboarding candidates response
 */
export interface OnboardingCandidatesResponse {
  candidates: CandidateOnboardingInfo[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

/**
 * Onboarding statistics
 */
export interface OnboardingStats {
  pending_assignment: number;
  assigned: number;
  pending_onboarding: number;
  onboarded: number;
  approved: number;
  rejected: number;
  total: number;
}

/**
 * Onboarding stats query filters
 */
export interface OnboardingStatsFilters {
  assigned_to_user_id?: number;
}
