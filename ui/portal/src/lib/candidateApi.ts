/**
 * Candidate API Service
 * Handles all candidate-related API calls using universal API client
 */

import { apiRequest } from './api-client';
import type {
  Candidate,
  CandidateListResponse,
  CandidateCreateInput,
  CandidateUpdateInput,
  CandidateFilters,
  UploadResumeResponse,
  CandidateStats,
} from '@/types/candidate';

export const candidateApi = {
  /**
   * Create a candidate manually
   */
  createCandidate: async (data: CandidateCreateInput): Promise<Candidate> => {
    return apiRequest.post<Candidate>('/api/candidates', data);
  },

  /**
   * Get a candidate by ID
   */
  getCandidate: async (id: number): Promise<Candidate> => {
    return apiRequest.get<Candidate>(`/api/candidates/${id}`);
  },

  /**
   * Update a candidate
   */
  updateCandidate: async (id: number, data: CandidateUpdateInput): Promise<Candidate> => {
    return apiRequest.put<Candidate>(`/api/candidates/${id}`, data);
  },

  /**
   * Delete a candidate
   */
  deleteCandidate: async (id: number): Promise<void> => {
    return apiRequest.delete<void>(`/api/candidates/${id}`);
  },

  /**
   * List candidates with filters
   */
  listCandidates: async (filters: CandidateFilters = {}): Promise<CandidateListResponse> => {
    const params = new URLSearchParams();

    if (filters.status) params.append('status', filters.status);
    if (filters.search) params.append('search', filters.search);
    if (filters.page) params.append('page', filters.page.toString());
    if (filters.per_page) params.append('per_page', filters.per_page.toString());

    // Handle skills array
    if (filters.skills && filters.skills.length > 0) {
      filters.skills.forEach(skill => params.append('skills[]', skill));
    }

    return apiRequest.get<CandidateListResponse>(
      `/api/candidates?${params.toString()}`
    );
  },

  /**
   * Upload resume and auto-create candidate
   */
  uploadResume: async (file: File): Promise<UploadResumeResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    return apiRequest.post<UploadResumeResponse>(
      '/api/candidates/upload',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 120000, // 120 seconds (2 minutes) for AI processing
      }
    );
  },

  /**
   * Upload resume for existing candidate
   */
  uploadResumeForCandidate: async (
    candidateId: number,
    file: File
  ): Promise<UploadResumeResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    return apiRequest.post<UploadResumeResponse>(
      `/api/candidates/${candidateId}/resume`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 120000, // 120 seconds (2 minutes) for AI processing
      }
    );
  },

  /**
   * Re-parse existing resume
   */
  reparseResume: async (candidateId: number): Promise<UploadResumeResponse> => {
    return apiRequest.post<UploadResumeResponse>(
      `/api/candidates/${candidateId}/reparse`,
      {},
      {
        timeout: 120000, // 120 seconds (2 minutes) for AI processing
      }
    );
  },

  /**
   * Get candidate statistics
   */
  getStats: async (): Promise<CandidateStats> => {
    return apiRequest.get<CandidateStats>('/api/candidates/stats');
  },

  /**
   * Get candidates pending review (status='pending_review')
   */
  getPendingReview: async (): Promise<CandidateListResponse> => {
    return apiRequest.get<CandidateListResponse>('/api/candidates/pending-review');
  },

  /**
   * Review and edit parsed candidate data
   */
  reviewCandidate: async (id: number, data: Partial<CandidateUpdateInput>): Promise<Candidate> => {
    return apiRequest.put<Candidate>(`/api/candidates/${id}/review`, data);
  },

  /**
   * Approve candidate after review
   * Changes status from 'pending_review' to 'onboarded' and triggers job matching
   */
  approveCandidate: async (id: number): Promise<Candidate> => {
    return apiRequest.post<Candidate>(`/api/candidates/${id}/approve`);
  },

  /**
   * Generate AI role suggestions
   */
  generateRoleSuggestions: async (id: number): Promise<any> => {
    return apiRequest.post<any>(`/api/candidates/${id}/suggest-roles`);
  },
};

