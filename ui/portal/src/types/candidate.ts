/**
 * Candidate-related types
 */

export type CandidateStatus =
  | 'processing'
  | 'pending_review'
  | 'new'
  | 'screening'
  | 'interviewed'
  | 'offered'
  | 'hired'
  | 'rejected'
  | 'withdrawn'
  | 'onboarded'
  | 'ready_for_assignment';

export interface Education {
  degree: string;
  field_of_study?: string;
  institution: string;
  graduation_year?: number;
  gpa?: number;
}

export interface WorkExperience {
  title: string;
  company: string;
  location?: string;
  start_date?: string; // Format: YYYY-MM
  end_date?: string; // Format: YYYY-MM or 'Present'
  is_current: boolean;
  description?: string;
  duration_months?: number;
}

export interface PolishedResumeData {
  markdown_content: string;
  polished_at: string;
  polished_by: 'ai' | 'recruiter';
  ai_model?: string;
  version: number;
  last_edited_at?: string | null;
  last_edited_by_user_id?: number | null;
}

/**
 * Resume processing status
 */
export type ResumeProcessingStatus = 'pending' | 'processing' | 'completed' | 'failed';

/**
 * Candidate Resume - multiple resumes per candidate
 */
export interface CandidateResume {
  id: number;
  tenant_id: number;
  candidate_id: number;
  file_key: string;
  storage_backend: 'local' | 'gcs';
  original_filename: string;
  file_size?: number;
  file_size_mb?: number;
  file_extension?: string;
  mime_type?: string;
  is_primary: boolean;
  processing_status: ResumeProcessingStatus;
  processing_error?: string | null;
  has_parsed_data: boolean;
  has_polished_resume: boolean;
  uploaded_by_user_id?: number | null;
  uploaded_by_candidate: boolean;
  uploaded_at: string;
  processed_at?: string | null;
  created_at: string;
  updated_at: string;
  // Optional - included when requesting full data
  parsed_resume_data?: Record<string, unknown>;
  polished_resume_data?: PolishedResumeData;
  polished_resume_markdown?: string;
}

/**
 * Response for listing resumes
 */
export interface CandidateResumeListResponse {
  candidate_id: number;
  resumes: CandidateResume[];
  total: number;
  primary_resume_id?: number | null;
}

export interface Candidate {
  id: number;
  tenant_id: number;

  // Basic Info
  first_name: string;
  last_name: string;
  email?: string;
  phone?: string;
  full_name?: string;

  // Resume Info (from primary resume - for backward compatibility)
  resume_file_key?: string;
  resume_storage_backend?: string;
  // Signed URLs are provided via the `GET /api/candidates/:id/resume-url` endpoint;
  // Do not depend on `resume_file_url` which was a legacy public field.
  resume_uploaded_at?: string;
  resume_parsed_at?: string;
  
  // Multi-resume support
  has_primary_resume?: boolean;
  resume_count?: number;
  resumes?: CandidateResume[];  // Included when requesting with include_resumes=true

  // Enhanced Personal Info
  location?: string;
  linkedin_url?: string;
  portfolio_url?: string;

  // Professional Info
  current_title?: string;
  total_experience_years?: number;
  notice_period?: string;
  expected_salary?: string;
  professional_summary?: string;

  // Arrays
  preferred_locations: string[];
  skills: string[];
  certifications: string[];
  languages: string[];
  preferred_roles?: string[];
  suggested_roles?: {
    roles: Array<{
      role: string;
      score: number;
      reasoning: string;
    }>;
    generated_at: string;
    model_version: string;
  };

  // JSONB data
  education: Education[];
  work_experience: WorkExperience[];
  parsed_resume_data?: Record<string, unknown>;
  polished_resume_data?: PolishedResumeData;

  // Metadata
  status: CandidateStatus;
  source: string;
  created_at: string;
  updated_at: string;
}

export interface CandidateListItem {
  id: number;
  tenant_id: number;
  first_name: string;
  last_name: string;
  full_name?: string;
  email?: string;
  phone?: string;
  current_title?: string;
  location?: string;
  total_experience_years?: number;
  skills: string[];
  status: CandidateStatus;
  source: string;
  resume_uploaded_at?: string;
  created_at: string;
  updated_at: string;
}

export interface CandidateListResponse {
  candidates: CandidateListItem[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface CandidateCreateInput {
  first_name: string;
  last_name: string;
  email?: string;
  phone?: string;
  full_name?: string;
  location?: string;
  linkedin_url?: string;
  portfolio_url?: string;
  current_title?: string;
  total_experience_years?: number;
  notice_period?: string;
  expected_salary?: string;
  professional_summary?: string;
  preferred_locations?: string[];
  skills?: string[];
  certifications?: string[];
  languages?: string[];
  education?: Education[];
  work_experience?: WorkExperience[];
  status?: CandidateStatus;
  source?: string;
}

export interface CandidateUpdateInput {
  first_name?: string;
  last_name?: string;
  email?: string;
  phone?: string;
  full_name?: string;
  location?: string;
  linkedin_url?: string;
  portfolio_url?: string;
  current_title?: string;
  total_experience_years?: number;
  notice_period?: string;
  expected_salary?: string;
  professional_summary?: string;
  preferred_locations?: string[];
  skills?: string[];
  certifications?: string[];
  languages?: string[];
  education?: Education[];
  work_experience?: WorkExperience[];
  status?: CandidateStatus;
  source?: string;
}

export interface UploadResumeResponse {
  candidate_id?: number;
  status: 'success' | 'error' | 'processing'; // Added 'processing' for async workflow
  message?: string;
  error?: string;
  file_info?: {
    file_path: string;
    file_url: string;
    filename: string;
    original_filename?: string; // Added
    size: number;
    extension: string;
  };
  parsed_data?: {
    full_name?: string;
    email?: string;
    phone?: string;
    location?: string;
    linkedin_url?: string;
    portfolio_url?: string;
    current_title?: string;
    total_experience_years?: number;
    professional_summary?: string;
    skills: string[];
    education: Education[];
    work_experience: WorkExperience[];
    certifications: string[];
    languages: string[];
    confidence_scores?: Record<string, number>;
  };
  extracted_metadata?: {
    page_count: number;
    method: string;
    has_images: boolean;
  };
}

export interface CandidateStats {
  total_candidates: number;
  by_status: Record<CandidateStatus, number>;
  recent_uploads: number;
}

export interface CandidateFilters {
  status?: CandidateStatus;
  skills?: string[];
  search?: string;
  page?: number;
  per_page?: number;
}

/**
 * Resume upload response (for new candidate via resume)
 */
export interface ResumeUploadResponse {
  resume_id: number;
  candidate_id: number;
  file_key: string;
  processing_status: ResumeProcessingStatus;
  is_primary: boolean;
  message?: string;
}

/**
 * Resume signed URL response
 */
export interface ResumeUrlResponse {
  signed_url: string;
  resume_id: number;
  expires_in?: number;
}
