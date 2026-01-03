/**
 * Resume Tailor API Client
 * Handles all API calls for the resume tailoring feature
 */

import axios from 'axios';
import { apiRequest, tokenManager } from './api-client';
import { env } from './env';
import type {
  TailoredResume,
  TailorResumeResponse,
  TailoredResumeListResponse,
  TailorStatsResponse,
  CompareResponse,
  ExportFormat,
} from '@/types/tailoredResume';

const BASE_URL = '/api/resume-tailor';

// Extended timeout for AI operations (3 minutes)
const AI_TIMEOUT = 180000;

// Create a dedicated axios instance for long-running AI operations
// This ensures the timeout is definitely applied
const aiClient = axios.create({
  baseURL: env.apiBaseUrl,
  timeout: AI_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to AI client requests
aiClient.interceptors.request.use((config) => {
  const token = tokenManager.getAccessToken();
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const resumeTailorApi = {
  /**
   * Tailor a resume for a specific job posting
   */
  tailorResume: async (
    candidateId: number,
    jobPostingId: number
  ): Promise<TailorResumeResponse> => {
    const response = await aiClient.post<TailorResumeResponse>(
      `${BASE_URL}/tailor`,
      {
        candidate_id: candidateId,
        job_posting_id: jobPostingId,
      }
    );
    return response.data;
  },

  /**
   * Tailor a resume based on an existing job match
   */
  tailorFromMatch: async (
    matchId: number
  ): Promise<TailorResumeResponse> => {
    const response = await aiClient.post<TailorResumeResponse>(
      `${BASE_URL}/tailor-from-match`,
      { match_id: matchId }
    );
    return response.data;
  },

  /**
   * Tailor a resume using a manually provided job description (no job posting record)
   */
  tailorManual: async (params: {
    candidateId: number;
    jobTitle: string;
    jobDescription: string;
    jobCompany?: string;
    jobLocation?: string;
    targetScore?: number;
    maxIterations?: number;
  }): Promise<TailorResumeResponse> => {
    const response = await aiClient.post<TailorResumeResponse>(
      `${BASE_URL}/tailor-manual`,
      {
        candidate_id: params.candidateId,
        job_title: params.jobTitle,
        job_description: params.jobDescription,
        job_company: params.jobCompany,
        job_location: params.jobLocation,
        target_score: params.targetScore ?? 80,
        max_iterations: params.maxIterations ?? 1,
      }
    );
    return response.data;
  },

  /**
   * Get a specific tailored resume by tailor_id (UUID)
   */
  getTailoredResume: async (tailorId: string): Promise<TailoredResume> => {
    return apiRequest.get<TailoredResume>(`${BASE_URL}/${tailorId}`);
  },

  /**
   * Get side-by-side comparison of original and tailored resume
   */
  compareResumes: async (tailorId: string): Promise<CompareResponse> => {
    return apiRequest.get<CompareResponse>(`${BASE_URL}/${tailorId}/compare`);
  },

  /**
   * Export tailored resume in specified format
   */
  exportResume: async (tailorId: string, format: ExportFormat): Promise<Blob> => {
    return apiRequest.getBlob(`${BASE_URL}/${tailorId}/export`, {
      params: { format },
    });
  },

  /**
   * Download exported resume
   */
  downloadResume: async (
    tailorId: string,
    format: ExportFormat,
    filename?: string
  ): Promise<void> => {
    const blob = await resumeTailorApi.exportResume(tailorId, format);
    
    // Create download link
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename || `tailored_resume.${format === 'markdown' ? 'md' : format}`;
    document.body.appendChild(a);
    a.click();
    
    // Cleanup
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  },

  /**
   * Get all tailored resumes for a candidate
   */
  getCandidateTailoredResumes: async (
    candidateId: number
  ): Promise<TailoredResumeListResponse> => {
    return apiRequest.get<TailoredResumeListResponse>(
      `${BASE_URL}/candidate/${candidateId}`
    );
  },

  /**
   * Get tailoring statistics
   */
  getStats: async (): Promise<TailorStatsResponse> => {
    return apiRequest.get<TailorStatsResponse>(`${BASE_URL}/stats`);
  },
};
