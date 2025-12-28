/**
 * Email Jobs Page
 * Displays jobs discovered from email integrations
 */

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

import { toast } from 'sonner';
import {
  Mail,
  Briefcase,
  Search,
  MoreVertical,
  Trash2,
  ExternalLink,
  Loader2,
  Clock,
  User,
  MapPin,
  DollarSign,
  Building2,
  CheckCircle2,
  Settings,
  RefreshCw,
} from 'lucide-react';
import {
  emailJobsApi,
  type EmailJob,
} from '@/lib/emailIntegrationApi';

export function EmailJobsPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [page, setPage] = useState(1);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [jobToDelete, setJobToDelete] = useState<EmailJob | null>(null);
  const perPage = 20;

  // Query for jobs
  const { data: jobsData, isLoading: jobsLoading } = useQuery({
    queryKey: ['email-jobs', page, searchQuery, statusFilter],
    queryFn: () =>
      emailJobsApi.list({
        page,
        per_page: perPage,
        search: searchQuery || undefined,
        status: statusFilter || undefined,
      }),
    staleTime: 0,
  });

  // Query for stats
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['email-jobs-stats'],
    queryFn: emailJobsApi.getStats,
    staleTime: 60000, // 1 minute
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (jobId: number) => emailJobsApi.delete(jobId),
    onSuccess: () => {
      toast.success('Job deleted');
      setDeleteDialogOpen(false);
      setJobToDelete(null);
      queryClient.invalidateQueries({ queryKey: ['email-jobs'] });
      queryClient.invalidateQueries({ queryKey: ['email-jobs-stats'] });
    },
    onError: (error: Error) => {
      toast.error('Failed to delete job', {
        description: error.message,
      });
    },
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
  };

  const handleDeleteClick = (job: EmailJob) => {
    setJobToDelete(job);
    setDeleteDialogOpen(true);
  };

  const confirmDelete = () => {
    if (jobToDelete) {
      deleteMutation.mutate(jobToDelete.id);
    }
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString();
  };

  const formatRate = (job: EmailJob) => {
    if (job.salary_range) {
      return job.salary_range;
    }
    if (job.salary_min && job.salary_max) {
      return `$${(job.salary_min / 1000).toFixed(0)}k - $${(job.salary_max / 1000).toFixed(0)}k/yr`;
    }
    if (job.salary_min) {
      return `$${(job.salary_min / 1000).toFixed(0)}k/yr`;
    }
    if (job.salary_max) {
      return `$${(job.salary_max / 1000).toFixed(0)}k/yr`;
    }
    return '-';
  };

  return (
    <div className="space-y-6">
      {/* Action Bar */}
      <div className="flex justify-end">
        <Link to="/settings">
          <Button variant="outline">
            <Settings className="mr-2 h-4 w-4" />
            Manage Integrations
          </Button>
        </Link>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-full bg-blue-100">
                <Briefcase className="h-6 w-6 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-slate-600">Total Jobs</p>
                <p className="text-2xl font-bold">
                  {statsLoading ? '-' : stats?.total_jobs || 0}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-full bg-green-100">
                <CheckCircle2 className="h-6 w-6 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-slate-600">Active Jobs</p>
                <p className="text-2xl font-bold">
                  {statsLoading ? '-' : stats?.by_status?.active || 0}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-full bg-purple-100">
                <Mail className="h-6 w-6 text-purple-600" />
              </div>
              <div>
                <p className="text-sm text-slate-600">Emails Scanned</p>
                <p className="text-2xl font-bold">
                  {statsLoading ? '-' : stats?.emails_processed || 0}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-full bg-orange-100">
                <RefreshCw className="h-6 w-6 text-orange-600" />
              </div>
              <div>
                <p className="text-sm text-slate-600">Conversion Rate</p>
                <p className="text-2xl font-bold">
                  {statsLoading ? '-' : `${stats?.conversion_rate || 0}%`}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Jobs Table */}
      <Card>
        <CardHeader>
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <CardTitle>Discovered Jobs</CardTitle>
            <div className="flex items-center gap-2">
              <form onSubmit={handleSearch} className="flex gap-2">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                  <Input
                    placeholder="Search jobs..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-9 w-64"
                  />
                </div>
                <Button type="submit" variant="secondary" size="icon">
                  <Search className="h-4 w-4" />
                </Button>
              </form>
              <Select value={statusFilter || "all"} onValueChange={(val) => setStatusFilter(val === "all" ? "" : val)}>
                <SelectTrigger className="w-36">
                  <SelectValue placeholder="All Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="expired">Expired</SelectItem>
                  <SelectItem value="closed">Closed</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {jobsLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
            </div>
          ) : !jobsData?.jobs.length ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Mail className="h-12 w-12 text-slate-300 mb-4" />
              <h3 className="text-lg font-semibold text-slate-900">No jobs found</h3>
              <p className="text-slate-600 max-w-sm mt-1">
                {searchQuery
                  ? 'Try adjusting your search query'
                  : 'Connect your email accounts in Settings to start discovering jobs'}
              </p>
              {!searchQuery && (
                <Link to="/settings" className="mt-4">
                  <Button>
                    <Settings className="mr-2 h-4 w-4" />
                    Go to Settings
                  </Button>
                </Link>
              )}
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Job Title</TableHead>
                    <TableHead>Company</TableHead>
                    <TableHead>Location</TableHead>
                    <TableHead>Rate</TableHead>
                    <TableHead>Source</TableHead>
                    <TableHead>Added</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="w-12"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {jobsData.jobs.map((job) => (
                    <TableRow 
                      key={job.id} 
                      className="cursor-pointer hover:bg-slate-50"
                      onClick={() => navigate(`/email-jobs/${job.id}`)}
                    >
                      <TableCell>
                        <div className="font-medium">{job.title}</div>
                        {job.skills && job.skills.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-1">
                            {job.skills.slice(0, 3).map((skill, i) => (
                              <Badge key={i} variant="secondary" className="text-xs">
                                {skill}
                              </Badge>
                            ))}
                            {job.skills.length > 3 && (
                              <Badge variant="outline" className="text-xs">
                                +{job.skills.length - 3}
                              </Badge>
                            )}
                          </div>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <Building2 className="h-4 w-4 text-slate-400" />
                          {job.company || '-'}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <MapPin className="h-4 w-4 text-slate-400" />
                          {job.location || '-'}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <DollarSign className="h-4 w-4 text-slate-400" />
                          {formatRate(job)}
                        </div>
                      </TableCell>
                      <TableCell>
                        {job.sourced_by ? (
                          <div className="flex items-center gap-1 text-sm">
                            <User className="h-4 w-4 text-slate-400" />
                            <span className="truncate max-w-24" title={job.sourced_by.name}>
                              {job.sourced_by.name}
                            </span>
                          </div>
                        ) : (
                          '-'
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1 text-sm text-slate-600">
                          <Clock className="h-4 w-4" />
                          {formatDate(job.created_at)}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            job.status === 'active'
                              ? 'default'
                              : job.status === 'expired'
                                ? 'secondary'
                                : 'outline'
                          }
                        >
                          {job.status}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon">
                              <MoreVertical className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem asChild>
                              <Link to={`/jobs/${job.id}`}>
                                <ExternalLink className="mr-2 h-4 w-4" />
                                View Details
                              </Link>
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              className="text-red-600"
                              onClick={() => handleDeleteClick(job)}
                            >
                              <Trash2 className="mr-2 h-4 w-4" />
                              Delete
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {/* Pagination */}
              {jobsData.pagination.pages > 1 && (
                <div className="flex items-center justify-between mt-4">
                  <p className="text-sm text-slate-600">
                    Showing {(page - 1) * perPage + 1} -{' '}
                    {Math.min(page * perPage, jobsData.pagination.total)} of{' '}
                    {jobsData.pagination.total} jobs
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={!jobsData.pagination.has_prev}
                      onClick={() => setPage(page - 1)}
                    >
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={!jobsData.pagination.has_next}
                      onClick={() => setPage(page + 1)}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Jobs by User */}
      {stats?.by_user && stats.by_user.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Jobs by Team Member</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {stats.by_user.map((user) => (
                <div
                  key={user.user_id}
                  className="flex items-center gap-3 p-3 rounded-lg border"
                >
                  <div className="flex-shrink-0 h-10 w-10 rounded-full bg-slate-100 flex items-center justify-center">
                    <User className="h-5 w-5 text-slate-600" />
                  </div>
                  <div>
                    <p className="font-medium text-sm truncate">{user.name}</p>
                    <p className="text-xs text-slate-500">{user.jobs_count} jobs</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Job?</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{jobToDelete?.title}"? This action cannot be
              undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={confirmDelete}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
