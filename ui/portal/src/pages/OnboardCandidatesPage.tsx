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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import {
  AlertCircle,
  Users,
  UserPlus,
  UserCheck,
  Clock,
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
import { candidateAssignmentApi } from '@/lib/candidateAssignmentApi';
import { teamApi } from '@/lib/teamApi';
import { usePermissions } from '@/hooks/usePermissions';
import { ReviewModal } from '@/components/candidates/ReviewModal'; // Added for async resume review
import type { OnboardingStatus, CandidateOnboardingInfo, InvitationWithRelations, Candidate } from '@/types'; // Modified import

const ONBOARDING_STATUS_COLORS: Record<OnboardingStatus, string> = {
  PENDING_ASSIGNMENT: 'bg-gray-100 text-gray-800',
  ASSIGNED: 'bg-blue-100 text-blue-800',
  PENDING_ONBOARDING: 'bg-yellow-100 text-yellow-800',
  ONBOARDED: 'bg-purple-100 text-purple-800',
  APPROVED: 'bg-green-100 text-green-800',
  REJECTED: 'bg-red-100 text-red-800',
};

type TabValue = 'pending-review' | 'pending-assignment' | 'pending-onboarding' | 'all'; // Modified type

export function OnboardCandidatesPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { hasPermission } = usePermissions();
  const [activeTab, setActiveTab] = useState<TabValue>('pending-assignment');
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(1);
  
  // Dialogs and selected items
  const [assignDialogOpen, setAssignDialogOpen] = useState(false);
  const [onboardDialogOpen, setOnboardDialogOpen] = useState(false);
  const [rejectDialogOpen, setRejectDialogOpen] = useState(false);
  const [reviewModalOpen, setReviewModalOpen] = useState(false); // For async resume review
  const [selectedCandidate, setSelectedCandidate] = useState<CandidateOnboardingInfo | null>(null);
  const [selectedResumeCandidate, setSelectedResumeCandidate] = useState<Candidate | null>(null); // For async resume candidates
  const [selectedUserId, setSelectedUserId] = useState<string>('');
  const [rejectionReason, setRejectionReason] = useState('');

  // Permission checks
  const canViewCandidates = hasPermission('candidates.view');
  const canOnboardCandidates = hasPermission('candidates.onboard');
  const canApproveCandidates = hasPermission('candidates.approve');

  // Fetch onboarding stats
  const {
    data: statsData,
    isLoading: isLoadingStats,
  } = useQuery({
    queryKey: ['onboarding-stats'],
    queryFn: () => onboardingApi.getOnboardingStats(),
    enabled: canViewCandidates,
  });

  // Fetch submitted invitations for review (self-onboarding)
  const {
    data: submittedInvitationsData,
    isLoading: isLoadingSubmittedInvitations,
    error: submittedInvitationsError,
  } = useQuery({
    queryKey: ['submitted-invitations', page],
    queryFn: () => invitationApi.getSubmittedInvitations({ page, per_page: 20 }),
    enabled: canViewCandidates && activeTab === 'pending-review',
  });

  // Fetch candidates with status='pending_review' (async resume uploads)
  const {
    data: pendingReviewCandidatesData,
    isLoading: isLoadingPendingReviewCandidates,
  } = useQuery({
    queryKey: ['candidates-pending-review', page],
    queryFn: () => candidateApi.getPendingReview(),
    enabled: canViewCandidates && activeTab === 'pending-review',
  });

  // Fetch candidates based on active tab
  const getCandidatesQueryKey = () => {
    if (activeTab === 'pending-review') { // Added
      return ['submitted-invitations', page];
    } else if (activeTab === 'pending-assignment') {
      return ['pending-candidates', 'PENDING_ASSIGNMENT', page];
    } else if (activeTab === 'pending-onboarding') {
      return ['pending-candidates', 'ASSIGNED,PENDING_ONBOARDING', page];
    }
    return ['pending-candidates', 'all', page];
  };

  const getCandidatesQueryFn = () => {
    if (activeTab === 'pending-review') { // Added
      return () => invitationApi.getSubmittedInvitations({ page, per_page: 20 });
    } else if (activeTab === 'pending-assignment') {
      return () => onboardingApi.getPendingCandidates({ page, per_page: 20, status: 'PENDING_ASSIGNMENT' });
    } else if (activeTab === 'pending-onboarding') {
      return () => onboardingApi.getPendingCandidates({ page, per_page: 20, status: 'ASSIGNED,PENDING_ONBOARDING' });
    }
    return () => onboardingApi.getPendingCandidates({ page, per_page: 20 });
  };

  const {
    data: candidatesData,
    isLoading: isLoadingCandidates,
    error: candidatesError,
  } = useQuery({
    queryKey: getCandidatesQueryKey(),
    queryFn: getCandidatesQueryFn(),
    enabled: canViewCandidates && activeTab !== 'pending-review', // Modified enabled
  });

  // Fetch available users for assignment
  const { data: availableUsersData } = useQuery({
    queryKey: ['available-managers'],
    queryFn: () => teamApi.getAvailableManagers(),
    enabled: assignDialogOpen && canOnboardCandidates,
  });

  // Assign candidate mutation
  const assignMutation = useMutation({
    mutationFn: candidateAssignmentApi.assignCandidate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pending-assignment-candidates'] });
      queryClient.invalidateQueries({ queryKey: ['onboarding-stats'] });
      toast.success('Candidate assigned successfully');
      setAssignDialogOpen(false);
      setSelectedCandidate(null);
      setSelectedUserId('');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to assign candidate');
    },
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

  // Approve invitation mutation
  const approveInvitationMutation = useMutation({
    mutationFn: (invitationId: number) => invitationApi.approve(invitationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['submitted-invitations'] });
      queryClient.invalidateQueries({ queryKey: ['onboarding-stats'] });
      toast.success('Invitation approved and candidate created');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to approve invitation');
    },
  });

  // Reject invitation mutation
  const rejectInvitationMutation = useMutation({
    mutationFn: (data: { invitationId: number; rejectionReason: string }) => 
      invitationApi.reject(data.invitationId, { rejection_reason: data.rejectionReason }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['submitted-invitations'] });
      queryClient.invalidateQueries({ queryKey: ['onboarding-stats'] });
      toast.success('Invitation rejected');
      setRejectDialogOpen(false);
      setSelectedCandidate(null);
      setRejectionReason('');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to reject invitation');
    },
  });

  // Handle assign candidate
  const handleAssign = (candidate: CandidateOnboardingInfo) => {
    setSelectedCandidate(candidate);
    setAssignDialogOpen(true);
  };

  // Confirm assign
  const confirmAssign = () => {
    if (!selectedCandidate || !selectedUserId) {
      toast.error('Please select a user to assign');
      return;
    }
    assignMutation.mutate({
      candidate_id: selectedCandidate.id,
      assigned_to_user_id: parseInt(selectedUserId),
    });
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
    // Check if selectedCandidate is an invitation or a candidate
    if ('email' in selectedCandidate && !('onboarding_status' in selectedCandidate)) { // Assuming invitations have email but not onboarding_status
      rejectInvitationMutation.mutate({
        invitationId: selectedCandidate.id,
        rejectionReason: rejectionReason.trim(),
      });
    } else {
      rejectMutation.mutate({
        candidate_id: selectedCandidate.id,
        rejection_reason: rejectionReason.trim(),
      });
    }
  };

  // Handle approve invitation
  const handleApproveInvitation = (invitationId: number) => {
    approveInvitationMutation.mutate(invitationId);
  };

  // Handle reject invitation
  const handleRejectInvitation = (invitationId: number) => {
    setSelectedCandidate({ id: invitationId } as CandidateOnboardingInfo); // Use selectedCandidate state for dialog
    setRejectionReason(''); // Clear any previous rejection reason
    setRejectDialogOpen(true);
  };

  // Handle view candidate
  const handleViewCandidate = (candidateId: number) => {
    navigate(`/candidates/${candidateId}`);
  };

  // Filter candidates by search query (only for non-pending-review tabs)
  const filteredCandidates = activeTab !== 'pending-review' 
    ? (candidatesData?.candidates.filter((candidate) => {
        if (!searchQuery) return true;
        const query = searchQuery.toLowerCase();
        return (
          candidate.first_name.toLowerCase().includes(query) ||
          candidate.last_name.toLowerCase().includes(query) ||
          candidate.email.toLowerCase().includes(query)
        );
      }) || [])
    : [];

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
      {/* Page Header with contextual help */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <ClipboardList className="h-5 w-5 text-blue-600 mt-0.5" />
          <div>
            <h3 className="font-semibold text-slate-900">Review & Approve Candidate Submissions</h3>
            <p className="text-sm text-slate-600 mt-1">
              Review candidate submissions, approve qualified candidates, and manage the onboarding workflow.
            </p>
          </div>
        </div>
      </div>

      {/* Tabs and Content */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Candidate Pipeline</CardTitle>
              <CardDescription className="mt-1.5">
                {activeTab === 'pending-review' && 'Review submitted applications and approve qualified candidates'}
                {activeTab === 'pending-assignment' && 'Assign approved candidates to recruiters or managers'}
                {activeTab === 'pending-onboarding' && 'Monitor candidates in the onboarding process'}
                {activeTab === 'all' && 'View all candidates across all stages'}
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <Tabs value={activeTab} onValueChange={(value) => {
            setActiveTab(value as TabValue);
            setPage(1);
            setSearchQuery('');
          }}>
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="pending-review" className="gap-2">
                <Mail className="h-3.5 w-3.5" />
                Review Submissions
                {stats.pending_review > 0 && (
                  <Badge variant="secondary" className="ml-1 bg-amber-100 text-amber-700 hover:bg-amber-100">
                    {stats.pending_review}
                  </Badge>
                )}
              </TabsTrigger>
              <TabsTrigger value="pending-assignment" className="gap-2">
                <UserPlus className="h-3.5 w-3.5" />
                Ready to Assign
                {stats.pending_assignment > 0 && (
                  <Badge variant="secondary" className="ml-1">{stats.pending_assignment}</Badge>
                )}
              </TabsTrigger>
              <TabsTrigger value="pending-onboarding" className="gap-2">
                <Clock className="h-3.5 w-3.5" />
                In Progress
                {stats.pending_onboarding > 0 && (
                  <Badge variant="secondary" className="ml-1">{stats.pending_onboarding}</Badge>
                )}
              </TabsTrigger>
              <TabsTrigger value="all" className="gap-2">
                <Users className="h-3.5 w-3.5" />
                All ({stats.total})
              </TabsTrigger>
            </TabsList>

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
                  queryClient.invalidateQueries({ queryKey: getCandidatesQueryKey() });
                  queryClient.invalidateQueries({ queryKey: ['onboarding-stats'] });
                }}
                disabled={isLoadingCandidates}
              >
                <RefreshCw className={`h-4 w-4 ${isLoadingCandidates ? 'animate-spin' : ''}`} />
              </Button>
            </div>

            <TabsContent value="pending-review" className="mt-0">
              <div className="space-y-6">
                {/* Async Resume Uploads Section */}
                {(isLoadingPendingReviewCandidates || (pendingReviewCandidatesData && pendingReviewCandidatesData.candidates.length > 0)) && (
                  <div>
                    <h3 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
                      <Upload className="h-4 w-4" />
                      Resume Uploads (AI Parsed)
                      {pendingReviewCandidatesData && pendingReviewCandidatesData.total > 0 && (
                        <Badge variant="secondary" className="bg-yellow-100 text-yellow-800">
                          {pendingReviewCandidatesData.total}
                        </Badge>
                      )}
                    </h3>
                    {isLoadingPendingReviewCandidates ? (
                      <div className="space-y-2">
                        <Skeleton className="h-12 w-full" />
                        <Skeleton className="h-12 w-full" />
                      </div>
                    ) : pendingReviewCandidatesData && pendingReviewCandidatesData.candidates.length > 0 ? (
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Name</TableHead>
                            <TableHead>Email</TableHead>
                            <TableHead>Source</TableHead>
                            <TableHead>Uploaded At</TableHead>
                            <TableHead className="text-right">Actions</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {pendingReviewCandidatesData.candidates.map((candidate: Candidate) => (
                            <TableRow key={`resume-${candidate.id}`}>
                              <TableCell className="font-medium">
                                {candidate.first_name} {candidate.last_name}
                              </TableCell>
                              <TableCell>{candidate.email || '—'}</TableCell>
                              <TableCell>
                                <Badge variant="outline" className="bg-yellow-50">Resume Upload</Badge>
                              </TableCell>
                              <TableCell>
                                <div className="text-sm text-slate-600">
                                  {candidate.resume_uploaded_at ? formatDate(candidate.resume_uploaded_at) : '—'}
                                </div>
                              </TableCell>
                              <TableCell className="text-right">
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => {
                                    setSelectedResumeCandidate(candidate);
                                    setReviewModalOpen(true);
                                  }}
                                  className="gap-2"
                                >
                                  <Eye className="h-4 w-4" />
                                  Review & Approve
                                </Button>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    ) : null}
                  </div>
                )}

                {/* Self-Onboarding Invitations Section */}
                <div>
                  <h3 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
                    <Mail className="h-4 w-4" />
                    Self-Onboarding Submissions
                    {submittedInvitationsData && submittedInvitationsData.total > 0 && (
                      <Badge variant="secondary" className="bg-blue-100 text-blue-800">
                        {submittedInvitationsData.total}
                      </Badge>
                    )}
                  </h3>
                  {isLoadingSubmittedInvitations ? (
                    <div className="space-y-2">
                      <Skeleton className="h-12 w-full" />
                      <Skeleton className="h-12 w-full" />
                      <Skeleton className="h-12 w-full" />
                    </div>
                  ) : submittedInvitationsError ? (
                    <Alert variant="destructive">
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription>
                        Failed to load submitted invitations. Please try again.
                      </AlertDescription>
                    </Alert>
                  ) : submittedInvitationsData?.items.length > 0 ? (
                    <>
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Name</TableHead>
                            <TableHead>Email</TableHead>
                            <TableHead>Position</TableHead>
                            <TableHead>Status</TableHead>
                            <TableHead>Submitted At</TableHead>
                            <TableHead className="text-right">Actions</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {submittedInvitationsData.items.map((invitation) => (
                            <TableRow key={`invitation-${invitation.id}`}>
                              <TableCell className="font-medium">
                                {invitation.first_name} {invitation.last_name}
                              </TableCell>
                              <TableCell>{invitation.email}</TableCell>
                              <TableCell>{invitation.position || '—'}</TableCell>
                              <TableCell>
                                <Badge variant="outline">
                                  {invitation.status.replace(/_/g, ' ')}
                                </Badge>
                              </TableCell>
                              <TableCell>
                                <div className="text-sm text-slate-600">
                                  {formatDate(invitation.submitted_at)}
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
                                    <DropdownMenuItem onClick={() => navigate(`/invitations/${invitation.id}/review`)}>
                                      <Eye className="h-4 w-4 mr-2" />
                                      Review Submission
                                    </DropdownMenuItem>
                                    {canApproveCandidates && (
                                      <>
                                        <DropdownMenuSeparator />
                                        <DropdownMenuItem onClick={() => handleApproveInvitation(invitation.id)}>
                                          <CheckCircle2 className="h-4 w-4 mr-2 text-green-600" />
                                          Approve
                                        </DropdownMenuItem>
                                        <DropdownMenuItem onClick={() => handleRejectInvitation(invitation.id)} className="text-red-600">
                                          <XCircle className="h-4 w-4 mr-2" />
                                          Reject
                                        </DropdownMenuItem>
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
                      {submittedInvitationsData && submittedInvitationsData.pages > 1 && (
                        <div className="flex items-center justify-between mt-4 pt-4 border-t">
                          <div className="text-sm text-slate-600">
                            Page {submittedInvitationsData.page} of {submittedInvitationsData.pages}
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
                              disabled={page === submittedInvitationsData.pages}
                            >
                              Next
                            </Button>
                          </div>
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="text-center py-8 text-slate-500">
                      <Mail className="h-10 w-10 mx-auto mb-3 text-slate-300" />
                      <p className="text-sm">No self-onboarding submissions found</p>
                    </div>
                  )}
                </div>

                {/* Empty State - Both sources empty */}
                {!isLoadingSubmittedInvitations && 
                 !isLoadingPendingReviewCandidates && 
                 (!submittedInvitationsData || submittedInvitationsData.items.length === 0) &&
                 (!pendingReviewCandidatesData || pendingReviewCandidatesData.candidates.length === 0) && (
                  <div className="text-center py-12 text-slate-500 border-2 border-dashed border-slate-200 rounded-lg">
                    <ClipboardList className="h-12 w-12 mx-auto mb-4 text-slate-300" />
                    <p className="text-lg font-medium">No Submissions Pending Review</p>
                    <p className="text-sm mt-1">
                      Resume uploads and self-onboarding submissions will appear here
                    </p>
                  </div>
                )}
              </div>
            </TabsContent>

            <TabsContent value="pending-assignment" className="mt-0">
              {isLoadingCandidates ? (
                <div className="space-y-2">
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                </div>
              ) : candidatesError ? (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    Failed to load candidates. Please try again.
                  </AlertDescription>
                </Alert>
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
                            <Badge
                              className={
                                ONBOARDING_STATUS_COLORS[candidate.onboarding_status] ||
                                'bg-gray-100 text-gray-800'
                              }
                            >
                              {candidate.onboarding_status.replace(/_/g, ' ')}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            {candidate.recruiter ? (
                              <span className="text-sm">
                                {candidate.recruiter.first_name} {candidate.recruiter.last_name}
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
                                {getActionButtons(candidate).length > 0 && (
                                  <>
                                    <DropdownMenuSeparator />
                                    {getActionButtons(candidate)}
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
                  {candidatesData && candidatesData.total_pages > 1 && (
                    <div className="flex items-center justify-between mt-4 pt-4 border-t">
                      <div className="text-sm text-slate-600">
                        Page {candidatesData.page} of {candidatesData.total_pages}
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
                          disabled={page === candidatesData.total_pages}
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

            <TabsContent value="pending-onboarding" className="mt-0">
              {isLoadingCandidates ? (
                <div className="space-y-2">
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                </div>
              ) : candidatesError ? (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    Failed to load candidates. Please try again.
                  </AlertDescription>
                </Alert>
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
                            <Badge
                              className={
                                ONBOARDING_STATUS_COLORS[candidate.onboarding_status] ||
                                'bg-gray-100 text-gray-800'
                              }
                            >
                              {candidate.onboarding_status.replace(/_/g, ' ')}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            {candidate.recruiter ? (
                              <span className="text-sm">
                                {candidate.recruiter.first_name} {candidate.recruiter.last_name}
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
                                {getActionButtons(candidate).length > 0 && (
                                  <>
                                    <DropdownMenuSeparator />
                                    {getActionButtons(candidate)}
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
                  {candidatesData && candidatesData.total_pages > 1 && (
                    <div className="flex items-center justify-between mt-4 pt-4 border-t">
                      <div className="text-sm text-slate-600">
                        Page {candidatesData.page} of {candidatesData.total_pages}
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
                          disabled={page === candidatesData.total_pages}
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

            <TabsContent value="all" className="mt-0">
              {isLoadingCandidates ? (
                <div className="space-y-2">
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                </div>
              ) : candidatesError ? (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    Failed to load candidates. Please try again.
                  </AlertDescription>
                </Alert>
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
                            <Badge
                              className={
                                ONBOARDING_STATUS_COLORS[candidate.onboarding_status] ||
                                'bg-gray-100 text-gray-800'
                              }
                            >
                              {candidate.onboarding_status.replace(/_/g, ' ')}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            {candidate.recruiter ? (
                              <span className="text-sm">
                                {candidate.recruiter.first_name} {candidate.recruiter.last_name}
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
                                {getActionButtons(candidate).length > 0 && (
                                  <>
                                    <DropdownMenuSeparator />
                                    {getActionButtons(candidate)}
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
                  {candidatesData && candidatesData.total_pages > 1 && (
                    <div className="flex items-center justify-between mt-4 pt-4 border-t">
                      <div className="text-sm text-slate-600">
                        Page {candidatesData.page} of {candidatesData.total_pages}
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
                          disabled={page === candidatesData.total_pages}
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
          </Tabs>
        </CardContent>
      </Card>

      {/* Assign Dialog */}
      <Dialog open={assignDialogOpen} onOpenChange={setAssignDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Assign Candidate</DialogTitle>
            <DialogDescription>
              Assign {selectedCandidate?.first_name} {selectedCandidate?.last_name} to a user for
              onboarding
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Select User</label>
              <Select value={selectedUserId} onValueChange={setSelectedUserId}>
                <SelectTrigger>
                  <SelectValue placeholder="Choose a user" />
                </SelectTrigger>
                <SelectContent>
                  {availableUsersData?.managers.map((user) => (
                    <SelectItem key={user.id} value={user.id.toString()}>
                      {user.first_name} {user.last_name} ({user.email})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setAssignDialogOpen(false);
                setSelectedCandidate(null);
                setSelectedUserId('');
              }}
            >
              Cancel
            </Button>
            <Button onClick={confirmAssign} disabled={assignMutation.isPending || !selectedUserId}>
              {assignMutation.isPending ? 'Assigning...' : 'Assign'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

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
          candidate={selectedResumeCandidate}
          open={reviewModalOpen}
          onOpenChange={setReviewModalOpen}
          onSuccess={() => {
            queryClient.invalidateQueries({ queryKey: ['candidates-pending-review'] });
            queryClient.invalidateQueries({ queryKey: ['onboarding-stats'] });
            setSelectedResumeCandidate(null);
          }}
        />
      )}
    </div>
  );
}
