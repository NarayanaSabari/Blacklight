/**
 * Job Posting API Client
 * API functions for job posting operations.
 * Supports both scraped jobs (global) and email-sourced jobs (tenant-specific).
 */

import { apiRequest } from './api-client';
import type { JobPosting } from '@/types';

/** Matched candidate info returned with job listing */
export interface MatchedCandidate {
  candidate_id: number;
  name: string;
  match_score: number;
  match_grade: string;
}

/** Extended JobPosting with sourced_by info */
export interface JobPostingWithSource extends JobPosting {
  sourced_by?: {
    id: number;
    first_name: string;
    last_name: string;
    email: string;
  } | null;
  additional_source_users?: Array<{
    user_id: number;
    email_id: string;
    received_at: string;
  }>;
  email_integration?: {
    provider: 'gmail' | 'outlook';
    email_address: string;
    email_direct_link: string | null;
  } | null;
  matched_candidates?: MatchedCandidate[];
  matched_candidates_count?: number;
}

/** Job source filter type */
export type JobSourceFilter = 'all' | 'email' | 'scraped';

/** List jobs response */
export interface JobListResponse {
  jobs: JobPostingWithSource[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

/** Job statistics response */
export interface JobStatisticsResponse {
  total_jobs: number;
  active_jobs: number;
  remote_jobs: number;
  unique_companies: number;
  unique_locations: number;
  // Source breakdown
  scraped_jobs: number;
  email_jobs: number;
  by_platform: Record<string, number>;
  // Email stats
  email_by_user: Array<{
    user_id: number;
    name: string;
    email: string;
    jobs_count: number;
  }>;
  emails_processed: number;
  emails_converted: number;
  email_conversion_rate: number;
}

/** Job sources response */
export interface JobSourcesResponse {
  sources: Array<{
    platform: string;
    count: number;
    is_email: boolean;
    display_name: string;
  }>;
  total_sources: number;
}

/** Team sources response */
export interface TeamSourcesResponse {
  team_sources: Array<{
    user: {
      id: number;
      name: string;
      email: string;
    };
    job_count: number;
    jobs: JobPosting[];
  }>;
  total_team_members: number;
  page: number;
  per_page: number;
}

export const jobPostingApi = {
  /**
   * Get job posting details by ID
   */
  getJobPosting: async (jobId: number): Promise<JobPostingWithSource> => {
    return apiRequest.get<JobPostingWithSource>(`/api/job-postings/${jobId}`);
  },

  /**
   * List all job postings with optional filters.
   * 
   * Visibility rules:
   * - Scraped jobs (is_email_sourced=false): Visible to all tenants
   * - Email jobs (is_email_sourced=true): Only visible to source tenant
   * 
   * @param params.source - Filter by source: 'all', 'email', or 'scraped'
   * @param params.platform - Filter by specific platform (indeed, dice, email, etc.)
   * @param params.sourced_by - Filter email jobs by user ID who sourced them
   */
  listJobPostings: async (params?: {
    page?: number;
    per_page?: number;
    status?: string;
    search?: string;
    location?: string;
    is_remote?: boolean;
    // New unified job filters
    source?: JobSourceFilter;
    platform?: string;
    sourced_by?: number;
    sort_by?: 'date' | 'posted_date' | 'title' | 'company' | 'salary_min' | 'created_at';
    sort_order?: 'asc' | 'desc';
  }): Promise<JobListResponse> => {
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
  searchJobPostings: async (query: string): Promise<JobPostingWithSource[]> => {
    return apiRequest.get<JobPostingWithSource[]>(`/api/job-postings/search?q=${encodeURIComponent(query)}`);
  },

  /**
   * Get job posting statistics including email breakdown
   */
  getStatistics: async (): Promise<JobStatisticsResponse> => {
    return apiRequest.get<JobStatisticsResponse>('/api/job-postings/statistics');
  },

  /**
   * Get available job sources/platforms
   */
  getSources: async (): Promise<JobSourcesResponse> => {
    return apiRequest.get<JobSourcesResponse>('/api/job-postings/sources');
  },

  /**
   * Get jobs grouped by team member who sourced them (email jobs)
   */
  getTeamSources: async (params?: {
    page?: number;
    per_page?: number;
    user_id?: number;
  }): Promise<TeamSourcesResponse> => {
    const queryParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          queryParams.append(key, String(value));
        }
      });
    }
    return apiRequest.get<TeamSourcesResponse>(`/api/job-postings/team-sources?${queryParams.toString()}`);
  },
};
