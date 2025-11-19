/**
 * Job Match API Service
 * Handles all job matching-related API calls using universal API client
 */

import { apiRequest } from './api-client';
import type {
  JobMatch,
  JobMatchListResponse,
  JobMatchStats,
  GenerateMatchesRequest,
  GenerateMatchesResponse,
  JobMatchFilters,
} from '@/types/jobMatch';

export const jobMatchApi = {
  /**
   * Get matches for a specific candidate
   */
  getCandidateMatches: async (
    candidateId: number,
    filters: JobMatchFilters = {}
  ): Promise<JobMatchListResponse> => {
    const params = new URLSearchParams();
    
    if (filters.min_score) params.append('min_score', filters.min_score.toString());
    if (filters.max_score) params.append('max_score', filters.max_score.toString());
    if (filters.grade) params.append('grade', filters.grade);
    if (filters.page) params.append('page', filters.page.toString());
    if (filters.per_page) params.append('per_page', filters.per_page.toString());
    if (filters.sort_by) params.append('sort_by', filters.sort_by);
    if (filters.sort_order) params.append('sort_order', filters.sort_order);
    
    const queryString = params.toString();
    const url = `/api/job-matches/candidates/${candidateId}${queryString ? '?' + queryString : ''}`;
    
    return apiRequest.get<JobMatchListResponse>(url);
  },

  /**
   * Get a specific match by ID
   */
  getMatch: async (matchId: number): Promise<JobMatch> => {
    return apiRequest.get<JobMatch>(`/api/job-matches/${matchId}`);
  },

  /**
   * Generate matches for a candidate
   */
  generateMatches: async (
    candidateId: number,
    options: GenerateMatchesRequest = {}
  ): Promise<GenerateMatchesResponse> => {
    return apiRequest.post<GenerateMatchesResponse>(
      `/api/job-matches/candidates/${candidateId}/generate`,
      options
    );
  },

  /**
   * Get match statistics for a candidate
   */
  getMatchStats: async (candidateId: number): Promise<JobMatchStats> => {
    return apiRequest.get<JobMatchStats>(
      `/api/job-matches/candidates/${candidateId}/stats`
    );
  },

  /**
   * Delete a specific match
   */
  deleteMatch: async (matchId: number): Promise<void> => {
    return apiRequest.delete<void>(`/api/job-matches/${matchId}`);
  },

  /**
   * Refresh all matches for a candidate (regenerate)
   */
  refreshCandidateMatches: async (
    candidateId: number,
    options: GenerateMatchesRequest = {}
  ): Promise<GenerateMatchesResponse> => {
    return apiRequest.post<GenerateMatchesResponse>(
      `/api/job-matches/candidates/${candidateId}/refresh`,
      options
    );
  },

  /**
   * Bulk refresh matches for all candidates in tenant
   * (Admin operation)
   */
  refreshAllMatches: async (
    options: GenerateMatchesRequest = {}
  ): Promise<{
    message: string;
    total_candidates: number;
    total_matches: number;
  }> => {
    return apiRequest.post(
      '/api/job-matches/generate-all',
      options
    );
  },
};
