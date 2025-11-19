/**
 * Job Detail Page
 * 
 * Displays comprehensive job posting information including:
 * - Job title, company, and location
 * - Full job description
 * - Required and preferred skills
 * - Salary range and experience requirements
 * - Match score (when accessed from candidate matches)
 * - Apply button and other actions
 */

import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowLeft,
  Building2,
  MapPin,
  DollarSign,
  Briefcase,
  Calendar,
  ExternalLink,
  Share2,
  Bookmark,
  CheckCircle2,
  Clock,
  Users,
  Globe,
} from 'lucide-react';
import { format } from 'date-fns';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { jobPostingApi } from '@/lib/jobPostingApi';
import type { JobPosting, JobMatch } from '@/types';

export function JobDetailPage() {
  const { jobId, candidateId } = useParams<{ jobId: string; candidateId?: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  
  // Get match data from navigation state if coming from matches page
  const matchData = location.state?.match as JobMatch | undefined;
  
  const jobIdNum = parseInt(jobId || '0', 10);
  const candidateIdNum = candidateId ? parseInt(candidateId, 10) : undefined;

  // Fetch job details
  const {
    data: job,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['jobPosting', jobIdNum],
    queryFn: () => jobPostingApi.getJobPosting(jobIdNum),
    enabled: !!jobIdNum,
  });

  const handleBack = () => {
    if (candidateIdNum) {
      navigate(`/candidates/${candidateIdNum}/matches`);
    } else {
      navigate('/jobs');
    }
  };

  const handleApply = () => {
    toast.success('Application submitted successfully!');
    // Implement actual apply logic
  };

  const handleViewSource = () => {
    if (job?.job_url) {
      window.open(job.job_url, '_blank', 'noopener,noreferrer');
    } else {
      toast.error('Job source URL not available');
    }
  };

  const handleShare = () => {
    navigator.clipboard.writeText(window.location.href);
    toast.success('Link copied to clipboard');
  };

  const handleSave = () => {
    toast.success('Job saved to favorites');
    // Implement actual save logic
  };

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-5xl">
        <Skeleton className="h-8 w-24 mb-6" />
        <Card>
          <CardHeader>
            <Skeleton className="h-8 w-3/4 mb-2" />
            <Skeleton className="h-6 w-1/2" />
          </CardHeader>
          <CardContent className="space-y-4">
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-64 w-full" />
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error || !job) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-5xl">
        <Button variant="ghost" onClick={handleBack} className="mb-6">
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back
        </Button>
        <Alert variant="destructive">
          <AlertDescription>
            Failed to load job details. Please try again.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

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
    <div className="container mx-auto px-4 py-8 max-w-5xl">
      {/* Header with Back Button */}
      <div className="flex items-center justify-between mb-6">
        <Button variant="ghost" onClick={handleBack}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to {candidateIdNum ? 'Matches' : 'Jobs'}
        </Button>
        <div className="flex gap-2">
          {job?.job_url && (
            <Button variant="default" size="sm" onClick={handleViewSource}>
              <Globe className="h-4 w-4 mr-2" />
              View on {job.source || 'Source'}
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={handleShare}>
            <Share2 className="h-4 w-4 mr-2" />
            Share
          </Button>
          <Button variant="outline" size="sm" onClick={handleSave}>
            <Bookmark className="h-4 w-4 mr-2" />
            Save
          </Button>
        </div>
      </div>

      {/* Match Score Card (shown when coming from candidate matches) */}
      {matchData && (
        <Card className="mb-6 border-primary bg-primary/5">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-5 w-5 text-primary" />
                  <span className="font-semibold text-lg">Match Score</span>
                </div>
                <span className="text-3xl font-bold text-primary">
                  {matchData.match_score.toFixed(0)}%
                </span>
                {matchData.match_grade && (
                  <Badge className="text-base px-3 py-1">
                    {matchData.match_grade}
                  </Badge>
                )}
              </div>
              <div className="text-sm text-muted-foreground">
                Skills Match: {matchData.skill_match_score.toFixed(0)}% • 
                Experience: {matchData.experience_match_score.toFixed(0)}%
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Main Job Details Card */}
      <Card>
        <CardHeader className="pb-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 space-y-3">
              <div>
                <h1 className="text-3xl font-bold mb-2">{job.title}</h1>
                <div className="flex items-center gap-2 text-xl text-muted-foreground">
                  <Building2 className="h-5 w-5" />
                  <span className="font-medium">{job.company}</span>
                </div>
              </div>

              {/* Quick Info */}
              <div className="flex flex-wrap gap-4 text-sm">
                <div className="flex items-center gap-1.5">
                  <MapPin className="h-4 w-4 text-muted-foreground" />
                  <span>{job.location}</span>
                  {job.is_remote && (
                    <Badge variant="secondary" className="ml-1">
                      Remote
                    </Badge>
                  )}
                </div>
                <div className="flex items-center gap-1.5">
                  <DollarSign className="h-4 w-4 text-muted-foreground" />
                  <span>{formatSalary(job.salary_min, job.salary_max)}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <Briefcase className="h-4 w-4 text-muted-foreground" />
                  <span>{formatExperience(job.experience_min, job.experience_max)}</span>
                </div>
                {job.posted_date && (
                  <div className="flex items-center gap-1.5">
                    <Calendar className="h-4 w-4 text-muted-foreground" />
                    <span>Posted {format(new Date(job.posted_date), 'MMM dd, yyyy')}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Apply Button */}
            <div className="flex flex-col gap-2">
              <Button size="lg" onClick={handleApply} className="min-w-[120px]">
                Apply Now
              </Button>
              <Badge variant="outline" className="justify-center">
                {job.status}
              </Badge>
            </div>
          </div>
        </CardHeader>

        <Separator />

        <CardContent className="pt-6 space-y-8">
          {/* Job Description */}
          <div>
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <Users className="h-5 w-5" />
              Job Description
            </h2>
            <div className="prose prose-sm max-w-none text-muted-foreground leading-relaxed whitespace-pre-wrap">
              {job.description}
            </div>
          </div>

          <Separator />

          {/* Required Skills */}
          {job.skills && job.skills.length > 0 && (
            <div>
              <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5" />
                Required Skills
              </h2>
              <div className="flex flex-wrap gap-2">
                {job.skills.map((skill, idx) => (
                  <Badge key={idx} variant="secondary" className="text-sm px-3 py-1.5">
                    {skill}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* Matched Skills (when coming from candidate matches) */}
          {matchData?.matched_skills && matchData.matched_skills.length > 0 && (
            <div>
              <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-green-600" />
                Your Matching Skills
              </h2>
              <div className="flex flex-wrap gap-2">
                {matchData.matched_skills.map((skill, idx) => (
                  <Badge
                    key={idx}
                    className="bg-green-50 text-green-700 border-green-200 text-sm px-3 py-1.5"
                  >
                    {skill}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          <Separator />

          {/* Additional Details */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h3 className="font-semibold mb-3 flex items-center gap-2">
                <Briefcase className="h-4 w-4" />
                Experience Level
              </h3>
              <p className="text-muted-foreground">
                {formatExperience(job.experience_min, job.experience_max)}
              </p>
            </div>

            <div>
              <h3 className="font-semibold mb-3 flex items-center gap-2">
                <DollarSign className="h-4 w-4" />
                Salary Range
              </h3>
              <p className="text-muted-foreground">
                {formatSalary(job.salary_min, job.salary_max)}
              </p>
            </div>

            <div>
              <h3 className="font-semibold mb-3 flex items-center gap-2">
                <MapPin className="h-4 w-4" />
                Location
              </h3>
              <p className="text-muted-foreground">
                {job.location}
                {job.is_remote && ' (Remote)'}
              </p>
            </div>

            <div>
              <h3 className="font-semibold mb-3 flex items-center gap-2">
                <Globe className="h-4 w-4" />
                Job Source
              </h3>
              <p className="text-muted-foreground">{job.source}</p>
            </div>

            {job.posted_date && (
              <div>
                <h3 className="font-semibold mb-3 flex items-center gap-2">
                  <Clock className="h-4 w-4" />
                  Posted Date
                </h3>
                <p className="text-muted-foreground">
                  {format(new Date(job.posted_date), 'MMMM dd, yyyy')}
                </p>
              </div>
            )}
          </div>

          <Separator />

          {/* Match Explanation (when coming from candidate matches) */}
          {matchData?.explanation && (
            <div className="bg-primary/5 rounded-lg p-6 border border-primary/20">
              <h3 className="font-semibold mb-3 flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-primary" />
                Why This is a Good Match
              </h3>
              <p className="text-muted-foreground leading-relaxed">
                {matchData.explanation}
              </p>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-4 pt-4">
            {job.job_url && (
              <Button size="lg" onClick={handleViewSource} className="flex-1">
                <Globe className="h-4 w-4 mr-2" />
                View on {job.source || 'Source'}
              </Button>
            )}
            <Button size="lg" onClick={handleApply} className="flex-1" variant={job.job_url ? "outline" : "default"}>
              <ExternalLink className="h-4 w-4 mr-2" />
              Apply Now
            </Button>
            <Button variant="outline" size="lg" onClick={handleSave}>
              <Bookmark className="h-4 w-4 mr-2" />
              Save for Later
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Additional Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
        {/* Company Info Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Building2 className="h-5 w-5" />
              About the Company
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">
              {job.company} is hiring for this position. Learn more about the company and their culture.
            </p>
          </CardContent>
        </Card>

        {/* Similar Jobs Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Briefcase className="h-5 w-5" />
              Similar Opportunities
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">
              Explore other positions that match your skills and experience.
            </p>
            <Button variant="link" className="px-0 mt-2">
              View similar jobs
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
