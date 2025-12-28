/**
 * All Candidates Tab
 * Unified layout: Search/Filter bar → Table → Pagination
 */

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
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
import { Skeleton } from '@/components/ui/skeleton';
import { Users, Search, MoreVertical, Pencil, Trash2, Eye, UserPlus } from 'lucide-react';
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

export function AllCandidatesTab() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [page, setPage] = useState(1);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [candidateToDelete, setCandidateToDelete] = useState<number | null>(null);
  const [assignDialogOpen, setAssignDialogOpen] = useState(false);
  const [candidateToAssign, setCandidateToAssign] = useState<CandidateListItem | null>(null);

  const { data: candidatesData, isLoading } = useQuery({
    queryKey: ['candidates', { page, status: statusFilter, search: searchQuery }],
    queryFn: () =>
      candidateApi.listCandidates({
        page,
        per_page: 20,
        status: statusFilter !== 'all' ? (statusFilter as CandidateStatus) : undefined,
        search: searchQuery || undefined,
      }),
    staleTime: 0,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => candidateApi.deleteCandidate(id),
    onSuccess: async () => {
      await queryClient.refetchQueries({ queryKey: ['candidates'] });
      await queryClient.refetchQueries({ queryKey: ['onboarding-stats'] });
      toast.success('Candidate deleted successfully');
      setDeleteDialogOpen(false);
      setCandidateToDelete(null);
    },
    onError: async (error: any) => {
      if (error.response?.status === 404) {
        toast.success('Candidate deleted successfully');
      } else {
        toast.error(error.message || 'Failed to delete candidate');
      }
      setDeleteDialogOpen(false);
      setCandidateToDelete(null);
      await queryClient.refetchQueries({ queryKey: ['candidates'] });
    },
  });

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
    <div className="space-y-4">
      {/* Search and Filters */}
      <div className="flex flex-col md:flex-row gap-4">
        <div className="flex-1">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search candidates..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-full md:w-48">
            <SelectValue placeholder="All Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="new">New</SelectItem>
            <SelectItem value="screening">Screening</SelectItem>
            <SelectItem value="interviewed">Interviewed</SelectItem>
            <SelectItem value="offered">Offered</SelectItem>
            <SelectItem value="hired">Hired</SelectItem>
            <SelectItem value="rejected">Rejected</SelectItem>
            <SelectItem value="onboarded">Onboarded</SelectItem>
            <SelectItem value="ready_for_assignment">Ready for Assignment</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
        </div>
      ) : candidatesData?.candidates.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          <Users className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p className="text-lg font-medium">No candidates found</p>
          <p className="text-sm mt-1">
            {searchQuery || statusFilter !== 'all'
              ? 'Try adjusting your search or filters'
              : 'No candidates in the system'}
          </p>
        </div>
      ) : (
        <>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Phone</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Date</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {candidatesData?.candidates.map((candidate: CandidateListItem) => (
                <TableRow key={candidate.id}>
                  <TableCell className="font-medium">
                    {candidate.full_name || `${candidate.first_name} ${candidate.last_name}`}
                  </TableCell>
                  <TableCell>{candidate.email}</TableCell>
                  <TableCell>{candidate.phone || '—'}</TableCell>
                  <TableCell>
                    <Badge className={STATUS_COLORS[candidate.status]}>
                      {candidate.status.replace(/_/g, ' ')}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {formatDate(candidate.created_at)}
                  </TableCell>
                  <TableCell className="text-right">
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon">
                          <MoreVertical className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => navigate(`/candidates/${candidate.id}`)}>
                          <Eye className="h-4 w-4 mr-2" />
                          View Details
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => {
                          setCandidateToAssign(candidate);
                          setAssignDialogOpen(true);
                        }}>
                          <UserPlus className="h-4 w-4 mr-2" />
                          Assign
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => navigate(`/candidates/${candidate.id}/edit`)}>
                          <Pencil className="h-4 w-4 mr-2" />
                          Edit
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          className="text-red-600"
                          onClick={() => {
                            setCandidateToDelete(candidate.id);
                            setDeleteDialogOpen(true);
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

          {/* Pagination */}
          {candidatesData && candidatesData.pages > 1 && (
            <div className="flex items-center justify-between pt-4 border-t">
              <div className="text-sm text-muted-foreground">
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

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Are you sure?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete this candidate and their resume. This action cannot be undone.
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
