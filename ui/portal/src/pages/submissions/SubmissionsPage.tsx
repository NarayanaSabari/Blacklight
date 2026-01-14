/**
 * Submissions Page
 * View and manage candidate submissions to job postings
 */

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { ManualSubmissionDialog } from '@/components/ManualSubmissionDialog';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
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
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Send,
  Search,
  AlertCircle,
  ChevronRight,
  ChevronLeft,
  ChevronsLeft,
  ChevronsRight,
  Building2,
  User,
  Briefcase,
  Clock,
  DollarSign,
  MoreHorizontal,
  Eye,
  Edit,
  Trash2,
  Calendar,
  Flame,
  Filter,
  TrendingUp,
  CheckCircle2,
  XCircle,
  PauseCircle,
  Plus,
  ExternalLink,
} from 'lucide-react';
import { submissionApi } from '@/lib/submissionApi';
import { format, formatDistanceToNow } from 'date-fns';
import type { Submission, SubmissionStatus, PriorityLevel } from '@/types/submission';
import {
  SUBMISSION_STATUSES,
  PRIORITY_LEVELS,
  STATUS_LABELS,
  STATUS_COLORS,
  PRIORITY_COLORS,
} from '@/types/submission';

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

// Status icons for quick visual identification
const STATUS_ICONS: Record<SubmissionStatus, React.ReactNode> = {
  SUBMITTED: <Send className="h-3.5 w-3.5" />,
  CLIENT_REVIEW: <Eye className="h-3.5 w-3.5" />,
  INTERVIEW_SCHEDULED: <Calendar className="h-3.5 w-3.5" />,
  INTERVIEWED: <CheckCircle2 className="h-3.5 w-3.5" />,
  OFFERED: <TrendingUp className="h-3.5 w-3.5" />,
  PLACED: <CheckCircle2 className="h-3.5 w-3.5" />,
  REJECTED: <XCircle className="h-3.5 w-3.5" />,
  WITHDRAWN: <XCircle className="h-3.5 w-3.5" />,
  ON_HOLD: <PauseCircle className="h-3.5 w-3.5" />,
};

export function SubmissionsPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  // Manual submission dialog state
  const [manualSubmissionOpen, setManualSubmissionOpen] = useState(false);

  // Filter state from URL params
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<SubmissionStatus | 'all'>(
    (searchParams.get('status') as SubmissionStatus) || 'all'
  );
  const [priorityFilter, setPriorityFilter] = useState<PriorityLevel | 'all'>(
    (searchParams.get('priority') as PriorityLevel) || 'all'
  );
  const [isActiveFilter, setIsActiveFilter] = useState<boolean | undefined>(
    searchParams.get('active') === 'true' ? true : undefined
  );
  const [submitterFilter, setSubmitterFilter] = useState<string>(
    searchParams.get('submitter') || 'all'
  );
  const [currentPage, setCurrentPage] = useState(
    parseInt(searchParams.get('page') || '1', 10)
  );
  const [pageSize, setPageSize] = useState(
    parseInt(searchParams.get('per_page') || '25', 10)
  );

  // Update URL when filters change
  const updateFilters = (updates: Record<string, string | undefined>) => {
    const newParams = new URLSearchParams(searchParams);
    Object.entries(updates).forEach(([key, value]) => {
      if (value && value !== 'all') {
        newParams.set(key, value);
      } else {
        newParams.delete(key);
      }
    });
    setSearchParams(newParams);
  };

  // Fetch submissions
  const {
    data: submissionsData,
    isLoading,
    error,
  } = useQuery({
    queryKey: [
      'submissions',
      statusFilter,
      priorityFilter,
      isActiveFilter,
      submitterFilter,
      currentPage,
      pageSize,
    ],
    queryFn: () =>
      submissionApi.listSubmissions({
        status: statusFilter !== 'all' ? statusFilter : undefined,
        priority: priorityFilter !== 'all' ? priorityFilter : undefined,
        is_active: isActiveFilter,
        submitted_by_user_id: submitterFilter !== 'all' ? parseInt(submitterFilter, 10) : undefined,
        page: currentPage,
        per_page: pageSize,
        sort_by: 'submitted_at',
        sort_order: 'desc',
      }),
    staleTime: 0,
  });

  // Fetch submitters for filter dropdown
  const { data: submittersData } = useQuery({
    queryKey: ['submission-submitters'],
    queryFn: () => submissionApi.getSubmitters(),
    staleTime: 300000, // 5 minutes
  });

  // Fetch stats
  const { data: statsData } = useQuery({
    queryKey: ['submission-stats'],
    queryFn: () => submissionApi.getStats(),
    staleTime: 60000, // 1 minute
  });

  const submissions = submissionsData?.items || [];
  const totalItems = submissionsData?.total || 0;
  const totalPages = submissionsData?.pages || 0;

  // Filter submissions by search (client-side for responsiveness)
  const filteredSubmissions = submissions.filter((submission) => {
    if (!searchQuery) return true;
    const searchLower = searchQuery.toLowerCase();
    const candidateName =
      `${submission.candidate?.first_name || ''} ${submission.candidate?.last_name || ''}`.toLowerCase();
    const jobTitle = submission.is_external_job 
      ? submission.external_job_title?.toLowerCase() || ''
      : submission.job?.title?.toLowerCase() || '';
    const company = submission.is_external_job
      ? submission.external_job_company?.toLowerCase() || ''
      : submission.job?.company?.toLowerCase() || '';
    const vendor = submission.vendor_company?.toLowerCase() || '';
    return (
      candidateName.includes(searchLower) ||
      jobTitle.includes(searchLower) ||
      company.includes(searchLower) ||
      vendor.includes(searchLower)
    );
  });

  const handleRowClick = (submission: Submission) => {
    navigate(`/submissions/${submission.id}`);
  };

  const handleStatusFilterChange = (value: string) => {
    const newStatus = value as SubmissionStatus | 'all';
    setStatusFilter(newStatus);
    setCurrentPage(1);
    updateFilters({ status: value, page: '1' });
  };

  const handlePriorityFilterChange = (value: string) => {
    const newPriority = value as PriorityLevel | 'all';
    setPriorityFilter(newPriority);
    setCurrentPage(1);
    updateFilters({ priority: value, page: '1' });
  };

  const handleActiveFilterChange = (value: string) => {
    const newActive = value === 'active' ? true : value === 'closed' ? false : undefined;
    setIsActiveFilter(newActive);
    setCurrentPage(1);
    updateFilters({ 
      active: newActive === true ? 'true' : newActive === false ? 'false' : undefined,
      page: '1' 
    });
  };

  const handleSubmitterFilterChange = (value: string) => {
    setSubmitterFilter(value);
    setCurrentPage(1);
    updateFilters({ submitter: value, page: '1' });
  };

  const handlePageChange = (newPage: number) => {
    setCurrentPage(newPage);
    updateFilters({ page: newPage.toString() });
  };

  const handlePageSizeChange = (value: string) => {
    const newSize = parseInt(value, 10);
    setPageSize(newSize);
    setCurrentPage(1);
    updateFilters({ per_page: value, page: '1' });
  };

  const formatRate = (rate?: number, type?: string) => {
    if (!rate) return '-';
    return `$${rate.toFixed(0)}/${type?.toLowerCase() === 'hourly' ? 'hr' : type?.toLowerCase() || 'hr'}`;
  };

  const getMarginColor = (marginPct?: number) => {
    if (!marginPct) return 'text-muted-foreground';
    if (marginPct >= 30) return 'text-green-600';
    if (marginPct >= 20) return 'text-blue-600';
    if (marginPct >= 10) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <TooltipProvider>
      <div className="space-y-6">

        {/* Stats Cards */}
        {statsData && (
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            <Card>
              <CardContent className="pt-4">
                <div className="text-2xl font-bold">{statsData.total}</div>
                <p className="text-xs text-muted-foreground">Total Submissions</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4">
                <div className="text-2xl font-bold text-blue-600">
                  {statsData.submitted_this_week}
                </div>
                <p className="text-xs text-muted-foreground">This Week</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4">
                <div className="text-2xl font-bold text-purple-600">
                  {statsData.interviews_scheduled}
                </div>
                <p className="text-xs text-muted-foreground">Interviews</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4">
                <div className="text-2xl font-bold text-green-600">
                  {statsData.placements_this_month}
                </div>
                <p className="text-xs text-muted-foreground">Placements (Month)</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4">
                <div className="text-2xl font-bold text-emerald-600">
                  {statsData.interview_rate?.toFixed(0) || 0}%
                </div>
                <p className="text-xs text-muted-foreground">Interview Rate</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4">
                <div className="text-2xl font-bold text-amber-600">
                  {statsData.placement_rate?.toFixed(0) || 0}%
                </div>
                <p className="text-xs text-muted-foreground">Placement Rate</p>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Filters and Table */}
        <Card>
          <CardHeader className="pb-4">
            <div className="flex flex-col md:flex-row gap-4 items-start md:items-center justify-between">
              {/* Search */}
              <div className="relative w-full md:w-80">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search candidates, jobs, companies..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-8"
                />
              </div>

              {/* Filters */}
              <div className="flex flex-wrap gap-2">
                {/* Add Submission Button */}
                <Button onClick={() => setManualSubmissionOpen(true)}>
                  <Plus className="h-4 w-4 mr-2" />
                  Add Submission
                </Button>

                {/* Status Filter */}
                <Select value={statusFilter} onValueChange={handleStatusFilterChange}>
                  <SelectTrigger className="w-[160px]">
                    <Filter className="h-4 w-4 mr-2" />
                    <SelectValue placeholder="Status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Statuses</SelectItem>
                    {SUBMISSION_STATUSES.map((status) => (
                      <SelectItem key={status} value={status}>
                        <div className="flex items-center gap-2">
                          {STATUS_ICONS[status]}
                          {STATUS_LABELS[status]}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                {/* Priority Filter */}
                <Select value={priorityFilter} onValueChange={handlePriorityFilterChange}>
                  <SelectTrigger className="w-[130px]">
                    <SelectValue placeholder="Priority" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Priorities</SelectItem>
                    {PRIORITY_LEVELS.map((priority) => (
                      <SelectItem key={priority} value={priority}>
                        {priority}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                {/* Active/Closed Filter */}
                <Select
                  value={isActiveFilter === true ? 'active' : isActiveFilter === false ? 'closed' : 'all'}
                  onValueChange={handleActiveFilterChange}
                >
                  <SelectTrigger className="w-[120px]">
                    <SelectValue placeholder="State" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All</SelectItem>
                    <SelectItem value="active">Active</SelectItem>
                    <SelectItem value="closed">Closed</SelectItem>
                  </SelectContent>
                </Select>

                {/* Submitter/Recruiter Filter */}
                {submittersData && submittersData.submitters.length > 0 && (
                  <Select value={submitterFilter} onValueChange={handleSubmitterFilterChange}>
                    <SelectTrigger className="w-[180px]">
                      <User className="h-4 w-4 mr-2" />
                      <SelectValue placeholder="Submitted By" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Recruiters</SelectItem>
                      {submittersData.submitters.map((submitter) => (
                        <SelectItem key={submitter.id} value={submitter.id.toString()}>
                          <div className="flex items-center justify-between w-full">
                            <span>{submitter.first_name} {submitter.last_name}</span>
                            <Badge variant="secondary" className="ml-2 text-xs">
                              {submitter.submission_count}
                            </Badge>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              </div>
            </div>
          </CardHeader>

          <CardContent>
            {isLoading ? (
              <div className="space-y-3">
                {[1, 2, 3, 4, 5].map((i) => (
                  <Skeleton key={i} className="h-16 w-full" />
                ))}
              </div>
            ) : error ? (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  Failed to load submissions. Please try again.
                </AlertDescription>
              </Alert>
            ) : filteredSubmissions.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <Send className="h-12 w-12 text-muted-foreground mb-4" />
                <h3 className="text-lg font-medium mb-1">No Submissions Found</h3>
                <p className="text-muted-foreground text-sm max-w-sm">
                  {searchQuery || statusFilter !== 'all' || priorityFilter !== 'all' || submitterFilter !== 'all'
                    ? 'Try adjusting your filters or search query'
                    : 'Submit candidates to jobs to see them here'}
                </p>
              </div>
            ) : (
              <>
                {/* Table */}
                <div className="rounded-md border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-[200px]">Candidate</TableHead>
                        <TableHead className="w-[250px]">Job</TableHead>
                        <TableHead className="w-[120px]">Status</TableHead>
                        <TableHead className="w-[100px]">Priority</TableHead>
                        <TableHead className="w-[120px]">Rates</TableHead>
                        <TableHead className="w-[120px]">Submitted</TableHead>
                        <TableHead className="w-[50px]"></TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredSubmissions.map((submission) => (
                        <TableRow
                          key={submission.id}
                          className="cursor-pointer hover:bg-muted/50"
                          onClick={() => handleRowClick(submission)}
                        >
                          {/* Candidate */}
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                                <User className="h-4 w-4 text-primary" />
                              </div>
                              <div>
                                <p className="font-medium text-sm">
                                  {submission.candidate?.first_name}{' '}
                                  {submission.candidate?.last_name}
                                </p>
                                <p className="text-xs text-muted-foreground truncate max-w-[160px]">
                                  {submission.candidate?.current_title || 'No title'}
                                </p>
                              </div>
                            </div>
                          </TableCell>

                          {/* Job */}
                          <TableCell>
                            <div className="flex items-start gap-2">
                              {submission.is_external_job ? (
                                <ExternalLink className="h-4 w-4 text-purple-500 mt-0.5 flex-shrink-0" />
                              ) : (
                                <Briefcase className="h-4 w-4 text-muted-foreground mt-0.5 flex-shrink-0" />
                              )}
                              <div className="min-w-0">
                                <div className="flex items-center gap-1.5">
                                  <p className="font-medium text-sm truncate">
                                    {submission.is_external_job 
                                      ? submission.external_job_title 
                                      : submission.job?.title}
                                  </p>
                                  {submission.is_external_job && (
                                    <Badge variant="outline" className="text-[10px] px-1.5 py-0 bg-purple-50 text-purple-700 border-purple-200">
                                      External
                                    </Badge>
                                  )}
                                </div>
                                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                                  <Building2 className="h-3 w-3" />
                                  <span className="truncate">
                                    {submission.is_external_job 
                                      ? submission.external_job_company 
                                      : submission.job?.company}
                                  </span>
                                </div>
                              </div>
                            </div>
                          </TableCell>

                          {/* Status */}
                          <TableCell>
                            <Badge
                              className={`${STATUS_COLORS[submission.status]} text-xs`}
                            >
                              <span className="flex items-center gap-1">
                                {STATUS_ICONS[submission.status]}
                                {STATUS_LABELS[submission.status]}
                              </span>
                            </Badge>
                          </TableCell>

                          {/* Priority */}
                          <TableCell>
                            <div className="flex items-center gap-1">
                              {submission.is_hot && (
                                <Tooltip>
                                  <TooltipTrigger>
                                    <Flame className="h-4 w-4 text-orange-500" />
                                  </TooltipTrigger>
                                  <TooltipContent>Hot submission</TooltipContent>
                                </Tooltip>
                              )}
                              <Badge
                                variant="outline"
                                className={`${PRIORITY_COLORS[submission.priority || 'MEDIUM']} text-xs`}
                              >
                                {submission.priority || 'MEDIUM'}
                              </Badge>
                            </div>
                          </TableCell>

                          {/* Rates */}
                          <TableCell>
                            <div className="text-sm">
                              <div className="flex items-center gap-1">
                                <DollarSign className="h-3 w-3 text-muted-foreground" />
                                <span>{formatRate(submission.bill_rate, submission.rate_type)}</span>
                              </div>
                              {submission.margin_percentage && (
                                <span
                                  className={`text-xs ${getMarginColor(submission.margin_percentage)}`}
                                >
                                  {submission.margin_percentage.toFixed(1)}% margin
                                </span>
                              )}
                            </div>
                          </TableCell>

                          {/* Submitted Date */}
                          <TableCell>
                            <Tooltip>
                              <TooltipTrigger>
                                <div className="flex items-center gap-1 text-sm text-muted-foreground">
                                  <Clock className="h-3 w-3" />
                                  <span>
                                    {formatDistanceToNow(new Date(submission.submitted_at), {
                                      addSuffix: true,
                                    })}
                                  </span>
                                </div>
                              </TooltipTrigger>
                              <TooltipContent>
                                {format(new Date(submission.submitted_at), 'PPpp')}
                              </TooltipContent>
                            </Tooltip>
                          </TableCell>

                          {/* Actions */}
                          <TableCell>
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="h-8 w-8"
                                  onClick={(e) => e.stopPropagation()}
                                >
                                  <MoreHorizontal className="h-4 w-4" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                <DropdownMenuLabel>Actions</DropdownMenuLabel>
                                <DropdownMenuSeparator />
                                <DropdownMenuItem
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    navigate(`/submissions/${submission.id}`);
                                  }}
                                >
                                  <Eye className="h-4 w-4 mr-2" />
                                  View Details
                                </DropdownMenuItem>
                                <DropdownMenuItem
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    navigate(`/submissions/${submission.id}/edit`);
                                  }}
                                >
                                  <Edit className="h-4 w-4 mr-2" />
                                  Edit
                                </DropdownMenuItem>
                                <DropdownMenuItem
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    navigate(`/candidates/${submission.candidate_id}`);
                                  }}
                                >
                                  <User className="h-4 w-4 mr-2" />
                                  View Candidate
                                </DropdownMenuItem>
                                <DropdownMenuSeparator />
                                <DropdownMenuItem
                                  className="text-destructive"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    // TODO: Implement delete confirmation
                                  }}
                                >
                                  <Trash2 className="h-4 w-4 mr-2" />
                                  Delete
                                </DropdownMenuItem>
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>

                {/* Pagination */}
                <div className="flex items-center justify-between mt-4">
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <span>Show</span>
                    <Select
                      value={pageSize.toString()}
                      onValueChange={handlePageSizeChange}
                    >
                      <SelectTrigger className="w-[70px] h-8">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {PAGE_SIZE_OPTIONS.map((size) => (
                          <SelectItem key={size} value={size.toString()}>
                            {size}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <span>
                      Showing {(currentPage - 1) * pageSize + 1}-
                      {Math.min(currentPage * pageSize, totalItems)} of {totalItems}
                    </span>
                  </div>

                  <div className="flex items-center gap-1">
                    <Button
                      variant="outline"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => handlePageChange(1)}
                      disabled={currentPage === 1}
                    >
                      <ChevronsLeft className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => handlePageChange(currentPage - 1)}
                      disabled={currentPage === 1}
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <span className="px-3 text-sm">
                      Page {currentPage} of {totalPages || 1}
                    </span>
                    <Button
                      variant="outline"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => handlePageChange(currentPage + 1)}
                      disabled={currentPage >= totalPages}
                    >
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => handlePageChange(totalPages)}
                      disabled={currentPage >= totalPages}
                    >
                      <ChevronsRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* Manual Submission Dialog */}
        <ManualSubmissionDialog
          open={manualSubmissionOpen}
          onOpenChange={setManualSubmissionOpen}
        />
      </div>
    </TooltipProvider>
  );
}
