/**
 * Ready to Assign Tab
 * Unified layout: Search bar → Table → Pagination
 * Shows approved candidates ready to be assigned to recruiters
 */

import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
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
import { Skeleton } from '@/components/ui/skeleton';
import { Search, Eye, RefreshCw, MoreVertical, UserPlus, Users } from 'lucide-react';
import { toast } from 'sonner';
import { onboardingApi } from '@/lib/onboardingApi';
import { usePermissions } from '@/hooks/usePermissions';
import { CandidateAssignmentDialog } from '@/components/CandidateAssignmentDialog';
import type { CandidateOnboardingInfo } from '@/types';

const STATUS_COLORS: Record<string, string> = {
  PENDING_ASSIGNMENT: 'bg-gray-100 text-gray-800',
  ASSIGNED: 'bg-blue-100 text-blue-800',
  PENDING_ONBOARDING: 'bg-yellow-100 text-yellow-800',
  ONBOARDED: 'bg-purple-100 text-purple-800',
  APPROVED: 'bg-green-100 text-green-800',
  REJECTED: 'bg-red-100 text-red-800',
};

export function ReadyToAssignTab() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { hasPermission } = usePermissions();
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(1);
  const [assignDialogOpen, setAssignDialogOpen] = useState(false);
  const [selectedCandidate, setSelectedCandidate] = useState<CandidateOnboardingInfo | null>(null);

  const canViewCandidates = hasPermission('candidates.view');
  const canOnboardCandidates = hasPermission('candidates.onboard');

  const { data: readyToAssignData, isLoading } = useQuery({
    queryKey: ['ready-to-assign', page],
    queryFn: () => onboardingApi.getPendingCandidates({ page, per_page: 20, status: 'APPROVED' }),
    enabled: canViewCandidates,
    staleTime: 0,
  });

  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ['ready-to-assign'] });
    queryClient.invalidateQueries({ queryKey: ['onboarding-stats'] });
  };

  const handleAssign = (candidate: CandidateOnboardingInfo) => {
    setSelectedCandidate(candidate);
    setAssignDialogOpen(true);
  };

  // Filter candidates by search
  const candidates = readyToAssignData?.candidates || [];
  const filteredCandidates = searchQuery
    ? candidates.filter((c) =>
        `${c.first_name} ${c.last_name}`.toLowerCase().includes(searchQuery.toLowerCase()) ||
        c.email?.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : candidates;

  const formatDate = (dateString: string | null) => {
    if (!dateString) return '—';
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  return (
    <div className="space-y-4">
      {/* Search and Refresh */}
      <div className="flex flex-col md:flex-row gap-4">
        <div className="flex-1">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search by name or email..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>
        <Button variant="outline" size="icon" onClick={handleRefresh} disabled={isLoading}>
          <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
        </Button>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
        </div>
      ) : filteredCandidates.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          <Users className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p className="text-lg font-medium">No candidates ready to assign</p>
          <p className="text-sm mt-1">
            {searchQuery ? 'Try adjusting your search' : 'Approved candidates will appear here'}
          </p>
        </div>
      ) : (
        <>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Approved Date</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredCandidates.map((candidate) => (
                <TableRow key={candidate.id}>
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-green-500 text-white flex items-center justify-center text-xs font-medium">
                        {candidate.first_name?.[0]}{candidate.last_name?.[0]}
                      </div>
                      <span className="font-medium">{candidate.first_name} {candidate.last_name}</span>
                    </div>
                  </TableCell>
                  <TableCell className="text-muted-foreground">{candidate.email || '—'}</TableCell>
                  <TableCell>
                    <Badge className={STATUS_COLORS[candidate.onboarding_status] || 'bg-gray-100 text-gray-800'}>
                      {candidate.onboarding_status?.replace(/_/g, ' ') || 'Approved'}
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
                        {canOnboardCandidates && (
                          <DropdownMenuItem onClick={() => handleAssign(candidate)}>
                            <UserPlus className="h-4 w-4 mr-2" />
                            Assign to Recruiter
                          </DropdownMenuItem>
                        )}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          {/* Pagination */}
          {readyToAssignData && readyToAssignData.total_pages > 1 && (
            <div className="flex items-center justify-between pt-4 border-t">
              <div className="text-sm text-muted-foreground">
                Page {readyToAssignData.page} of {readyToAssignData.total_pages}
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
                  disabled={page === readyToAssignData.total_pages}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Assignment Dialog */}
      {selectedCandidate && (
        <CandidateAssignmentDialog
          candidateId={selectedCandidate.id}
          candidateName={`${selectedCandidate.first_name} ${selectedCandidate.last_name}`}
          open={assignDialogOpen}
          onOpenChange={setAssignDialogOpen}
          onSuccess={() => {
            toast.success('Candidate assigned successfully!');
            setSelectedCandidate(null);
            queryClient.invalidateQueries({ queryKey: ['ready-to-assign'] });
            queryClient.invalidateQueries({ queryKey: ['onboarding-stats'] });
          }}
        />
      )}
    </div>
  );
}
