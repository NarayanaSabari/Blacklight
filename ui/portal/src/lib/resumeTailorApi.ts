/**
 * Resume Tailor API Client
 * Handles all API calls for the resume tailoring feature
 */

import { apiRequest, apiClient, tokenManager } from './api-client';
import type {
  TailoredResume,
  TailorResumeResponse,
  TailoredResumeListResponse,
  TailorStatsResponse,
  CompareResponse,
  ExportFormat,
  TailorStreamEvent,
} from '@/types/tailoredResume';

const BASE_URL = '/api/resume-tailor';

export const resumeTailorApi = {
  /**
   * Tailor a resume for a specific job posting
   */
  tailorResume: async (
    candidateId: number,
    jobPostingId: number
  ): Promise<TailorResumeResponse> => {
    return apiRequest.post<TailorResumeResponse>(`${BASE_URL}/tailor`, {
      candidate_id: candidateId,
      job_posting_id: jobPostingId,
    });
  },

  /**
   * Tailor a resume based on an existing job match
   */
  tailorFromMatch: async (
    candidateId: number,
    jobMatchId: number
  ): Promise<TailorResumeResponse> => {
    return apiRequest.post<TailorResumeResponse>(`${BASE_URL}/tailor-from-match`, {
      candidate_id: candidateId,
      job_match_id: jobMatchId,
    });
  },

  /**
   * Tailor resume with streaming progress updates
   * Returns an EventSource for SSE events
   */
  tailorWithStreaming: (
    candidateId: number,
    jobPostingId: number,
    onProgress: (event: TailorStreamEvent) => void,
    onComplete: (result: TailoredResume) => void,
    onError: (error: string) => void
  ): (() => void) => {
    const token = tokenManager.getAccessToken();
    
    // Create URL with query params for auth
    const url = new URL(`${apiClient.defaults.baseURL}${BASE_URL}/tailor-stream`);
    
    // Use fetch with POST for SSE (EventSource doesn't support POST)
    const controller = new AbortController();
    
    const fetchStream = async () => {
      try {
        const response = await fetch(url.toString(), {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify({
            candidate_id: candidateId,
            job_posting_id: jobPostingId,
          }),
          signal: controller.signal,
        });

        if (!response.ok) {
          const error = await response.json();
          onError(error.message || 'Failed to start tailoring');
          return;
        }

        const reader = response.body?.getReader();
        if (!reader) {
          onError('No response body');
          return;
        }

        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const event: TailorStreamEvent = JSON.parse(line.slice(6));
                
                if (event.type === 'complete' && event.result) {
                  onComplete(event.result);
                } else if (event.type === 'error') {
                  onError(event.error || 'Unknown error');
                } else {
                  onProgress(event);
                }
              } catch (e) {
                console.warn('Failed to parse SSE event:', e);
              }
            }
          }
        }
      } catch (error) {
        if ((error as Error).name !== 'AbortError') {
          onError((error as Error).message || 'Stream error');
        }
      }
    };

    fetchStream();

    // Return cleanup function
    return () => controller.abort();
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
