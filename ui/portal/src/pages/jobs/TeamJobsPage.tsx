/**
 * Team Jobs Page - Merged View
 * Combines team hierarchy navigation with job matching functionality
 * 
 * Role-based behavior:
 * - RECRUITER: Shows only their assigned candidates (2-column: candidates | jobs)
 * - MANAGER/TEAM_LEAD: Shows 3-column layout (team | candidates | jobs)
 * - TENANT_ADMIN: Same as manager, starts at top level
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
  Users,
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
  Home,
  ArrowLeft,
  UserCog,
  Mail,
  LayoutGrid,
  List,
} from 'lucide-react';
import { apiRequest } from '@/lib/api-client';
import { jobMatchApi } from '@/lib/jobMatchApi';
import { format } from 'date-fns';
import type { JobMatch, MatchGrade, CandidateInfo, TeamMemberWithCounts } from '@/types';
import { SubmissionDialog } from '@/components/SubmissionDialog';
import { usePortalAuth } from '@/contexts/PortalAuthContext';

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

const GRADE_CONFIG: Record<MatchGrade, { label: string; colorClass: string; bgClass: string }> = {
  'A+': { label: 'A+', colorClass: 'text-emerald-700', bgClass: 'bg-emerald-100' },
  A: { label: 'A', colorClass: 'text-green-700', bgClass: 'bg-green-100' },
  'B+': { label: 'B+', colorClass: 'text-blue-700', bgClass: 'bg-blue-100' },
  B: { label: 'B', colorClass: 'text-blue-600', bgClass: 'bg-blue-50' },
  'C+': { label: 'C+', colorClass: 'text-yellow-700', bgClass: 'bg-yellow-100' },
  C: { label: 'C', colorClass: 'text-yellow-600', bgClass: 'bg-yellow-50' },
};

const ONBOARDING_STATUS_COLORS: Record<string, string> = {
  PENDING_ASSIGNMENT: 'bg-gray-100 text-gray-800',
  ASSIGNED: 'bg-blue-100 text-blue-800',
  PENDING_ONBOARDING: 'bg-yellow-100 text-yellow-800',
  ONBOARDED: 'bg-purple-100 text-purple-800',
  APPROVED: 'bg-green-100 text-green-800',
  REJECTED: 'bg-red-100 text-red-800',
};

// Unified Scoring Grades: A+ (90+), A (80-89), B+ (75-79), B (70-74), C+ (65-69), C (<65)
const calculateGrade = (score: number): MatchGrade => {
  if (score >= 90) return 'A+';
  if (score >= 80) return 'A';
  if (score >= 75) return 'B+';
  if (score >= 70) return 'B';
  if (score >= 65) return 'C+';
  return 'C';
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

export function TeamJobsPage() {
  const navigate = useNavigate();
  const { user } = usePortalAuth();
  const { candidateId: urlCandidateId } = useParams<{ candidateId: string }>();
  
  // Determine user role for UI adaptation
  const userRoles = user?.roles?.map(r => r.name) || [];
  const isTenantAdmin = userRoles.includes('TENANT_ADMIN');
  const isRecruiter = userRoles.includes('RECRUITER') && !userRoles.includes('TENANT_ADMIN') && !userRoles.includes('MANAGER') && !userRoles.includes('TEAM_LEAD');
  const hasTeamView = !isRecruiter; // Managers, Team Leads, Admins see team view
  
  // Team navigation state (only for non-recruiters)
  const [navigationStack, setNavigationStack] = useState<TeamMemberWithCounts[]>([]);
  const [selectedMemberId, setSelectedMemberId] = useState<number | null>(null);
  const [teamSearchQuery, setTeamSearchQuery] = useState('');
  
  // Candidate selection state
  const [selectedCandidateId, setSelectedCandidateId] = useState<number | null>(
    urlCandidateId ? parseInt(urlCandidateId, 10) : null
  );
  const [candidateSearchQuery, setCandidateSearchQuery] = useState('');
  
  // Job matching state
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>([]);
  const [selectedGrades, setSelectedGrades] = useState<string[]>([]);
  const [selectedSource, setSelectedSource] = useState<'all' | 'email' | 'scraped'>('all');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const AVAILABLE_GRADES = ['A+', 'A', 'B+', 'B', 'C+', 'C'] as const;

  // Submission dialog state
  const [submissionDialogOpen, setSubmissionDialogOpen] = useState(false);
  const [selectedJobForSubmission, setSelectedJobForSubmission] = useState<{
    jobId: number;
    jobTitle: string;
    company: string;
  } | null>(null);

  // Current context for team view
  const currentContextId = navigationStack.length > 0 
    ? navigationStack[navigationStack.length - 1].id 
    : null;

  // ============ API QUERIES ============

  // Get team members (for managers/admins)
  const {
    data: teamMembersData,
    isLoading: isLoadingTeam,
  } = useQuery({
    queryKey: ['team-members', currentContextId],
    queryFn: async () => {
      const url = currentContextId 
        ? `/api/team/${currentContextId}/team-members`
        : '/api/team/my-team-members';
      return apiRequest.get<{ team_members: TeamMemberWithCounts[]; total: number }>(url);
    },
    enabled: hasTeamView,
  });

  // Check if user has team members
  const hasNoTeamMembers = hasTeamView && teamMembersData && teamMembersData.team_members.length === 0;

  // Get ALL candidates in tenant (for tenant admins)
  const {
    data: allCandidatesData,
    isLoading: isLoadingAllCandidates,
  } = useQuery({
    queryKey: ['all-tenant-candidates'],
    queryFn: async () => {
      // Fetch all candidates with status ready for job matching
      return apiRequest.get<{ candidates: CandidateInfo[]; total: number; page: number; per_page: number; pages: number }>(
        '/api/candidates?per_page=500&status=ready_for_assignment'
      );
    },
    enabled: isTenantAdmin && hasNoTeamMembers,
  });

  // Get recruiter's own candidates (for recruiters OR non-admin managers with no team)
  const {
    data: ownCandidatesData,
    isLoading: isLoadingOwnCandidates,
  } = useQuery({
    queryKey: ['my-own-candidates'],
    queryFn: async () => {
      return apiRequest.get<{ candidates: CandidateInfo[]; total: number }>(
        '/api/candidates/assignments/my-candidates'
      );
    },
    enabled: isRecruiter || (hasNoTeamMembers && !isTenantAdmin),
  });

  // Get selected team member's candidates (for managers viewing team member)
  const {
    data: teamMemberCandidatesData,
    isLoading: isLoadingTeamCandidates,
  } = useQuery({
    queryKey: ['team-member-candidates', selectedMemberId],
    queryFn: async () => {
      if (!selectedMemberId) return null;
      return apiRequest.get<{ candidates: CandidateInfo[]; total: number }>(
        `/api/team/members/${selectedMemberId}/candidates`
      );
    },
    enabled: hasTeamView && !!selectedMemberId,
  });

  // Get job matches for selected candidate
  const { 
    data: matchesData, 
    isLoading: loadingMatches,
    error: matchesError 
  } = useQuery({
    queryKey: ['jobMatches', selectedCandidateId, currentPage, pageSize, selectedPlatforms, selectedGrades, selectedSource],
    queryFn: async () => {
      if (!selectedCandidateId) return null;
      return jobMatchApi.getCandidateMatches(selectedCandidateId, { 
        page: currentPage,
        per_page: pageSize,
        sort_by: 'match_score',
        sort_order: 'desc',
        platforms: selectedPlatforms.length > 0 ? selectedPlatforms : undefined,
        grades: selectedGrades.length > 0 ? selectedGrades : undefined,
        source: selectedSource,
      });
    },
    enabled: !!selectedCandidateId,
    staleTime: 0,
  });

  // ============ DERIVED DATA ============

  const currentTeamMembers = teamMembersData?.team_members || [];
  const currentMember = navigationStack[navigationStack.length - 1];
  
  // Determine which candidates to show based on context
  const getCandidates = (): CandidateInfo[] => {
    // Tenant admin with no team members sees ALL candidates in tenant
    if (isTenantAdmin && hasNoTeamMembers) {
      return allCandidatesData?.candidates || [];
    }
    if (isRecruiter || hasNoTeamMembers) {
      return ownCandidatesData?.candidates || [];
    }
    if (selectedMemberId) {
      return teamMemberCandidatesData?.candidates || [];
    }
    return [];
  };
  
  const candidates = getCandidates();
  const selectedCandidate = candidates.find((c) => c.id === selectedCandidateId);
  
  const matches = matchesData?.matches || [];
  const totalMatches = matchesData?.total_matches || 0;
  const totalPages = matchesData?.total_pages || 0;
  const availablePlatforms = matchesData?.available_platforms || [];
  const availableSources = matchesData?.available_sources || [];

  // Filter team members by search
  const filteredTeamMembers = currentTeamMembers.filter((member) =>
    member.full_name.toLowerCase().includes(teamSearchQuery.toLowerCase()) ||
    member.email.toLowerCase().includes(teamSearchQuery.toLowerCase())
  );

  // Filter candidates by search
  const filteredCandidates = candidates.filter((candidate) => {
    const searchLower = candidateSearchQuery.toLowerCase();
    const fullName = `${candidate.first_name} ${candidate.last_name}`.toLowerCase();
    const email = candidate.email?.toLowerCase() || '';
    return fullName.includes(searchLower) || email.includes(searchLower);
  });

  // Check if any filters are active
  const hasActiveFilters = selectedPlatforms.length > 0 || selectedGrades.length > 0 || selectedSource !== 'all';
  const activeFilterCount = selectedPlatforms.length + selectedGrades.length + (selectedSource !== 'all' ? 1 : 0);

  // ============ EFFECTS ============

  // Update selected candidate from URL param
  useEffect(() => {
    if (urlCandidateId) {
      const candidateId = parseInt(urlCandidateId, 10);
      if (candidateId !== selectedCandidateId) {
        setSelectedCandidateId(candidateId);
      }
    }
  }, [urlCandidateId]);

  // Reset page when candidate changes
  useEffect(() => {
    setCurrentPage(1);
  }, [selectedCandidateId]);

  // ============ HANDLERS ============

  // Handle team member click
  const handleTeamMemberClick = (member: TeamMemberWithCounts) => {
    if (member.has_team_members) {
      // Drill down - this member has team members
      setNavigationStack([...navigationStack, member]);
      setSelectedMemberId(null);
      setSelectedCandidateId(null);
    } else {
      // Show this member's candidates
      setSelectedMemberId(member.id);
      setSelectedCandidateId(null);
    }
  };

  // Handle back navigation in team hierarchy
  const handleTeamBack = () => {
    const newStack = [...navigationStack];
    newStack.pop();
    setNavigationStack(newStack);
    setSelectedMemberId(null);
    setSelectedCandidateId(null);
  };

  // Handle candidate selection
  const handleCandidateSelect = (candidateId: number) => {
    setSelectedCandidateId(candidateId);
    navigate(`/candidate/jobs/${candidateId}`, { replace: true });
  };

  // Handle job row click
  const handleRowClick = (match: JobMatch) => {
    const job = match.job || match.job_posting;
    if (job) {
      navigate(`/candidate/jobs/${selectedCandidateId}/job/${job.id}`, {
        state: { match }
      });
    }
  };

  // Toggle platform selection
  const togglePlatform = (platform: string) => {
    setSelectedPlatforms((prev) =>
      prev.includes(platform)
        ? prev.filter((p) => p !== platform)
        : [...prev, platform]
    );
    setCurrentPage(1);
  };

  // Toggle grade selection
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
    setSelectedSource('all');
    setCurrentPage(1);
  };

  // ============ RENDER HELPERS ============

  // Render candidate card in the list
  const renderCandidateItem = (candidate: CandidateInfo) => (
    <button
      key={candidate.id}
      onClick={() => handleCandidateSelect(candidate.id)}
      className={`w-full text-left p-3 rounded-lg border transition-all ${
        selectedCandidateId === candidate.id
          ? 'border-primary bg-primary/5 shadow-sm ring-1 ring-primary/20'
          : 'border-slate-200 bg-white hover:border-primary/50 hover:shadow-sm'
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <p className="font-medium text-sm truncate text-slate-900">
            {candidate.first_name} {candidate.last_name}
          </p>
          <p className="text-xs text-slate-500 truncate">
            {candidate.email}
          </p>
          <Badge
            className={`mt-1.5 text-xs ${ONBOARDING_STATUS_COLORS[candidate.onboarding_status || 'PENDING_ASSIGNMENT']}`}
          >
            {(candidate.onboarding_status || 'PENDING_ASSIGNMENT').replace(/_/g, ' ')}
          </Badge>
        </div>
        <ChevronRight className={`h-4 w-4 flex-shrink-0 mt-1 ${
          selectedCandidateId === candidate.id ? 'text-primary' : 'text-slate-400'
        }`} />
      </div>
    </button>
  );

  // Render job match card
  const renderJobCard = (match: JobMatch) => {
    const job = match.job || match.job_posting;
    if (!job) return null;
    
    const grade = (match.match_grade as MatchGrade) || calculateGrade(match.match_score);
    const gradeConfig = GRADE_CONFIG[grade] || GRADE_CONFIG['C'];
    const matchedCount = match.matched_skills?.length || 0;
    const missingCount = match.missing_skills?.length || 0;

    return (
      <Card
        key={match.id ?? match.job_posting_id ?? job.id}
        className="cursor-pointer hover:shadow-lg transition-all hover:border-primary/50 group"
        onClick={() => handleRowClick(match)}
      >
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
            {job.is_email_sourced && (
              <div className="flex items-center gap-2 col-span-2">
                <Mail className="h-4 w-4 text-purple-500 flex-shrink-0" />
                <Badge className="bg-purple-100 text-purple-700 text-xs px-1.5 py-0">
                  Email Job
                </Badge>
                {job.sourced_by && (
                  <span className="text-xs text-muted-foreground truncate">
                    via {job.sourced_by.first_name || job.sourced_by.last_name 
                      ? `${job.sourced_by.first_name || ''} ${job.sourced_by.last_name || ''}`.trim()
                      : job.sourced_by.email}
                  </span>
                )}
                {!job.sourced_by && job.source_email_sender && (
                  <span className="text-xs text-muted-foreground truncate">
                    from {job.source_email_sender}
                  </span>
                )}
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

          {/* Score Bars - Unified Scoring (Skills 45%, Experience 20%, Semantic 35%) */}
          {/* Note: Keyword scoring was removed to speed up job imports */}
          <div className="grid grid-cols-3 gap-2 pt-2 border-t">
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="text-center">
                  <div className="text-xs text-muted-foreground mb-1">Skills</div>
                  <div className={`text-sm font-semibold ${getScoreColor(match.skill_match_score)}`}>
                    {Math.round(match.skill_match_score)}%
                  </div>
                </div>
              </TooltipTrigger>
              <TooltipContent>Skills Match (45% weight)</TooltipContent>
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
              <TooltipContent>Experience Match (20% weight)</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="text-center">
                  <div className="text-xs text-muted-foreground mb-1">Semantic</div>
                  <div className={`text-sm font-semibold ${getScoreColor(match.semantic_similarity)}`}>
                    {Math.round(match.semantic_similarity)}%
                  </div>
                </div>
              </TooltipTrigger>
              <TooltipContent>Semantic Similarity (35% weight)</TooltipContent>
            </Tooltip>
          </div>

          {/* Footer with date and actions */}
          <div className="flex items-center justify-between pt-2 border-t">
            {(job.posted_date || job.created_at) ? (
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <Clock className="h-3.5 w-3.5" />
                <span>Posted {(() => {
                  // Prefer created_at for accurate timestamp, fall back to posted_date
                  const dateStr = job.created_at || job.posted_date;
                  if (!dateStr) return '';
                  const date = new Date(dateStr);
                  const hasTime = date.getHours() !== 0 || date.getMinutes() !== 0 || date.getSeconds() !== 0;
                  return hasTime 
                    ? format(date, 'MMM dd, yyyy h:mm a')
                    : format(date, 'MMM dd, yyyy');
                })()}</span>
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
                  navigate(`/candidate/jobs/${selectedCandidateId}/job/${job.id}`);
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
  };

  // Render job match as list row (compact view)
  const renderJobRow = (match: JobMatch) => {
    const job = match.job || match.job_posting;
    if (!job) return null;
    
    const grade = (match.match_grade as MatchGrade) || calculateGrade(match.match_score);
    const gradeConfig = GRADE_CONFIG[grade] || GRADE_CONFIG['C'];
    const matchedCount = match.matched_skills?.length || 0;

    return (
      <div
        key={match.id ?? match.job_posting_id ?? job.id}
        className="flex items-center gap-4 p-4 border-b hover:bg-muted/50 cursor-pointer transition-colors group"
        onClick={() => handleRowClick(match)}
      >
        {/* Grade & Score */}
        <div className="flex flex-col items-center gap-0.5 w-14 flex-shrink-0">
          <Badge className={`${gradeConfig.bgClass} ${gradeConfig.colorClass} font-bold text-xs px-2 py-0.5`}>
            {gradeConfig.label}
          </Badge>
          <span className={`text-sm font-semibold ${getScoreColor(match.match_score)}`}>
            {Math.round(match.match_score)}%
          </span>
        </div>

        {/* Job Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start gap-2">
            <h3 className="font-medium text-sm truncate group-hover:text-primary transition-colors">
              {job.title}
            </h3>
            {job.is_email_sourced && (
              <Badge className="bg-purple-100 text-purple-700 text-xs px-1.5 py-0 flex-shrink-0">
                <Mail className="h-3 w-3 mr-1" />
                Email
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <Building2 className="h-3 w-3" />
              {job.company}
            </span>
            <span className="flex items-center gap-1">
              <MapPin className="h-3 w-3" />
              {job.location || 'Not specified'}
              {job.is_remote && <Badge variant="secondary" className="text-[10px] px-1 py-0 ml-1">Remote</Badge>}
            </span>
            {job.platform && (
              <span className="flex items-center gap-1">
                <Globe className="h-3 w-3" />
                {job.platform}
              </span>
            )}
          </div>
        </div>

        {/* Salary */}
        <div className="w-28 flex-shrink-0 text-right">
          <div className="flex items-center justify-end gap-1 text-sm">
            <DollarSign className="h-3.5 w-3.5 text-muted-foreground" />
            <span>{formatSalary(job.salary_min, job.salary_max, job.salary_range)}</span>
          </div>
        </div>

        {/* Skills Summary */}
        <div className="w-24 flex-shrink-0 text-center">
          {matchedCount > 0 && (
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="flex items-center justify-center gap-1 text-sm text-green-600">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  <span>{matchedCount} skills</span>
                </div>
              </TooltipTrigger>
              <TooltipContent>
                <div className="max-w-xs">
                  <p className="font-medium mb-1">Matched Skills:</p>
                  <p className="text-xs">{match.matched_skills?.join(', ')}</p>
                </div>
              </TooltipContent>
            </Tooltip>
          )}
        </div>

        {/* Posted Date */}
        <div className="w-24 flex-shrink-0 text-xs text-muted-foreground text-right">
          {(job.posted_date || job.created_at) && (
            <span>{(() => {
              const dateStr = job.created_at || job.posted_date;
              if (!dateStr) return '';
              const date = new Date(dateStr);
              const hasTime = date.getHours() !== 0 || date.getMinutes() !== 0 || date.getSeconds() !== 0;
              return hasTime 
                ? format(date, 'MMM dd h:mm a')
                : format(date, 'MMM dd, yyyy');
            })()}</span>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1 flex-shrink-0">
          {job.job_url && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 w-7 p-0"
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
                className="h-7 w-7 p-0 text-blue-600 hover:text-blue-700 hover:bg-blue-50"
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
                <Send className="h-3.5 w-3.5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Submit candidate</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 w-7 p-0 text-violet-600 hover:text-violet-700 hover:bg-violet-50"
                onClick={(e) => {
                  e.stopPropagation();
                  navigate(`/candidate/jobs/${selectedCandidateId}/job/${job.id}`);
                }}
              >
                <Sparkles className="h-3.5 w-3.5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Tailor resume</TooltipContent>
          </Tooltip>
          <ChevronRight className="h-4 w-4 text-muted-foreground" />
        </div>
      </div>
    );
  };

  // ============ MAIN RENDER ============

  // Determine if we should show candidates column
  const showCandidates = isRecruiter || hasNoTeamMembers || selectedMemberId !== null;
  const isLoadingCandidates = isTenantAdmin && hasNoTeamMembers 
    ? isLoadingAllCandidates 
    : (isRecruiter || hasNoTeamMembers ? isLoadingOwnCandidates : isLoadingTeamCandidates);

  return (
    <TooltipProvider>
      <div className="flex flex-col h-[calc(100vh-120px)]">
        {/* Breadcrumb Navigation (for team view) */}
        {hasTeamView && !hasNoTeamMembers && navigationStack.length > 0 && (
          <div className="flex items-center gap-2 text-sm mb-4">
            <button
              onClick={() => {
                setNavigationStack([]);
                setSelectedMemberId(null);
                setSelectedCandidateId(null);
              }}
              className="flex items-center gap-1 hover:text-primary font-medium px-2 py-1 rounded hover:bg-slate-100 transition-colors"
            >
              <Home className="h-4 w-4" />
              Home
            </button>
            {navigationStack.map((member, index) => (
              <div key={member.id} className="flex items-center gap-2">
                <ChevronRight className="h-4 w-4 text-slate-400" />
                <button
                  onClick={() => {
                    setNavigationStack(navigationStack.slice(0, index + 1));
                    setSelectedMemberId(null);
                    setSelectedCandidateId(null);
                  }}
                  className="hover:text-primary font-medium px-2 py-1 rounded hover:bg-slate-100 transition-colors"
                >
                  {member.full_name}
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Main Layout */}
        <div className="flex gap-4 flex-1 min-h-0">
          
          {/* Column 1: Team Members (only for managers/admins with team) */}
          {hasTeamView && !hasNoTeamMembers && (
            <div className="w-64 flex-shrink-0">
              <Card className="h-full flex flex-col">
                <CardHeader className="pb-3 flex-shrink-0 border-b">
                  {currentMember ? (
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={handleTeamBack}
                          className="gap-2 -ml-2"
                        >
                          <ArrowLeft className="h-4 w-4" />
                          Back
                        </Button>
                      </div>
                      <div className="flex items-center gap-2 px-2 py-1.5 bg-primary/10 rounded-lg">
                        <div className="h-6 w-6 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-semibold text-xs">
                          {currentMember.full_name.charAt(0).toUpperCase()}
                        </div>
                        <span className="text-sm font-medium text-slate-900 truncate">
                          {currentMember.full_name}'s Team
                        </span>
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2">
                      <div className="p-1.5 rounded-md bg-blue-100">
                        <Users className="h-4 w-4 text-blue-600" />
                      </div>
                      <span className="font-semibold text-slate-900">My Team</span>
                      <Badge variant="secondary" className="ml-auto text-xs">
                        {currentTeamMembers.length}
                      </Badge>
                    </div>
                  )}
                  <div className="relative mt-3">
                    <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      placeholder="Search team..."
                      value={teamSearchQuery}
                      onChange={(e) => setTeamSearchQuery(e.target.value)}
                      className="pl-8 h-9"
                    />
                  </div>
                </CardHeader>
                <CardContent className="p-0 flex-1 overflow-hidden">
                  <ScrollArea className="h-full">
                    {isLoadingTeam ? (
                      <div className="space-y-2 p-3">
                        {[1, 2, 3].map((i) => (
                          <Skeleton key={i} className="h-16 w-full" />
                        ))}
                      </div>
                    ) : filteredTeamMembers.length === 0 ? (
                      <div className="flex flex-col items-center justify-center py-8 text-center px-4">
                        <Users className="h-10 w-10 text-muted-foreground mb-2" />
                        <p className="text-sm text-muted-foreground">
                          {teamSearchQuery ? 'No team members found' : 'No team members'}
                        </p>
                      </div>
                    ) : (
                      <div className="p-2 space-y-1">
                        {filteredTeamMembers.map((member) => (
                          <button
                            key={member.id}
                            onClick={() => handleTeamMemberClick(member)}
                            className={`w-full text-left p-3 rounded-lg border transition-all ${
                              selectedMemberId === member.id
                                ? 'border-primary bg-primary/5 shadow-sm ring-1 ring-primary/20'
                                : 'border-slate-200 bg-white hover:border-primary/50 hover:shadow-sm'
                            }`}
                          >
                            <div className="flex items-center gap-3">
                              <div className="h-8 w-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-semibold text-xs flex-shrink-0">
                                {member.full_name.charAt(0).toUpperCase()}
                              </div>
                              <div className="flex-1 min-w-0">
                                <p className="font-medium text-sm truncate text-slate-900">
                                  {member.full_name}
                                </p>
                                <div className="flex items-center gap-2 mt-0.5">
                                  <Badge variant="secondary" className="text-xs">
                                    {member.role_name}
                                  </Badge>
                                  <span className="text-xs text-slate-500">
                                    {member.candidate_count} cands
                                  </span>
                                </div>
                                {member.has_team_members && (
                                  <span className="text-xs text-primary font-medium">
                                    {member.team_member_count} team members →
                                  </span>
                                )}
                              </div>
                              <ChevronRight className={`h-4 w-4 flex-shrink-0 ${
                                selectedMemberId === member.id ? 'text-primary' : 'text-slate-400'
                              }`} />
                            </div>
                          </button>
                        ))}
                      </div>
                    )}
                  </ScrollArea>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Column 2: Candidates */}
          {showCandidates && (
            <div className="w-72 flex-shrink-0">
              <Card className="h-full flex flex-col">
                <CardHeader className="pb-3 flex-shrink-0 border-b">
                  <div className="flex items-center gap-2">
                    <div className="p-1.5 rounded-md bg-green-100">
                      <UserCog className="h-4 w-4 text-green-600" />
                    </div>
                    <span className="font-semibold text-slate-900">
                      {isRecruiter || hasNoTeamMembers ? 'My Candidates' : 'Candidates'}
                    </span>
                    <Badge variant="secondary" className="ml-auto text-xs">
                      {filteredCandidates.length}
                    </Badge>
                  </div>
                  <div className="relative mt-3">
                    <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      placeholder="Search candidates..."
                      value={candidateSearchQuery}
                      onChange={(e) => setCandidateSearchQuery(e.target.value)}
                      className="pl-8 h-9"
                    />
                  </div>
                </CardHeader>
                <CardContent className="p-0 flex-1 overflow-hidden">
                  <ScrollArea className="h-full">
                    {isLoadingCandidates ? (
                      <div className="space-y-2 p-3">
                        {[1, 2, 3, 4].map((i) => (
                          <Skeleton key={i} className="h-20 w-full" />
                        ))}
                      </div>
                    ) : filteredCandidates.length === 0 ? (
                      <div className="flex flex-col items-center justify-center py-8 text-center px-4">
                        <User className="h-10 w-10 text-muted-foreground mb-2" />
                        <p className="text-sm text-muted-foreground">
                          {candidateSearchQuery ? 'No candidates found' : 'No candidates available'}
                        </p>
                      </div>
                    ) : (
                      <div className="p-2 space-y-2">
                        {filteredCandidates.map(renderCandidateItem)}
                      </div>
                    )}
                  </ScrollArea>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Column 3 (or 2 for recruiters): Job Matches */}
          <div className="flex-1 min-w-0 flex flex-col">
            {/* Show prompt based on context */}
            {!showCandidates && hasTeamView && !hasNoTeamMembers ? (
              <Card className="flex-1 flex items-center justify-center">
                <CardContent className="text-center">
                  <Users className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
                  <h3 className="text-lg font-semibold mb-2">Select a Team Member</h3>
                  <p className="text-muted-foreground max-w-sm">
                    Choose a team member from the list to view their candidates and job matches
                  </p>
                </CardContent>
              </Card>
            ) : !selectedCandidateId ? (
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

                      {/* View Toggle */}
                      <div className="flex items-center border rounded-md">
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Button
                              variant={viewMode === 'grid' ? 'secondary' : 'ghost'}
                              size="sm"
                              className="h-8 px-2 rounded-r-none"
                              onClick={() => setViewMode('grid')}
                            >
                              <LayoutGrid className="h-4 w-4" />
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent>Grid View</TooltipContent>
                        </Tooltip>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Button
                              variant={viewMode === 'list' ? 'secondary' : 'ghost'}
                              size="sm"
                              className="h-8 px-2 rounded-l-none border-l"
                              onClick={() => setViewMode('list')}
                            >
                              <List className="h-4 w-4" />
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent>List View</TooltipContent>
                        </Tooltip>
                      </div>

                      {/* Filter Popover */}
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

                          {/* Grade Filter */}
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

                          {/* Platform Filter */}
                          {availablePlatforms.length > 0 && (
                            <div className="p-3 border-b">
                              <h5 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
                                Platform
                              </h5>
                              <div className="space-y-2 max-h-40 overflow-y-auto">
                                {availablePlatforms.map((platform) => (
                                  <div key={platform} className="flex items-center space-x-2">
                                    <Checkbox
                                      id={`platform-${platform}`}
                                      checked={selectedPlatforms.includes(platform.toLowerCase())}
                                      onCheckedChange={() => togglePlatform(platform.toLowerCase())}
                                    />
                                    <label
                                      htmlFor={`platform-${platform}`}
                                      className="flex-1 text-sm font-medium leading-none cursor-pointer capitalize"
                                    >
                                      {platform}
                                    </label>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Source Filter */}
                          {availableSources.length > 1 && (
                            <div className="p-3">
                              <h5 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
                                Source
                              </h5>
                              <div className="flex flex-wrap gap-1.5">
                                {[
                                  { value: 'all', label: 'All' },
                                  { value: 'scraped', label: 'Scraped' },
                                  { value: 'email', label: 'Email' },
                                ].map((source) => {
                                  const isSelected = selectedSource === source.value;
                                  return (
                                    <button
                                      key={source.value}
                                      onClick={() => {
                                        setSelectedSource(source.value as 'all' | 'email' | 'scraped');
                                        setCurrentPage(1);
                                      }}
                                      className={`px-2.5 py-1 text-xs font-medium rounded-md border transition-colors flex items-center gap-1.5 ${
                                        isSelected
                                          ? source.value === 'email'
                                            ? 'bg-purple-100 text-purple-700 border-purple-300'
                                            : source.value === 'scraped'
                                            ? 'bg-blue-100 text-blue-700 border-blue-300'
                                            : 'bg-slate-100 text-slate-700 border-slate-300'
                                          : 'bg-background hover:bg-muted border-border'
                                      }`}
                                    >
                                      {source.value === 'email' && <Mail className="h-3 w-3" />}
                                      {source.value === 'scraped' && <Globe className="h-3 w-3" />}
                                      {source.label}
                                    </button>
                                  );
                                })}
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

                {/* Job Cards/List */}
                <div className="flex-1 overflow-auto p-4">
                  {loadingMatches ? (
                    viewMode === 'grid' ? (
                      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
                        {[1, 2, 3, 4].map((i) => (
                          <Skeleton key={i} className="h-64 w-full rounded-lg" />
                        ))}
                      </div>
                    ) : (
                      <div className="border rounded-lg">
                        {[1, 2, 3, 4, 5].map((i) => (
                          <Skeleton key={i} className="h-16 w-full border-b last:border-b-0" />
                        ))}
                      </div>
                    )
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
                  ) : viewMode === 'grid' ? (
                    <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
                      {matches.map(renderJobCard)}
                    </div>
                  ) : (
                    <div className="border rounded-lg bg-background">
                      {/* List Header */}
                      <div className="flex items-center gap-4 px-4 py-2 border-b bg-muted/50 text-xs font-medium text-muted-foreground">
                        <div className="w-14 flex-shrink-0 text-center">Grade</div>
                        <div className="flex-1">Job Details</div>
                        <div className="w-28 flex-shrink-0 text-right">Salary</div>
                        <div className="w-24 flex-shrink-0 text-center">Skills</div>
                        <div className="w-24 flex-shrink-0 text-right">Posted</div>
                        <div className="w-28 flex-shrink-0 text-right">Actions</div>
                      </div>
                      {matches.map(renderJobRow)}
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
