/**
 * JobMatchTable Component
 * Compact table/list view for job matches - shows more jobs at a glance
 */

import { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet';
import { Progress } from '@/components/ui/progress';
import {
  ExternalLink,
  MapPin,
  DollarSign,
  Building2,
  CheckCircle2,
  XCircle,
  Globe,
  Sparkles,
  ChevronRight,
  TrendingUp,
  Briefcase,
  Clock,
} from 'lucide-react';
import { format } from 'date-fns';
import type { JobMatch, MatchGrade } from '@/types';

interface JobMatchTableProps {
  matches: JobMatch[];
  candidateId: number;
  onViewDetails?: (jobId: number) => void;
}

const GRADE_CONFIG: Record<
  MatchGrade,
  { label: string; colorClass: string; bgClass: string }
> = {
  'A+': { label: 'A+', colorClass: 'text-emerald-700', bgClass: 'bg-emerald-100' },
  A: { label: 'A', colorClass: 'text-green-700', bgClass: 'bg-green-100' },
  B: { label: 'B', colorClass: 'text-blue-700', bgClass: 'bg-blue-100' },
  C: { label: 'C', colorClass: 'text-yellow-700', bgClass: 'bg-yellow-100' },
  D: { label: 'D', colorClass: 'text-orange-700', bgClass: 'bg-orange-100' },
  F: { label: 'F', colorClass: 'text-red-700', bgClass: 'bg-red-100' },
};

const calculateGrade = (score: number): MatchGrade => {
  if (score >= 95) return 'A+';
  if (score >= 90) return 'A';
  if (score >= 80) return 'B';
  if (score >= 70) return 'C';
  if (score >= 60) return 'D';
  return 'F';
};

const getScoreColor = (score: number) => {
  if (score >= 80) return 'text-emerald-600';
  if (score >= 60) return 'text-blue-600';
  if (score >= 40) return 'text-yellow-600';
  return 'text-orange-600';
};

const formatSalary = (min: number | null, max: number | null, range?: string | null) => {
  if (range) return range;
  if (!min && !max) return '-';
  if (min && max) return `$${(min / 1000).toFixed(0)}K - $${(max / 1000).toFixed(0)}K`;
  if (min) return `$${(min / 1000).toFixed(0)}K+`;
  return `Up to $${(max! / 1000).toFixed(0)}K`;
};

export function JobMatchTable({ matches, onViewDetails }: JobMatchTableProps) {
  const [selectedMatch, setSelectedMatch] = useState<JobMatch | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);

  const handleRowClick = (match: JobMatch) => {
    setSelectedMatch(match);
    setSheetOpen(true);
  };

  if (matches.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12 text-center">
          <TrendingUp className="h-12 w-12 text-muted-foreground mb-4" />
          <h3 className="text-lg font-semibold mb-2">No Job Matches Yet</h3>
          <p className="text-muted-foreground max-w-md">
            Jobs will appear here once they are matched to this candidate's roles
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <TooltipProvider>
      <Card>
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/50">
              <TableHead className="w-[60px]">Score</TableHead>
              <TableHead>Job Title</TableHead>
              <TableHead>Company</TableHead>
              <TableHead>Location</TableHead>
              <TableHead>Salary</TableHead>
              <TableHead className="w-[100px]">Skills Match</TableHead>
              <TableHead className="w-[80px]">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {matches.map((match) => {
              const job = match.job || match.job_posting;
              if (!job) return null;
              
              const grade = (match.match_grade as MatchGrade) || calculateGrade(match.match_score);
              const gradeConfig = GRADE_CONFIG[grade] || GRADE_CONFIG['C'];
              const matchedCount = match.matched_skills?.length || 0;
              const totalSkills = matchedCount + (match.missing_skills?.length || 0);

              return (
                <TableRow
                  key={match.id}
                  className="cursor-pointer hover:bg-muted/50 transition-colors"
                  onClick={() => handleRowClick(match)}
                >
                  {/* Score & Grade */}
                  <TableCell>
                    <div className="flex flex-col items-center gap-1">
                      <Badge className={`${gradeConfig.bgClass} ${gradeConfig.colorClass} font-bold px-2`}>
                        {gradeConfig.label}
                      </Badge>
                      <span className={`text-sm font-semibold ${getScoreColor(match.match_score)}`}>
                        {Math.round(match.match_score)}%
                      </span>
                    </div>
                  </TableCell>

                  {/* Job Title */}
                  <TableCell>
                    <div className="flex flex-col">
                      <span className="font-medium text-slate-900 line-clamp-1">
                        {job.title}
                      </span>
                      {job.job_type && (
                        <span className="text-xs text-muted-foreground">
                          {job.job_type}
                        </span>
                      )}
                    </div>
                  </TableCell>

                  {/* Company */}
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <Building2 className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                      <span className="text-sm line-clamp-1">{job.company}</span>
                    </div>
                  </TableCell>

                  {/* Location */}
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <MapPin className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                      <span className="text-sm line-clamp-1">{job.location || 'N/A'}</span>
                      {job.is_remote && (
                        <Tooltip>
                          <TooltipTrigger>
                            <Globe className="h-3.5 w-3.5 text-blue-500" />
                          </TooltipTrigger>
                          <TooltipContent>Remote Available</TooltipContent>
                        </Tooltip>
                      )}
                    </div>
                  </TableCell>

                  {/* Salary */}
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <DollarSign className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                      <span className="text-sm">
                        {formatSalary(job.salary_min, job.salary_max, job.salary_range)}
                      </span>
                    </div>
                  </TableCell>

                  {/* Skills Match */}
                  <TableCell>
                    <Tooltip>
                      <TooltipTrigger className="w-full">
                        <div className="flex flex-col gap-1">
                          <div className="flex items-center justify-between text-xs">
                            <span className="text-green-600 font-medium">{matchedCount}</span>
                            <span className="text-muted-foreground">/{totalSkills}</span>
                          </div>
                          <Progress 
                            value={totalSkills > 0 ? (matchedCount / totalSkills) * 100 : 0} 
                            className="h-1.5"
                          />
                        </div>
                      </TooltipTrigger>
                      <TooltipContent side="left" className="max-w-xs">
                        <div className="space-y-2">
                          {matchedCount > 0 && (
                            <div>
                              <p className="text-xs font-medium text-green-600 mb-1">
                                Matched ({matchedCount}):
                              </p>
                              <p className="text-xs">
                                {match.matched_skills?.slice(0, 5).join(', ')}
                                {matchedCount > 5 && ` +${matchedCount - 5} more`}
                              </p>
                            </div>
                          )}
                          {match.missing_skills && match.missing_skills.length > 0 && (
                            <div>
                              <p className="text-xs font-medium text-orange-600 mb-1">
                                Missing ({match.missing_skills.length}):
                              </p>
                              <p className="text-xs">
                                {match.missing_skills.slice(0, 5).join(', ')}
                                {match.missing_skills.length > 5 && ` +${match.missing_skills.length - 5} more`}
                              </p>
                            </div>
                          )}
                        </div>
                      </TooltipContent>
                    </Tooltip>
                  </TableCell>

                  {/* Actions */}
                  <TableCell>
                    <div className="flex items-center gap-1">
                      {job.job_url && (
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8"
                              onClick={(e) => {
                                e.stopPropagation();
                                if (job.job_url) window.open(job.job_url, '_blank');
                              }}
                            >
                              <ExternalLink className="h-4 w-4" />
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent>Open Job Posting</TooltipContent>
                        </Tooltip>
                      )}
                      <ChevronRight className="h-4 w-4 text-muted-foreground" />
                    </div>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </Card>

      {/* Job Details Sheet */}
      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent className="w-[500px] sm:w-[600px] overflow-y-auto">
          {selectedMatch && (() => {
            const job = selectedMatch.job || selectedMatch.job_posting;
            if (!job) return null;
            
            const grade = (selectedMatch.match_grade as MatchGrade) || calculateGrade(selectedMatch.match_score);
            const gradeConfig = GRADE_CONFIG[grade] || GRADE_CONFIG['C'];

            return (
              <>
                <SheetHeader className="space-y-4 pb-4 border-b">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <SheetTitle className="text-xl">{job.title}</SheetTitle>
                      <SheetDescription className="text-base mt-1">
                        {job.company}
                      </SheetDescription>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      <Badge className={`${gradeConfig.bgClass} ${gradeConfig.colorClass} font-bold text-lg px-3 py-1`}>
                        {gradeConfig.label}
                      </Badge>
                      <span className="text-2xl font-bold">{Math.round(selectedMatch.match_score)}%</span>
                    </div>
                  </div>
                </SheetHeader>

                <div className="py-6 space-y-6">
                  {/* Job Info */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="flex items-center gap-2 text-sm">
                      <MapPin className="h-4 w-4 text-muted-foreground" />
                      <span>{job.location || 'Not specified'}</span>
                      {job.is_remote && (
                        <Badge variant="secondary" className="text-xs">Remote</Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-2 text-sm">
                      <DollarSign className="h-4 w-4 text-muted-foreground" />
                      <span>{formatSalary(job.salary_min, job.salary_max, job.salary_range)}</span>
                    </div>
                    {job.job_type && (
                      <div className="flex items-center gap-2 text-sm">
                        <Briefcase className="h-4 w-4 text-muted-foreground" />
                        <span>{job.job_type}</span>
                      </div>
                    )}
                    {job.platform && (
                      <div className="flex items-center gap-2 text-sm">
                        <Globe className="h-4 w-4 text-muted-foreground" />
                        <span>{job.platform}</span>
                      </div>
                    )}
                  </div>

                  {/* Score Breakdown */}
                  <div className="space-y-3">
                    <h4 className="font-semibold flex items-center gap-2">
                      <TrendingUp className="h-4 w-4" />
                      Score Breakdown
                    </h4>
                    <div className="grid grid-cols-2 gap-3">
                      {[
                        { label: 'Skills', value: selectedMatch.skill_match_score },
                        { label: 'Experience', value: selectedMatch.experience_match_score },
                        { label: 'Location', value: selectedMatch.location_match_score },
                        { label: 'Salary', value: selectedMatch.salary_match_score },
                        { label: 'Semantic', value: selectedMatch.semantic_similarity },
                      ].map((score) => (
                        <div key={score.label} className="flex items-center justify-between bg-muted/50 rounded-lg px-3 py-2">
                          <span className="text-sm text-muted-foreground">{score.label}</span>
                          <span className={`font-semibold ${getScoreColor(score.value ?? 0)}`}>
                            {Math.round(score.value ?? 0)}%
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Matched Skills */}
                  {selectedMatch.matched_skills && selectedMatch.matched_skills.length > 0 && (
                    <div className="space-y-2">
                      <h4 className="font-semibold flex items-center gap-2 text-green-700">
                        <CheckCircle2 className="h-4 w-4" />
                        Matched Skills ({selectedMatch.matched_skills.length})
                      </h4>
                      <div className="flex flex-wrap gap-1.5">
                        {selectedMatch.matched_skills.map((skill, idx) => (
                          <Badge key={idx} variant="secondary" className="bg-green-50 text-green-700">
                            {skill}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Missing Skills */}
                  {selectedMatch.missing_skills && selectedMatch.missing_skills.length > 0 && (
                    <div className="space-y-2">
                      <h4 className="font-semibold flex items-center gap-2 text-orange-700">
                        <XCircle className="h-4 w-4" />
                        Skills to Develop ({selectedMatch.missing_skills.length})
                      </h4>
                      <div className="flex flex-wrap gap-1.5">
                        {selectedMatch.missing_skills.map((skill, idx) => (
                          <Badge key={idx} variant="outline" className="text-orange-600 border-orange-300">
                            {skill}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Description */}
                  {job.description && (
                    <div className="space-y-2">
                      <h4 className="font-semibold">Description</h4>
                      <p className="text-sm text-muted-foreground whitespace-pre-line">
                        {job.description}
                      </p>
                    </div>
                  )}

                  {/* Posted Date */}
                  {job.posted_date && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground pt-2 border-t">
                      <Clock className="h-4 w-4" />
                      <span>Posted {format(new Date(job.posted_date), 'MMM dd, yyyy')}</span>
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="flex gap-3 pt-4 border-t">
                  {job.job_url && (
                    <Button
                      variant="outline"
                      className="flex-1"
                      onClick={() => job.job_url && window.open(job.job_url, '_blank')}
                    >
                      <ExternalLink className="h-4 w-4 mr-2" />
                      View Job Posting
                    </Button>
                  )}
                  {onViewDetails && (
                    <Button
                      className="flex-1 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700"
                      onClick={() => {
                        setSheetOpen(false);
                        onViewDetails(job.id);
                      }}
                    >
                      <Sparkles className="h-4 w-4 mr-2" />
                      Tailor Resume
                    </Button>
                  )}
                </div>
              </>
            );
          })()}
        </SheetContent>
      </Sheet>
    </TooltipProvider>
  );
}
