/**
 * Interviews API Functions
 */

import { apiClient } from '@/lib/api-client';
import type {
  Interview,
  InterviewCreateRequest,
  InterviewUpdateRequest,
  InterviewListResponse,
  FilterParams,
} from '@/types';

const BASE_URL = '/api/portal/interviews';

/**
 * Get all interviews with pagination and filters
 */
export async function fetchInterviews(params?: FilterParams): Promise<InterviewListResponse> {
  const response = await apiClient.get<InterviewListResponse>(BASE_URL, { params });
  return response.data;
}

/**
 * Get single interview by ID
 */
export async function fetchInterview(id: number): Promise<Interview> {
  const response = await apiClient.get<Interview>(`${BASE_URL}/${id}`);
  return response.data;
}

/**
 * Create new interview
 */
export async function createInterview(data: InterviewCreateRequest): Promise<Interview> {
  const response = await apiClient.post<Interview>(BASE_URL, data);
  return response.data;
}

/**
 * Update existing interview
 */
export async function updateInterview(id: number, data: InterviewUpdateRequest): Promise<Interview> {
  const response = await apiClient.put<Interview>(`${BASE_URL}/${id}`, data);
  return response.data;
}

/**
 * Delete interview
 */
export async function deleteInterview(id: number): Promise<void> {
  await apiClient.delete(`${BASE_URL}/${id}`);
}

/**
 * Change interview status
 */
export async function changeInterviewStatus(
  id: number,
  status: 'SCHEDULED' | 'COMPLETED' | 'CANCELLED' | 'NO_SHOW' | 'RESCHEDULED'
): Promise<Interview> {
  const response = await apiClient.patch<Interview>(`${BASE_URL}/${id}/status`, { status });
  return response.data;
}

/**
 * Submit interview feedback
 */
export async function submitInterviewFeedback(
  id: number,
  data: {
    feedback: string;
    rating: number;
    recommendation: 'STRONG_YES' | 'YES' | 'MAYBE' | 'NO' | 'STRONG_NO';
  }
): Promise<Interview> {
  const response = await apiClient.patch<Interview>(`${BASE_URL}/${id}/feedback`, data);
  return response.data;
}

/**
 * Get interviews for a specific application
 */
export async function fetchApplicationInterviews(applicationId: number, params?: FilterParams): Promise<InterviewListResponse> {
  const response = await apiClient.get<InterviewListResponse>(`/api/portal/applications/${applicationId}/interviews`, { params });
  return response.data;
}

/**
 * Get upcoming interviews
 */
export async function fetchUpcomingInterviews(days: number = 7): Promise<InterviewListResponse> {
  const response = await apiClient.get<InterviewListResponse>(`${BASE_URL}/upcoming`, { params: { days } });
  return response.data;
}
