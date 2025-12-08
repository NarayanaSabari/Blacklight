/**
 * Onboard Candidates Page
 * Multi-tab interface for managing candidate onboarding workflow
 */

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
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
  DropdownMenuSeparator,
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
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import {
  AlertCircle,
  Users,
  UserPlus,
  CheckCircle2,
  XCircle,
  MoreVertical,
  Eye,
  Search,
  RefreshCw,
  ClipboardList,
  Mail,
  Upload, // Added for resume uploads section
} from 'lucide-react';
import { toast } from 'sonner';
import { onboardingApi } from '@/lib/onboardingApi';
import { invitationApi } from '@/lib/api/invitationApi'; // Added import
import { candidateApi } from '@/lib/candidateApi'; // Added for async resume uploads
import { usePermissions } from '@/hooks/usePermissions';
import { ReviewModal } from '@/components/candidates/ReviewModal'; // Added for async resume review
import { CandidateAssignmentDialog } from '@/components/CandidateAssignmentDialog';
import type { OnboardingStatus, CandidateOnboardingInfo, Candidate } from '@/types'; // Modified import

const ONBOARDING_STATUS_COLORS: Record<OnboardingStatus, string> = {
  PENDING_ASSIGNMENT: 'bg-gray-100 text-gray-800',
  ASSIGNED: 'bg-blue-100 text-blue-800',
  PENDING_ONBOARDING: 'bg-yellow-100 text-yellow-800',
  ONBOARDED: 'bg-purple-100 text-purple-800',
  APPROVED: 'bg-green-100 text-green-800',
  REJECTED: 'bg-red-100 text-red-800',
};

type TabValue = 'all-candidates' | 'review-submissions' | 'ready-to-assign' | 'email-invitations';

interface OnboardCandidatesPageProps {
  defaultTab?: TabValue;
  hideTabNavigation?: boolean;
}

export function OnboardCandidatesPage({ defaultTab, hideTabNavigation = false }: OnboardCandidatesPageProps = {}) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { hasPermission } = usePermissions();
  const [activeTab, setActiveTab] = useState<TabValue>(defaultTab || 'all-candidates');
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(1);

  // Dialogs and selected items
  const [assignDialogOpen, setAssignDialogOpen] = useState(false);
  const [onboardDialogOpen, setOnboardDialogOpen] = useState(false);
  const [rejectDialogOpen, setRejectDialogOpen] = useState(false);
  const [reviewModalOpen, setReviewModalOpen] = useState(false); // For async resume review
  const [selectedCandidate, setSelectedCandidate] = useState<CandidateOnboardingInfo | null>(null);
  const [selectedResumeCandidate, setSelectedResumeCandidate] = useState<Candidate | null>(null); // For async resume candidates
  const [rejectionReason, setRejectionReason] = useState('');

  // Permission checks
  const canViewCandidates = hasPermission('candidates.view');
  const canOnboardCandidates = hasPermission('candidates.onboard');
  const canApproveCandidates = hasPermission('candidates.approve');

  // Fetch onboarding stats
  const {
    data: statsData,
  } = useQuery({
    queryKey: ['onboarding-stats'],
    queryFn: () => onboardingApi.getOnboardingStats(),
    enabled: canViewCandidates,
  });

  // Fetch submitted invitations for review (self-onboarding)
  const {
    data: submittedInvitationsData,
    isLoading: isLoadingSubmittedInvitations,
  } = useQuery({
    queryKey: ['submitted-invitations', page],
    queryFn: () => invitationApi.getSubmittedInvitations({ page, per_page: 20 }),
    enabled: canViewCandidates && activeTab === 'review-submissions',
    staleTime: 0, // Always refetch to ensure fresh data
  });

  // Fetch candidates with status='pending_review' (async resume uploads)
  const {
    data: pendingReviewCandidatesData,
    isLoading: isLoadingPendingReviewCandidates,
  } = useQuery({
    queryKey: ['candidates-pending-review', page],
    queryFn: () => candidateApi.getPendingReview(),
    enabled: canViewCandidates && activeTab === 'review-submissions',
    staleTime: 0, // Always refetch to ensure fresh data
  });

  // Fetch all candidates (for all-candidates tab)
  const { data: allCandidatesData, isLoading: isLoadingAllCandidates } = useQuery({
    queryKey: ['all-candidates', page, searchQuery],
    queryFn: () => candidateApi.listCandidates({ page, per_page: 20, search: searchQuery || undefined }),
    enabled: canViewCandidates && activeTab === 'all-candidates',
  });

  // Fetch ready-to-assign candidates
  const { data: readyToAssignData, isLoading: isLoadingReadyToAssign } = useQuery({
    queryKey: ['ready-to-assign', page],
    queryFn: () => onboardingApi.getPendingCandidates({ page, per_page: 20, status: 'PENDING_ASSIGNMENT' }),
    enabled: canViewCandidates && activeTab === 'ready-to-assign',
  });

  // Fetch email invitations
  const { data: emailInvitationsData, isLoading: isLoadingEmailInvitations } = useQuery({
    queryKey: ['email-invitations', page],
    queryFn: () => invitationApi.list({ page, per_page: 20 }),
    enabled: canViewCandidates && activeTab === 'email-invitations',
  });

  // Onboard candidate mutation
  const onboardMutation = useMutation({
    mutationFn: onboardingApi.onboardCandidate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pending-onboarding-candidates'] });
      queryClient.invalidateQueries({ queryKey: ['onboarding-stats'] });
      toast.success('Candidate onboarded successfully');
      setOnboardDialogOpen(false);
      setSelectedCandidate(null);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to onboard candidate');
    },
  });

  // Approve candidate mutation
  const approveMutation = useMutation({
    mutationFn: onboardingApi.approveCandidate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pending-onboarding-candidates'] });
      queryClient.invalidateQueries({ queryKey: ['all-onboarding-candidates'] });
      queryClient.invalidateQueries({ queryKey: ['onboarding-stats'] });
      toast.success('Candidate approved successfully');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to approve candidate');
    },
  });

  // Reject candidate mutation
  const rejectMutation = useMutation({
    mutationFn: onboardingApi.rejectCandidate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pending-onboarding-candidates'] });
      queryClient.invalidateQueries({ queryKey: ['all-onboarding-candidates'] });
      queryClient.invalidateQueries({ queryKey: ['onboarding-stats'] });
      toast.success('Candidate rejected');
      setRejectDialogOpen(false);
      setSelectedCandidate(null);
      setRejectionReason('');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to reject candidate');
    },
  });

  // Handle assign candidate
  const handleAssign = (candidate: CandidateOnboardingInfo) => {
    setSelectedCandidate(candidate);
    setAssignDialogOpen(true);
  };

  // Handle onboard candidate
  const handleOnboard = (candidate: CandidateOnboardingInfo) => {
    setSelectedCandidate(candidate);
    setOnboardDialogOpen(true);
  };

  // Confirm onboard
  const confirmOnboard = () => {
    if (!selectedCandidate) return;
    onboardMutation.mutate({ candidate_id: selectedCandidate.id });
  };

  // Handle approve candidate
  const handleApprove = (candidate: CandidateOnboardingInfo) => {
    approveMutation.mutate({ candidate_id: candidate.id });
  };

  // Handle reject candidate
  const handleReject = (candidate: CandidateOnboardingInfo) => {
    setSelectedCandidate(candidate);
    setRejectDialogOpen(true);
  };

  // Confirm reject
  const confirmReject = () => {
    if (!selectedCandidate || !rejectionReason.trim()) {
      toast.error('Please provide a rejection reason');
      return;
    }
    rejectMutation.mutate({
      candidate_id: selectedCandidate.id,
      rejection_reason: rejectionReason.trim(),
    });
  };

  // Handle view candidate
  const handleViewCandidate = (candidateId: number) => {
    navigate(`/candidates/${candidateId}`);
  };

  // Filter candidates by search query based on active tab
  const filteredCandidates = (() => {
    if (activeTab === 'review-submissions') return [];
    if (activeTab === 'email-invitations') return [];

    const candidates = activeTab === 'ready-to-assign'
      ? (readyToAssignData?.candidates || [])
      : (allCandidatesData?.candidates || []);

    if (!searchQuery) return candidates;

    const query = searchQuery.toLowerCase();
    return candidates.filter((candidate) => (
      candidate.first_name.toLowerCase().includes(query) ||
      candidate.last_name.toLowerCase().includes(query) ||
      candidate.email?.toLowerCase().includes(query)
    ));
  })();

  // Format date
  const formatDate = (dateString: string | null) => {
    if (!dateString) return '—';
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  // Get action buttons based on status
  const getActionButtons = (candidate: CandidateOnboardingInfo) => {
    const actions = [];

    // Assign action (PENDING_ASSIGNMENT status)
    if (candidate.onboarding_status === 'PENDING_ASSIGNMENT' && canOnboardCandidates) {
      actions.push(
        <DropdownMenuItem key="assign" onClick={() => handleAssign(candidate)}>
          <UserPlus className="h-4 w-4 mr-2" />
          Assign to User
        </DropdownMenuItem>
      );
    }

    // Onboard action (ASSIGNED status)
    if (candidate.onboarding_status === 'ASSIGNED' && canOnboardCandidates) {
      actions.push(
        <DropdownMenuItem key="onboard" onClick={() => handleOnboard(candidate)}>
          <ClipboardList className="h-4 w-4 mr-2" />
          Onboard
        </DropdownMenuItem>
      );
    }

    // Approve/Reject actions (ONBOARDED status)
    if (candidate.onboarding_status === 'ONBOARDED' && canApproveCandidates) {
      actions.push(
        <DropdownMenuItem key="approve" onClick={() => handleApprove(candidate)}>
          <CheckCircle2 className="h-4 w-4 mr-2 text-green-600" />
          Approve
        </DropdownMenuItem>
      );
      actions.push(
        <DropdownMenuItem
          key="reject"
          onClick={() => handleReject(candidate)}
          className="text-red-600"
        >
          <XCircle className="h-4 w-4 mr-2" />
          Reject
        </DropdownMenuItem>
      );
    }

    return actions;
  };

  if (!canViewCandidates) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Onboard Candidates</h1>
          <p className="text-slate-600 mt-1">Manage candidate onboarding workflow</p>
        </div>
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            You don't have permission to view candidates. Contact your administrator for access.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  const stats = {
    pending_review: (submittedInvitationsData?.total || 0) + (pendingReviewCandidatesData?.total || 0), // Include both sources
    pending_assignment: statsData?.pending_assignment || 0,
    assigned: statsData?.assigned || 0,
    pending_onboarding: statsData?.pending_onboarding || 0,
    onboarded: statsData?.onboarded || 0,
    approved: statsData?.approved || 0,
    rejected: statsData?.rejected || 0,
    total: (statsData?.total || 0) + (submittedInvitationsData?.total || 0) + (pendingReviewCandidatesData?.total || 0), // Sum of all
  };

  return (
    <div className="space-y-6">

      {/* Tabs and Content */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Candidate Pipeline</CardTitle>
              <CardDescription className="mt-1.5">
                {activeTab === 'all-candidates' && 'View all candidates across all statuses'}
                {activeTab === 'review-submissions' && 'Review submitted applications and approve qualified candidates'}
                {activeTab === 'ready-to-assign' && 'Assign approved candidates to recruiters or managers'}
                {activeTab === 'email-invitations' && 'Manage and track email invitations sent to candidates'}
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="overflow-hidden max-w-full min-w-0">
          <Tabs value={activeTab} onValueChange={(value) => {
            setActiveTab(value as TabValue);
            setPage(1);
            setSearchQuery('');
          }}>
            {!hideTabNavigation && (
              <TabsList className="grid w-full grid-cols-4">
                <TabsTrigger value="all-candidates" className="gap-2">
                  <Users className="h-3.5 w-3.5" />
                  All Candidates
                  {stats.total > 0 && (
                    <Badge variant="secondary" className="ml-1">{stats.total}</Badge>
                  )}
                </TabsTrigger>
                <TabsTrigger value="review-submissions" className="gap-2">
                  <ClipboardList className="h-3.5 w-3.5" />
                  Review Submissions
                  {stats.pending_review > 0 && (
                    <Badge variant="secondary" className="ml-1 bg-amber-100 text-amber-700 hover:bg-amber-100">
                      {stats.pending_review}
                    </Badge>
                  )}
                </TabsTrigger>
                <TabsTrigger value="ready-to-assign" className="gap-2">
                  <UserPlus className="h-3.5 w-3.5" />
                  Ready to Assign
                  {stats.pending_assignment > 0 && (
                    <Badge variant="secondary" className="ml-1">{stats.pending_assignment}</Badge>
                  )}
                </TabsTrigger>
                <TabsTrigger value="email-invitations" className="gap-2">
                  <Mail className="h-3.5 w-3.5" />
                  Email Invitations
                </TabsTrigger>
              </TabsList>
            )}

            {/* Search and Filters */}
            <div className="flex flex-col md:flex-row gap-4 mt-6 mb-4">
              <div className="flex-1">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
                  <Input
                    placeholder="Search candidates..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-10"
                  />
                </div>
              </div>
              <Button
                variant="outline"
                size="icon"
                onClick={() => {
                  queryClient.invalidateQueries({ queryKey: ['submitted-invitations'] });
                  queryClient.invalidateQueries({ queryKey: ['candidates-pending-review'] });
                  queryClient.invalidateQueries({ queryKey: ['all-candidates'] });
                  queryClient.invalidateQueries({ queryKey: ['ready-to-assign'] });
                  queryClient.invalidateQueries({ queryKey: ['email-invitations'] });
                  queryClient.invalidateQueries({ queryKey: ['onboarding-stats'] });
                }}
                disabled={isLoadingSubmittedInvitations || isLoadingPendingReviewCandidates || isLoadingAllCandidates || isLoadingReadyToAssign || isLoadingEmailInvitations}
              >
                <RefreshCw className={`h-4 w-4 ${(isLoadingSubmittedInvitations || isLoadingPendingReviewCandidates || isLoadingAllCandidates || isLoadingReadyToAssign || isLoadingEmailInvitations) ? 'animate-spin' : ''}`} />
              </Button>
            </div>

            <TabsContent value="review-submissions" className="mt-0">
              {/* Pending Review Table */}
              {isLoadingPendingReviewCandidates || isLoadingSubmittedInvitations ? (
                <div className="space-y-3">
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                </div>
              ) : (
                <>
                  {/* Combine candidates and invitations */}
                  {(() => {
                    const allCandidates = pendingReviewCandidatesData?.candidates || [];
                    const invitations = submittedInvitationsData?.items || [];
                    
                    // Get candidate IDs that are linked to pending invitations
                    // to avoid showing duplicates (invitation + candidate for same person)
                    const invitationCandidateIds = new Set(
                      invitations
                        .filter((inv: { candidate_id?: number }) => inv.candidate_id)
                        .map((inv: { candidate_id?: number }) => inv.candidate_id)
                    );
                    
                    // Show all candidates EXCEPT those already linked to a pending invitation
                    // (those will be shown in the invitations section)
                    const candidates = allCandidates.filter(c => !invitationCandidateIds.has(c.id));
                    const hasPendingReviews = candidates.length > 0 || invitations.length > 0;

                    if (!hasPendingReviews) {
                      return (
                        <Card className="border-2 border-dashed border-slate-300">
                          <CardContent className="flex flex-col items-center justify-center py-16">
                            <div className="rounded-full bg-green-100 p-6 mb-4">
                              <CheckCircle2 className="h-16 w-16 text-green-600" />
                            </div>
                            <h3 className="text-2xl font-bold text-slate-900 mb-2">All Caught Up!</h3>
                            <p className="text-base text-slate-600 text-center max-w-md">
                              No candidates pending review at the moment.<br />
                              New resume uploads and email submissions will appear here.
                            </p>
                          </CardContent>
                        </Card>
                      );
                    }

                    return (
                      <Card className="border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
                        <CardHeader className="bg-gradient-to-r from-slate-50 to-slate-100 border-b-2 border-black">
                          <CardTitle className="text-lg font-bold">Pending Review</CardTitle>
                          <CardDescription>
                            {candidates.length + invitations.length} submission{candidates.length + invitations.length === 1 ? '' : 's'} awaiting your review
                          </CardDescription>
                        </CardHeader>
                        <CardContent className="p-0">
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
                              {/* All pending review candidates */}
                              {candidates.map((candidate) => (
                                <TableRow key={`candidate-${candidate.id}`}>
                                  <TableCell>
                                    <div className="flex items-center gap-3">
                                      <div className={`flex-shrink-0 w-10 h-10 rounded-full ${candidate.source === 'email_invitation' ? 'bg-blue-500' : 'bg-primary'} text-primary-foreground flex items-center justify-center text-sm font-bold border-2 border-black`}>
                                        {candidate.first_name?.[0]}{candidate.last_name?.[0]}
                                      </div>
                                      <div className="font-medium text-slate-900">
                                        {candidate.first_name} {candidate.last_name}
                                      </div>
                                    </div>
                                  </TableCell>
                                  <TableCell className="text-slate-600">{candidate.email || '—'}</TableCell>
                                  <TableCell>
                                    {candidate.source === 'email_invitation' ? (
                                      <Badge variant="outline" className="bg-blue-50 border-blue-300 text-blue-800">
                                        <Mail className="h-3 w-3 mr-1" />
                                        Email Invitation
                                      </Badge>
                                    ) : (
                                      <Badge variant="outline" className="bg-yellow-50 border-yellow-300 text-yellow-800">
                                        <Upload className="h-3 w-3 mr-1" />
                                        Resume Upload
                                      </Badge>
                                    )}
                                  </TableCell>
                                  <TableCell className="text-sm text-slate-600">
                                    {candidate.created_at ? new Date(candidate.created_at).toLocaleDateString('en-US', {
                                      month: 'short',
                                      day: 'numeric',
                                      year: 'numeric',
                                    }) : '—'}
                                  </TableCell>
                                  <TableCell className="text-right">
                                    <Button
                                      variant="default"
                                      size="sm"
                                      className="gap-2 border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:shadow-[3px_3px_0px_0px_rgba(0,0,0,1)]"
                                      onClick={() => navigate(`/candidates/${candidate.id}?mode=review`)}
                                    >
                                      <Eye className="h-4 w-4" />
                                      Review
                                    </Button>
                                  </TableCell>
                                </TableRow>
                              ))}

                              {/* Email Invitations (candidates from email invitations) */}
                              {invitations.map((invitation) => (
                                <TableRow key={`invitation-${invitation.id}`}>
                                  <TableCell>
                                    <div className="flex items-center gap-3">
                                      <div className="flex-shrink-0 w-10 h-10 rounded-full bg-blue-500 text-white flex items-center justify-center text-sm font-bold border-2 border-black">
                                        {invitation.first_name?.[0]}{invitation.last_name?.[0]}
                                      </div>
                                      <div className="font-medium text-slate-900">
                                        {invitation.first_name} {invitation.last_name}
                                      </div>
                                    </div>
                                  </TableCell>
                                  <TableCell className="text-slate-600">{invitation.email}</TableCell>
                                  <TableCell>
                                    <Badge variant="outline" className="bg-blue-50 border-blue-300 text-blue-800">
                                      <Mail className="h-3 w-3 mr-1" />
                                      Email Invitation
                                    </Badge>
                                  </TableCell>
                                  <TableCell className="text-sm text-slate-600">
                                    {invitation.submitted_at ? new Date(invitation.submitted_at).toLocaleDateString('en-US', {
                                      month: 'short',
                                      day: 'numeric',
                                      year: 'numeric',
                                    }) : '—'}
                                  </TableCell>
                                  <TableCell className="text-right">
                                    <Button
                                      variant="default"
                                      size="sm"
                                      className="gap-2 border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:shadow-[3px_3px_0px_0px_rgba(0,0,0,1)]"
                                      onClick={() => {
                                        // Navigate to candidate detail if invitation has been converted
                                        // For now, use invitation review page as fallback
                                        if (invitation.candidate_id) {
                                          navigate(`/candidates/${invitation.candidate_id}?mode=review`);
                                        } else {
                                          navigate(`/invitations/${invitation.id}/review`);
                                        }
                                      }}
                                    >
                                      <Eye className="h-4 w-4" />
                                      Review
                                    </Button>
                                  </TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </CardContent>
                      </Card>
                    );
                  })()}
                </>
              )}
            </TabsContent>

            <TabsContent value="ready-to-assign" className="mt-0">
              {isLoadingReadyToAssign ? (
                <div className="space-y-2">
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                </div>
              ) : filteredCandidates.length > 0 ? (
                <>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Name</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Assigned To</TableHead>
                        <TableHead>Date</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredCandidates.map((candidate) => (
                        <TableRow key={candidate.id}>
                          <TableCell className="font-medium">
                            {candidate.first_name} {candidate.last_name}
                          </TableCell>
                          <TableCell>
                            {'onboarding_status' in candidate && candidate.onboarding_status ? (
                              <Badge
                                className={
                                  ONBOARDING_STATUS_COLORS[candidate.onboarding_status] ||
                                  'bg-gray-100 text-gray-800'
                                }
                              >
                                {candidate.onboarding_status.replace(/_/g, ' ')}
                              </Badge>
                            ) : '—'}
                          </TableCell>
                          <TableCell>
                            {'recruiter' in candidate && (candidate as CandidateOnboardingInfo).recruiter ? (
                              <span className="text-sm">
                                {(candidate as CandidateOnboardingInfo).recruiter!.first_name}{' '}
                                {(candidate as CandidateOnboardingInfo).recruiter!.last_name}
                              </span>
                            ) : (
                              '—'
                            )}
                          </TableCell>
                          <TableCell>
                            <div className="text-sm text-slate-600">
                              {formatDate(candidate.created_at)}
                            </div>
                          </TableCell>
                          <TableCell className="text-right">
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button variant="ghost" size="icon">
                                  <MoreVertical className="h-4 w-4" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                <DropdownMenuItem onClick={() => handleViewCandidate(candidate.id)}>
                                  <Eye className="h-4 w-4 mr-2" />
                                  View Details
                                </DropdownMenuItem>
                                {getActionButtons(candidate as CandidateOnboardingInfo).length > 0 && (
                                  <>
                                    <DropdownMenuSeparator />
                                    {getActionButtons(candidate as CandidateOnboardingInfo)}
                                  </>
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
                    <div className="flex items-center justify-between mt-4 pt-4 border-t">
                      <div className="text-sm text-slate-600">
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
              ) : (
                <div className="text-center py-12 text-slate-500">
                  <Users className="h-12 w-12 mx-auto mb-4 text-slate-300" />
                  <p className="text-lg font-medium">No candidates found</p>
                  <p className="text-sm mt-1">
                    {searchQuery
                      ? 'Try adjusting your search'
                      : 'No candidates in this stage'}
                  </p>
                </div>
              )}
            </TabsContent>

            <TabsContent value="all-candidates" className="mt-0">
              {isLoadingAllCandidates ? (
                <div className="space-y-2">
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                </div>
              ) : filteredCandidates.length > 0 ? (
                <>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Name</TableHead>
                        <TableHead>Email</TableHead>
                        <TableHead>Phone</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Assigned To</TableHead>
                        <TableHead>Date</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredCandidates.map((candidate) => (
                        <TableRow key={candidate.id}>
                          <TableCell className="font-medium">
                            {candidate.first_name} {candidate.last_name}
                          </TableCell>
                          <TableCell>{candidate.email}</TableCell>
                          <TableCell>{candidate.phone || '—'}</TableCell>
                          <TableCell>
                            {'onboarding_status' in candidate && candidate.onboarding_status ? (
                              <Badge
                                className={
                                  ONBOARDING_STATUS_COLORS[candidate.onboarding_status] ||
                                  'bg-gray-100 text-gray-800'
                                }
                              >
                                {candidate.onboarding_status.replace(/_/g, ' ')}
                              </Badge>
                            ) : '—'}
                          </TableCell>
                          <TableCell>
                            {'recruiter' in candidate && (candidate as CandidateOnboardingInfo).recruiter ? (
                              <span className="text-sm">
                                {(candidate as CandidateOnboardingInfo).recruiter!.first_name}{' '}
                                {(candidate as CandidateOnboardingInfo).recruiter!.last_name}
                              </span>
                            ) : (
                              '—'
                            )}
                          </TableCell>
                          <TableCell>
                            <div className="text-sm text-slate-600">
                              {formatDate(candidate.created_at)}
                            </div>
                          </TableCell>
                          <TableCell className="text-right">
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button variant="ghost" size="icon">
                                  <MoreVertical className="h-4 w-4" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                <DropdownMenuItem onClick={() => handleViewCandidate(candidate.id)}>
                                  <Eye className="h-4 w-4 mr-2" />
                                  View Details
                                </DropdownMenuItem>
                                {getActionButtons(candidate as CandidateOnboardingInfo).length > 0 && (
                                  <>
                                    <DropdownMenuSeparator />
                                    {getActionButtons(candidate as CandidateOnboardingInfo)}
                                  </>
                                )}
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>

                  {/* Pagination */}
                  {allCandidatesData && allCandidatesData.pages > 1 && (
                    <div className="flex items-center justify-between mt-4 pt-4 border-t">
                      <div className="text-sm text-slate-600">
                        Page {allCandidatesData.page} of {allCandidatesData.pages}
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
                          disabled={page === allCandidatesData.pages}
                        >
                          Next
                        </Button>
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="text-center py-12 text-slate-500">
                  <Users className="h-12 w-12 mx-auto mb-4 text-slate-300" />
                  <p className="text-lg font-medium">No candidates found</p>
                  <p className="text-sm mt-1">
                    {searchQuery
                      ? 'Try adjusting your search'
                      : 'No candidates in this stage'}
                  </p>
                </div>
              )}
            </TabsContent>

            <TabsContent value="email-invitations" className="mt-0">
              {isLoadingEmailInvitations ? (
                <div className="space-y-2">
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                </div>
              ) : emailInvitationsData?.items && emailInvitationsData.items.length > 0 ? (
                <>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Name</TableHead>
                        <TableHead>Email</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Sent Date</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {emailInvitationsData.items.map((invitation) => (
                        <TableRow key={invitation.id}>
                          <TableCell className="font-medium">
                            {invitation.first_name} {invitation.last_name}
                          </TableCell>
                          <TableCell>{invitation.email}</TableCell>
                          <TableCell>
                            <Badge variant="outline">
                              {invitation.status.replace(/_/g, ' ')}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-sm text-slate-600">
                            {new Date(invitation.created_at).toLocaleDateString('en-US', {
                              month: 'short',
                              day: 'numeric',
                              year: 'numeric',
                            })}
                          </TableCell>
                          <TableCell className="text-right">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => navigate(`/invitations/${invitation.id}`)}
                            >
                              <Eye className="h-4 w-4 mr-2" />
                              View
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>

                  {/* Pagination */}
                  {emailInvitationsData && emailInvitationsData.pages > 1 && (
                    <div className="flex items-center justify-between mt-4 pt-4 border-t">
                      <div className="text-sm text-slate-600">
                        Page {emailInvitationsData.page} of {emailInvitationsData.pages}
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
                          disabled={page === emailInvitationsData.pages}
                        >
                          Next
                        </Button>
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="text-center py-12 text-slate-500">
                  <Mail className="h-12 w-12 mx-auto mb-4 text-slate-300" />
                  <p className="text-lg font-medium">No email invitations</p>
                  <p className="text-sm mt-1">
                    Email invitations sent to candidates will appear here
                  </p>
                </div>
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Assign Dialog - Using CandidateAssignmentDialog */}
      {selectedCandidate && (
        <CandidateAssignmentDialog
          candidateId={selectedCandidate.id}
          candidateName={`${selectedCandidate.first_name} ${selectedCandidate.last_name}`}
          open={assignDialogOpen}
          onOpenChange={(open) => {
            setAssignDialogOpen(open);
            if (!open) {
              setSelectedCandidate(null);
            }
          }}
          onSuccess={() => {
            queryClient.invalidateQueries({ queryKey: ['ready-to-assign'] });
            queryClient.invalidateQueries({ queryKey: ['onboarding-stats'] });
          }}
        />
      )}

      {/* Onboard Dialog */}
      <Dialog open={onboardDialogOpen} onOpenChange={setOnboardDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Onboard Candidate</DialogTitle>
            <DialogDescription>
              Mark {selectedCandidate?.first_name} {selectedCandidate?.last_name} as onboarded.
              This will update their status to ONBOARDED and make them ready for approval.
            </DialogDescription>
          </DialogHeader>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setOnboardDialogOpen(false);
                setSelectedCandidate(null);
              }}
            >
              Cancel
            </Button>
            <Button onClick={confirmOnboard} disabled={onboardMutation.isPending}>
              {onboardMutation.isPending ? 'Onboarding...' : 'Onboard'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reject Dialog */}
      <Dialog open={rejectDialogOpen} onOpenChange={setRejectDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reject Candidate</DialogTitle>
            <DialogDescription>
              Provide a reason for rejecting {selectedCandidate?.first_name}{' '}
              {selectedCandidate?.last_name}. This action will update their status to REJECTED.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">
                Rejection Reason <span className="text-red-500">*</span>
              </label>
              <Textarea
                placeholder="Enter the reason for rejection..."
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
                rows={4}
                className="resize-none"
              />
              {rejectionReason.trim() === '' && (
                <p className="text-xs text-red-500">Rejection reason is required</p>
              )}
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setRejectDialogOpen(false);
                setSelectedCandidate(null);
                setRejectionReason('');
              }}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={confirmReject}
              disabled={rejectMutation.isPending || !rejectionReason.trim()}
            >
              {rejectMutation.isPending ? 'Rejecting...' : 'Reject'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Review Modal for Async Resume Uploads */}
      {selectedResumeCandidate && (
        <ReviewModal
          candidate={selectedResumeCandidate as any}
          open={reviewModalOpen}
          onOpenChange={setReviewModalOpen}
          onSuccess={() => {
            queryClient.invalidateQueries({ queryKey: ['candidates-pending-review'] });
            queryClient.invalidateQueries({ queryKey: ['onboarding-stats'] });
            setSelectedResumeCandidate(null);
          }}
        />
      )}
    </div >
  );
}
