/**
 * Jobs Page - View all job postings in the database
 */

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Briefcase,
  Search,
  ExternalLink,
  MapPin,
  Building2,
  DollarSign,
  Clock,
  Laptop,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  X,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Skeleton } from '@/components/ui/skeleton';
import { ScrollArea } from '@/components/ui/scroll-area';
import { jobPostingsApi } from '@/lib/dashboard-api';
import type { JobPosting, JobListParams } from '@/lib/dashboard-api';
import { formatDistanceToNow } from 'date-fns';

// Platform badge colors
const platformColors: Record<string, string> = {
  linkedin: 'bg-blue-500',
  indeed: 'bg-purple-500',
  monster: 'bg-green-500',
  dice: 'bg-red-500',
  glassdoor: 'bg-emerald-500',
  techfetch: 'bg-orange-500',
};

// Status badge variants
const statusVariants: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  ACTIVE: 'default',
  EXPIRED: 'secondary',
  CLOSED: 'destructive',
  FILLED: 'outline',
};

export function JobsPage() {
  const [filters, setFilters] = useState<JobListParams>({
    page: 1,
    perPage: 50,
    sortBy: 'created_at',
    sortOrder: 'desc',
  });
  const [searchInput, setSearchInput] = useState('');
  const [selectedJob, setSelectedJob] = useState<JobPosting | null>(null);
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);

  // Fetch jobs list
  const {
    data: jobsData,
    isLoading: jobsLoading,
    refetch: refetchJobs,
  } = useQuery({
    queryKey: ['jobs', filters],
    queryFn: () => jobPostingsApi.listJobs(filters),
  });

  // Fetch statistics
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['job-statistics'],
    queryFn: () => jobPostingsApi.getStatistics(),
  });

  // Fetch job detail when selected
  const { data: jobDetail, isLoading: detailLoading } = useQuery({
    queryKey: ['job-detail', selectedJob?.id],
    queryFn: () => (selectedJob ? jobPostingsApi.getJob(selectedJob.id) : null),
    enabled: !!selectedJob,
  });

  // Handle search
  const handleSearch = () => {
    setFilters((prev) => ({ ...prev, search: searchInput, page: 1 }));
  };

  // Handle filter changes
  const handleFilterChange = (key: keyof JobListParams, value: string | undefined) => {
    setFilters((prev) => ({
      ...prev,
      [key]: value === 'all' ? undefined : value,
      page: 1,
    }));
  };

  // Handle pagination
  const handlePageChange = (newPage: number) => {
    setFilters((prev) => ({ ...prev, page: newPage }));
  };

  // Clear all filters
  const clearFilters = () => {
    setFilters({
      page: 1,
      perPage: 50,
      sortBy: 'created_at',
      sortOrder: 'desc',
    });
    setSearchInput('');
  };

  // Open job detail dialog
  const openJobDetail = (job: JobPosting) => {
    setSelectedJob(job);
    setDetailDialogOpen(true);
  };

  // Format salary
  const formatSalary = (job: JobPosting) => {
    if (job.salaryRange) return job.salaryRange;
    if (job.salaryMin && job.salaryMax) {
      return `$${job.salaryMin.toLocaleString()} - $${job.salaryMax.toLocaleString()}`;
    }
    if (job.salaryMin) return `$${job.salaryMin.toLocaleString()}+`;
    return null;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Job Postings</h1>
          <p className="text-muted-foreground">
            View and manage all scraped job postings
          </p>
        </div>
        <Button onClick={() => refetchJobs()} variant="outline" size="sm">
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </div>

      {/* Statistics Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Jobs</CardTitle>
            <Briefcase className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <div className="text-2xl font-bold">
                {stats?.totalJobs.toLocaleString() ?? 0}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">This Week</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <div className="text-2xl font-bold">
                {stats?.jobsThisWeek.toLocaleString() ?? 0}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Remote Jobs</CardTitle>
            <Laptop className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <div className="text-2xl font-bold">
                {stats?.remoteJobs.toLocaleString() ?? 0}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Companies</CardTitle>
            <Building2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <div className="text-2xl font-bold">
                {stats?.uniqueCompanies.toLocaleString() ?? 0}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Platform breakdown */}
      {stats && Object.keys(stats.jobsByPlatform).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Jobs by Platform</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {Object.entries(stats.jobsByPlatform).map(([platform, count]) => (
                <Badge
                  key={platform}
                  variant="secondary"
                  className={`${platformColors[platform] || 'bg-gray-500'} text-white`}
                >
                  {platform}: {count.toLocaleString()}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-end">
            {/* Search */}
            <div className="flex-1">
              <label className="text-sm font-medium mb-2 block">Search</label>
              <div className="flex gap-2">
                <Input
                  placeholder="Search by title, company, or location..."
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  className="flex-1"
                />
                <Button onClick={handleSearch} size="icon">
                  <Search className="h-4 w-4" />
                </Button>
              </div>
            </div>

            {/* Platform filter */}
            <div className="w-full md:w-40">
              <label className="text-sm font-medium mb-2 block">Platform</label>
              <Select
                value={filters.platform || 'all'}
                onValueChange={(value) => handleFilterChange('platform', value)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="All platforms" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All platforms</SelectItem>
                  {jobsData?.filters.platforms.map((platform) => (
                    <SelectItem key={platform} value={platform}>
                      {platform}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Status filter */}
            <div className="w-full md:w-32">
              <label className="text-sm font-medium mb-2 block">Status</label>
              <Select
                value={filters.status || 'all'}
                onValueChange={(value) => handleFilterChange('status', value)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="All" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All</SelectItem>
                  {jobsData?.filters.statuses.map((status) => (
                    <SelectItem key={status} value={status}>
                      {status}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Location filter */}
            <div className="w-full md:w-48">
              <label className="text-sm font-medium mb-2 block">Location</label>
              <Select
                value={filters.location || 'all'}
                onValueChange={(value) => handleFilterChange('location', value)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="All locations" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All locations</SelectItem>
                  {jobsData?.filters.locations?.map((location) => (
                    <SelectItem key={location} value={location}>
                      {location}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Remote filter */}
            <div className="w-full md:w-32">
              <label className="text-sm font-medium mb-2 block">Remote</label>
              <Select
                value={filters.isRemote === undefined ? 'all' : filters.isRemote.toString()}
                onValueChange={(value) =>
                  handleFilterChange('isRemote', value === 'all' ? undefined : value)
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="All" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All</SelectItem>
                  <SelectItem value="true">Remote</SelectItem>
                  <SelectItem value="false">On-site</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Clear filters */}
            <Button variant="ghost" onClick={clearFilters} className="md:mb-0">
              <X className="mr-2 h-4 w-4" />
              Clear
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Jobs Table */}
      <Card>
        <CardContent className="p-0">
          {jobsLoading ? (
            <div className="p-6 space-y-4">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : jobsData?.jobs.length === 0 ? (
            <div className="p-12 text-center text-muted-foreground">
              <Briefcase className="mx-auto h-12 w-12 mb-4 opacity-50" />
              <p>No jobs found</p>
              <p className="text-sm mt-1">Try adjusting your filters</p>
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[300px]">Job Title</TableHead>
                    <TableHead>Company</TableHead>
                    <TableHead>Location</TableHead>
                    <TableHead>Platform</TableHead>
                    <TableHead>Salary</TableHead>
                    <TableHead>Posted</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {jobsData?.jobs.map((job) => (
                    <TableRow
                      key={job.id}
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => openJobDetail(job)}
                    >
                      <TableCell>
                        <div className="font-medium line-clamp-1">{job.title}</div>
                        {job.isRemote && (
                          <Badge variant="outline" className="mt-1 text-xs">
                            <Laptop className="mr-1 h-3 w-3" />
                            Remote
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <Building2 className="h-3 w-3 text-muted-foreground" />
                          <span className="line-clamp-1">{job.company}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        {job.location ? (
                          <div className="flex items-center gap-1">
                            <MapPin className="h-3 w-3 text-muted-foreground" />
                            <span className="line-clamp-1">{job.location}</span>
                          </div>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <Badge
                          className={`${platformColors[job.platform] || 'bg-gray-500'} text-white`}
                        >
                          {job.platform}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {formatSalary(job) ? (
                          <div className="flex items-center gap-1">
                            <DollarSign className="h-3 w-3 text-muted-foreground" />
                            <span className="text-sm">{formatSalary(job)}</span>
                          </div>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </TableCell>
                      <TableCell>
                        {job.postedDate ? (
                          <span className="text-sm text-muted-foreground">
                            {formatDistanceToNow(new Date(job.postedDate), {
                              addSuffix: true,
                            })}
                          </span>
                        ) : job.createdAt ? (
                          <span className="text-sm text-muted-foreground">
                            {formatDistanceToNow(new Date(job.createdAt), {
                              addSuffix: true,
                            })}
                          </span>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <Badge variant={statusVariants[job.status] || 'secondary'}>
                          {job.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={(e) => {
                            e.stopPropagation();
                            window.open(job.jobUrl, '_blank');
                          }}
                        >
                          <ExternalLink className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {/* Pagination */}
              <div className="flex items-center justify-between px-6 py-4 border-t">
                <div className="text-sm text-muted-foreground">
                  Showing {((filters.page || 1) - 1) * (filters.perPage || 50) + 1} to{' '}
                  {Math.min(
                    (filters.page || 1) * (filters.perPage || 50),
                    jobsData?.total || 0
                  )}{' '}
                  of {jobsData?.total.toLocaleString()} jobs
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handlePageChange((filters.page || 1) - 1)}
                    disabled={(filters.page || 1) <= 1}
                  >
                    <ChevronLeft className="h-4 w-4" />
                    Previous
                  </Button>
                  <span className="text-sm px-4">
                    Page {filters.page || 1} of {jobsData?.pages || 1}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handlePageChange((filters.page || 1) + 1)}
                    disabled={(filters.page || 1) >= (jobsData?.pages || 1)}
                  >
                    Next
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Job Detail Dialog */}
      <Dialog open={detailDialogOpen} onOpenChange={setDetailDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {detailLoading ? (
                <Skeleton className="h-6 w-64" />
              ) : (
                <>
                  {jobDetail?.title}
                  {jobDetail?.isRemote && (
                    <Badge variant="outline">
                      <Laptop className="mr-1 h-3 w-3" />
                      Remote
                    </Badge>
                  )}
                </>
              )}
            </DialogTitle>
            <DialogDescription>
              {detailLoading ? (
                <Skeleton className="h-4 w-48" />
              ) : (
                <span className="flex items-center gap-4">
                  <span className="flex items-center gap-1">
                    <Building2 className="h-4 w-4" />
                    {jobDetail?.company}
                  </span>
                  {jobDetail?.location && (
                    <span className="flex items-center gap-1">
                      <MapPin className="h-4 w-4" />
                      {jobDetail.location}
                    </span>
                  )}
                </span>
              )}
            </DialogDescription>
          </DialogHeader>

          {detailLoading ? (
            <div className="space-y-4">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-32 w-full" />
            </div>
          ) : jobDetail ? (
            <ScrollArea className="max-h-[60vh] pr-4">
              <div className="space-y-6">
                {/* Meta info */}
                <div className="flex flex-wrap gap-3">
                  <Badge
                    className={`${platformColors[jobDetail.platform] || 'bg-gray-500'} text-white`}
                  >
                    {jobDetail.platform}
                  </Badge>
                  <Badge variant={statusVariants[jobDetail.status] || 'secondary'}>
                    {jobDetail.status}
                  </Badge>
                  {formatSalary(jobDetail) && (
                    <Badge variant="outline">
                      <DollarSign className="mr-1 h-3 w-3" />
                      {formatSalary(jobDetail)}
                    </Badge>
                  )}
                  {jobDetail.jobType && (
                    <Badge variant="outline">{jobDetail.jobType}</Badge>
                  )}
                  {jobDetail.experienceRequired && (
                    <Badge variant="outline">{jobDetail.experienceRequired}</Badge>
                  )}
                </div>

                {/* Skills */}
                {jobDetail.skills && jobDetail.skills.length > 0 && (
                  <div>
                    <h4 className="font-medium mb-2">Skills</h4>
                    <div className="flex flex-wrap gap-1">
                      {jobDetail.skills.map((skill, idx) => (
                        <Badge key={idx} variant="secondary" className="text-xs">
                          {skill}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* Description */}
                <div>
                  <h4 className="font-medium mb-2">Description</h4>
                  <div className="text-sm text-muted-foreground whitespace-pre-wrap">
                    {jobDetail.description || jobDetail.snippet || 'No description available'}
                  </div>
                </div>

                {/* Requirements */}
                {jobDetail.requirements && (
                  <div>
                    <h4 className="font-medium mb-2">Requirements</h4>
                    <div className="text-sm text-muted-foreground whitespace-pre-wrap">
                      {jobDetail.requirements}
                    </div>
                  </div>
                )}

                {/* Meta info */}
                <div className="text-sm text-muted-foreground space-y-1 pt-4 border-t">
                  <p>
                    <strong>External ID:</strong> {jobDetail.externalJobId}
                  </p>
                  {jobDetail.postedDate && (
                    <p>
                      <strong>Posted:</strong> {new Date(jobDetail.postedDate).toLocaleDateString()}
                    </p>
                  )}
                  {jobDetail.importedAt && (
                    <p>
                      <strong>Imported:</strong>{' '}
                      {new Date(jobDetail.importedAt).toLocaleString()}
                    </p>
                  )}
                  {jobDetail.scraperName && (
                    <p>
                      <strong>Scraped by:</strong> {jobDetail.scraperName}
                    </p>
                  )}
                  {jobDetail.roleName && (
                    <p>
                      <strong>Role:</strong> {jobDetail.roleName}
                    </p>
                  )}
                </div>

                {/* Actions */}
                <div className="flex gap-2 pt-4">
                  <Button asChild>
                    <a href={jobDetail.jobUrl} target="_blank" rel="noopener noreferrer">
                      <ExternalLink className="mr-2 h-4 w-4" />
                      View Original
                    </a>
                  </Button>
                  {jobDetail.applyUrl && (
                    <Button variant="outline" asChild>
                      <a href={jobDetail.applyUrl} target="_blank" rel="noopener noreferrer">
                        Apply Now
                      </a>
                    </Button>
                  )}
                </div>
              </div>
            </ScrollArea>
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  );
}
