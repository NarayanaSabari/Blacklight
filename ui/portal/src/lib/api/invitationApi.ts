/**
 * Invitation API Client
 * All API calls for invitation management and candidate onboarding
 */

import { apiRequest } from '@/lib/api-client';
import type {
  InvitationWithRelations,
  InvitationCreateRequest,
  InvitationUpdateRequest,
  InvitationListParams,
  InvitationListResponse,
  InvitationStatsResponse,
  InvitationReviewRequest,
  OnboardingSubmissionRequest,
  OnboardingSubmissionResponse,
  DocumentUploadResponse,
  BulkInvitationRequest,
  BulkInvitationResponse,
  InvitationAuditLog,
} from '@/types';

const INVITATION_BASE = '/api/invitations';

/**
 * HR/Admin Invitation Management (Authenticated Routes)
 */

export const invitationApi = {
  /**
   * List all invitations with filters and pagination
   */
  list: (params?: InvitationListParams): Promise<InvitationListResponse> => {
    const queryParams = new URLSearchParams();
    
    if (params?.page) queryParams.append('page', String(params.page));
    if (params?.per_page) queryParams.append('per_page', String(params.per_page));
    if (params?.status) queryParams.append('status', params.status);
    if (params?.search) queryParams.append('search', params.search);
    if (params?.sort_by) queryParams.append('sort_by', params.sort_by);
    if (params?.sort_order) queryParams.append('sort_order', params.sort_order);

    const url = queryParams.toString() 
      ? `${INVITATION_BASE}?${queryParams.toString()}`
      : INVITATION_BASE;

    return apiRequest.get<InvitationListResponse>(url);
  },

  /**
   * Get invitation statistics
   */
  stats: (): Promise<InvitationStatsResponse> => {
    return apiRequest.get<InvitationStatsResponse>(`${INVITATION_BASE}/stats`);
  },

  /**
   * Create a new invitation
   */
  create: (data: InvitationCreateRequest): Promise<InvitationWithRelations> => {
    return apiRequest.post<InvitationWithRelations>(INVITATION_BASE, data);
  },

  /**
   * Get invitation details by ID
   */
  getById: (id: number): Promise<InvitationWithRelations> => {
    return apiRequest.get<InvitationWithRelations>(`${INVITATION_BASE}/${id}`);
  },

  /**
   * Update an invitation
   */
  update: (id: number, data: InvitationUpdateRequest): Promise<InvitationWithRelations> => {
    return apiRequest.put<InvitationWithRelations>(`${INVITATION_BASE}/${id}`, data);
  },

  /**
   * Resend invitation email
   */
  resend: (id: number): Promise<{ success: boolean; message: string }> => {
    return apiRequest.post<{ success: boolean; message: string }>(
      `${INVITATION_BASE}/${id}/resend`,
      {} // Send empty object to ensure Content-Type: application/json
    );
  },

  /**
   * Cancel an invitation
   */
  cancel: (id: number): Promise<InvitationWithRelations> => {
    return apiRequest.post<InvitationWithRelations>(`${INVITATION_BASE}/${id}/cancel`);
  },

  /**
   * Approve a submitted invitation with optional HR edits
   */
  approve: (id: number, data?: { notes?: string; edited_data?: Record<string, any> }): Promise<{ message: string; candidate_id: number; invitation_id: number }> => {
    return apiRequest.post<{ message: string; candidate_id: number; invitation_id: number }>(
      `${INVITATION_BASE}/${id}/review`,
      {
        action: 'approve',
        notes: data?.notes,
        edited_data: data?.edited_data
      }
    );
  },

  /**
   * Reject a submitted invitation
   */
  reject: (id: number, data: { rejection_reason: string; notes?: string }): Promise<{ message: string; invitation_id: number }> => {
    return apiRequest.post<{ message: string; invitation_id: number }>(
      `${INVITATION_BASE}/${id}/review`,
      {
        action: 'reject',
        rejection_reason: data.rejection_reason,
        notes: data?.notes
      }
    );
  },

  /**
   * Get audit logs for an invitation
   */
  getAuditLogs: (id: number): Promise<InvitationAuditLog[]> => {
    return apiRequest.get<InvitationAuditLog[]>(`${INVITATION_BASE}/${id}/audit-logs`);
  },

  /**
   * Bulk create invitations
   */
  bulkCreate: (data: BulkInvitationRequest): Promise<BulkInvitationResponse> => {
    return apiRequest.post<BulkInvitationResponse>(`${INVITATION_BASE}/bulk`, data);
  },

  /**
   * Get submitted invitations for review
   */
  getSubmittedInvitations: (params?: InvitationListParams): Promise<InvitationListResponse> => {
    const queryParams = new URLSearchParams();
    
    if (params?.page) queryParams.append('page', String(params.page));
    if (params?.per_page) queryParams.append('per_page', String(params.per_page));
    // Always filter by status=submitted for this endpoint
    queryParams.append('status', 'submitted'); 
    if (params?.search) queryParams.append('search', params.search);
    if (params?.sort_by) queryParams.append('sort_by', params.sort_by);
    if (params?.sort_order) queryParams.append('sort_order', params.sort_order);

    const url = `${INVITATION_BASE}${
      queryParams.toString() ? `?${queryParams.toString()}` : ''
    }`;

    return apiRequest.get<InvitationListResponse>(url);
  },
};

/**
 * Public Candidate Onboarding (Unauthenticated Routes)
 */

export const onboardingApi = {
  /**
   * Verify invitation token
   */
  verify: (token: string): Promise<InvitationWithRelations> => {
    return apiRequest.get<InvitationWithRelations>(`${INVITATION_BASE}/public/verify?token=${token}`);
  },

  /**
   * Submit candidate onboarding data
   */
  submit: (
    token: string,
    data: OnboardingSubmissionRequest
  ): Promise<OnboardingSubmissionResponse> => {
    return apiRequest.post<OnboardingSubmissionResponse>(
      `${INVITATION_BASE}/public/submit?token=${token}`,
      data
    );
  },

  /**
   * Upload document during onboarding (using new document API)
   */
  uploadDocument: (
    token: string,
    file: File,
    documentType: string
  ): Promise<DocumentUploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', documentType);

    return apiRequest.postForm<DocumentUploadResponse>(
      `${INVITATION_BASE}/public/documents?token=${token}`,
      formData
    );
  },

  /**
   * Parse resume using AI during onboarding
   */
  parseResume: (token: string, file: File): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('invitation_token', token);

    return apiRequest.postForm<any>(
      '/api/public/invitations/parse-resume',
      formData
    );
  },
};
