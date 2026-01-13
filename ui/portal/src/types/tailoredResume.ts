/**
 * Types for Resume Tailor feature
 * Used for tailoring resumes to specific job postings
 */

export type TailorStatus = 'pending' | 'processing' | 'completed' | 'failed';

export type ExportFormat = 'pdf' | 'docx' | 'markdown';

export type ResumeTemplate = 'modern' | 'classic';

export interface TemplateInfo {
  id: ResumeTemplate;
  name: string;
  description: string;
  is_default: boolean;
}

export interface TemplateListResponse {
  templates: TemplateInfo[];
  default_template: ResumeTemplate;
}

export interface TailoredResume {
  id: number;
  tailor_id: string;  // UUID for API calls
  candidate_id: number;
  job_posting_id: number | null;

  // Content
  original_resume_content: string;
  tailored_resume_content: string;

  // Scores (as percentages 0-100)
  original_match_score: number;
  tailored_match_score: number;
  score_improvement: number;

  // Skills analysis
  matched_skills: string[];
  missing_skills: string[];
  added_skills: string[];

  // Detailed improvements
  improvements: TailorImprovement[];
  skill_comparison: SkillComparison;

  // Processing status
  status: TailorStatus;
  processing_step: string | null;
  processing_progress: number;
  error_message: string | null;
  
  // Job info
  job_title?: string;
  job_company?: string;

  // Timestamps
  created_at: string;
  updated_at: string;
  completed_at?: string;
}

export interface TailorImprovement {
  section: string;
  type: 'added' | 'enhanced' | 'reworded' | 'removed';
  original?: string;
  improved: string;
  reason: string;
}

export interface SkillComparison {
  kept: string[];
  added: string[];
  enhanced: string[];
  removed: string[];
}

/**
 * Request DTOs
 */
export interface TailorResumeRequest {
  candidate_id: number;
  job_posting_id: number;
}

export interface TailorFromMatchRequest {
  candidate_id: number;
  job_match_id: number;
}

export interface ExportResumeRequest {
  format: ExportFormat;
  template?: ResumeTemplate;
}

/**
 * Response DTOs
 */
export interface TailorResumeResponse {
  message: string;
  tailored_resume: TailoredResume;
}

export interface TailoredResumeListResponse {
  tailored_resumes: TailoredResume[];
  total: number;
}

export interface TailorStatsResponse {
  total_tailored: number;
  avg_score_improvement: number;
  best_improvement: number;
  by_status: Record<TailorStatus, number>;
  recent_tailors: TailoredResume[];
}

export interface CompareResponse {
  original: {
    content: string;
    score: number;
    skills: string[];
  };
  tailored: {
    content: string;
    score: number;
    skills: string[];
  };
  improvements: TailorImprovement[];
  skill_comparison: SkillComparison;
  score_improvement: number;
}

/**
 * UI state interfaces
 */
export interface TailorDialogState {
  isOpen: boolean;
  candidateId: number | null;
  jobPostingId: number | null;
  jobMatchId: number | null;
  jobTitle: string;
  company: string;
}

export interface TailorProgressState {
  status: TailorStatus;
  step: string;
  progress: number;
  message: string;
}
