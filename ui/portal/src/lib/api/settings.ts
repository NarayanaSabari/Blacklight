/**
 * Settings API Functions
 */

import { apiClient } from '@/lib/api-client';

const BASE_URL = '/api/portal/settings';

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
