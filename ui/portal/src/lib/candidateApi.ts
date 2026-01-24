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
  PolishedResumeData,
  CandidateResume,
  CandidateResumeListResponse,
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
  uploadResume: async (file: File, candidateName?: string): Promise<UploadResumeResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    if (candidateName) {
      formData.append('candidate_name', candidateName);
    }

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

  /**
   * Update preferred roles with normalization
   * Triggers async workflow to normalize roles and add them to the global scraping queue
   */
  updatePreferredRoles: async (id: number, roles: string[]): Promise<{
    message: string;
    candidate: Candidate;
    normalization_status: 'pending' | 'skipped';
  }> => {
    return apiRequest.put(`/api/candidates/${id}/preferred-roles`, {
      preferred_roles: roles
    });
  },

  /**
   * Generate a signed/resumable URL to download a candidate's resume
   * Server returns { signed_url: string }
   */
  getResumeUrl: async (id: number, ttl?: number): Promise<string> => {
    const url = ttl ? `/api/candidates/${id}/resume-url?ttl=${ttl}` : `/api/candidates/${id}/resume-url`;
    const resp = await apiRequest.get<{ signed_url: string }>(url);
    return resp.signed_url;
  },

  // ==================== Polished Resume APIs ====================

  /**
   * Get the polished resume data for a candidate
   */
  getPolishedResume: async (id: number): Promise<{
    has_polished_resume: boolean;
    polished_resume_data: PolishedResumeData | null;
    candidate_id: number;
  }> => {
    return apiRequest.get(`/api/candidates/${id}/polished-resume`);
  },

  /**
   * Update the polished resume markdown (recruiter edit)
   */
  updatePolishedResume: async (id: number, markdownContent: string): Promise<{
    message: string;
    polished_resume_data: PolishedResumeData;
    candidate_id: number;
  }> => {
    return apiRequest.put(`/api/candidates/${id}/polished-resume`, {
      markdown_content: markdownContent
    });
  },

  /**
   * Regenerate the polished resume using AI
   */
  regeneratePolishedResume: async (id: number): Promise<{
    message: string;
    polished_resume_data: PolishedResumeData;
    candidate_id: number;
  }> => {
    return apiRequest.post(`/api/candidates/${id}/polished-resume/regenerate`);
  },

  // ==================== Multi-Resume APIs ====================

  /**
   * List all resumes for a candidate
   */
  listResumes: async (candidateId: number): Promise<CandidateResumeListResponse> => {
    return apiRequest.get(`/api/candidates/${candidateId}/resumes`);
  },

  /**
   * Get a specific resume by ID
   */
  getResume: async (candidateId: number, resumeId: number): Promise<CandidateResume> => {
    const resp = await apiRequest.get<{ resume: CandidateResume }>(
      `/api/candidates/${candidateId}/resumes/${resumeId}`
    );
    return resp.resume;
  },

  /**
   * Upload a new resume for a candidate
   */
  uploadNewResume: async (
    candidateId: number,
    file: File,
    options?: {
      is_primary?: boolean;
      trigger_parsing?: boolean;
    }
  ): Promise<{ resume: CandidateResume; message: string }> => {
    const formData = new FormData();
    formData.append('file', file);
    if (options?.is_primary) formData.append('is_primary', 'true');
    if (options?.trigger_parsing !== false) formData.append('trigger_parsing', 'true');

    return apiRequest.post(`/api/candidates/${candidateId}/resumes`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000,
    });
  },

  /**
   * Set a resume as primary
   */
  setResumePrimary: async (candidateId: number, resumeId: number): Promise<CandidateResume> => {
    const resp = await apiRequest.patch<{ resume: CandidateResume; message: string }>(
      `/api/candidates/${candidateId}/resumes/${resumeId}/primary`
    );
    return resp.resume;
  },

  /**
   * Delete a resume
   */
  deleteResume: async (candidateId: number, resumeId: number): Promise<void> => {
    await apiRequest.delete(`/api/candidates/${candidateId}/resumes/${resumeId}`);
  },

  /**
   * Get signed URL for a specific resume
   */
  getResumeDownloadUrl: async (candidateId: number, resumeId: number): Promise<string> => {
    const resp = await apiRequest.get<{ signed_url: string }>(
      `/api/candidates/${candidateId}/resumes/${resumeId}/url`
    );
    return resp.signed_url;
  },

  /**
   * Trigger re-parsing of a specific resume
   */
  reparseSpecificResume: async (
    candidateId: number,
    resumeId: number,
    updateProfile?: boolean
  ): Promise<{ message: string; resume: CandidateResume }> => {
    return apiRequest.post(`/api/candidates/${candidateId}/resumes/${resumeId}/reparse`, {
      update_candidate_profile: updateProfile ?? true,
    });
  },
};

