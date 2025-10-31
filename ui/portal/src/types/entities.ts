/**
 * Portal Entity Types
 * Core data models for Jobs, Candidates, Applications, Interviews
 */

// ==================== JOBS ====================

export interface Job {
  id: number;
  tenant_id: number;
  title: string;
  description: string;
  department: string | null;
  location: string;
  employment_type: 'FULL_TIME' | 'PART_TIME' | 'CONTRACT' | 'INTERNSHIP';
  experience_level: 'ENTRY' | 'MID' | 'SENIOR' | 'LEAD' | 'EXECUTIVE';
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string;
  status: 'DRAFT' | 'OPEN' | 'CLOSED' | 'FILLED' | 'ON_HOLD';
  requirements: string[];
  responsibilities: string[];
  benefits: string[];
  posted_date: string | null;
  closing_date: string | null;
  positions_available: number;
  positions_filled: number;
  created_by_id: number;
  created_at: string;
  updated_at: string;
  // Relations
  created_by?: PortalUserBasic;
  applications_count?: number;
}

export interface JobCreateRequest {
  title: string;
  description: string;
  department?: string;
  location: string;
  employment_type: 'FULL_TIME' | 'PART_TIME' | 'CONTRACT' | 'INTERNSHIP';
  experience_level: 'ENTRY' | 'MID' | 'SENIOR' | 'LEAD' | 'EXECUTIVE';
  salary_min?: number;
  salary_max?: number;
  salary_currency?: string;
  status?: 'DRAFT' | 'OPEN';
  requirements?: string[];
  responsibilities?: string[];
  benefits?: string[];
  positions_available?: number;
  closing_date?: string;
}

export interface JobUpdateRequest {
  title?: string;
  description?: string;
  department?: string;
  location?: string;
  employment_type?: 'FULL_TIME' | 'PART_TIME' | 'CONTRACT' | 'INTERNSHIP';
  experience_level?: 'ENTRY' | 'MID' | 'SENIOR' | 'LEAD' | 'EXECUTIVE';
  salary_min?: number;
  salary_max?: number;
  salary_currency?: string;
  status?: 'DRAFT' | 'OPEN' | 'CLOSED' | 'FILLED' | 'ON_HOLD';
  requirements?: string[];
  responsibilities?: string[];
  benefits?: string[];
  positions_available?: number;
  closing_date?: string;
}

export interface JobListResponse {
  jobs: Job[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

// ==================== CANDIDATES ====================

export interface Candidate {
  id: number;
  tenant_id: number;
  first_name: string;
  last_name: string;
  full_name: string;
  email: string;
  phone: string | null;
  location: string | null;
  current_company: string | null;
  current_title: string | null;
  experience_years: number | null;
  education: string | null;
  skills: string[];
  linkedin_url: string | null;
  resume_url: string | null;
  portfolio_url: string | null;
  status: 'NEW' | 'SCREENING' | 'INTERVIEWING' | 'OFFERED' | 'HIRED' | 'REJECTED' | 'WITHDRAWN';
  source: 'DIRECT' | 'REFERRAL' | 'LINKEDIN' | 'INDEED' | 'CAREER_SITE' | 'OTHER';
  notes: string | null;
  rating: number | null;
  added_by_id: number;
  created_at: string;
  updated_at: string;
  // Relations
  added_by?: PortalUserBasic;
  applications_count?: number;
}

export interface CandidateCreateRequest {
  first_name: string;
  last_name: string;
  email: string;
  phone?: string;
  location?: string;
  current_company?: string;
  current_title?: string;
  experience_years?: number;
  education?: string;
  skills?: string[];
  linkedin_url?: string;
  resume_url?: string;
  portfolio_url?: string;
  source?: 'DIRECT' | 'REFERRAL' | 'LINKEDIN' | 'INDEED' | 'CAREER_SITE' | 'OTHER';
  notes?: string;
}

export interface CandidateUpdateRequest {
  first_name?: string;
  last_name?: string;
  email?: string;
  phone?: string;
  location?: string;
  current_company?: string;
  current_title?: string;
  experience_years?: number;
  education?: string;
  skills?: string[];
  linkedin_url?: string;
  resume_url?: string;
  portfolio_url?: string;
  source?: 'DIRECT' | 'REFERRAL' | 'LINKEDIN' | 'INDEED' | 'CAREER_SITE' | 'OTHER';
  status?: 'NEW' | 'SCREENING' | 'INTERVIEWING' | 'OFFERED' | 'HIRED' | 'REJECTED' | 'WITHDRAWN';
  notes?: string;
  rating?: number;
}

export interface CandidateListResponse {
  candidates: Candidate[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

// ==================== APPLICATIONS ====================

export interface Application {
  id: number;
  tenant_id: number;
  job_id: number;
  candidate_id: number;
  status: 'APPLIED' | 'SCREENING' | 'INTERVIEWING' | 'OFFERED' | 'ACCEPTED' | 'REJECTED' | 'WITHDRAWN';
  applied_date: string;
  cover_letter: string | null;
  resume_url: string | null;
  screening_score: number | null;
  screening_notes: string | null;
  interview_stage: string | null;
  rejection_reason: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  // Relations
  job?: Job;
  candidate?: Candidate;
  interviews_count?: number;
}

export interface ApplicationCreateRequest {
  job_id: number;
  candidate_id: number;
  cover_letter?: string;
  resume_url?: string;
  notes?: string;
}

export interface ApplicationUpdateRequest {
  status?: 'APPLIED' | 'SCREENING' | 'INTERVIEWING' | 'OFFERED' | 'ACCEPTED' | 'REJECTED' | 'WITHDRAWN';
  screening_score?: number;
  screening_notes?: string;
  interview_stage?: string;
  rejection_reason?: string;
  notes?: string;
}

export interface ApplicationListResponse {
  applications: Application[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

// ==================== INTERVIEWS ====================

export interface Interview {
  id: number;
  tenant_id: number;
  application_id: number;
  interviewer_id: number;
  interview_type: 'PHONE_SCREEN' | 'VIDEO' | 'ONSITE' | 'TECHNICAL' | 'BEHAVIORAL' | 'FINAL';
  scheduled_date: string;
  duration_minutes: number;
  location: string | null;
  meeting_link: string | null;
  status: 'SCHEDULED' | 'COMPLETED' | 'CANCELLED' | 'NO_SHOW' | 'RESCHEDULED';
  feedback: string | null;
  rating: number | null;
  recommendation: 'STRONG_YES' | 'YES' | 'MAYBE' | 'NO' | 'STRONG_NO' | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  // Relations
  application?: Application;
  interviewer?: PortalUserBasic;
  candidate?: Candidate;
  job?: Job;
}

export interface InterviewCreateRequest {
  application_id: number;
  interviewer_id: number;
  interview_type: 'PHONE_SCREEN' | 'VIDEO' | 'ONSITE' | 'TECHNICAL' | 'BEHAVIORAL' | 'FINAL';
  scheduled_date: string;
  duration_minutes?: number;
  location?: string;
  meeting_link?: string;
  notes?: string;
}

export interface InterviewUpdateRequest {
  application_id?: number;
  interviewer_id?: number;
  interview_type?: 'PHONE_SCREEN' | 'VIDEO' | 'ONSITE' | 'TECHNICAL' | 'BEHAVIORAL' | 'FINAL';
  scheduled_date?: string;
  duration_minutes?: number;
  location?: string;
  meeting_link?: string;
  status?: 'SCHEDULED' | 'COMPLETED' | 'CANCELLED' | 'NO_SHOW' | 'RESCHEDULED';
  feedback?: string;
  rating?: number;
  recommendation?: 'STRONG_YES' | 'YES' | 'MAYBE' | 'NO' | 'STRONG_NO';
  notes?: string;
}

export interface InterviewListResponse {
  interviews: Interview[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

// ==================== USERS ====================

export interface PortalUserBasic {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  role?: {
    name: string;
    display_name: string;
  };
}

export interface PortalUserFull extends PortalUserBasic {
  tenant_id: number;
  phone: string | null;
  role_id: number;
  role: {
    id: number;
    name: string;
    display_name: string;
    description: string | null;
    is_system_role: boolean;
    tenant_id: number | null;
  };
  is_active: boolean;
  last_login: string | null;
  is_locked: boolean;
  locked_until: string | null;
  created_at: string;
  updated_at: string;
}

export interface UserCreateRequest {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  phone?: string;
  role_id: number;
}

export interface UserUpdateRequest {
  first_name?: string;
  last_name?: string;
  phone?: string;
  role_id?: number;
  is_active?: boolean;
}

export interface UserListResponse {
  users: PortalUserFull[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface ResetPasswordRequest {
  new_password: string;
}

// ==================== ROLES ====================

export interface Role {
  id: number;
  name: string;
  display_name: string;
  description: string | null;
  is_system_role: boolean;
  tenant_id: number | null;
  created_at: string;
  updated_at: string;
  permissions?: Permission[];
}

export interface Permission {
  id: number;
  name: string;
  display_name: string;
  description: string | null;
  category: string;
}

export interface RoleListResponse {
  roles: Role[];
  total: number;
}

// ==================== DASHBOARD STATS ====================

export interface DashboardStats {
  users: {
    total: number;
    active: number;
    by_role: Record<string, number>;
  };
  jobs: {
    total: number;
    open: number;
    filled: number;
    draft: number;
  };
  candidates: {
    total: number;
    new: number;
    interviewing: number;
    offered: number;
  };
  applications: {
    total: number;
    pending: number;
    in_progress: number;
  };
  interviews: {
    scheduled: number;
    completed: number;
    upcoming_7_days: number;
  };
}

export interface TenantUsageStats {
  current: {
    users: number;
    candidates: number;
    jobs: number;
    storage_gb: number;
  };
  limits: {
    max_users: number;
    max_candidates: number;
    max_jobs: number;
    max_storage_gb: number;
  };
  subscription_plan: {
    name: string;
    display_name: string;
  };
}

// ==================== COMMON ====================

export interface ApiError {
  error: string;
  message: string;
  status: number;
  details?: Record<string, unknown>;
}

export interface PaginationParams {
  page?: number;
  per_page?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface FilterParams extends PaginationParams {
  search?: string;
  status?: string;
  [key: string]: string | number | undefined;
}
