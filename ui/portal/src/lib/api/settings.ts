/**
 * Settings API Functions
 */

import { apiClient } from '@/lib/api-client';
import type { PortalUserFull } from '@/types';

const BASE_URL = '/api/portal/settings';
const AUTH_URL = '/api/portal/auth';

/**
 * Document requirement configuration type
 */
export interface DocumentRequirement {
  id: string;
  document_type: string;
  label: string;
  description?: string;
  is_required: boolean;
  display_order: number;
  allowed_file_types: string[];
  max_file_size_mb: number;
}

/**
 * Response from get document requirements endpoint
 */
export interface DocumentRequirementsResponse {
  requirements: DocumentRequirement[];
  message?: string;
}

/**
 * Request to update document requirements
 */
export interface UpdateDocumentRequirementsRequest {
  requirements: DocumentRequirement[];
}

/**
 * Profile update request
 */
export interface ProfileUpdateRequest {
  first_name?: string;
  last_name?: string;
  phone?: string;
}

/**
 * Change password request
 */
export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

/**
 * Get tenant document requirements for self-onboarding
 */
export async function fetchDocumentRequirements(): Promise<DocumentRequirementsResponse> {
  const response = await apiClient.get<DocumentRequirementsResponse>(`${BASE_URL}/document-requirements`);
  return response.data;
}

/**
 * Update tenant document requirements for self-onboarding
 */
export async function updateDocumentRequirements(
  data: UpdateDocumentRequirementsRequest
): Promise<DocumentRequirementsResponse> {
  const response = await apiClient.put<DocumentRequirementsResponse>(
    `${BASE_URL}/document-requirements`,
    data
  );
  return response.data;
}

/**
 * Get current user profile
 */
export async function fetchCurrentUserProfile(): Promise<PortalUserFull> {
  const response = await apiClient.get<PortalUserFull>(`${AUTH_URL}/me`);
  return response.data;
}

/**
 * Update current user profile
 */
export async function updateProfile(data: ProfileUpdateRequest): Promise<PortalUserFull> {
  const response = await apiClient.put<PortalUserFull>(`${AUTH_URL}/me`, data);
  return response.data;
}

/**
 * Change current user password
 */
export async function changePassword(data: ChangePasswordRequest): Promise<{ message: string }> {
  const response = await apiClient.post<{ message: string }>(`${AUTH_URL}/change-password`, data);
  return response.data;
}
