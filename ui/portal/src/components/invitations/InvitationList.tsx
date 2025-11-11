/**
 * InvitationList Component
 * DataTable with filters, search, and pagination for viewing invitations
 */

import { useState } from 'react';
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
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
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
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  MoreHorizontal,
  Mail,
  CheckCircle2,
  XCircle,
  Clock,
  Ban,
  AlertCircle,
  Eye,
  Send,
  Trash2,
  Search,
} from 'lucide-react';
import { format } from 'date-fns';
import { useInvitations } from '@/hooks/useInvitations';
import { useResendInvitation, useCancelInvitation } from '@/hooks/useInvitations';
import { Skeleton } from '@/components/ui/skeleton';
import { Empty, EmptyHeader, EmptyMedia, EmptyTitle, EmptyDescription } from '@/components/ui/empty';
import type { InvitationStatus, InvitationListParams } from '@/types';

interface InvitationListProps {
  onViewDetails: (id: number) => void;
  onCreateNew?: () => void;
}

const STATUS_CONFIG: Record<
  InvitationStatus,
  { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline'; icon: typeof Mail }
> = {
  sent: { label: 'Sent', variant: 'default', icon: Mail },
  pending_review: { label: 'Pending Review', variant: 'secondary', icon: Clock },
  approved: { label: 'Approved', variant: 'outline', icon: CheckCircle2 },
  rejected: { label: 'Rejected', variant: 'destructive', icon: XCircle },
  cancelled: { label: 'Cancelled', variant: 'outline', icon: Ban },
  expired: { label: 'Expired', variant: 'destructive', icon: AlertCircle },
};

export function InvitationList({ onViewDetails, onCreateNew }: InvitationListProps) {
  const [params, setParams] = useState<InvitationListParams>({
    page: 1,
    per_page: 10,
    sort_by: 'invited_at',
    sort_order: 'desc',
  });

  const { data, isLoading, error } = useInvitations(params);
  const resendMutation = useResendInvitation();
  const cancelMutation = useCancelInvitation();

  const handleSearch = (search: string) => {
    setParams((prev) => ({ ...prev, search: search || undefined, page: 1 }));
  };

  const handleStatusFilter = (status: string) => {
    setParams((prev) => ({
      ...prev,
      status: status === 'all' ? undefined : (status as InvitationStatus),
      page: 1,
    }));
  };

  const handlePageChange = (page: number) => {
    setParams((prev) => ({ ...prev, page }));
  };

  const handleResend = (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    resendMutation.mutate(id);
  };

  const handleCancel = (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm('Are you sure you want to cancel this invitation?')) {
      cancelMutation.mutate(id);
    }
  };

  if (isLoading) {
    return <InvitationListSkeleton />;
  }

  if (error) {
    return (
      <Card>
        <CardContent className="py-8">
          <Empty>
            <EmptyHeader>
              <EmptyMedia variant="icon">
                <AlertCircle className="size-6" />
              </EmptyMedia>
              <EmptyTitle>Failed to load invitations</EmptyTitle>
              <EmptyDescription>{error.message}</EmptyDescription>
            </EmptyHeader>
          </Empty>
        </CardContent>
      </Card>
    );
  }

  const invitations = data?.items || [];
  const hasInvitations = invitations.length > 0;

  return (
    <div className="space-y-4">
      {/* Header & Filters */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Candidate Invitations</CardTitle>
              <CardDescription>
                Manage and track candidate onboarding invitations
              </CardDescription>
            </div>
            {onCreateNew && (
              <Button onClick={onCreateNew}>
                <Mail className="mr-2 h-4 w-4" />
                Send Invitation
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-4 md:flex-row md:items-center">
            {/* Search */}
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search by email or name..."
                className="pl-9"
                value={params.search || ''}
                onChange={(e) => handleSearch(e.target.value)}
              />
            </div>

            {/* Status Filter */}
            <Select
              value={params.status || 'all'}
              onValueChange={handleStatusFilter}
            >
              <SelectTrigger className="w-full md:w-[180px]">
                <SelectValue placeholder="Filter by status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                <SelectItem value="sent">Sent</SelectItem>
                <SelectItem value="pending_review">Pending Review</SelectItem>
                <SelectItem value="approved">Approved</SelectItem>
                <SelectItem value="rejected">Rejected</SelectItem>
                <SelectItem value="cancelled">Cancelled</SelectItem>
                <SelectItem value="expired">Expired</SelectItem>
              </SelectContent>
            </Select>

            {/* Sort */}
            <Select
              value={`${params.sort_by}-${params.sort_order}`}
              onValueChange={(value) => {
                const [sort_by, sort_order] = value.split('-') as [string, 'asc' | 'desc'];
                setParams((prev) => ({ ...prev, sort_by, sort_order }));
              }}
            >
              <SelectTrigger className="w-full md:w-[180px]">
                <SelectValue placeholder="Sort by" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="invited_at-desc">Newest First</SelectItem>
                <SelectItem value="invited_at-asc">Oldest First</SelectItem>
                <SelectItem value="email-asc">Email A-Z</SelectItem>
                <SelectItem value="email-desc">Email Z-A</SelectItem>
                <SelectItem value="expires_at-asc">Expiring Soon</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          {!hasInvitations ? (
            <div className="py-12">
              <Empty>
                <EmptyHeader>
                  <EmptyMedia variant="icon">
                    <Mail className="size-6" />
                  </EmptyMedia>
                  <EmptyTitle>No invitations found</EmptyTitle>
                  <EmptyDescription>
                    {params.search || params.status
                      ? 'Try adjusting your filters'
                      : 'Send your first invitation to get started'}
                  </EmptyDescription>
                </EmptyHeader>
              </Empty>
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Candidate</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Invited By</TableHead>
                    <TableHead>Invited At</TableHead>
                    <TableHead>Expires At</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {invitations.map((invitation) => {
                    const config = STATUS_CONFIG[invitation.status];
                    const Icon = config.icon;
                    const isExpired = new Date(invitation.expires_at) < new Date();
                    const canResend = ['sent', 'expired', 'cancelled'].includes(invitation.status);
                    const canCancel = ['sent', 'pending_review'].includes(invitation.status);

                    return (
                      <TableRow
                        key={invitation.id}
                        className="cursor-pointer hover:bg-muted/50"
                        onClick={() => onViewDetails(invitation.id)}
                      >
                        <TableCell>
                          <div className="flex flex-col">
                            <span className="font-medium">
                              {invitation.first_name || invitation.last_name
                                ? `${invitation.first_name || ''} ${invitation.last_name || ''}`.trim()
                                : 'N/A'}
                            </span>
                            <span className="text-sm text-muted-foreground">
                              {invitation.email}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant={config.variant} className="flex w-fit items-center gap-1">
                            <Icon className="h-3 w-3" />
                            {config.label}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-col">
                            <span className="text-sm">
                              {invitation.invited_by?.first_name || invitation.invited_by?.email || 'N/A'}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <span className="text-sm text-muted-foreground">
                            {format(new Date(invitation.invited_at), 'MMM dd, yyyy')}
                          </span>
                        </TableCell>
                        <TableCell>
                          <span
                            className={`text-sm ${
                              isExpired ? 'text-destructive font-medium' : 'text-muted-foreground'
                            }`}
                          >
                            {format(new Date(invitation.expires_at), 'MMM dd, yyyy')}
                          </span>
                        </TableCell>
                        <TableCell className="text-right">
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                              <Button variant="ghost" size="icon">
                                <MoreHorizontal className="h-4 w-4" />
                                <span className="sr-only">Open menu</span>
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuLabel>Actions</DropdownMenuLabel>
                              <DropdownMenuItem onClick={() => onViewDetails(invitation.id)}>
                                <Eye className="mr-2 h-4 w-4" />
                                View Details
                              </DropdownMenuItem>
                              {canResend && (
                                <>
                                  <DropdownMenuSeparator />
                                  <DropdownMenuItem
                                    onClick={(e) => handleResend(invitation.id, e)}
                                    disabled={resendMutation.isPending}
                                  >
                                    <Send className="mr-2 h-4 w-4" />
                                    Resend Invitation
                                  </DropdownMenuItem>
                                </>
                              )}
                              {canCancel && (
                                <>
                                  <DropdownMenuSeparator />
                                  <DropdownMenuItem
                                    onClick={(e) => handleCancel(invitation.id, e)}
                                    disabled={cancelMutation.isPending}
                                    className="text-destructive"
                                  >
                                    <Trash2 className="mr-2 h-4 w-4" />
                                    Cancel Invitation
                                  </DropdownMenuItem>
                                </>
                              )}
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>

              {/* Pagination */}
              {data && data.pages > 1 && (
                <div className="flex items-center justify-between border-t px-4 py-4">
                  <div className="text-sm text-muted-foreground">
                    Showing {(data.page - 1) * data.per_page + 1} to{' '}
                    {Math.min(data.page * data.per_page, data.total)} of {data.total} invitations
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handlePageChange(params.page! - 1)}
                      disabled={params.page === 1}
                    >
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handlePageChange(params.page! + 1)}
                      disabled={params.page === data.pages}
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
    </div>
  );
}

function InvitationListSkeleton() {
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-4 w-96" />
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <Skeleton className="h-10 flex-1" />
            <Skeleton className="h-10 w-[180px]" />
            <Skeleton className="h-10 w-[180px]" />
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="p-6">
          <div className="space-y-4">
            {[...Array(5)].map((_, i) => (
              <Skeleton key={i} className="h-16 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
