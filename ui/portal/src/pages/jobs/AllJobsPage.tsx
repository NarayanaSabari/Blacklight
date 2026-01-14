/**
 * All Jobs Page - Unified Job Browser
 * Shows all jobs (scraped + email-sourced) with source filtering.
 * 
 * Features:
 * - Source tabs: All, Scraped, Email
 * - Platform filter (Indeed, Dice, Email, etc.)
 * - Search and status filters
 * - Shows sourced_by info for email jobs
 * - Card grid layout with pagination
 */

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  Mail,
  Briefcase,
  Search,
  ExternalLink,
  Clock,
  User,
  MapPin,
  DollarSign,
  Building2,
  Globe,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Filter,
  Database,
  Inbox,
  LayoutGrid,
  List,
} from 'lucide-react';
import { jobPostingApi, type JobSourceFilter, type JobPostingWithSource } from '@/lib/jobPostingApi';
import { format } from 'date-fns';

const PAGE_SIZE_OPTIONS = [12, 24, 48, 96];

type ViewMode = 'list' | 'grid';

export function AllJobsPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  
  // Get initial values from URL
  const initialSource = (searchParams.get('source') as JobSourceFilter) || 'all';
  const initialPlatform = searchParams.get('platform') || '';
  const initialSearch = searchParams.get('search') || '';
  const initialPage = parseInt(searchParams.get('page') || '1', 10);
  
  // State
  const [source, setSource] = useState<JobSourceFilter>(initialSource);
  const [platform, setPlatform] = useState(initialPlatform);
  const [searchQuery, setSearchQuery] = useState(initialSearch);
  const [page, setPage] = useState(initialPage);
  const [perPage, setPerPage] = useState(24);
  const [viewMode, setViewMode] = useState<ViewMode>('list');

  // Update URL when filters change
  const updateUrl = (newParams: Record<string, string | undefined>) => {
    const params = new URLSearchParams(searchParams);
    Object.entries(newParams).forEach(([key, value]) => {
      if (value) {
        params.set(key, value);
      } else {
        params.delete(key);
      }
    });
    setSearchParams(params, { replace: true });
  };

  // Fetch jobs
  const { data: jobsData, isLoading: jobsLoading } = useQuery({
    queryKey: ['all-jobs', source, platform, searchQuery, page, perPage],
    queryFn: () =>
      jobPostingApi.listJobPostings({
        source,
        platform: platform || undefined,
        search: searchQuery || undefined,
        page,
        per_page: perPage,
        sort_by: 'created_at',
        sort_order: 'desc',
      }),
    staleTime: 0,
  });

  // Fetch job sources for filter dropdown
  const { data: sourcesData } = useQuery({
    queryKey: ['job-sources'],
    queryFn: () => jobPostingApi.getSources(),
    staleTime: 60000,
  });

  // Fetch statistics
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['job-statistics'],
    queryFn: () => jobPostingApi.getStatistics(),
    staleTime: 60000,
  });

  // Handlers
  const handleSourceChange = (newSource: JobSourceFilter) => {
    setSource(newSource);
    setPage(1);
    updateUrl({ source: newSource === 'all' ? undefined : newSource, page: undefined });
  };

  const handlePlatformChange = (newPlatform: string) => {
    setPlatform(newPlatform === 'all' ? '' : newPlatform);
    setPage(1);
    updateUrl({ platform: newPlatform === 'all' ? undefined : newPlatform, page: undefined });
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    updateUrl({ search: searchQuery || undefined, page: undefined });
  };

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
    updateUrl({ page: newPage > 1 ? String(newPage) : undefined });
  };

  // Format helpers
  const formatDate = (dateStr: string | null | undefined) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    // Check if date has time component (not midnight UTC)
    const hasTime = date.getHours() !== 0 || date.getMinutes() !== 0 || date.getSeconds() !== 0;
    if (hasTime) {
      return format(date, 'MMM dd, yyyy h:mm a');
    }
    return format(date, 'MMM dd, yyyy');
  };

  const formatSalary = (job: JobPostingWithSource) => {
    if (job.salary_range) return job.salary_range;
    if (job.salary_min && job.salary_max) {
      return `$${(job.salary_min / 1000).toFixed(0)}k - $${(job.salary_max / 1000).toFixed(0)}k`;
    }
    if (job.salary_min) return `$${(job.salary_min / 1000).toFixed(0)}k+`;
    if (job.salary_max) return `Up to $${(job.salary_max / 1000).toFixed(0)}k`;
    return '-';
  };

  const getStatusBadge = (status: string) => {
    switch (status?.toUpperCase()) {
      case 'ACTIVE':
        return <Badge className="bg-green-100 text-green-700 hover:bg-green-100">Active</Badge>;
      case 'EXPIRED':
        return <Badge className="bg-gray-100 text-gray-700 hover:bg-gray-100">Expired</Badge>;
      case 'CLOSED':
        return <Badge className="bg-red-100 text-red-700 hover:bg-red-100">Closed</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const getSourceBadge = (job: JobPostingWithSource) => {
    if (job.is_email_sourced) {
      return (
        <Badge className="bg-purple-100 text-purple-700 border-purple-200">
          <Mail className="h-3 w-3 mr-1" />
          Email
        </Badge>
      );
    }
    return (
      <Badge className="bg-blue-100 text-blue-700 border-blue-200">
        <Globe className="h-3 w-3 mr-1" />
        {job.platform || 'Scraped'}
      </Badge>
    );
  };

  const totalPages = jobsData?.pages || 0;
  const jobs = jobsData?.jobs || [];

  return (
    <TooltipProvider>
      <div className="space-y-6">
        {/* Header Card */}
        <Card>
          <CardHeader className="border-b bg-slate-50/50">
            <div className="flex flex-col gap-4">
              {/* Stats Row */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-6">
                  <div className="flex items-center gap-2">
                    <div className="p-1.5 rounded-md bg-blue-100">
                      <Briefcase className="h-4 w-4 text-blue-600" />
                    </div>
                    <div>
                      <span className="text-2xl font-bold">
                        {statsLoading ? '-' : stats?.total_jobs || 0}
                      </span>
                      <span className="text-sm text-muted-foreground ml-1.5">Total Jobs</span>
                    </div>
                  </div>
                  <div className="h-8 w-px bg-border" />
                  <div className="flex items-center gap-3 text-sm">
                    <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
                      <Database className="h-3 w-3 mr-1" />
                      {stats?.scraped_jobs || 0} Scraped
                    </Badge>
                    <Badge variant="outline" className="bg-purple-50 text-purple-700 border-purple-200">
                      <Mail className="h-3 w-3 mr-1" />
                      {stats?.email_jobs || 0} Email
                    </Badge>
                    <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                      <Building2 className="h-3 w-3 mr-1" />
                      {stats?.unique_companies || 0} Companies
                    </Badge>
                  </div>
                </div>
              </div>

              {/* Filters Row */}
              <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                {/* Source Tabs */}
                <Tabs value={source} onValueChange={(v) => handleSourceChange(v as JobSourceFilter)}>
                  <TabsList className="bg-white border">
                    <TabsTrigger value="all" className="gap-1.5">
                      <Briefcase className="h-3.5 w-3.5" />
                      All Jobs
                    </TabsTrigger>
                    <TabsTrigger value="scraped" className="gap-1.5">
                      <Database className="h-3.5 w-3.5" />
                      Scraped
                    </TabsTrigger>
                    <TabsTrigger value="email" className="gap-1.5">
                      <Mail className="h-3.5 w-3.5" />
                      From Email
                    </TabsTrigger>
                  </TabsList>
                </Tabs>

                {/* Search and Platform Filter */}
                <div className="flex items-center gap-3">
                  <form onSubmit={handleSearch} className="flex gap-2">
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                      <Input
                        placeholder="Search jobs..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="pl-9 w-64 bg-white"
                      />
                    </div>
                    <Button type="submit" variant="secondary" size="icon">
                      <Search className="h-4 w-4" />
                    </Button>
                  </form>
                  
                  {sourcesData && sourcesData.sources.length > 0 && (
                    <Select 
                      value={platform || 'all'} 
                      onValueChange={handlePlatformChange}
                    >
                      <SelectTrigger className="w-40 bg-white">
                        <Filter className="h-4 w-4 mr-2" />
                        <SelectValue placeholder="Platform" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Platforms</SelectItem>
                        {sourcesData.sources.map((src) => (
                          <SelectItem key={src.platform} value={src.platform}>
                            {src.display_name} ({src.count})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}

                  {/* View Mode Toggle */}
                  <div className="flex items-center border rounded-md bg-white">
                    <Button
                      variant={viewMode === 'list' ? 'secondary' : 'ghost'}
                      size="icon"
                      className="h-9 w-9 rounded-r-none"
                      onClick={() => setViewMode('list')}
                    >
                      <List className="h-4 w-4" />
                    </Button>
                    <Button
                      variant={viewMode === 'grid' ? 'secondary' : 'ghost'}
                      size="icon"
                      className="h-9 w-9 rounded-l-none"
                      onClick={() => setViewMode('grid')}
                    >
                      <LayoutGrid className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </CardHeader>

          <CardContent className="p-6">
            {/* Jobs Display */}
            {jobsLoading ? (
              viewMode === 'grid' ? (
                <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
                  {[1, 2, 3, 4, 5, 6].map((i) => (
                    <Skeleton key={i} className="h-56 w-full rounded-lg" />
                  ))}
                </div>
              ) : (
                <div className="space-y-3">
                  {[1, 2, 3, 4, 5, 6].map((i) => (
                    <Skeleton key={i} className="h-20 w-full rounded-lg" />
                  ))}
                </div>
              )
            ) : jobs.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <div className="p-4 rounded-full bg-slate-100 mb-4">
                  <Inbox className="h-12 w-12 text-slate-400" />
                </div>
                <h3 className="text-lg font-semibold text-slate-900 mb-2">No jobs found</h3>
                <p className="text-slate-600 max-w-sm">
                  {searchQuery || platform
                    ? 'Try adjusting your search query or filters'
                    : source === 'email'
                    ? 'No email-sourced jobs yet. Connect your email in Settings.'
                    : 'No jobs available at the moment.'}
                </p>
              </div>
            ) : (
              <>
                {/* List View */}
                {viewMode === 'list' ? (
                  <div className="space-y-3">
                    {jobs.map((job) => (
                      <div
                        key={job.id}
                        className="flex items-center gap-4 p-4 border rounded-lg cursor-pointer hover:shadow-md hover:border-primary/50 transition-all bg-white group"
                        onClick={() => navigate(`/jobs/${job.id}`)}
                      >
                        {/* Job Info */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-start gap-3">
                            <div className="flex-1 min-w-0">
                              <h3 className="font-semibold text-base group-hover:text-primary transition-colors truncate">
                                {job.title}
                              </h3>
                              <div className="flex items-center gap-4 mt-1 text-sm text-muted-foreground">
                                <span className="flex items-center gap-1.5 truncate">
                                  <Building2 className="h-4 w-4 flex-shrink-0" />
                                  {job.company || 'Unknown Company'}
                                </span>
                                <span className="flex items-center gap-1.5 truncate">
                                  <MapPin className="h-4 w-4 flex-shrink-0" />
                                  {job.location || 'Not specified'}
                                </span>
                                <span className="flex items-center gap-1.5">
                                  <DollarSign className="h-4 w-4 flex-shrink-0" />
                                  {formatSalary(job)}
                                </span>
                                <span className="flex items-center gap-1.5">
                                  <Clock className="h-4 w-4 flex-shrink-0" />
                                  {formatDate(job.posted_date || job.created_at)}
                                </span>
                              </div>
                            </div>
                          </div>

                          {/* Skills Row */}
                          {job.skills && job.skills.length > 0 && (
                            <div className="flex flex-wrap gap-1.5 mt-2">
                              {job.skills.slice(0, 6).map((skill, i) => (
                                <Badge key={i} variant="secondary" className="text-xs font-normal">
                                  {skill}
                                </Badge>
                              ))}
                              {job.skills.length > 6 && (
                                <Badge variant="outline" className="text-xs">
                                  +{job.skills.length - 6}
                                </Badge>
                              )}
                            </div>
                          )}
                        </div>

                        {/* Email Sourced Info */}
                        {job.is_email_sourced && job.sourced_by && (
                          <div className="hidden md:flex items-center gap-2 text-sm px-3 py-1.5 bg-purple-50 rounded-md">
                            <User className="h-4 w-4 text-purple-500" />
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <span className="font-medium text-purple-700 truncate max-w-[120px]">
                                  {job.sourced_by.first_name || job.sourced_by.last_name 
                                    ? `${job.sourced_by.first_name || ''} ${job.sourced_by.last_name || ''}`.trim()
                                    : job.sourced_by.email}
                                </span>
                              </TooltipTrigger>
                              <TooltipContent>
                                {job.sourced_by.email}
                              </TooltipContent>
                            </Tooltip>
                          </div>
                        )}

                        {/* Badges */}
                        <div className="flex items-center gap-2 flex-shrink-0">
                          {job.is_remote && (
                            <Badge variant="secondary" className="text-xs">
                              Remote
                            </Badge>
                          )}
                          {getStatusBadge(job.status)}
                          {getSourceBadge(job)}
                        </div>

                        {/* Actions */}
                        <div className="flex items-center gap-1 flex-shrink-0">
                          {job.job_url && (
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-8 w-8 p-0"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    window.open(job.job_url!, '_blank');
                                  }}
                                >
                                  <ExternalLink className="h-4 w-4" />
                                </Button>
                              </TooltipTrigger>
                              <TooltipContent>Open original posting</TooltipContent>
                            </Tooltip>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  /* Grid View */
                  <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
                    {jobs.map((job) => (
                      <Card
                        key={job.id}
                        className="cursor-pointer hover:shadow-lg transition-all hover:border-primary/50 group border"
                        onClick={() => navigate(`/jobs/${job.id}`)}
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
                                  {job.company || 'Unknown Company'}
                                </span>
                              </div>
                            </div>
                            <div className="flex flex-col items-end gap-1.5 flex-shrink-0">
                              {getStatusBadge(job.status)}
                              {getSourceBadge(job)}
                            </div>
                          </div>
                        </CardHeader>

                        <CardContent className="pt-0 space-y-3">
                          {/* Job Details Grid */}
                          <div className="grid grid-cols-2 gap-2 text-sm">
                            <div className="flex items-center gap-2">
                              <MapPin className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                              <span className="truncate">{job.location || 'Not specified'}</span>
                            </div>
                            <div className="flex items-center gap-2">
                              <DollarSign className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                              <span className="truncate">{formatSalary(job)}</span>
                            </div>
                            {job.is_remote && (
                              <Badge variant="secondary" className="text-xs w-fit">
                                Remote
                              </Badge>
                            )}
                            <div className="flex items-center gap-2">
                              <Clock className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                              <span className="truncate">{formatDate(job.posted_date || job.created_at)}</span>
                            </div>
                          </div>

                          {/* Sourced By (for email jobs) */}
                          {job.is_email_sourced && job.sourced_by && (
                            <div className="flex items-center gap-2 pt-2 border-t text-sm">
                              <User className="h-4 w-4 text-purple-500 flex-shrink-0" />
                              <span className="text-muted-foreground">Sourced by:</span>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <span className="font-medium text-purple-700 truncate">
                                    {job.sourced_by.first_name || job.sourced_by.last_name 
                                      ? `${job.sourced_by.first_name || ''} ${job.sourced_by.last_name || ''}`.trim()
                                      : job.sourced_by.email}
                                  </span>
                                </TooltipTrigger>
                                <TooltipContent>
                                  {job.sourced_by.email}
                                </TooltipContent>
                              </Tooltip>
                            </div>
                          )}

                          {/* Skills */}
                          {job.skills && job.skills.length > 0 && (
                            <div className="flex flex-wrap gap-1.5 pt-2 border-t">
                              {job.skills.slice(0, 4).map((skill, i) => (
                                <Badge key={i} variant="secondary" className="text-xs font-normal">
                                  {skill}
                                </Badge>
                              ))}
                              {job.skills.length > 4 && (
                                <Badge variant="outline" className="text-xs">
                                  +{job.skills.length - 4}
                                </Badge>
                              )}
                            </div>
                          )}

                          {/* Footer */}
                          <div className="flex items-center justify-between pt-2 border-t">
                            <div className="text-xs text-muted-foreground">
                              {job.job_type || 'Full-time'}
                            </div>
                            {job.job_url && (
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-7 px-2"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      window.open(job.job_url!, '_blank');
                                    }}
                                  >
                                    <ExternalLink className="h-3.5 w-3.5" />
                                  </Button>
                                </TooltipTrigger>
                                <TooltipContent>Open original posting</TooltipContent>
                              </Tooltip>
                            )}
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                )}

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="flex items-center justify-between pt-6 mt-6 border-t">
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <span>Show</span>
                      <Select
                        value={perPage.toString()}
                        onValueChange={(v) => {
                          setPerPage(parseInt(v));
                          setPage(1);
                        }}
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
                        • {(page - 1) * perPage + 1}-{Math.min(page * perPage, jobsData?.total || 0)} of {jobsData?.total || 0}
                      </span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Button
                        variant="outline"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => handlePageChange(1)}
                        disabled={page === 1}
                      >
                        <ChevronsLeft className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="outline"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => handlePageChange(page - 1)}
                        disabled={page === 1}
                      >
                        <ChevronLeft className="h-4 w-4" />
                      </Button>
                      <span className="px-2 text-sm">
                        Page {page} of {totalPages}
                      </span>
                      <Button
                        variant="outline"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => handlePageChange(page + 1)}
                        disabled={page >= totalPages}
                      >
                        <ChevronRight className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="outline"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => handlePageChange(totalPages)}
                        disabled={page >= totalPages}
                      >
                        <ChevronsRight className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>

        {/* Email Jobs by Team Member Section */}
        {source === 'email' && stats?.email_by_user && stats.email_by_user.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <User className="h-5 w-5 text-purple-600" />
                Jobs by Team Member
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {stats.email_by_user.map((user) => (
                  <button
                    key={user.user_id}
                    onClick={() => {
                      // Filter by this user
                      navigate(`/all-jobs?source=email&sourced_by=${user.user_id}`);
                    }}
                    className="flex items-center gap-3 p-3 rounded-lg border hover:bg-slate-50 hover:border-primary/50 transition-colors text-left"
                  >
                    <div className="flex-shrink-0 h-10 w-10 rounded-full bg-gradient-to-br from-purple-500 to-blue-600 flex items-center justify-center text-white font-semibold">
                      {user.name.charAt(0).toUpperCase()}
                    </div>
                    <div className="min-w-0">
                      <p className="font-medium text-sm truncate">{user.name}</p>
                      <p className="text-xs text-slate-500">{user.jobs_count} jobs</p>
                    </div>
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </TooltipProvider>
  );
}
