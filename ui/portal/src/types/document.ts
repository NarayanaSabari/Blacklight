/**
 * Document-related types
 */

export type DocumentType = 
  | 'resume'
  | 'id_proof'
  | 'address_proof'
  | 'education_certificate'
  | 'experience_letter'
  | 'other';

export type StorageBackend = 'local' | 'gcs';

export interface Document {
  id: number;
  tenant_id: number;
  candidate_id?: number;
  invitation_id?: number;
  
  // File info
  file_name: string;
  file_path?: string;
  file_key: string;
  file_size: number;
  mime_type: string;
  storage_backend: StorageBackend;
  
  // Document metadata
  document_type: DocumentType;
  description?: string;
  
  // Verification
  is_verified: boolean;
  verified_at?: string;
  verified_by_id?: number;
  verification_notes?: string;
  
  // Upload tracking
  uploaded_by_id?: number;
  uploaded_at: string;
  
  // Timestamps
  created_at: string;
  updated_at: string;
}

export interface DocumentListItem {
  id: number;
  tenant_id: number;
  candidate_id?: number;
  invitation_id?: number;
  file_name: string;
  file_size: number;
  mime_type: string;
  document_type: DocumentType;
  is_verified: boolean;
  verified_at?: string;
  uploaded_at: string;
  storage_backend: StorageBackend;
}

export interface DocumentListResponse {
  documents: DocumentListItem[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface DocumentUploadRequest {
  file: File;
  document_type: DocumentType;
  candidate_id?: number;
  invitation_id?: number;
  description?: string;
}

export interface DocumentResponse {
  id: number;
  tenant_id: number;
  candidate_id?: number;
  invitation_id?: number;
  file_name: string;
  file_path?: string;
  file_key: string;
  file_size: number;
  mime_type: string;
  storage_backend: StorageBackend;
  document_type: DocumentType;
  description?: string;
  is_verified: boolean;
  uploaded_by_id?: number;
  uploaded_at: string;
  created_at: string;
  updated_at: string;
}

export interface DocumentUrlResponse {
  document_id: number;
  file_name: string;
  url: string;
  expires_in: number;
}

export interface DocumentVerifyRequest {
  notes?: string;
}

export interface DocumentStats {
  total_documents: number;
  by_type: Record<DocumentType, number>;
  verified_count: number;
  unverified_count: number;
  total_size_bytes: number;
  by_storage: Record<StorageBackend, number>;
}

export interface DocumentFilters {
  candidate_id?: number;
  invitation_id?: number;
  document_type?: DocumentType;
  is_verified?: boolean;
  page?: number;
  per_page?: number;
}

export interface PublicDocumentUploadRequest {
  file: File;
  invitation_token: string;
  document_type: DocumentType;
}

// UI-specific types
export interface DocumentUploadProgress {
  file: File;
  progress: number;
  status: 'pending' | 'uploading' | 'success' | 'error';
  error?: string;
  document?: Document;
}

export const DOCUMENT_TYPE_LABELS: Record<DocumentType, string> = {
  resume: 'Resume/CV',
  id_proof: 'ID Proof',
  address_proof: 'Address Proof',
  education_certificate: 'Education Certificate',
  experience_letter: 'Experience Letter',
  other: 'Other',
};

export const DOCUMENT_TYPE_ICONS: Record<DocumentType, string> = {
  resume: '📄',
  id_proof: '🪪',
  address_proof: '🏠',
  education_certificate: '🎓',
  experience_letter: '💼',
  other: '📎',
};

export const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
export const ALLOWED_FILE_TYPES = [
  'application/pdf',
  'image/jpeg',
  'image/jpg',
  'image/png',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
];

export const ALLOWED_FILE_EXTENSIONS = ['.pdf', '.jpg', '.jpeg', '.png', '.doc', '.docx'];
