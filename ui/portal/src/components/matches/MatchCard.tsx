/**
 * MatchCard Component
 * Displays a job match with score breakdown, grade badge, and action buttons
 */

import { Card, CardContent, CardFooter, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  ExternalLink,
  MapPin,
  DollarSign,
  Briefcase,
  TrendingUp,
  CheckCircle2,
  XCircle,
  Clock,
  Sparkles,
  Mail,
} from 'lucide-react';
import { format } from 'date-fns';
import type { JobMatch, MatchGrade } from '@/types';

interface MatchCardProps {
  match: JobMatch;
  candidateId?: number;
  onViewDetails?: (jobId: number) => void;
  onApply?: (jobId: number) => void;
  onTailorResume?: (matchId: number) => void;
  showActions?: boolean;
  showTailorButton?: boolean;
}

const GRADE_CONFIG: Record<
  MatchGrade,
  { label: string; colorClass: string; bgClass: string; description: string }
> = {
  'A+': {
    label: 'A+',
    colorClass: 'text-green-700',
    bgClass: 'bg-green-100 border-green-300',
    description: 'Excellent Match',
  },
  A: {
    label: 'A',
    colorClass: 'text-green-600',
    bgClass: 'bg-green-50 border-green-200',
    description: 'Great Match',
  },
  B: {
    label: 'B',
    colorClass: 'text-blue-600',
    bgClass: 'bg-blue-50 border-blue-200',
    description: 'Good Match',
  },
  C: {
    label: 'C',
    colorClass: 'text-yellow-600',
    bgClass: 'bg-yellow-50 border-yellow-200',
    description: 'Fair Match',
  },
  D: {
    label: 'D',
    colorClass: 'text-orange-600',
    bgClass: 'bg-orange-50 border-orange-200',
    description: 'Below Average',
  },
  F: {
    label: 'F',
    colorClass: 'text-red-600',
    bgClass: 'bg-red-50 border-red-200',
    description: 'Poor Match',
  },
};

const ScoreBar = ({ label, value, icon: Icon }: { label: string; value: number; icon: React.ComponentType<{ className?: string }> }) => {
  const getColorClass = (score: number) => {
    if (score >= 80) return 'bg-green-500';
    if (score >= 60) return 'bg-blue-500';
    if (score >= 40) return 'bg-yellow-500';
    return 'bg-orange-500';
  };

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center gap-2">
          <Icon className="h-3.5 w-3.5 text-muted-foreground" />
          <span className="text-muted-foreground">{label}</span>
        </div>
        <span className="font-medium">{Math.round(value ?? 0)}%</span>
      </div>
      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${getColorClass(value)}`}
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  );
};

export function MatchCard({ 
  match, 
  candidateId,
  onViewDetails, 
  onApply, 
  showActions = true,
  showTailorButton = true,
}: MatchCardProps) {
  const job = match.job || match.job_posting;
  if (!job) return null;

  // Calculate grade from match_score if match_grade not provided
  const calculateGrade = (score: number): MatchGrade => {
    if (score >= 95) return 'A+';
    if (score >= 90) return 'A';
    if (score >= 80) return 'B';
    if (score >= 70) return 'C';
    if (score >= 60) return 'D';
    return 'F';
  };

  const grade = (match.match_grade as MatchGrade) || calculateGrade(match.match_score);
  const gradeConfig = GRADE_CONFIG[grade] || GRADE_CONFIG['C'];

  const formatSalary = (min: number | null, max: number | null) => {
    if (!min && !max) return 'Not specified';
    if (min && max) return `$${(min / 1000).toFixed(0)}K - $${(max / 1000).toFixed(0)}K`;
    if (min) return `$${(min / 1000).toFixed(0)}K+`;
    return `Up to $${(max! / 1000).toFixed(0)}K`;
  };

  const formatExperience = (min: number | null, max: number | null) => {
    if (!min && !max) return 'Any level';
    if (min && max) return `${min}-${max} years`;
    if (min) return `${min}+ years`;
    return `Up to ${max} years`;
  };

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 space-y-1">
            <div className="flex items-center gap-2">
              <h3 className="text-lg font-semibold leading-tight">{job.title}</h3>
              {job.is_email_sourced && (
                <Badge variant="outline" className="bg-purple-50 text-purple-700 border-purple-200">
                  <Mail className="h-3 w-3 mr-1" />
                  Email
                </Badge>
              )}
            </div>
            <p className="text-sm text-muted-foreground font-medium">{job.company}</p>
          </div>
          <div className="flex flex-col items-end gap-2">
            <Badge
              className={`${gradeConfig.bgClass} ${gradeConfig.colorClass} border font-bold text-base px-3 py-1`}
            >
              {gradeConfig.label}
            </Badge>
            <span className="text-2xl font-bold">{Math.round(match.match_score ?? 0)}%</span>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Job Details */}
        <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
          <div className="flex items-center gap-1.5">
            <MapPin className="h-4 w-4" />
            <span>{job.location}</span>
            {job.is_remote && (
              <Badge variant="secondary" className="ml-1">
                Remote
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-1.5">
            <DollarSign className="h-4 w-4" />
            <span>{formatSalary(job.salary_min, job.salary_max)}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Briefcase className="h-4 w-4" />
            <span>{formatExperience(job.experience_min, job.experience_max)}</span>
          </div>
        </div>

        {/* Match Explanation */}
        {(match.explanation || match.recommendation_reason || (match.match_reasons && match.match_reasons[0])) && (
          <p className="text-sm text-muted-foreground leading-relaxed">
            {match.explanation || match.recommendation_reason || (match.match_reasons && match.match_reasons[0])}
          </p>
        )}

        {/* Score Breakdown */}
        <div className="space-y-2.5 pt-2">
          <ScoreBar label="Skills" value={match.skill_match_score} icon={TrendingUp} />
          <ScoreBar label="Experience" value={match.experience_match_score} icon={Briefcase} />
          <ScoreBar label="Location" value={match.location_match_score} icon={MapPin} />
          <ScoreBar label="Salary" value={match.salary_match_score} icon={DollarSign} />
          <ScoreBar label="Semantic" value={match.semantic_similarity} icon={CheckCircle2} />
        </div>

        {/* Skills Match */}
        {match.matched_skills && match.matched_skills.length > 0 && (
          <div className="pt-2">
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              <span className="text-sm font-medium">
                Matched Skills ({match.matched_skills.length})
              </span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {match.matched_skills.slice(0, 8).map((skill, idx) => (
                <Badge key={idx} variant="secondary" className="bg-green-50 text-green-700">
                  {skill}
                </Badge>
              ))}
              {match.matched_skills.length > 8 && (
                <Badge variant="outline">+{match.matched_skills.length - 8} more</Badge>
              )}
            </div>
          </div>
        )}

        {/* Missing Skills */}
        {match.missing_skills && match.missing_skills.length > 0 && (
          <div className="pt-2">
            <div className="flex items-center gap-2 mb-2">
              <XCircle className="h-4 w-4 text-orange-600" />
              <span className="text-sm font-medium">
                Skills to Develop ({match.missing_skills.length})
              </span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {match.missing_skills.slice(0, 6).map((skill, idx) => (
                <Badge key={idx} variant="outline" className="text-orange-600">
                  {skill}
                </Badge>
              ))}
              {match.missing_skills.length > 6 && (
                <Badge variant="outline">+{match.missing_skills.length - 6} more</Badge>
              )}
            </div>
          </div>
        )}

        {/* Match Date */}
        {(match.matched_at || match.match_date || match.created_at) && (
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground pt-2">
            <Clock className="h-3.5 w-3.5" />
            <span>Matched {format(new Date(match.matched_at || match.match_date || match.created_at), 'MMM dd, yyyy')}</span>
          </div>
        )}
      </CardContent>

      {showActions && (
        <CardFooter className="flex gap-2 pt-4">
          {onViewDetails && (
            <Button
              variant="outline"
              className="flex-1"
              onClick={() => onViewDetails(job.id)}
            >
              <ExternalLink className="h-4 w-4 mr-2" />
              View Details
            </Button>
          )}
          {showTailorButton && candidateId && onViewDetails && (
            <Button
              variant="outline"
              className="flex-1 bg-gradient-to-r from-violet-50 to-indigo-50 hover:from-violet-100 hover:to-indigo-100 border-violet-200"
              onClick={() => onViewDetails(job.id)}
            >
              <Sparkles className="h-4 w-4 mr-2 text-violet-600" />
              <span className="text-violet-700">Tailor Resume</span>
            </Button>
          )}
          {onApply && (
            <Button className="flex-1" onClick={() => onApply(job.id)}>
              Apply Now
            </Button>
          )}
        </CardFooter>
      )}
    </Card>
  );
}
