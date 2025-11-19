/**
 * Candidate Onboarding API Service
 * Handles all candidate onboarding workflow API calls
 */

import { apiRequest } from './api-client';
import type {
  OnboardCandidateRequest,
  OnboardCandidateResponse,
  ApproveCandidateRequest,
  ApproveCandidateResponse,
  RejectCandidateRequest,
  RejectCandidateResponse,
  UpdateOnboardingStatusRequest,
  UpdateOnboardingStatusResponse,
  OnboardingCandidatesFilters,
  OnboardingCandidatesResponse,
  OnboardingStats,
  OnboardingStatsFilters,
  CandidateOnboardingInfo,
} from '@/types';

export const onboardingApi = {
  /**
   * Mark a candidate as onboarded
   * @param data - Candidate ID to onboard
   */
  onboardCandidate: async (data: OnboardCandidateRequest): Promise<OnboardCandidateResponse> => {
    return apiRequest.post<OnboardCandidateResponse>(
      '/api/candidates/onboarding/onboard',
      data
    );
  },

  /**
   * Approve an onboarded candidate (HR approval)
   * @param data - Candidate ID to approve
   */
  approveCandidate: async (data: ApproveCandidateRequest): Promise<ApproveCandidateResponse> => {
    return apiRequest.post<ApproveCandidateResponse>(
      '/api/candidates/onboarding/approve',
      data
    );
  },

  /**
   * Reject an onboarded candidate with reason (HR rejection)
   * @param data - Candidate ID and rejection reason
   */
  rejectCandidate: async (data: RejectCandidateRequest): Promise<RejectCandidateResponse> => {
    return apiRequest.post<RejectCandidateResponse>(
      '/api/candidates/onboarding/reject',
      data
    );
  },

  /**
   * Update candidate onboarding status directly
   * @param data - Candidate ID and new status
   */
  updateOnboardingStatus: async (
    data: UpdateOnboardingStatusRequest
  ): Promise<UpdateOnboardingStatusResponse> => {
    return apiRequest.patch<UpdateOnboardingStatusResponse>(
      '/api/candidates/onboarding/status',
      data
    );
  },

  /**
   * Get candidates pending onboarding (paginated)
   * @param filters - Optional filters (page, per_page, status, assigned_to_user_id)
   */
  getPendingCandidates: async (
    filters: OnboardingCandidatesFilters = {}
  ): Promise<OnboardingCandidatesResponse> => {
    const params = new URLSearchParams();
    
    if (filters.page) {
      params.append('page', filters.page.toString());
    }
    if (filters.per_page) {
      params.append('per_page', filters.per_page.toString());
    }
    if (filters.status) {
      params.append('status', filters.status);
    }
    if (filters.assigned_to_user_id) {
      params.append('assigned_to_user_id', filters.assigned_to_user_id.toString());
    }

    const url = `/api/candidates/onboarding/pending${
      params.toString() ? `?${params.toString()}` : ''
    }`;
    return apiRequest.get<OnboardingCandidatesResponse>(url);
  },

  /**
   * Get candidates assigned to current user that are pending onboarding
   * @param filters - Optional filters (page, per_page, status)
   */
  getMyPendingCandidates: async (
    filters: Omit<OnboardingCandidatesFilters, 'assigned_to_user_id'> = {}
  ): Promise<OnboardingCandidatesResponse> => {
    const params = new URLSearchParams();
    
    if (filters.page) {
      params.append('page', filters.page.toString());
    }
    if (filters.per_page) {
      params.append('per_page', filters.per_page.toString());
    }
    if (filters.status) {
      params.append('status', filters.status);
    }

    const url = `/api/candidates/onboarding/my-pending${
      params.toString() ? `?${params.toString()}` : ''
    }`;
    return apiRequest.get<OnboardingCandidatesResponse>(url);
  },

  /**
   * Get onboarding statistics (counts by status)
   * @param filters - Optional filters (assigned_to_user_id)
   */
  getOnboardingStats: async (
    filters: OnboardingStatsFilters = {}
  ): Promise<OnboardingStats> => {
    const params = new URLSearchParams();
    
    if (filters.assigned_to_user_id) {
      params.append('assigned_to_user_id', filters.assigned_to_user_id.toString());
    }

    const url = `/api/candidates/onboarding/stats${
      params.toString() ? `?${params.toString()}` : ''
    }`;
    return apiRequest.get<OnboardingStats>(url);
  },

  /**
   * Get detailed onboarding information for a specific candidate
   * @param candidateId - Candidate ID
   */
  getCandidateOnboardingDetails: async (
    candidateId: number
  ): Promise<CandidateOnboardingInfo> => {
    return apiRequest.get<CandidateOnboardingInfo>(
      `/api/candidates/onboarding/candidate/${candidateId}`
    );
  },
};
