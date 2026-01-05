/**
 * Document API Service
 * Handles all document-related API calls using universal API client
 */

import { apiRequest } from './api-client';
import type {
  Document,
  DocumentListResponse,
  DocumentResponse,
  DocumentUrlResponse,
  DocumentStats,
  DocumentFilters,
  DocumentUploadRequest,
  DocumentVerifyRequest,
  StorageBrowseResponse,
} from '@/types/document';

export const documentApi = {
  /**
   * Upload a document
   */
  uploadDocument: async (request: DocumentUploadRequest): Promise<DocumentResponse> => {
    const formData = new FormData();
    formData.append('file', request.file);
    formData.append('document_type', request.document_type);
    
    if (request.candidate_id) {
      formData.append('candidate_id', request.candidate_id.toString());
    }
    if (request.invitation_id) {
      formData.append('invitation_id', request.invitation_id.toString());
    }
    if (request.description) {
      formData.append('description', request.description);
    }

    return apiRequest.postForm<DocumentResponse>('/api/documents/upload', formData);
  },

  /**
   * List documents with filters
   */
  listDocuments: async (filters: DocumentFilters = {}): Promise<DocumentListResponse> => {
    const params = new URLSearchParams();
    
    if (filters.candidate_id) params.append('candidate_id', filters.candidate_id.toString());
    if (filters.invitation_id) params.append('invitation_id', filters.invitation_id.toString());
    if (filters.document_type) params.append('document_type', filters.document_type);
    if (filters.is_verified !== undefined) params.append('is_verified', filters.is_verified.toString());
    if (filters.page) params.append('page', filters.page.toString());
    if (filters.per_page) params.append('per_page', filters.per_page.toString());

    const queryString = params.toString();
    const url = queryString ? `/api/documents?${queryString}` : '/api/documents';
    
    return apiRequest.get<DocumentListResponse>(url);
  },

  /**
   * Get document metadata by ID
   */
  getDocument: async (id: number): Promise<Document> => {
    return apiRequest.get<Document>(`/api/documents/${id}`);
  },

  /**
   * Download document file
   */
  downloadDocument: async (id: number): Promise<Blob> => {
    return apiRequest.getBlob(`/api/documents/${id}/download`);
  },

  /**
   * Get signed URL for document (for GCS backend)
   */
  getDocumentUrl: async (id: number, expirySeconds: number = 3600): Promise<DocumentUrlResponse> => {
    return apiRequest.get<DocumentUrlResponse>(`/api/documents/${id}/url?expiry=${expirySeconds}`);
  },

  /**
   * Verify a document (HR only)
   */
  verifyDocument: async (id: number, request: DocumentVerifyRequest): Promise<Document> => {
    return apiRequest.post<Document>(`/api/documents/${id}/verify`, request);
  },

  /**
   * Delete a document
   */
  deleteDocument: async (id: number): Promise<void> => {
    return apiRequest.delete<void>(`/api/documents/${id}`);
  },

  /**
   * Get document statistics
   */
  getStats: async (): Promise<DocumentStats> => {
    return apiRequest.get<DocumentStats>('/api/documents/stats');
  },

  /**
   * Browse storage files and folders
   */
  browseStorage: async (path: string = '', recursive: boolean = false): Promise<StorageBrowseResponse> => {
    const params = new URLSearchParams();
    if (path) params.append('path', path);
    if (recursive) params.append('recursive', 'true');
    
    const queryString = params.toString();
    const url = queryString ? `/api/documents/storage/browse?${queryString}` : '/api/documents/storage/browse';
    
    return apiRequest.get<StorageBrowseResponse>(url);
  },

  /**
   * Download a file from storage by path
   */
  downloadStorageFile: async (path: string): Promise<Blob> => {
    return apiRequest.getBlob(`/api/documents/storage/download?path=${encodeURIComponent(path)}`);
  },
};

// Public document API (for candidate onboarding)
export const publicDocumentApi = {
  /**
   * Upload document during onboarding (token-based auth)
   */
  uploadDocument: async (
    file: File,
    invitationToken: string,
    documentType: string
  ): Promise<DocumentResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('invitation_token', invitationToken);
    formData.append('document_type', documentType);

    return apiRequest.postForm<DocumentResponse>('/api/public/documents/upload', formData);
  },

  /**
   * Get document by ID during onboarding
   */
  getDocument: async (id: number, invitationToken: string): Promise<Document> => {
    return apiRequest.get<Document>(`/api/public/documents/${id}?token=${invitationToken}`);
  },

  /**
   * List documents for an invitation
   */
  listDocuments: async (invitationToken: string): Promise<DocumentListResponse> => {
    return apiRequest.get<DocumentListResponse>(`/api/public/documents?token=${invitationToken}`);
  },
};
