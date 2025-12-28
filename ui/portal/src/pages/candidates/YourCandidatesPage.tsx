/**
 * Your Candidates Page
 * View and manage candidates assigned to the current user
 */

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
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
  Bell,
  UserCheck,
  UserX,
  MoreVertical,
  Eye,
  Search,
  Filter,
  RefreshCw,
} from 'lucide-react';
import { toast } from 'sonner';
import { candidateAssignmentApi } from '@/lib/candidateAssignmentApi';
import { usePermissions } from '@/hooks/usePermissions';
import type { AssignmentStatus, CandidateInfo } from '@/types';

const ONBOARDING_STATUS_COLORS: Record<string, string> = {
  PENDING_ASSIGNMENT: 'bg-gray-100 text-gray-800',
  ASSIGNED: 'bg-blue-100 text-blue-800',
  PENDING_ONBOARDING: 'bg-yellow-100 text-yellow-800',
  ONBOARDED: 'bg-purple-100 text-purple-800',
  APPROVED: 'bg-green-100 text-green-800',
  REJECTED: 'bg-red-100 text-red-800',
};

const ASSIGNMENT_STATUS_COLORS: Record<AssignmentStatus, string> = {
  ACTIVE: 'bg-green-100 text-green-800',
  COMPLETED: 'bg-gray-100 text-gray-800',
  CANCELLED: 'bg-red-100 text-red-800',
};

export function YourCandidatesPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { hasPermission } = usePermissions();
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [includeCompleted, setIncludeCompleted] = useState(false);
  const [unassignDialogOpen, setUnassignDialogOpen] = useState(false);
  const [selectedCandidate, setSelectedCandidate] = useState<CandidateInfo | null>(null);
  const [notificationBadgeOpen, setNotificationBadgeOpen] = useState(false);

  // Permission checks - Recruiters have candidates.view_assigned, Managers/HR have candidates.view
  const canViewCandidates = hasPermission('candidates.view_assigned') || hasPermission('candidates.view');
  const canAssignCandidates = hasPermission('candidates.assign');

  // Fetch assigned candidates
  const {
    data: candidatesData,
    isLoading: isLoadingCandidates,
    error: candidatesError,
  } = useQuery({
    queryKey: ['my-assigned-candidates', statusFilter, includeCompleted],
    queryFn: () =>
      candidateAssignmentApi.getMyAssignedCandidates({
        status: statusFilter !== 'all' ? (statusFilter as AssignmentStatus) : undefined,
        include_completed: includeCompleted,
      }),
    enabled: canViewCandidates,
  });

  // Fetch notifications
  const {
    data: notificationsData,
    isLoading: isLoadingNotifications,
  } = useQuery({
    queryKey: ['assignment-notifications'],
    queryFn: () =>
      candidateAssignmentApi.getUserNotifications({
        unread_only: false,
        limit: 20,
      }),
    refetchInterval: 30000, // Poll every 30 seconds
  });

  // Unassign candidate mutation
  const unassignMutation = useMutation({
    mutationFn: candidateAssignmentApi.unassignCandidate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my-assigned-candidates'] });
      queryClient.invalidateQueries({ queryKey: ['assignment-notifications'] });
      toast.success('Candidate unassigned successfully');
      setUnassignDialogOpen(false);
      setSelectedCandidate(null);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to unassign candidate');
    },
  });

  // Mark notification as read mutation
  const markReadMutation = useMutation({
    mutationFn: candidateAssignmentApi.markNotificationAsRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assignment-notifications'] });
    },
  });

  // Mark all notifications as read
  const markAllReadMutation = useMutation({
    mutationFn: candidateAssignmentApi.markAllNotificationsAsRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assignment-notifications'] });
      toast.success('All notifications marked as read');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to mark notifications as read');
    },
  });

  // Handle view candidate
  const handleViewCandidate = (candidateId: number) => {
    navigate(`/candidates/${candidateId}`);
  };

  // Handle unassign
  const handleUnassign = (candidate: CandidateInfo) => {
    setSelectedCandidate(candidate);
    setUnassignDialogOpen(true);
  };

  // Confirm unassign
  const confirmUnassign = () => {
    if (!selectedCandidate) return;
    unassignMutation.mutate({
      candidate_id: selectedCandidate.id,
    });
  };

  // Handle notification click
  const handleNotificationClick = (notificationId: number) => {
    markReadMutation.mutate({ notification_id: notificationId });
  };

  // Filter candidates by search query
  const filteredCandidates = candidatesData?.candidates.filter((candidate) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      candidate.first_name.toLowerCase().includes(query) ||
      candidate.last_name.toLowerCase().includes(query) ||
      candidate.email.toLowerCase().includes(query)
    );
  }) || [];

  // Calculate stats
  const stats = {
    total: candidatesData?.candidates.length || 0,
    active: candidatesData?.candidates.filter(
      (c) => c.current_assignment?.status === 'ACTIVE'
    ).length || 0,
    onboarded: candidatesData?.candidates.filter(
      (c) => c.onboarding_status === 'ONBOARDED'
    ).length || 0,
  };

  const unreadCount = notificationsData?.unread_count || 0;

  if (!canViewCandidates) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Your Candidates</h1>
          <p className="text-slate-600 mt-1">Manage candidates assigned to you</p>
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

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Your Candidates</h1>
          <p className="text-slate-600 mt-1">Manage candidates assigned to you</p>
        </div>

        {/* Notifications Button */}
        <div className="relative">
          <Button
            variant="outline"
            size="sm"
            className="gap-2"
            onClick={() => setNotificationBadgeOpen(!notificationBadgeOpen)}
          >
            <Bell className="h-4 w-4" />
            Notifications
            {unreadCount > 0 && (
              <Badge variant="destructive" className="ml-1 px-1.5 py-0 text-xs">
                {unreadCount}
              </Badge>
            )}
          </Button>

          {/* Notifications Dropdown */}
          {notificationBadgeOpen && (
            <Card className="absolute right-0 top-12 w-96 z-50 shadow-lg">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">Notifications</CardTitle>
                  {unreadCount > 0 && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => markAllReadMutation.mutate()}
                      disabled={markAllReadMutation.isPending}
                    >
                      Mark all read
                    </Button>
                  )}
                </div>
              </CardHeader>
              <CardContent className="max-h-96 overflow-y-auto">
                {isLoadingNotifications ? (
                  <div className="space-y-2">
                    <Skeleton className="h-16 w-full" />
                    <Skeleton className="h-16 w-full" />
                  </div>
                ) : notificationsData && notificationsData.notifications.length > 0 ? (
                  <div className="space-y-2">
                    {notificationsData.notifications.map((notification) => (
                      <div
                        key={notification.id}
                        className={`p-3 rounded-lg border cursor-pointer hover:bg-slate-50 transition-colors ${
                          !notification.is_read ? 'bg-blue-50 border-blue-200' : 'bg-white'
                        }`}
                        onClick={() => handleNotificationClick(notification.id)}
                      >
                        <div className="flex items-start gap-3">
                          <div className="flex-1">
                            <p className="text-sm font-medium text-slate-900">
                              Candidate Assignment
                            </p>
                            {notification.assignment && (
                              <p className="text-sm text-slate-600 mt-1">
                                You've been assigned to{' '}
                                {notification.assignment.candidate?.first_name}{' '}
                                {notification.assignment.candidate?.last_name}
                              </p>
                            )}
                            <p className="text-xs text-slate-500 mt-1">
                              {new Date(notification.created_at).toLocaleString()}
                            </p>
                          </div>
                          {!notification.is_read && (
                            <div className="w-2 h-2 bg-blue-500 rounded-full mt-1" />
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-slate-500">
                    <Bell className="h-12 w-12 mx-auto mb-3 text-slate-300" />
                    <p>No notifications</p>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2 flex flex-row items-center justify-between">
            <CardDescription>Total Assigned</CardDescription>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <CardTitle className="text-3xl">
              {isLoadingCandidates ? <Skeleton className="h-9 w-12" /> : stats.total}
            </CardTitle>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2 flex flex-row items-center justify-between">
            <CardDescription>Active Assignments</CardDescription>
            <UserCheck className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <CardTitle className="text-3xl">
              {isLoadingCandidates ? <Skeleton className="h-9 w-12" /> : stats.active}
            </CardTitle>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2 flex flex-row items-center justify-between">
            <CardDescription>Onboarded</CardDescription>
            <UserCheck className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <CardTitle className="text-3xl">
              {isLoadingCandidates ? <Skeleton className="h-9 w-12" /> : stats.onboarded}
            </CardTitle>
          </CardContent>
        </Card>
      </div>

      {/* Filters and Search */}
      <Card>
        <CardHeader>
          <CardTitle>Assigned Candidates</CardTitle>
          <CardDescription>View and manage your assigned candidates</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col md:flex-row gap-4 mb-6">
            {/* Search */}
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

            {/* Status Filter */}
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-full md:w-48">
                <SelectValue placeholder="Filter by status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                <SelectItem value="ACTIVE">Active</SelectItem>
                <SelectItem value="COMPLETED">Completed</SelectItem>
                <SelectItem value="CANCELLED">Cancelled</SelectItem>
              </SelectContent>
            </Select>

            {/* Include Completed Toggle */}
            <Button
              variant={includeCompleted ? 'default' : 'outline'}
              onClick={() => setIncludeCompleted(!includeCompleted)}
              className="gap-2"
            >
              <Filter className="h-4 w-4" />
              {includeCompleted ? 'Hide' : 'Show'} Completed
            </Button>

            {/* Refresh */}
            <Button
              variant="outline"
              size="icon"
              onClick={() => queryClient.invalidateQueries({ queryKey: ['my-assigned-candidates'] })}
              disabled={isLoadingCandidates}
            >
              <RefreshCw className={`h-4 w-4 ${isLoadingCandidates ? 'animate-spin' : ''}`} />
            </Button>
          </div>

          {/* Candidates Table */}
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
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Phone</TableHead>
                  <TableHead>Onboarding Status</TableHead>
                  <TableHead>Assignment Status</TableHead>
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
                      {candidate.current_assignment && (
                        <Badge
                          className={
                            ASSIGNMENT_STATUS_COLORS[candidate.current_assignment.status]
                          }
                        >
                          {candidate.current_assignment.status}
                        </Badge>
                      )}
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
                          {canAssignCandidates &&
                            candidate.current_assignment?.status === 'ACTIVE' && (
                              <>
                                <DropdownMenuSeparator />
                                <DropdownMenuItem
                                  onClick={() => handleUnassign(candidate)}
                                  className="text-red-600"
                                >
                                  <UserX className="h-4 w-4 mr-2" />
                                  Unassign
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
          ) : (
            <div className="text-center py-12 text-slate-500">
              <Users className="h-12 w-12 mx-auto mb-4 text-slate-300" />
              <p className="text-lg font-medium">No candidates assigned</p>
              <p className="text-sm mt-1">
                {searchQuery
                  ? 'Try adjusting your search'
                  : 'Candidates assigned to you will appear here'}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Unassign Dialog */}
      <Dialog open={unassignDialogOpen} onOpenChange={setUnassignDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Unassign Candidate</DialogTitle>
            <DialogDescription>
              Are you sure you want to unassign {selectedCandidate?.first_name}{' '}
              {selectedCandidate?.last_name}? This will remove your assignment and reset their
              onboarding status.
            </DialogDescription>
          </DialogHeader>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setUnassignDialogOpen(false);
                setSelectedCandidate(null);
              }}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={confirmUnassign}
              disabled={unassignMutation.isPending}
            >
              {unassignMutation.isPending ? 'Unassigning...' : 'Unassign'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Click outside to close notifications */}
      {notificationBadgeOpen && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setNotificationBadgeOpen(false)}
        />
      )}
    </div>
  );
}
