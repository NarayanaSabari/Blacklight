/**
 * Role Location Queue Component
 * Shows role+location combinations in the scraping queue
 * PM_ADMIN can approve, reject, and manage priorities
 */

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { roleLocationQueueApi, type RoleLocationQueueEntry } from "@/lib/dashboard-api";
import { usePMAdminAuth } from "@/hooks/usePMAdminAuth";
import { 
  Search,
  RefreshCw,
  Loader2,
  CheckCircle2,
  Clock,
  XCircle,
  MapPin,
  MoreVertical,
  Trash2,
  CheckCheck,
  Users,
  Briefcase
} from "lucide-react";
import { toast } from "sonner";
import { formatDistanceToNow } from "date-fns";

function StatusBadge({ status }: { status: string }) {
  const statusConfig: Record<string, { variant: "default" | "secondary" | "destructive" | "outline"; icon: React.ReactNode; className: string }> = {
    pending: { 
      variant: "secondary", 
      icon: <Clock className="h-3 w-3 mr-1" />,
      className: "bg-yellow-100 text-yellow-800 border-yellow-300"
    },
    approved: { 
      variant: "default", 
      icon: <CheckCircle2 className="h-3 w-3 mr-1" />,
      className: "bg-green-100 text-green-800 border-green-300"
    },
    processing: { 
      variant: "default", 
      icon: <Loader2 className="h-3 w-3 mr-1 animate-spin" />,
      className: "bg-blue-100 text-blue-800 border-blue-300"
    },
    completed: { 
      variant: "outline", 
      icon: <CheckCircle2 className="h-3 w-3 mr-1" />,
      className: "bg-gray-100 text-gray-700 border-gray-300"
    },
    rejected: { 
      variant: "destructive", 
      icon: <XCircle className="h-3 w-3 mr-1" />,
      className: ""
    },
  };

  const config = statusConfig[status] || statusConfig.pending;
  
  return (
    <Badge variant={config.variant} className={`flex items-center ${config.className}`}>
      {config.icon}
      {status}
    </Badge>
  );
}

export function RoleLocationQueue() {
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const queryClient = useQueryClient();
  const { isAuthenticated, isLoading: authLoading } = usePMAdminAuth();

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['role-location-queue', statusFilter],
    queryFn: () => roleLocationQueueApi.getEntries({ 
      status: statusFilter === 'all' ? undefined : statusFilter,
      perPage: 100 
    }),
    staleTime: 0,
    enabled: !authLoading && isAuthenticated,
  });

  const approveMutation = useMutation({
    mutationFn: (entryId: number) => roleLocationQueueApi.approveEntry(entryId),
    onSuccess: () => {
      queryClient.refetchQueries({ queryKey: ['role-location-queue'] });
      queryClient.refetchQueries({ queryKey: ['dashboard-stats'] });
      toast.success("Entry approved for scraping");
    },
    onError: () => {
      toast.error("Failed to approve entry");
    },
  });

  const rejectMutation = useMutation({
    mutationFn: (entryId: number) => roleLocationQueueApi.rejectEntry(entryId),
    onSuccess: () => {
      queryClient.refetchQueries({ queryKey: ['role-location-queue'] });
      toast.success("Entry rejected");
    },
    onError: () => {
      toast.error("Failed to reject entry");
    },
  });

  const updatePriorityMutation = useMutation({
    mutationFn: ({ entryId, priority }: { entryId: number; priority: string }) => 
      roleLocationQueueApi.updatePriority(entryId, priority),
    onSuccess: () => {
      queryClient.refetchQueries({ queryKey: ['role-location-queue'] });
      toast.success("Priority updated");
    },
    onError: () => {
      toast.error("Failed to update priority");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (entryId: number) => roleLocationQueueApi.deleteEntry(entryId),
    onSuccess: () => {
      queryClient.refetchQueries({ queryKey: ['role-location-queue'] });
      toast.success("Entry deleted");
    },
    onError: () => {
      toast.error("Failed to delete entry");
    },
  });

  const bulkApproveMutation = useMutation({
    mutationFn: () => roleLocationQueueApi.bulkApprove(),
    onSuccess: (result) => {
      queryClient.refetchQueries({ queryKey: ['role-location-queue'] });
      queryClient.refetchQueries({ queryKey: ['dashboard-stats'] });
      toast.success(`Approved ${result.approvedCount} entries`);
    },
    onError: () => {
      toast.error("Failed to bulk approve entries");
    },
  });

  const filteredEntries = data?.entries?.filter(entry =>
    (entry.roleName?.toLowerCase() || '').includes(searchTerm.toLowerCase()) ||
    entry.location.toLowerCase().includes(searchTerm.toLowerCase())
  ) || [];

  // Status counts from API
  const statusCounts = data?.stats?.byStatus || {};
  const pendingCount = statusCounts.pending || 0;
  const approvedCount = statusCounts.approved || 0;
  const processingCount = statusCounts.processing || 0;
  const completedCount = statusCounts.completed || 0;

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-64" />
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <Skeleton key={i} className="h-16 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="py-8">
          <div className="text-center">
            <p className="text-sm text-destructive">Failed to load role+location queue</p>
            <Button variant="ghost" size="sm" onClick={() => refetch()} className="mt-2">
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <MapPin className="h-5 w-5" />
              Role + Location Queue
            </CardTitle>
            <CardDescription>
              Location-specific scraping queue for targeted job searches
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            {pendingCount > 0 && (
              <Button 
                size="sm" 
                onClick={() => bulkApproveMutation.mutate()}
                disabled={bulkApproveMutation.isPending}
              >
                {bulkApproveMutation.isPending ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <CheckCheck className="h-4 w-4 mr-2" />
                )}
                Approve All ({pendingCount})
              </Button>
            )}
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Stats Summary */}
        <div className="flex gap-4 mt-4">
          <div className="flex items-center gap-2 text-sm">
            <Clock className="h-4 w-4 text-yellow-600" />
            <span>{pendingCount} Pending</span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <CheckCircle2 className="h-4 w-4 text-green-600" />
            <span>{approvedCount} Approved</span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <Loader2 className="h-4 w-4 text-blue-600" />
            <span>{processingCount} Processing</span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <Briefcase className="h-4 w-4 text-gray-600" />
            <span>{completedCount} Completed</span>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        {/* Filters */}
        <div className="flex items-center gap-4 mb-4">
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search role or location..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-9"
            />
          </div>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Filter status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Statuses</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
              <SelectItem value="approved">Approved</SelectItem>
              <SelectItem value="processing">Processing</SelectItem>
              <SelectItem value="completed">Completed</SelectItem>
              <SelectItem value="rejected">Rejected</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Table */}
        {filteredEntries.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <MapPin className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No role+location entries found</p>
            <p className="text-sm mt-1">
              Entries are created when candidates with preferred locations are approved
            </p>
          </div>
        ) : (
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Role</TableHead>
                  <TableHead>Location</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Priority</TableHead>
                  <TableHead className="text-center">
                    <Users className="h-4 w-4 inline mr-1" />
                    Candidates
                  </TableHead>
                  <TableHead className="text-center">
                    <Briefcase className="h-4 w-4 inline mr-1" />
                    Jobs Scraped
                  </TableHead>
                  <TableHead>Last Scraped</TableHead>
                  <TableHead className="w-12"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredEntries.map((entry) => (
                  <RoleLocationRow
                    key={entry.id}
                    entry={entry}
                    onApprove={() => approveMutation.mutate(entry.id)}
                    onReject={() => rejectMutation.mutate(entry.id)}
                    onPriorityChange={(priority) => 
                      updatePriorityMutation.mutate({ entryId: entry.id, priority })
                    }
                    onDelete={() => deleteMutation.mutate(entry.id)}
                    isLoading={
                      approveMutation.isPending || 
                      rejectMutation.isPending ||
                      updatePriorityMutation.isPending ||
                      deleteMutation.isPending
                    }
                  />
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

interface RoleLocationRowProps {
  entry: RoleLocationQueueEntry;
  onApprove: () => void;
  onReject: () => void;
  onPriorityChange: (priority: string) => void;
  onDelete: () => void;
  isLoading: boolean;
}

function RoleLocationRow({ 
  entry, 
  onApprove, 
  onReject, 
  onPriorityChange, 
  onDelete,
  isLoading 
}: RoleLocationRowProps) {
  return (
    <TableRow>
      <TableCell className="font-medium">
        {entry.roleName || `Role #${entry.globalRoleId}`}
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-1">
          <MapPin className="h-3 w-3 text-muted-foreground" />
          {entry.location}
        </div>
      </TableCell>
      <TableCell>
        <StatusBadge status={entry.queueStatus} />
      </TableCell>
      <TableCell>
        <Select 
          value={entry.priority} 
          onValueChange={onPriorityChange}
          disabled={isLoading || entry.queueStatus === 'processing'}
        >
          <SelectTrigger className="w-24 h-8">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="urgent">Urgent</SelectItem>
            <SelectItem value="high">High</SelectItem>
            <SelectItem value="normal">Normal</SelectItem>
            <SelectItem value="low">Low</SelectItem>
          </SelectContent>
        </Select>
      </TableCell>
      <TableCell className="text-center">
        <Badge variant="outline">{entry.candidateCount}</Badge>
      </TableCell>
      <TableCell className="text-center">
        {entry.totalJobsScraped > 0 ? (
          <Badge variant="secondary">{entry.totalJobsScraped}</Badge>
        ) : (
          <span className="text-muted-foreground">-</span>
        )}
      </TableCell>
      <TableCell className="text-muted-foreground text-sm">
        {entry.lastScrapedAt 
          ? formatDistanceToNow(new Date(entry.lastScrapedAt), { addSuffix: true })
          : 'Never'
        }
      </TableCell>
      <TableCell>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-8 w-8" disabled={isLoading}>
              <MoreVertical className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            {entry.queueStatus === 'pending' && (
              <>
                <DropdownMenuItem onClick={onApprove}>
                  <CheckCircle2 className="h-4 w-4 mr-2 text-green-600" />
                  Approve
                </DropdownMenuItem>
                <DropdownMenuItem onClick={onReject}>
                  <XCircle className="h-4 w-4 mr-2 text-red-600" />
                  Reject
                </DropdownMenuItem>
                <DropdownMenuSeparator />
              </>
            )}
            {entry.queueStatus === 'rejected' && (
              <>
                <DropdownMenuItem onClick={onApprove}>
                  <CheckCircle2 className="h-4 w-4 mr-2 text-green-600" />
                  Approve
                </DropdownMenuItem>
                <DropdownMenuSeparator />
              </>
            )}
            <DropdownMenuItem 
              onClick={onDelete}
              className="text-destructive focus:text-destructive"
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </TableCell>
    </TableRow>
  );
}

export default RoleLocationQueue;
