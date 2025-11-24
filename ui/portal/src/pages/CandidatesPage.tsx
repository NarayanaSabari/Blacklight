/**
 * Candidates Page
 * Manage and track candidates with resume parsing
 */

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
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
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Users, Plus, Search, Loader2, MoreVertical, Pencil, Trash2, Eye, TrendingUp, UserCheck, Clock, UserPlus } from 'lucide-react';
import { toast } from 'sonner';
import { candidateApi } from '@/lib/candidateApi';
import { CandidateAssignmentDialog } from '@/components/CandidateAssignmentDialog';
import type { CandidateListItem, CandidateStatus } from '@/types/candidate';

const STATUS_COLORS: Record<CandidateStatus, string> = {
  processing: 'bg-orange-100 text-orange-800',
  pending_review: 'bg-yellow-100 text-yellow-800',
  new: 'bg-blue-100 text-blue-800',
  screening: 'bg-purple-100 text-purple-800',
  interviewed: 'bg-indigo-100 text-indigo-800',
  offered: 'bg-green-100 text-green-800',
  hired: 'bg-emerald-100 text-emerald-800',
  rejected: 'bg-red-100 text-red-800',
  withdrawn: 'bg-gray-100 text-gray-800',
  onboarded: 'bg-teal-100 text-teal-800',
  ready_for_assignment: 'bg-cyan-100 text-cyan-800',
};

export function CandidatesPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  // State
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [page, setPage] = useState(1);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [candidateToDelete, setCandidateToDelete] = useState<number | null>(null);
  const [assignDialogOpen, setAssignDialogOpen] = useState(false);
  const [candidateToAssign, setCandidateToAssign] = useState<CandidateListItem | null>(null);

  // Fetch stats
  const { data: stats } = useQuery({
    queryKey: ['candidate-stats'],
    queryFn: () => candidateApi.getStats(),
    staleTime: 0, // Always refetch to ensure fresh data
  });

  // Fetch candidates
  const { data: candidatesData, isLoading } = useQuery({
    queryKey: ['candidates', { page, status: statusFilter, search: searchQuery }],
    queryFn: () =>
      candidateApi.listCandidates({
        page,
        per_page: 20,
        status: statusFilter !== 'all' ? (statusFilter as CandidateStatus) : undefined,
        search: searchQuery || undefined,
      }),
    staleTime: 0, // Always refetch to ensure fresh data after mutations
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: number) => candidateApi.deleteCandidate(id),
    onSuccess: async () => {
      // Force immediate refetch of data
      await queryClient.refetchQueries({ queryKey: ['candidates'] });
      await queryClient.refetchQueries({ queryKey: ['candidate-stats'] });
      toast.success('Candidate deleted successfully');
      setDeleteDialogOpen(false);
      setCandidateToDelete(null);
    },
    onError: async (error: any) => {
      // Log the error for debugging
      console.error('Delete error:', error);

      // If 404, the candidate doesn't exist (already deleted) - treat as success
      if (error.response?.status === 404 || error.message?.includes('404')) {
        toast.success('Candidate deleted successfully');
      } else {
        toast.error(error.message || 'Failed to delete candidate');
      }

      setDeleteDialogOpen(false);
      setCandidateToDelete(null);
      // Force refetch anyway in case the candidate was actually deleted
      await queryClient.refetchQueries({ queryKey: ['candidates'] });
      await queryClient.refetchQueries({ queryKey: ['candidate-stats'] });
    },
  });

  const handleDelete = (id: number) => {
    setCandidateToDelete(id);
    setDeleteDialogOpen(true);
  };

  const confirmDelete = () => {
    if (candidateToDelete) {
      deleteMutation.mutate(candidateToDelete);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Candidates</h1>
          <p className="text-slate-600 mt-1">Manage and track your candidate pipeline</p>
        </div>
        <Button className="gap-2" onClick={() => navigate('/candidates/new')}>
          <Plus className="h-4 w-4" />
          Add Candidate
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-2">
              <Users className="h-4 w-4" />
              Total Candidates
            </CardDescription>
            <CardTitle className="text-3xl">
              {stats?.total_candidates || 0}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-2">
              <Clock className="h-4 w-4" />
              Screening
            </CardDescription>
            <CardTitle className="text-3xl">
              {stats?.by_status.screening || 0}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-2">
              <UserCheck className="h-4 w-4" />
              Hired
            </CardDescription>
            <CardTitle className="text-3xl">
              {stats?.by_status.hired || 0}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4" />
              Recent Uploads
            </CardDescription>
            <CardTitle className="text-3xl">
              {stats?.recent_uploads || 0}
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      {/* Main Content */}
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <CardTitle>Candidate List</CardTitle>
              <CardDescription>
                {candidatesData?.total || 0} total candidates
              </CardDescription>
            </div>

            <div className="flex gap-2">
              <div className="relative flex-1 md:w-64">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                <Input
                  placeholder="Search candidates..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9"
                />
              </div>

              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-40">
                  <SelectValue placeholder="All Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="processing">Processing</SelectItem>
                  <SelectItem value="pending_review">Pending Review</SelectItem>
                  <SelectItem value="new">New</SelectItem>
                  <SelectItem value="screening">Screening</SelectItem>
                  <SelectItem value="interviewed">Interviewed</SelectItem>
                  <SelectItem value="offered">Offered</SelectItem>
                  <SelectItem value="hired">Hired</SelectItem>
                  <SelectItem value="rejected">Rejected</SelectItem>
                  <SelectItem value="withdrawn">Withdrawn</SelectItem>
                  <SelectItem value="onboarded">Onboarded</SelectItem>
                  <SelectItem value="ready_for_assignment">Ready for Assignment</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>

        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : candidatesData?.candidates.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Users className="h-12 w-12 text-slate-400 mb-4" />
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                No candidates found
              </h3>
              <p className="text-slate-600 mb-4 max-w-sm">
                {searchQuery || statusFilter !== 'all'
                  ? 'Try adjusting your filters'
                  : 'Start building your talent pipeline by adding candidates'}
              </p>
              <Button className="gap-2" onClick={() => navigate('/candidates/new')}>
                <Plus className="h-4 w-4" />
                Add Your First Candidate
              </Button>
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Title</TableHead>
                    <TableHead>Location</TableHead>
                    <TableHead>Skills</TableHead>
                    <TableHead>Experience</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Added</TableHead>
                    <TableHead className="w-12"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {candidatesData?.candidates.map((candidate: CandidateListItem) => (
                    <TableRow key={candidate.id}>
                      <TableCell>
                        <div>
                          <div className="font-medium text-slate-900">
                            {candidate.full_name || `${candidate.first_name} ${candidate.last_name}`}
                          </div>
                          <div className="text-sm text-slate-600">{candidate.email}</div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="text-sm">{candidate.current_title || '-'}</div>
                      </TableCell>
                      <TableCell>
                        <div className="text-sm">{candidate.location || '-'}</div>
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1 max-w-xs">
                          {candidate.skills.slice(0, 3).map((skill, idx) => (
                            <Badge key={idx} variant="secondary" className="text-xs">
                              {skill}
                            </Badge>
                          ))}
                          {candidate.skills.length > 3 && (
                            <Badge variant="secondary" className="text-xs">
                              +{candidate.skills.length - 3}
                            </Badge>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="text-sm">
                          {candidate.total_experience_years
                            ? `${candidate.total_experience_years} yrs`
                            : '-'}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge className={STATUS_COLORS[candidate.status]}>
                          {candidate.status}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="text-sm text-slate-600">
                          {formatDate(candidate.created_at)}
                        </div>
                      </TableCell>
                      <TableCell>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="sm">
                              <MoreVertical className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem
                              className="gap-2"
                              onClick={() => navigate(`/candidates/${candidate.id}`)}
                            >
                              <Eye className="h-4 w-4" />
                              View Details
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              className="gap-2"
                              onClick={() => navigate(`/candidates/${candidate.id}/edit`)}
                            >
                              <Pencil className="h-4 w-4" />
                              Edit
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              className="gap-2"
                              onClick={() => {
                                setCandidateToAssign(candidate);
                                setAssignDialogOpen(true);
                              }}
                            >
                              <UserPlus className="h-4 w-4" />
                              Assign
                            </DropdownMenuItem>

                            {/* Show Review & Approve for pending_review status */}
                            {candidate.status === 'pending_review' && (
                              <>
                                <DropdownMenuItem
                                  className="gap-2 text-blue-600"
                                  onClick={() => navigate(`/candidates/${candidate.id}/edit`)}
                                >
                                  <Eye className="h-4 w-4" />
                                  Review & Edit
                                </DropdownMenuItem>
                                <DropdownMenuItem
                                  className="gap-2 text-green-600"
                                  onClick={async () => {
                                    try {
                                      await candidateApi.approveCandidate(candidate.id);
                                      toast.success('Candidate approved! Job matching in progress...');
                                      await queryClient.refetchQueries({ queryKey: ['candidates'] });
                                      await queryClient.refetchQueries({ queryKey: ['candidate-stats'] });
                                    } catch (error: any) {
                                      toast.error(error.message || 'Failed to approve candidate');
                                    }
                                  }}
                                >
                                  <UserCheck className="h-4 w-4" />
                                  Approve
                                </DropdownMenuItem>
                              </>
                            )}

                            <DropdownMenuItem
                              className="gap-2 text-destructive"
                              onClick={() => handleDelete(candidate.id)}
                            >
                              <Trash2 className="h-4 w-4" />
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
              {candidatesData && candidatesData.pages > 1 && (
                <div className="flex items-center justify-between mt-4 pt-4 border-t">
                  <div className="text-sm text-slate-600">
                    Page {candidatesData.page} of {candidatesData.pages}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page === 1}
                    >
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => p + 1)}
                      disabled={page === candidatesData.pages}
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

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Are you sure?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete this candidate and their resume. This action cannot be
              undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Candidate Assignment Dialog */}
      {candidateToAssign && (
        <CandidateAssignmentDialog
          candidateId={candidateToAssign.id}
          candidateName={candidateToAssign.full_name || `${candidateToAssign.first_name} ${candidateToAssign.last_name}`}
          open={assignDialogOpen}
          onOpenChange={setAssignDialogOpen}
          onSuccess={() => {
            toast.success('Candidate assigned successfully!');
            setCandidateToAssign(null);
          }}
        />
      )}
    </div>
  );
}
