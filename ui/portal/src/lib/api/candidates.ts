/**
 * Candidates API Functions
 */

import { apiRequest } from '@/lib/api-client';
import type {
  Candidate,
  CandidateCreateRequest,
  CandidateUpdateRequest,
  CandidateListResponse,
  FilterParams,
} from '@/types';

const BASE_URL = '/api/portal/candidates';

/**
 * Get all candidates with pagination and filters
 */
export async function fetchCandidates(params?: FilterParams): Promise<CandidateListResponse> {
  return apiRequest.get<CandidateListResponse>(BASE_URL, { params });
}

/**
 * Get single candidate by ID
 */
export async function fetchCandidate(id: number): Promise<Candidate> {
  return apiRequest.get<Candidate>(`${BASE_URL}/${id}`);
}

/**
 * Create new candidate
 */
export async function createCandidate(data: CandidateCreateRequest): Promise<Candidate> {
  return apiRequest.post<Candidate>(BASE_URL, data);
}

/**
 * Update existing candidate
 */
export async function updateCandidate(id: number, data: CandidateUpdateRequest): Promise<Candidate> {
  return apiRequest.put<Candidate>(`${BASE_URL}/${id}`, data);
}

/**
 * Delete candidate
 */
export async function deleteCandidate(id: number): Promise<void> {
  return apiRequest.delete<void>(`${BASE_URL}/${id}`);
}

/**
 * Change candidate status
 */
export async function changeCandidateStatus(
  id: number,
  status: 'NEW' | 'SCREENING' | 'INTERVIEWING' | 'OFFERED' | 'HIRED' | 'REJECTED' | 'WITHDRAWN'
): Promise<Candidate> {
  return apiRequest.patch<Candidate>(`${BASE_URL}/${id}/status`, { status });
}

/**
 * Rate candidate
 */
export async function rateCandidate(id: number, rating: number): Promise<Candidate> {
  return apiRequest.patch<Candidate>(`${BASE_URL}/${id}/rating`, { rating });
}

