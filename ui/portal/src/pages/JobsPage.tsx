/**
 * Jobs Page
 * View candidates and their matched jobs with a clean, professional layout
 */

import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
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
  Briefcase, 
  Search, 
  User,
  Target,
  AlertCircle,
  ChevronRight,
  ChevronLeft,
  ChevronsLeft,
  ChevronsRight,
  MapPin,
  DollarSign,
  Building2,
  Globe,
  ExternalLink,
  CheckCircle2,
  XCircle,
  TrendingUp,
  Clock,
  Sparkles,
} from 'lucide-react';
import { candidateApi } from '@/lib/candidateApi';
import { jobMatchApi } from '@/lib/jobMatchApi';
import { format } from 'date-fns';
import type { JobMatch, MatchGrade } from '@/types';

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

const GRADE_CONFIG: Record<MatchGrade, { label: string; colorClass: string; bgClass: string }> = {
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

const formatSalary = (min?: number | null, max?: number | null, range?: string | null) => {
  if (range) return range;
  if (!min && !max) return '-';
  if (min && max) return `$${(min / 1000).toFixed(0)}K - $${(max / 1000).toFixed(0)}K`;
  if (min) return `$${(min / 1000).toFixed(0)}K+`;
  if (max) return `Up to $${(max / 1000).toFixed(0)}K`;
  return '-';
};

export function JobsPage() {
  const navigate = useNavigate();
  const [selectedCandidateId, setSelectedCandidateId] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [selectedMatch, setSelectedMatch] = useState<JobMatch | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);

  // Reset page when candidate changes
  useEffect(() => {
    setCurrentPage(1);
  }, [selectedCandidateId]);

  // Fetch all candidates
  const { data: candidatesData, isLoading: loadingCandidates } = useQuery({
    queryKey: ['candidates', { page: 1, per_page: 100 }],
    queryFn: () => candidateApi.listCandidates({ page: 1, per_page: 100 }),
    staleTime: 0,
  });

  const candidates = candidatesData?.candidates || [];
  
  // Filter candidates by search
  const filteredCandidates = candidates.filter((candidate) => {
    const searchLower = searchQuery.toLowerCase();
    const fullName = `${candidate.first_name} ${candidate.last_name}`.toLowerCase();
    const email = candidate.email?.toLowerCase() || '';
    return fullName.includes(searchLower) || email.includes(searchLower);
  });

  // Fetch matches for selected candidate with pagination
  const { 
    data: matchesData, 
    isLoading: loadingMatches,
    error: matchesError 
  } = useQuery({
    queryKey: ['jobMatches', selectedCandidateId, currentPage, pageSize],
    queryFn: async () => {
      if (!selectedCandidateId) return null;
      return jobMatchApi.getCandidateMatches(selectedCandidateId, { 
        page: currentPage,
        per_page: pageSize,
        sort_by: 'match_score',
        sort_order: 'desc'
      });
    },
    enabled: !!selectedCandidateId,
    staleTime: 0,
  });

  const matches = matchesData?.matches || [];
  const totalMatches = matchesData?.total_matches || 0;
  const totalPages = matchesData?.total_pages || 0;
  const selectedCandidate = candidates.find((c) => c.id === selectedCandidateId);

  const handleRowClick = (match: JobMatch) => {
    setSelectedMatch(match);
    setSheetOpen(true);
  };

  return (
    <TooltipProvider>
      <div className="flex flex-col h-[calc(100vh-120px)]">
        {/* Page Header */}
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Job Matches</h1>
            <p className="text-slate-600 text-sm">View AI-powered job recommendations for candidates</p>
          </div>
        </div>

        {/* Main Layout */}
        <div className="flex gap-4 flex-1 min-h-0">
          {/* Left Sidebar: Candidates */}
          <div className="w-72 flex-shrink-0">
            <Card className="h-full flex flex-col">
              <CardHeader className="pb-3 flex-shrink-0">
                <CardTitle className="text-base flex items-center gap-2">
                  <User className="h-4 w-4" />
                  Candidates ({filteredCandidates.length})
                </CardTitle>
                <div className="relative mt-2">
                  <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-8 h-9"
                  />
                </div>
              </CardHeader>
              <CardContent className="p-0 flex-1 overflow-hidden">
                <ScrollArea className="h-full">
                  {loadingCandidates ? (
                    <div className="space-y-2 p-3">
                      {[1, 2, 3, 4, 5].map((i) => (
                        <Skeleton key={i} className="h-14 w-full" />
                      ))}
                    </div>
                  ) : filteredCandidates.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-8 text-center px-4">
                      <User className="h-10 w-10 text-muted-foreground mb-2" />
                      <p className="text-sm text-muted-foreground">
                        {searchQuery ? 'No candidates found' : 'No candidates available'}
                      </p>
                    </div>
                  ) : (
                    <div className="p-2 space-y-1">
                      {filteredCandidates.map((candidate) => (
                        <button
                          key={candidate.id}
                          onClick={() => setSelectedCandidateId(candidate.id)}
                          className={`w-full text-left px-3 py-2.5 rounded-md transition-colors ${
                            selectedCandidateId === candidate.id
                              ? 'bg-primary text-primary-foreground'
                              : 'hover:bg-muted'
                          }`}
                        >
                          <p className="font-medium text-sm truncate">
                            {candidate.first_name} {candidate.last_name}
                          </p>
                          <p className={`text-xs truncate ${
                            selectedCandidateId === candidate.id 
                              ? 'text-primary-foreground/70' 
                              : 'text-muted-foreground'
                          }`}>
                            {candidate.email}
                          </p>
                        </button>
                      ))}
                    </div>
                  )}
                </ScrollArea>
              </CardContent>
            </Card>
          </div>

          {/* Right Panel: Jobs Table */}
          <div className="flex-1 min-w-0 flex flex-col">
            {!selectedCandidateId ? (
              <Card className="flex-1 flex items-center justify-center">
                <CardContent className="text-center">
                  <Target className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
                  <h3 className="text-lg font-semibold mb-2">Select a Candidate</h3>
                  <p className="text-muted-foreground max-w-sm">
                    Choose a candidate from the list to view their job matches
                  </p>
                </CardContent>
              </Card>
            ) : (
              <Card className="flex-1 flex flex-col overflow-hidden">
                {/* Header with candidate info and pagination */}
                <CardHeader className="pb-3 flex-shrink-0 border-b">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Briefcase className="h-5 w-5 text-primary" />
                      <div>
                        <CardTitle className="text-lg">
                          {selectedCandidate?.first_name} {selectedCandidate?.last_name}
                        </CardTitle>
                        <p className="text-sm text-muted-foreground">{selectedCandidate?.email}</p>
                      </div>
                    </div>
                    <Badge variant="secondary" className="text-sm">
                      {totalMatches} job{totalMatches !== 1 ? 's' : ''} matched
                    </Badge>
                  </div>

                  {/* Pagination Controls */}
                  {totalMatches > 0 && (
                    <div className="flex items-center justify-between mt-4 pt-3 border-t">
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <span>Show</span>
                        <Select value={pageSize.toString()} onValueChange={(v) => { setPageSize(parseInt(v)); setCurrentPage(1); }}>
                          <SelectTrigger className="w-[70px] h-8">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {PAGE_SIZE_OPTIONS.map((size) => (
                              <SelectItem key={size} value={size.toString()}>{size}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <span className="text-muted-foreground">
                          • {((currentPage - 1) * pageSize) + 1}-{Math.min(currentPage * pageSize, totalMatches)} of {totalMatches}
                        </span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Button variant="outline" size="icon" className="h-8 w-8" onClick={() => setCurrentPage(1)} disabled={currentPage === 1}>
                          <ChevronsLeft className="h-4 w-4" />
                        </Button>
                        <Button variant="outline" size="icon" className="h-8 w-8" onClick={() => setCurrentPage(p => p - 1)} disabled={currentPage === 1}>
                          <ChevronLeft className="h-4 w-4" />
                        </Button>
                        <span className="px-2 text-sm">Page {currentPage} of {totalPages || 1}</span>
                        <Button variant="outline" size="icon" className="h-8 w-8" onClick={() => setCurrentPage(p => p + 1)} disabled={currentPage >= totalPages}>
                          <ChevronRight className="h-4 w-4" />
                        </Button>
                        <Button variant="outline" size="icon" className="h-8 w-8" onClick={() => setCurrentPage(totalPages)} disabled={currentPage >= totalPages}>
                          <ChevronsRight className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  )}
                </CardHeader>

                {/* Table Content */}
                <div className="flex-1 overflow-auto">
                  {loadingMatches ? (
                    <div className="p-4 space-y-3">
                      {[1, 2, 3, 4, 5].map((i) => (
                        <Skeleton key={i} className="h-12 w-full" />
                      ))}
                    </div>
                  ) : matchesError ? (
                    <div className="p-4">
                      <Alert variant="destructive">
                        <AlertCircle className="h-4 w-4" />
                        <AlertDescription>Failed to load job matches. Please try again.</AlertDescription>
                      </Alert>
                    </div>
                  ) : matches.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-center p-8">
                      <Target className="h-12 w-12 text-muted-foreground mb-3" />
                      <h3 className="text-lg font-medium mb-1">No Job Matches</h3>
                      <p className="text-muted-foreground text-sm max-w-sm">
                        Jobs will appear here once they are matched to this candidate's roles
                      </p>
                    </div>
                  ) : (
                    <Table>
                      <TableHeader className="sticky top-0 bg-background z-10">
                        <TableRow className="bg-muted/50 hover:bg-muted/50">
                          <TableHead className="w-16 text-center">Score</TableHead>
                          <TableHead className="min-w-[200px]">Job Title</TableHead>
                          <TableHead className="min-w-[150px]">Company</TableHead>
                          <TableHead className="min-w-[140px]">Location</TableHead>
                          <TableHead className="min-w-[120px]">Salary</TableHead>
                          <TableHead className="w-24 text-center">Skills</TableHead>
                          <TableHead className="w-16"></TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {matches.map((match) => {
                          const job = match.job || match.job_posting;
                          if (!job) return null;
                          
                          const grade = (match.match_grade as MatchGrade) || calculateGrade(match.match_score);
                          const gradeConfig = GRADE_CONFIG[grade] || GRADE_CONFIG['C'];
                          const matchedCount = match.matched_skills?.length || 0;
                          const missingCount = match.missing_skills?.length || 0;
                          const totalSkills = matchedCount + missingCount;

                          return (
                            <TableRow
                              key={match.id}
                              className="cursor-pointer hover:bg-muted/50"
                              onClick={() => handleRowClick(match)}
                            >
                              <TableCell className="text-center">
                                <div className="flex flex-col items-center gap-0.5">
                                  <Badge className={`${gradeConfig.bgClass} ${gradeConfig.colorClass} font-bold text-xs px-1.5`}>
                                    {gradeConfig.label}
                                  </Badge>
                                  <span className={`text-xs font-semibold ${getScoreColor(match.match_score)}`}>
                                    {Math.round(match.match_score)}%
                                  </span>
                                </div>
                              </TableCell>
                              <TableCell>
                                <div className="flex flex-col gap-0.5">
                                  <span className="font-medium text-sm line-clamp-1">{job.title}</span>
                                  {job.job_type && (
                                    <span className="text-xs text-muted-foreground">{job.job_type}</span>
                                  )}
                                </div>
                              </TableCell>
                              <TableCell>
                                <div className="flex items-center gap-1.5">
                                  <Building2 className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
                                  <span className="text-sm line-clamp-1">{job.company}</span>
                                </div>
                              </TableCell>
                              <TableCell>
                                <div className="flex items-center gap-1.5">
                                  <MapPin className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
                                  <span className="text-sm line-clamp-1">{job.location || '-'}</span>
                                  {job.is_remote && (
                                    <Tooltip>
                                      <TooltipTrigger>
                                        <Globe className="h-3 w-3 text-blue-500" />
                                      </TooltipTrigger>
                                      <TooltipContent>Remote</TooltipContent>
                                    </Tooltip>
                                  )}
                                </div>
                              </TableCell>
                              <TableCell>
                                <span className="text-sm">{formatSalary(job.salary_min, job.salary_max, job.salary_range)}</span>
                              </TableCell>
                              <TableCell>
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <div className="flex flex-col gap-1 cursor-help">
                                      <div className="flex items-center justify-between text-xs">
                                        <span className="text-green-600 font-medium">{matchedCount}</span>
                                        <span className="text-muted-foreground">/ {totalSkills}</span>
                                      </div>
                                      <Progress 
                                        value={totalSkills > 0 ? (matchedCount / totalSkills) * 100 : 0} 
                                        className="h-1.5"
                                      />
                                    </div>
                                  </TooltipTrigger>
                                  <TooltipContent side="left" className="max-w-[250px]">
                                    <div className="space-y-2 text-xs">
                                      {matchedCount > 0 && (
                                        <div>
                                          <p className="font-medium text-green-600 mb-0.5">Matched ({matchedCount}):</p>
                                          <p>{match.matched_skills?.slice(0, 5).join(', ')}{matchedCount > 5 && ` +${matchedCount - 5}`}</p>
                                        </div>
                                      )}
                                      {missingCount > 0 && (
                                        <div>
                                          <p className="font-medium text-orange-600 mb-0.5">Missing ({missingCount}):</p>
                                          <p>{match.missing_skills?.slice(0, 5).join(', ')}{missingCount > 5 && ` +${missingCount - 5}`}</p>
                                        </div>
                                      )}
                                    </div>
                                  </TooltipContent>
                                </Tooltip>
                              </TableCell>
                              <TableCell>
                                <div className="flex items-center justify-end gap-1">
                                  {job.job_url && (
                                    <Tooltip>
                                      <TooltipTrigger asChild>
                                        <Button
                                          variant="ghost"
                                          size="icon"
                                          className="h-7 w-7"
                                          onClick={(e) => {
                                            e.stopPropagation();
                                            if (job.job_url) window.open(job.job_url, '_blank');
                                          }}
                                        >
                                          <ExternalLink className="h-3.5 w-3.5" />
                                        </Button>
                                      </TooltipTrigger>
                                      <TooltipContent>Open job posting</TooltipContent>
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
                  )}
                </div>
              </Card>
            )}
          </div>
        </div>

        {/* Job Details Sheet */}
        <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
          <SheetContent className="w-[500px] sm:w-[550px] overflow-y-auto">
            {selectedMatch && (() => {
              const job = selectedMatch.job || selectedMatch.job_posting;
              if (!job) return null;
              
              const grade = (selectedMatch.match_grade as MatchGrade) || calculateGrade(selectedMatch.match_score);
              const gradeConfig = GRADE_CONFIG[grade] || GRADE_CONFIG['C'];

              return (
                <>
                  <SheetHeader className="pb-4 border-b">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <SheetTitle className="text-lg leading-tight">{job.title}</SheetTitle>
                        <SheetDescription className="text-sm mt-1">{job.company}</SheetDescription>
                      </div>
                      <div className="flex flex-col items-end gap-1 flex-shrink-0">
                        <Badge className={`${gradeConfig.bgClass} ${gradeConfig.colorClass} font-bold text-base px-2.5`}>
                          {gradeConfig.label}
                        </Badge>
                        <span className="text-xl font-bold">{Math.round(selectedMatch.match_score)}%</span>
                      </div>
                    </div>
                  </SheetHeader>

                  <div className="py-5 space-y-5">
                    {/* Job Info Grid */}
                    <div className="grid grid-cols-2 gap-3">
                      <div className="flex items-center gap-2 text-sm">
                        <MapPin className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                        <span className="truncate">{job.location || 'Not specified'}</span>
                        {job.is_remote && <Badge variant="secondary" className="text-xs ml-1">Remote</Badge>}
                      </div>
                      <div className="flex items-center gap-2 text-sm">
                        <DollarSign className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                        <span>{formatSalary(job.salary_min, job.salary_max, job.salary_range)}</span>
                      </div>
                      {job.job_type && (
                        <div className="flex items-center gap-2 text-sm">
                          <Briefcase className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                          <span>{job.job_type}</span>
                        </div>
                      )}
                      {job.platform && (
                        <div className="flex items-center gap-2 text-sm">
                          <Globe className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                          <span>{job.platform}</span>
                        </div>
                      )}
                    </div>

                    {/* Score Breakdown */}
                    <div className="space-y-2">
                      <h4 className="text-sm font-semibold flex items-center gap-2">
                        <TrendingUp className="h-4 w-4" /> Score Breakdown
                      </h4>
                      <div className="grid grid-cols-2 gap-2">
                        {[
                          { label: 'Skills', value: selectedMatch.skill_match_score },
                          { label: 'Experience', value: selectedMatch.experience_match_score },
                          { label: 'Location', value: selectedMatch.location_match_score },
                          { label: 'Salary', value: selectedMatch.salary_match_score },
                          { label: 'Semantic', value: selectedMatch.semantic_similarity },
                        ].map((score) => (
                          <div key={score.label} className="flex items-center justify-between bg-muted/50 rounded px-2.5 py-1.5">
                            <span className="text-xs text-muted-foreground">{score.label}</span>
                            <span className={`text-sm font-semibold ${getScoreColor(score.value ?? 0)}`}>
                              {Math.round(score.value ?? 0)}%
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Matched Skills */}
                    {selectedMatch.matched_skills && selectedMatch.matched_skills.length > 0 && (
                      <div className="space-y-2">
                        <h4 className="text-sm font-semibold flex items-center gap-2 text-green-700">
                          <CheckCircle2 className="h-4 w-4" /> Matched Skills ({selectedMatch.matched_skills.length})
                        </h4>
                        <div className="flex flex-wrap gap-1">
                          {selectedMatch.matched_skills.map((skill, idx) => (
                            <Badge key={idx} variant="secondary" className="bg-green-50 text-green-700 text-xs">
                              {skill}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Missing Skills */}
                    {selectedMatch.missing_skills && selectedMatch.missing_skills.length > 0 && (
                      <div className="space-y-2">
                        <h4 className="text-sm font-semibold flex items-center gap-2 text-orange-700">
                          <XCircle className="h-4 w-4" /> Skills to Develop ({selectedMatch.missing_skills.length})
                        </h4>
                        <div className="flex flex-wrap gap-1">
                          {selectedMatch.missing_skills.map((skill, idx) => (
                            <Badge key={idx} variant="outline" className="text-orange-600 border-orange-300 text-xs">
                              {skill}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Description */}
                    {job.description && (
                      <div className="space-y-2">
                        <h4 className="text-sm font-semibold">Description</h4>
                        <p className="text-sm text-muted-foreground whitespace-pre-line leading-relaxed">
                          {job.description}
                        </p>
                      </div>
                    )}

                    {/* Posted Date */}
                    {job.posted_date && (
                      <div className="flex items-center gap-2 text-xs text-muted-foreground pt-2 border-t">
                        <Clock className="h-3.5 w-3.5" />
                        <span>Posted {format(new Date(job.posted_date), 'MMM dd, yyyy')}</span>
                      </div>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="flex gap-2 pt-4 border-t">
                    {job.job_url && (
                      <Button variant="outline" className="flex-1" onClick={() => job.job_url && window.open(job.job_url, '_blank')}>
                        <ExternalLink className="h-4 w-4 mr-2" /> View Posting
                      </Button>
                    )}
                    <Button
                      className="flex-1 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700"
                      onClick={() => {
                        setSheetOpen(false);
                        navigate(`/candidates/${selectedCandidateId}/matches/jobs/${job.id}`);
                      }}
                    >
                      <Sparkles className="h-4 w-4 mr-2" /> Tailor Resume
                    </Button>
                  </div>
                </>
              );
            })()}
          </SheetContent>
        </Sheet>
      </div>
    </TooltipProvider>
  );
}
