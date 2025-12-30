/**
 * Jobs Page
 * View candidates and their matched jobs with a clean, professional layout
 */

import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { Checkbox } from '@/components/ui/checkbox';
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
  Clock,
  Sparkles,
  Send,
  Filter,
} from 'lucide-react';
import { candidateApi } from '@/lib/candidateApi';
import { jobMatchApi } from '@/lib/jobMatchApi';
import { format } from 'date-fns';
import type { JobMatch, MatchGrade } from '@/types';
import { SubmissionDialog } from '@/components/SubmissionDialog';

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
  const { candidateId: urlCandidateId } = useParams<{ candidateId: string }>();
  const [selectedCandidateId, setSelectedCandidateId] = useState<number | null>(
    urlCandidateId ? parseInt(urlCandidateId, 10) : null
  );
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>([]);
  const [selectedGrades, setSelectedGrades] = useState<string[]>([]);

  // Available grades for filtering
  const AVAILABLE_GRADES = ['A+', 'A', 'B', 'C', 'D', 'F'] as const;

  // Submission dialog state
  const [submissionDialogOpen, setSubmissionDialogOpen] = useState(false);
  const [selectedJobForSubmission, setSelectedJobForSubmission] = useState<{
    jobId: number;
    jobTitle: string;
    company: string;
  } | null>(null);

  // Update selected candidate from URL param
  useEffect(() => {
    if (urlCandidateId) {
      const candidateId = parseInt(urlCandidateId, 10);
      if (candidateId !== selectedCandidateId) {
        setSelectedCandidateId(candidateId);
      }
    }
  }, [urlCandidateId]);

  // Update URL when candidate is selected
  const handleCandidateSelect = (candidateId: number) => {
    setSelectedCandidateId(candidateId);
    navigate(`/jobs/candidate/${candidateId}`, { replace: true });
  };

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

  // Fetch matches for selected candidate with pagination and filters
  const { 
    data: matchesData, 
    isLoading: loadingMatches,
    error: matchesError 
  } = useQuery({
    queryKey: ['jobMatches', selectedCandidateId, currentPage, pageSize, selectedPlatforms, selectedGrades],
    queryFn: async () => {
      if (!selectedCandidateId) return null;
      return jobMatchApi.getCandidateMatches(selectedCandidateId, { 
        page: currentPage,
        per_page: pageSize,
        sort_by: 'match_score',
        sort_order: 'desc',
        platforms: selectedPlatforms.length > 0 ? selectedPlatforms : undefined,
        grades: selectedGrades.length > 0 ? selectedGrades : undefined,
      });
    },
    enabled: !!selectedCandidateId,
    staleTime: 0,
  });

  const matches = matchesData?.matches || [];
  const totalMatches = matchesData?.total_matches || 0;
  const totalPages = matchesData?.total_pages || 0;
  const selectedCandidate = candidates.find((c) => c.id === selectedCandidateId);

  // Use available platforms from API response (covers all jobs, not just current page)
  const availablePlatforms = matchesData?.available_platforms || [];

  // Toggle platform selection (reset to page 1)
  const togglePlatform = (platform: string) => {
    setSelectedPlatforms((prev) =>
      prev.includes(platform)
        ? prev.filter((p) => p !== platform)
        : [...prev, platform]
    );
    setCurrentPage(1);
  };

  // Toggle grade selection (reset to page 1)
  const toggleGrade = (grade: string) => {
    setSelectedGrades((prev) =>
      prev.includes(grade)
        ? prev.filter((g) => g !== grade)
        : [...prev, grade]
    );
    setCurrentPage(1);
  };

  // Clear all filters
  const clearAllFilters = () => {
    setSelectedPlatforms([]);
    setSelectedGrades([]);
    setCurrentPage(1);
  };

  // Check if any filters are active
  const hasActiveFilters = selectedPlatforms.length > 0 || selectedGrades.length > 0;
  const activeFilterCount = selectedPlatforms.length + selectedGrades.length;

  const handleRowClick = (match: JobMatch) => {
    const job = match.job || match.job_posting;
    if (job) {
      navigate(`/candidates/${selectedCandidateId}/matches/jobs/${job.id}`, {
        state: { match }
      });
    }
  };

  return (
    <TooltipProvider>
      <div className="flex flex-col h-[calc(100vh-120px)]">
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
                          onClick={() => handleCandidateSelect(candidate.id)}
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
                    <div className="flex items-center gap-3">
                      <Badge variant="secondary" className="text-sm">
                        {hasActiveFilters 
                          ? `${totalMatches} jobs (filtered)`
                          : `${totalMatches} job${totalMatches !== 1 ? 's' : ''} matched`
                        }
                      </Badge>

                      {/* Combined Filter Popover */}
                      <Popover>
                        <PopoverTrigger asChild>
                          <Button variant="outline" size="sm" className="h-8 gap-2">
                            <Filter className="h-3.5 w-3.5" />
                            Filters
                            {activeFilterCount > 0 && (
                              <Badge variant="secondary" className="ml-1 h-5 px-1.5 text-xs">
                                {activeFilterCount}
                              </Badge>
                            )}
                          </Button>
                        </PopoverTrigger>
                        <PopoverContent className="w-64 p-0" align="end">
                          <div className="p-3 border-b">
                            <div className="flex items-center justify-between">
                              <h4 className="font-medium text-sm">Filters</h4>
                              {hasActiveFilters && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-6 px-2 text-xs text-muted-foreground hover:text-foreground"
                                  onClick={clearAllFilters}
                                >
                                  Clear all
                                </Button>
                              )}
                            </div>
                          </div>

                          {/* Grade Filter Section */}
                          <div className="p-3 border-b">
                            <h5 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
                              Grade
                            </h5>
                            <div className="flex flex-wrap gap-1.5">
                              {AVAILABLE_GRADES.map((grade) => {
                                const isSelected = selectedGrades.includes(grade);
                                const gradeConfig = GRADE_CONFIG[grade];
                                return (
                                  <button
                                    key={grade}
                                    onClick={() => toggleGrade(grade)}
                                    className={`px-2 py-1 text-xs font-medium rounded-md border transition-colors ${
                                      isSelected
                                        ? `${gradeConfig.bgClass} ${gradeConfig.colorClass} border-current`
                                        : 'bg-background hover:bg-muted border-border'
                                    }`}
                                  >
                                    {grade}
                                  </button>
                                );
                              })}
                            </div>
                          </div>

                          {/* Platform Filter Section */}
                          {availablePlatforms.length > 0 && (
                            <div className="p-3">
                              <h5 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
                                Platform
                              </h5>
                              <div className="space-y-2 max-h-40 overflow-y-auto">
                                {availablePlatforms.map((platform) => (
                                  <div
                                    key={platform}
                                    className="flex items-center space-x-2"
                                  >
                                    <Checkbox
                                      id={`platform-${platform}`}
                                      checked={selectedPlatforms.includes(platform.toLowerCase())}
                                      onCheckedChange={() => togglePlatform(platform.toLowerCase())}
                                    />
                                    <label
                                      htmlFor={`platform-${platform}`}
                                      className="flex-1 text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer capitalize"
                                    >
                                      {platform}
                                    </label>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </PopoverContent>
                      </Popover>
                    </div>
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
                <div className="flex-1 overflow-auto p-4">
                  {loadingMatches ? (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                      {[1, 2, 3, 4].map((i) => (
                        <Skeleton key={i} className="h-64 w-full rounded-lg" />
                      ))}
                    </div>
                  ) : matchesError ? (
                    <Alert variant="destructive">
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription>Failed to load job matches. Please try again.</AlertDescription>
                    </Alert>
                  ) : matches.length === 0 && hasActiveFilters ? (
                    <div className="flex flex-col items-center justify-center h-full text-center p-8">
                      <Filter className="h-12 w-12 text-muted-foreground mb-3" />
                      <h3 className="text-lg font-medium mb-1">No Matches Found</h3>
                      <p className="text-muted-foreground text-sm max-w-sm mb-3">
                        No jobs found for the selected filters. Try adjusting your criteria.
                      </p>
                      <Button variant="outline" size="sm" onClick={clearAllFilters}>
                        Clear Filters
                      </Button>
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
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                      {matches.map((match) => {
                        const job = match.job || match.job_posting;
                        if (!job) return null;
                        
                        const grade = (match.match_grade as MatchGrade) || calculateGrade(match.match_score);
                        const gradeConfig = GRADE_CONFIG[grade] || GRADE_CONFIG['C'];
                        const matchedCount = match.matched_skills?.length || 0;
                        const missingCount = match.missing_skills?.length || 0;

                        return (
                          <Card
                            key={match.id}
                            className="cursor-pointer hover:shadow-lg transition-all hover:border-primary/50 group"
                            onClick={() => handleRowClick(match)}
                          >
                            {/* Card Header with Score */}
                            <CardHeader className="pb-3">
                              <div className="flex items-start justify-between gap-3">
                                <div className="flex-1 min-w-0">
                                  <h3 className="font-semibold text-base line-clamp-2 group-hover:text-primary transition-colors">
                                    {job.title}
                                  </h3>
                                  <div className="flex items-center gap-2 mt-1.5">
                                    <Building2 className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                                    <span className="text-sm text-muted-foreground font-medium truncate">
                                      {job.company}
                                    </span>
                                  </div>
                                </div>
                                <div className="flex flex-col items-center gap-1 flex-shrink-0">
                                  <Badge className={`${gradeConfig.bgClass} ${gradeConfig.colorClass} font-bold text-sm px-2.5 py-0.5`}>
                                    {gradeConfig.label}
                                  </Badge>
                                  <span className={`text-lg font-bold ${getScoreColor(match.match_score)}`}>
                                    {Math.round(match.match_score)}%
                                  </span>
                                </div>
                              </div>
                            </CardHeader>

                            <CardContent className="pt-0 space-y-3">
                              {/* Job Details Grid */}
                              <div className="grid grid-cols-2 gap-2 text-sm">
                                <div className="flex items-center gap-2">
                                  <MapPin className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                                  <span className="truncate">{job.location || 'Not specified'}</span>
                                  {job.is_remote && (
                                    <Badge variant="secondary" className="text-xs px-1.5 py-0">Remote</Badge>
                                  )}
                                </div>
                                <div className="flex items-center gap-2">
                                  <DollarSign className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                                  <span className="truncate">{formatSalary(job.salary_min, job.salary_max, job.salary_range)}</span>
                                </div>
                                {job.job_type && (
                                  <div className="flex items-center gap-2">
                                    <Briefcase className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                                    <span className="truncate">{job.job_type}</span>
                                  </div>
                                )}
                                {job.platform && (
                                  <div className="flex items-center gap-2">
                                    <Globe className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                                    <span className="truncate">{job.platform}</span>
                                  </div>
                                )}
                              </div>

                              {/* Description Preview */}
                              {job.description && (
                                <p className="text-sm text-muted-foreground line-clamp-2">
                                  {job.description}
                                </p>
                              )}

                              {/* Skills Section */}
                              <div className="space-y-2">
                                {/* Matched Skills */}
                                {matchedCount > 0 && (
                                  <div className="flex items-start gap-2">
                                    <CheckCircle2 className="h-4 w-4 text-green-600 flex-shrink-0 mt-0.5" />
                                    <div className="flex flex-wrap gap-1">
                                      {match.matched_skills?.slice(0, 4).map((skill, idx) => (
                                        <Badge key={idx} variant="secondary" className="bg-green-50 text-green-700 text-xs px-1.5 py-0">
                                          {skill}
                                        </Badge>
                                      ))}
                                      {matchedCount > 4 && (
                                        <Badge variant="outline" className="text-xs px-1.5 py-0">
                                          +{matchedCount - 4} more
                                        </Badge>
                                      )}
                                    </div>
                                  </div>
                                )}

                                {/* Missing Skills */}
                                {missingCount > 0 && (
                                  <div className="flex items-start gap-2">
                                    <XCircle className="h-4 w-4 text-orange-500 flex-shrink-0 mt-0.5" />
                                    <div className="flex flex-wrap gap-1">
                                      {match.missing_skills?.slice(0, 3).map((skill, idx) => (
                                        <Badge key={idx} variant="outline" className="text-orange-600 border-orange-300 text-xs px-1.5 py-0">
                                          {skill}
                                        </Badge>
                                      ))}
                                      {missingCount > 3 && (
                                        <Badge variant="outline" className="text-xs px-1.5 py-0">
                                          +{missingCount - 3} more
                                        </Badge>
                                      )}
                                    </div>
                                  </div>
                                )}
                              </div>

                              {/* Score Bars */}
                              <div className="grid grid-cols-4 gap-2 pt-2 border-t">
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <div className="text-center">
                                      <div className="text-xs text-muted-foreground mb-1">Skills</div>
                                      <div className={`text-sm font-semibold ${getScoreColor(match.skill_match_score)}`}>
                                        {Math.round(match.skill_match_score)}%
                                      </div>
                                    </div>
                                  </TooltipTrigger>
                                  <TooltipContent>Skill Match Score</TooltipContent>
                                </Tooltip>
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <div className="text-center">
                                      <div className="text-xs text-muted-foreground mb-1">Exp</div>
                                      <div className={`text-sm font-semibold ${getScoreColor(match.experience_match_score)}`}>
                                        {Math.round(match.experience_match_score)}%
                                      </div>
                                    </div>
                                  </TooltipTrigger>
                                  <TooltipContent>Experience Match Score</TooltipContent>
                                </Tooltip>
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <div className="text-center">
                                      <div className="text-xs text-muted-foreground mb-1">Location</div>
                                      <div className={`text-sm font-semibold ${getScoreColor(match.location_match_score)}`}>
                                        {Math.round(match.location_match_score)}%
                                      </div>
                                    </div>
                                  </TooltipTrigger>
                                  <TooltipContent>Location Match Score</TooltipContent>
                                </Tooltip>
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <div className="text-center">
                                      <div className="text-xs text-muted-foreground mb-1">Salary</div>
                                      <div className={`text-sm font-semibold ${getScoreColor(match.salary_match_score)}`}>
                                        {Math.round(match.salary_match_score)}%
                                      </div>
                                    </div>
                                  </TooltipTrigger>
                                  <TooltipContent>Salary Match Score</TooltipContent>
                                </Tooltip>
                              </div>

                              {/* Footer with date and actions */}
                              <div className="flex items-center justify-between pt-2 border-t">
                                {job.posted_date ? (
                                  <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                                    <Clock className="h-3.5 w-3.5" />
                                    <span>Posted {format(new Date(job.posted_date), 'MMM dd, yyyy')}</span>
                                  </div>
                                ) : (
                                  <div />
                                )}
                                <div className="flex items-center gap-2">
                                  {job.job_url && (
                                    <Tooltip>
                                      <TooltipTrigger asChild>
                                        <Button
                                          variant="ghost"
                                          size="sm"
                                          className="h-7 px-2"
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
                                  <Tooltip>
                                      <TooltipTrigger asChild>
                                        <Button
                                          variant="ghost"
                                          size="sm"
                                          className="h-7 px-2 text-blue-600 hover:text-blue-700 hover:bg-blue-50"
                                          onClick={(e) => {
                                            e.stopPropagation();
                                            setSelectedJobForSubmission({
                                              jobId: job.id,
                                              jobTitle: job.title,
                                              company: job.company,
                                            });
                                            setSubmissionDialogOpen(true);
                                          }}
                                        >
                                          <Send className="h-3.5 w-3.5 mr-1" />
                                          Submit
                                        </Button>
                                      </TooltipTrigger>
                                      <TooltipContent>Submit candidate to this job</TooltipContent>
                                    </Tooltip>
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      className="h-7 px-2 text-violet-600 hover:text-violet-700 hover:bg-violet-50"
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        navigate(`/candidates/${selectedCandidateId}/matches/jobs/${job.id}`);
                                      }}
                                    >
                                      <Sparkles className="h-3.5 w-3.5 mr-1" />
                                      Tailor
                                    </Button>
                                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                                </div>
                              </div>
                            </CardContent>
                          </Card>
                        );
                      })}
                    </div>
                  )}
                </div>
              </Card>
            )}
          </div>
        </div>
      </div>

      {/* Submission Dialog */}
      {selectedCandidateId && selectedCandidate && selectedJobForSubmission && (
        <SubmissionDialog
          open={submissionDialogOpen}
          onOpenChange={(open) => {
            setSubmissionDialogOpen(open);
            if (!open) setSelectedJobForSubmission(null);
          }}
          candidateId={selectedCandidateId}
          candidateName={`${selectedCandidate.first_name} ${selectedCandidate.last_name}`}
          jobPostingId={selectedJobForSubmission.jobId}
          jobTitle={selectedJobForSubmission.jobTitle}
          company={selectedJobForSubmission.company}
          onSuccess={() => {
            setSubmissionDialogOpen(false);
            setSelectedJobForSubmission(null);
          }}
        />
      )}
    </TooltipProvider>
  );
}
