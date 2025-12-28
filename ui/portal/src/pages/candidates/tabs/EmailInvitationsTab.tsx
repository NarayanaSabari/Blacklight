/**
 * Email Invitations Tab
 * Unified layout: Search/Filter bar → Table → Pagination
 * Manages candidate email invitations
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
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
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Search,
  MoreHorizontal,
  Mail,
  Eye,
  Send,
  Ban,
  CheckCircle2,
  XCircle,
  Clock,
  AlertCircle,
  Plus,
} from 'lucide-react';
import { toast } from 'sonner';
import { invitationApi } from '@/lib/api/invitationApi';
import { InvitationForm } from '@/components/invitations/InvitationForm';
import type { InvitationStatus, InvitationListParams } from '@/types';

const STATUS_CONFIG: Record<InvitationStatus, { label: string; className: string; icon: typeof Mail }> = {
  sent: { label: 'Sent', className: 'bg-blue-100 text-blue-800', icon: Mail },
  opened: { label: 'Opened', className: 'bg-indigo-100 text-indigo-800', icon: Mail },
  in_progress: { label: 'In Progress', className: 'bg-yellow-100 text-yellow-800', icon: Clock },
  pending_review: { label: 'Pending Review', className: 'bg-orange-100 text-orange-800', icon: Clock },
  approved: { label: 'Approved', className: 'bg-green-100 text-green-800', icon: CheckCircle2 },
  rejected: { label: 'Rejected', className: 'bg-red-100 text-red-800', icon: XCircle },
  cancelled: { label: 'Cancelled', className: 'bg-gray-100 text-gray-800', icon: Ban },
  expired: { label: 'Expired', className: 'bg-red-100 text-red-800', icon: AlertCircle },
};

export function EmailInvitationsTab() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [params, setParams] = useState<InvitationListParams>({
    page: 1,
    per_page: 20,
    sort_by: 'invited_at',
    sort_order: 'desc',
  });

  const { data, isLoading } = useQuery({
    queryKey: ['invitations', params],
    queryFn: () => invitationApi.list(params),
    staleTime: 0,
  });

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

  const handleResend = async (id: number) => {
    try {
      await invitationApi.resend(id);
      toast.success('Invitation resent successfully');
      queryClient.invalidateQueries({ queryKey: ['invitations'] });
    } catch (error: any) {
      toast.error(error.message || 'Failed to resend invitation');
    }
  };

  const handleCancel = async (id: number) => {
    if (!confirm('Are you sure you want to cancel this invitation?')) return;
    try {
      await invitationApi.cancel(id);
      toast.success('Invitation cancelled');
      queryClient.invalidateQueries({ queryKey: ['invitations'] });
    } catch (error: any) {
      toast.error(error.message || 'Failed to cancel invitation');
    }
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return '—';
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const invitations = data?.items || [];

  return (
    <div className="space-y-4">
      {/* Search, Filters, and Create Button */}
      <div className="flex flex-col md:flex-row gap-4">
        <div className="flex-1">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search by email or name..."
              value={params.search || ''}
              onChange={(e) => handleSearch(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>
        <Select value={params.status || 'all'} onValueChange={handleStatusFilter}>
          <SelectTrigger className="w-full md:w-48">
            <SelectValue placeholder="All Statuses" />
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
        <Button onClick={() => setShowCreateDialog(true)} className="gap-2">
          <Plus className="h-4 w-4" />
          Send Invitation
        </Button>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
        </div>
      ) : invitations.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          <Mail className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p className="text-lg font-medium">No invitations found</p>
          <p className="text-sm mt-1">
            {params.search || params.status ? 'Try adjusting your filters' : 'Send your first invitation to get started'}
          </p>
        </div>
      ) : (
        <>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Candidate</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Sent Date</TableHead>
                <TableHead>Expires</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {invitations.map((invitation: any) => {
                const statusConfig = STATUS_CONFIG[invitation.status as InvitationStatus] || STATUS_CONFIG.sent;
                const canResend = ['sent', 'opened', 'expired'].includes(invitation.status);
                const canCancel = ['sent', 'opened', 'in_progress'].includes(invitation.status);

                return (
                  <TableRow key={invitation.id}>
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
                      <Badge className={statusConfig.className}>
                        {statusConfig.label}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {formatDate(invitation.invited_at)}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {formatDate(invitation.expires_at)}
                    </TableCell>
                    <TableCell className="text-right">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => navigate(`/invitations/${invitation.id}`)}>
                            <Eye className="h-4 w-4 mr-2" />
                            View Details
                          </DropdownMenuItem>
                          {canResend && (
                            <DropdownMenuItem onClick={() => handleResend(invitation.id)}>
                              <Send className="h-4 w-4 mr-2" />
                              Resend
                            </DropdownMenuItem>
                          )}
                          {canCancel && (
                            <>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem 
                                onClick={() => handleCancel(invitation.id)}
                                className="text-red-600"
                              >
                                <Ban className="h-4 w-4 mr-2" />
                                Cancel
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
            <div className="flex items-center justify-between pt-4 border-t">
              <div className="text-sm text-muted-foreground">
                Page {data.page} of {data.pages}
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setParams((p) => ({ ...p, page: Math.max(1, (p.page || 1) - 1) }))}
                  disabled={params.page === 1}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setParams((p) => ({ ...p, page: (p.page || 1) + 1 }))}
                  disabled={params.page === data.pages}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Create Dialog */}
      <InvitationForm
        open={showCreateDialog}
        onOpenChange={setShowCreateDialog}
        onSuccess={() => {
          setShowCreateDialog(false);
          queryClient.invalidateQueries({ queryKey: ['invitations'] });
          queryClient.invalidateQueries({ queryKey: ['onboarding-stats'] });
        }}
      />
    </div>
  );
}
