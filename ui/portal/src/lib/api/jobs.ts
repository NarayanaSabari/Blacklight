/**
 * Jobs API Functions
 */

import { apiClient } from '@/lib/api-client';
import type {
  Job,
  JobCreateRequest,
  JobUpdateRequest,
  JobListResponse,
  FilterParams,
} from '@/types';

const BASE_URL = '/api/portal/jobs';

/**
 * Get all jobs with pagination and filters
 */
export async function fetchJobs(params?: FilterParams): Promise<JobListResponse> {
  const response = await apiClient.get<JobListResponse>(BASE_URL, { params });
  return response.data;
}

/**
 * Get single job by ID
 */
export async function fetchJob(id: number): Promise<Job> {
  const response = await apiClient.get<Job>(`${BASE_URL}/${id}`);
  return response.data;
}

/**
 * Create new job
 */
export async function createJob(data: JobCreateRequest): Promise<Job> {
  const response = await apiClient.post<Job>(BASE_URL, data);
  return response.data;
}

/**
 * Update existing job
 */
export async function updateJob(id: number, data: JobUpdateRequest): Promise<Job> {
  const response = await apiClient.put<Job>(`${BASE_URL}/${id}`, data);
  return response.data;
}

/**
 * Delete job
 */
export async function deleteJob(id: number): Promise<void> {
  await apiClient.delete(`${BASE_URL}/${id}`);
}

/**
 * Change job status
 */
export async function changeJobStatus(
  id: number,
  status: 'DRAFT' | 'OPEN' | 'CLOSED' | 'FILLED' | 'ON_HOLD'
): Promise<Job> {
  const response = await apiClient.patch<Job>(`${BASE_URL}/${id}/status`, { status });
  return response.data;
}
