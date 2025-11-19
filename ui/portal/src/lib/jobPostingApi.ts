/**
 * Job Posting API Client
 * API functions for job posting operations
 */

import { apiRequest } from './api-client';
import type { JobPosting } from '@/types';

export const jobPostingApi = {
  /**
   * Get job posting details by ID
   */
  getJobPosting: async (jobId: number): Promise<JobPosting> => {
    return apiRequest.get<JobPosting>(`/api/job-postings/${jobId}`);
  },

  /**
   * List all job postings with optional filters
   */
  listJobPostings: async (params?: {
    page?: number;
    per_page?: number;
    status?: string;
    search?: string;
    location?: string;
    is_remote?: boolean;
  }): Promise<{
    jobs: JobPosting[];
    total: number;
    page: number;
    per_page: number;
    pages: number;
  }> => {
    const queryParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          queryParams.append(key, String(value));
        }
      });
    }

    return apiRequest.get(`/api/job-postings?${queryParams.toString()}`);
  },

  /**
   * Search job postings
   */
  searchJobPostings: async (query: string): Promise<JobPosting[]> => {
    return apiRequest.get<JobPosting[]>(`/api/job-postings/search?q=${encodeURIComponent(query)}`);
  },
};
