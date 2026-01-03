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
  // Populated sourced_by info (from API response)
  sourced_by?: {
    id: number;
    first_name: string;
    last_name: string;
    email: string;
  } | null;
  additional_source_users?: Array<{
    user_id: number;
    email_id: string;
    received_at: string;
  }>;
}

export interface JobMatch {
  id: number;
  candidate_id: number;
  job_posting_id: number;
  match_score: number;
  match_grade?: string;
  // Unified Scoring Components (weights: Skills 45%, Experience 20%, Semantic 35%)
  // Note: Keyword scoring was removed to speed up job imports
  skill_match_score: number;
  keyword_match_score?: number | null; // DEPRECATED - no longer used
  experience_match_score: number;
  semantic_similarity: number;
  // Skill matching details
  matched_skills: string[];
  missing_skills: string[];
  // Keyword matching details (DEPRECATED - no longer used)
  matched_keywords?: string[] | null;
  missing_keywords?: string[] | null;
  // AI Compatibility (on-demand, cached 24h)
  ai_compatibility_score?: number;
  ai_compatibility_details?: {
    strengths?: string[];
    gaps?: string[];
    recommendations?: string[];
    experience_analysis?: string;
    culture_fit_indicators?: string[];
  };
  ai_scored_at?: string;
  // Legacy/optional fields
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
  // Filter options
  available_platforms?: string[];
  available_sources?: string[];  // ['scraped', 'email']
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
  source?: 'all' | 'email' | 'scraped';  // Filter by job source
}

export type MatchGrade = 'A+' | 'A' | 'B+' | 'B' | 'C+' | 'C';

export interface GradeBadgeConfig {
  label: MatchGrade;
  colorClass: string;
  bgClass: string;
  description: string;
}
