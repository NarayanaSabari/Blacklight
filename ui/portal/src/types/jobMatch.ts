/**
 * Job Match Types
 * Types for AI-powered job matching system
 */

export interface JobPosting {
  id: number;
  title: string;
  company: string;
  location: string;
  description: string;
  skills: string[];
  experience_min: number | null;
  experience_max: number | null;
  salary_min: number | null;
  salary_max: number | null;
  is_remote: boolean;
  status: string;
  source: string;
  posted_date: string | null;
  created_at: string;
  updated_at: string;
  // Additional fields
  job_type?: string | null;
  salary_range?: string | null;
  experience_required?: string | null;
  requirements?: string | null;
  snippet?: string | null;
  job_url?: string | null;
  platform?: string | null;
  // Email source fields
  is_email_sourced?: boolean;
  source_tenant_id?: number | null;
  sourced_by_user_id?: number | null;
  source_email_id?: string | null;
  source_email_subject?: string | null;
  source_email_sender?: string | null;
  source_email_date?: string | null;
}

export interface JobMatch {
  id: number;
  candidate_id: number;
  job_posting_id: number;
  match_score: number;
  match_grade?: string;
  skill_match_score: number;
  experience_match_score: number;
  location_match_score: number;
  salary_match_score: number;
  semantic_similarity: number;
  matched_skills: string[];
  missing_skills: string[];
  explanation?: string;
  match_reasons?: string[];
  recommendation_reason?: string;
  is_recommended?: boolean;
  status?: string;
  matched_at?: string;
  viewed_at?: string | null;
  applied_at?: string | null;
  rejected_at?: string | null;
  rejection_reason?: string | null;
  notes?: string | null;
  match_date?: string;
  created_at: string;
  updated_at: string;
  job_posting?: JobPosting;  // Legacy field name
  job?: JobPosting;  // Current API response uses 'job' instead of 'job_posting'
}

export interface JobMatchListResponse {
  candidate_id: number;
  total_matches: number;
  matches: JobMatch[];
  // Pagination fields
  page?: number;
  per_page?: number;
  total_pages?: number;
  pages?: number;  // Legacy alias for total_pages
  // Platform filter
  available_platforms?: string[];
}

export interface JobMatchStats {
  candidate_id: number;
  total: number;
  by_grade: {
    [grade: string]: number;
  };
  by_status: {
    [status: string]: number;
  };
  avg_score: number;
  top_score: number;
  last_updated: string | null;
}

export interface GenerateMatchesRequest {
  min_score?: number;
  limit?: number;
}

export interface GenerateMatchesResponse {
  candidate_id: number;
  matches_generated: number;
  average_score: number;
  top_match_score: number;
  message: string;
}

export interface JobMatchFilters {
  min_score?: number;
  max_score?: number;
  grade?: string;
  grades?: string[];
  page?: number;
  per_page?: number;
  sort_by?: 'match_score' | 'match_date';
  sort_order?: 'asc' | 'desc';
  platforms?: string[];
}

export type MatchGrade = 'A+' | 'A' | 'B' | 'C' | 'D' | 'F';

export interface GradeBadgeConfig {
  label: MatchGrade;
  colorClass: string;
  bgClass: string;
  description: string;
}
