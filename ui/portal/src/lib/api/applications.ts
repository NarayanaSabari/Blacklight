/**
 * Applications API Functions
 */

import { apiClient } from '@/lib/api-client';
import type {
  Application,
  ApplicationCreateRequest,
  ApplicationUpdateRequest,
  ApplicationListResponse,
  FilterParams,
} from '@/types';

const BASE_URL = '/api/portal/applications';

/**
 * Get all applications with pagination and filters
 */
export async function fetchApplications(params?: FilterParams): Promise<ApplicationListResponse> {
  const response = await apiClient.get<ApplicationListResponse>(BASE_URL, { params });
  return response.data;
}

/**
 * Get single application by ID
 */
export async function fetchApplication(id: number): Promise<Application> {
  const response = await apiClient.get<Application>(`${BASE_URL}/${id}`);
  return response.data;
}

/**
 * Create new application
 */
export async function createApplication(data: ApplicationCreateRequest): Promise<Application> {
  const response = await apiClient.post<Application>(BASE_URL, data);
  return response.data;
}

/**
 * Update existing application
 */
export async function updateApplication(id: number, data: ApplicationUpdateRequest): Promise<Application> {
  const response = await apiClient.put<Application>(`${BASE_URL}/${id}`, data);
  return response.data;
}

/**
 * Delete application
 */
export async function deleteApplication(id: number): Promise<void> {
  await apiClient.delete(`${BASE_URL}/${id}`);
}

/**
 * Change application status
 */
export async function changeApplicationStatus(
  id: number,
  status: 'APPLIED' | 'SCREENING' | 'INTERVIEWING' | 'OFFERED' | 'ACCEPTED' | 'REJECTED' | 'WITHDRAWN'
): Promise<Application> {
  const response = await apiClient.patch<Application>(`${BASE_URL}/${id}/status`, { status });
  return response.data;
}

/**
 * Get applications for a specific job
 */
export async function fetchJobApplications(jobId: number, params?: FilterParams): Promise<ApplicationListResponse> {
  const response = await apiClient.get<ApplicationListResponse>(`/api/portal/jobs/${jobId}/applications`, { params });
  return response.data;
}

/**
 * Get applications for a specific candidate
 */
export async function fetchCandidateApplications(candidateId: number, params?: FilterParams): Promise<ApplicationListResponse> {
  const response = await apiClient.get<ApplicationListResponse>(`/api/portal/candidates/${candidateId}/applications`, { params });
  return response.data;
}
