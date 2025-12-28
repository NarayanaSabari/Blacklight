/**
 * Review Submissions Tab
 * Unified layout: Search bar → Table → Pagination
 * Shows candidates pending HR review (from resume uploads and email invitations)
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
import { Skeleton } from '@/components/ui/skeleton';
import { Search, Eye, RefreshCw, CheckCircle2, Mail, Upload } from 'lucide-react';
import { invitationApi } from '@/lib/api/invitationApi';
import { candidateApi } from '@/lib/candidateApi';
import { usePermissions } from '@/hooks/usePermissions';

export function ReviewSubmissionsTab() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { hasPermission } = usePermissions();
  const [searchQuery, setSearchQuery] = useState('');
  const [page] = useState(1);

  const canViewCandidates = hasPermission('candidates.view');

  // Fetch submitted invitations for review
  const { data: submittedInvitationsData, isLoading: isLoadingInvitations } = useQuery({
    queryKey: ['submitted-invitations', page],
    queryFn: () => invitationApi.getSubmittedInvitations({ page, per_page: 20 }),
    enabled: canViewCandidates,
    staleTime: 0,
  });

  // Fetch candidates with status='pending_review' (async resume uploads)
  const { data: pendingReviewCandidatesData, isLoading: isLoadingCandidates } = useQuery({
    queryKey: ['candidates-pending-review', page],
    queryFn: () => candidateApi.getPendingReview(),
    enabled: canViewCandidates,
    staleTime: 0,
  });

  const isLoading = isLoadingInvitations || isLoadingCandidates;

  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ['submitted-invitations'] });
    queryClient.invalidateQueries({ queryKey: ['candidates-pending-review'] });
    queryClient.invalidateQueries({ queryKey: ['onboarding-stats'] });
  };

  // Combine and filter data
  const allCandidates = pendingReviewCandidatesData?.candidates || [];
  const invitations = submittedInvitationsData?.items || [];
  
  // Get candidate IDs linked to pending invitations to avoid duplicates
  const invitationCandidateIds = new Set(
    invitations
      .filter((inv: { candidate_id?: number }) => inv.candidate_id)
      .map((inv: { candidate_id?: number }) => inv.candidate_id)
  );
  
  // Filter out candidates already linked to invitations
  const candidates = allCandidates.filter(c => !invitationCandidateIds.has(c.id));

  // Apply search filter
  const filteredCandidates = searchQuery
    ? candidates.filter(c => 
        `${c.first_name} ${c.last_name}`.toLowerCase().includes(searchQuery.toLowerCase()) ||
        c.email?.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : candidates;

  const filteredInvitations = searchQuery
    ? invitations.filter((inv: any) =>
        `${inv.first_name} ${inv.last_name}`.toLowerCase().includes(searchQuery.toLowerCase()) ||
        inv.email?.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : invitations;

  const totalItems = filteredCandidates.length + filteredInvitations.length;

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
      ) : totalItems === 0 ? (
        <div className="text-center py-12">
          <div className="rounded-full bg-green-100 p-4 w-16 h-16 mx-auto mb-4 flex items-center justify-center">
            <CheckCircle2 className="h-8 w-8 text-green-600" />
          </div>
          <p className="text-lg font-medium text-foreground">All Caught Up!</p>
          <p className="text-sm text-muted-foreground mt-1">
            No candidates pending review at the moment.
          </p>
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>Source</TableHead>
              <TableHead>Submitted</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {/* Resume Upload Candidates */}
            {filteredCandidates.map((candidate) => (
              <TableRow key={`candidate-${candidate.id}`}>
                <TableCell>
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-xs font-medium">
                      {candidate.first_name?.[0]}{candidate.last_name?.[0]}
                    </div>
                    <span className="font-medium">{candidate.first_name} {candidate.last_name}</span>
                  </div>
                </TableCell>
                <TableCell className="text-muted-foreground">{candidate.email || '—'}</TableCell>
                <TableCell>
                  <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-200">
                    <Upload className="h-3 w-3 mr-1" />
                    Resume Upload
                  </Badge>
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  {formatDate(candidate.created_at)}
                </TableCell>
                <TableCell className="text-right">
                  <Button
                    variant="default"
                    size="sm"
                    onClick={() => navigate(`/candidates/${candidate.id}?mode=review`)}
                  >
                    <Eye className="h-4 w-4 mr-2" />
                    Review
                  </Button>
                </TableCell>
              </TableRow>
            ))}

            {/* Email Invitation Candidates */}
            {filteredInvitations.map((invitation: any) => (
              <TableRow key={`invitation-${invitation.id}`}>
                <TableCell>
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-blue-500 text-white flex items-center justify-center text-xs font-medium">
                      {invitation.first_name?.[0]}{invitation.last_name?.[0]}
                    </div>
                    <span className="font-medium">{invitation.first_name} {invitation.last_name}</span>
                  </div>
                </TableCell>
                <TableCell className="text-muted-foreground">{invitation.email}</TableCell>
                <TableCell>
                  <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
                    <Mail className="h-3 w-3 mr-1" />
                    Email Invitation
                  </Badge>
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  {formatDate(invitation.submitted_at)}
                </TableCell>
                <TableCell className="text-right">
                  <Button
                    variant="default"
                    size="sm"
                    onClick={() => {
                      if (invitation.candidate_id) {
                        navigate(`/candidates/${invitation.candidate_id}?mode=review`);
                      } else {
                        navigate(`/invitations/${invitation.id}/review`);
                      }
                    }}
                  >
                    <Eye className="h-4 w-4 mr-2" />
                    Review
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
