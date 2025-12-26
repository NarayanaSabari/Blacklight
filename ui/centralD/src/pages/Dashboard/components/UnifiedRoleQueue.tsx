/**
 * Unified Role Queue Component
 * Shows all roles with expandable location queue entries
 * Merges GlobalRolesQueue and RoleLocationQueue into one view
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
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
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
import { globalRolesApi, roleLocationQueueApi } from "@/lib/dashboard-api";
import { usePMAdminAuth } from "@/hooks/usePMAdminAuth";
import { 
  Search,
  RefreshCw,
  Loader2,
  CheckCircle2,
  Clock,
  XCircle,
  PlayCircle,
  ListFilter,
  Trash2,
  ChevronDown,
  ChevronRight,
  MapPin,
  Briefcase,
  Users
} from "lucide-react";
import { toast } from "sonner";
import { formatDistanceToNow } from "date-fns";

// ============================================================================
// STATUS & PRIORITY BADGES
// ============================================================================

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

function PriorityBadge({ priority }: { priority: string }) {
  const variants: Record<string, { variant: "default" | "secondary" | "destructive" | "outline"; className: string }> = {
    urgent: { variant: "destructive", className: "" },
    high: { variant: "default", className: "bg-amber-500 hover:bg-amber-600" },
    normal: { variant: "secondary", className: "" },
    low: { variant: "outline", className: "" },
  };

  const config = variants[priority] || variants.normal;
  return (
    <Badge variant={config.variant} className={config.className}>
      {priority}
    </Badge>
  );
}

// ============================================================================
// LOCATION ROW COMPONENT
// ============================================================================

interface LocationEntry {
  id: number;
  location: string;
  queueStatus: string;
  priority: string;
  candidateCount: number;
  totalJobsScraped: number;
  lastScrapedAt: string | null;
}

interface LocationRowProps {
  location: LocationEntry;
  onApprove: () => void;
  onReject: () => void;
  onPriorityChange: (priority: string) => void;
  isLoading: boolean;
}

function LocationRow({ location, onApprove, onReject, onPriorityChange, isLoading }: LocationRowProps) {
  return (
    <div className="flex items-center justify-between py-2 px-4 bg-muted/30 rounded-md">
      <div className="flex items-center gap-3">
        <MapPin className="h-4 w-4 text-muted-foreground" />
        <span className="font-medium">{location.location}</span>
        <StatusBadge status={location.queueStatus} />
      </div>
      
      <div className="flex items-center gap-4">
        {/* Candidate count */}
        <div className="flex items-center gap-1 text-sm text-muted-foreground">
          <Users className="h-3 w-3" />
          <span>{location.candidateCount}</span>
        </div>
        
        {/* Jobs scraped */}
        <div className="flex items-center gap-1 text-sm text-muted-foreground">
          <Briefcase className="h-3 w-3" />
          <span>{location.totalJobsScraped}</span>
        </div>
        
        {/* Last scraped */}
        <span className="text-xs text-muted-foreground w-24">
          {location.lastScrapedAt 
            ? formatDistanceToNow(new Date(location.lastScrapedAt), { addSuffix: true })
            : 'Never'
          }
        </span>
        
        {/* Priority selector */}
        <Select 
          value={location.priority} 
          onValueChange={onPriorityChange}
          disabled={isLoading || location.queueStatus === 'processing'}
        >
          <SelectTrigger className="h-7 w-24 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="urgent">Urgent</SelectItem>
            <SelectItem value="high">High</SelectItem>
            <SelectItem value="normal">Normal</SelectItem>
            <SelectItem value="low">Low</SelectItem>
          </SelectContent>
        </Select>
        
        {/* Actions for pending status */}
        {(location.queueStatus === 'pending' || location.queueStatus === 'rejected') && (
          <div className="flex gap-1">
            <Button 
              size="sm" 
              variant="ghost" 
              className="h-7 px-2 text-green-600 hover:text-green-700 hover:bg-green-50"
              onClick={onApprove}
              disabled={isLoading}
            >
              <CheckCircle2 className="h-4 w-4" />
            </Button>
            {location.queueStatus === 'pending' && (
              <Button 
                size="sm" 
                variant="ghost" 
                className="h-7 px-2 text-red-600 hover:text-red-700 hover:bg-red-50"
                onClick={onReject}
                disabled={isLoading}
              >
                <XCircle className="h-4 w-4" />
              </Button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// EXPANDABLE ROLE ROW
// ============================================================================

interface RoleData {
  id: number;
  name: string;
  status: string;
  queuePriority: string;
  category: string | null;
  candidateCount: number;
  jobCount: number;
  aliases?: string[];
  lastScrapedAt: string | null;
}

interface ExpandableRoleRowProps {
  role: RoleData;
  onPriorityChange: (priority: string) => void;
  onDelete: () => void;
  isPriorityLoading: boolean;
  isDeleteLoading: boolean;
}

function ExpandableRoleRow({ 
  role, 
  onPriorityChange, 
  onDelete,
  isPriorityLoading,
  isDeleteLoading 
}: ExpandableRoleRowProps) {
  const [isOpen, setIsOpen] = useState(false);
  const queryClient = useQueryClient();
  
  // Fetch locations for this role when expanded
  const { data: locationsData, isLoading: locationsLoading } = useQuery({
    queryKey: ['role-locations', role.id],
    queryFn: () => roleLocationQueueApi.getLocationsForRole(role.id),
    enabled: isOpen,
    staleTime: 30000,
  });

  const approveMutation = useMutation({
    mutationFn: (entryId: number) => roleLocationQueueApi.approveEntry(entryId),
    onSuccess: () => {
      queryClient.refetchQueries({ queryKey: ['role-locations', role.id] });
      toast.success("Location approved for scraping");
    },
    onError: () => toast.error("Failed to approve location"),
  });

  const rejectMutation = useMutation({
    mutationFn: (entryId: number) => roleLocationQueueApi.rejectEntry(entryId),
    onSuccess: () => {
      queryClient.refetchQueries({ queryKey: ['role-locations', role.id] });
      toast.success("Location rejected");
    },
    onError: () => toast.error("Failed to reject location"),
  });

  const updateLocationPriorityMutation = useMutation({
    mutationFn: ({ entryId, priority }: { entryId: number; priority: string }) => 
      roleLocationQueueApi.updatePriority(entryId, priority),
    onSuccess: () => {
      queryClient.refetchQueries({ queryKey: ['role-locations', role.id] });
      toast.success("Location priority updated");
    },
    onError: () => toast.error("Failed to update priority"),
  });

  const hasLocations = locationsData && locationsData.totalLocations > 0;
  const locationCount = locationsData?.totalLocations || 0;

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <TableRow className="hover:bg-muted/50">
        <TableCell>
          <CollapsibleTrigger asChild>
            <Button variant="ghost" size="sm" className="p-0 h-auto hover:bg-transparent">
              {isOpen ? (
                <ChevronDown className="h-4 w-4 mr-2 text-muted-foreground" />
              ) : (
                <ChevronRight className="h-4 w-4 mr-2 text-muted-foreground" />
              )}
              <div className="text-left">
                <p className="font-medium">{role.name}</p>
                {role.aliases && role.aliases.length > 0 && (
                  <p className="text-xs text-muted-foreground">
                    +{role.aliases.length} aliases
                  </p>
                )}
              </div>
            </Button>
          </CollapsibleTrigger>
        </TableCell>
        <TableCell>
          <StatusBadge status={role.status} />
        </TableCell>
        <TableCell>
          <PriorityBadge priority={role.queuePriority} />
        </TableCell>
        <TableCell>
          <Badge variant="outline">
            {role.category || 'Uncategorized'}
          </Badge>
        </TableCell>
        <TableCell className="text-right font-medium">
          {role.candidateCount}
        </TableCell>
        <TableCell className="text-center">
          {isOpen && locationsLoading ? (
            <Loader2 className="h-4 w-4 animate-spin mx-auto" />
          ) : (
            <Badge 
              variant={hasLocations ? "secondary" : "outline"} 
              className="cursor-pointer"
              onClick={() => setIsOpen(!isOpen)}
            >
              <MapPin className="h-3 w-3 mr-1" />
              {locationCount}
            </Badge>
          )}
        </TableCell>
        <TableCell className="text-right">
          {role.jobCount || 0}
        </TableCell>
        <TableCell>
          {role.lastScrapedAt ? (
            <span className="text-xs text-muted-foreground">
              {formatDistanceToNow(new Date(role.lastScrapedAt), { addSuffix: true })}
            </span>
          ) : (
            <span className="text-xs text-muted-foreground">Never</span>
          )}
        </TableCell>
        <TableCell>
          <Select 
            value={role.queuePriority} 
            onValueChange={onPriorityChange}
            disabled={isPriorityLoading}
          >
            <SelectTrigger className="h-8 text-xs">
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
        <TableCell>
          <Button
            variant="ghost"
            size="sm"
            onClick={onDelete}
            disabled={isDeleteLoading || (role.candidateCount ?? 0) > 0}
            title={(role.candidateCount ?? 0) > 0 
              ? `Cannot delete: ${role.candidateCount} candidate(s) linked` 
              : "Delete role"}
            className="h-8 w-8 p-0 text-destructive hover:text-destructive hover:bg-destructive/10"
          >
            {isDeleteLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Trash2 className="h-4 w-4" />
            )}
          </Button>
        </TableCell>
      </TableRow>
      
      {/* Expanded Location Details */}
      <CollapsibleContent asChild>
        <TableRow className="bg-muted/20 hover:bg-muted/20">
          <TableCell colSpan={10} className="p-0">
            <div className="p-4 pl-12 space-y-2">
              {locationsLoading ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Loading locations...
                </div>
              ) : !hasLocations ? (
                <div className="text-sm text-muted-foreground flex items-center gap-2">
                  <MapPin className="h-4 w-4" />
                  No specific locations requested for this role
                </div>
              ) : (
                <>
                  <div className="text-xs text-muted-foreground mb-3 font-medium">
                    Requested Locations ({locationCount})
                  </div>
                  {locationsData?.locations.map((loc) => (
                    <LocationRow
                      key={loc.id}
                      location={loc}
                      onApprove={() => approveMutation.mutate(loc.id)}
                      onReject={() => rejectMutation.mutate(loc.id)}
                      onPriorityChange={(priority) => 
                        updateLocationPriorityMutation.mutate({ entryId: loc.id, priority })
                      }
                      isLoading={
                        approveMutation.isPending || 
                        rejectMutation.isPending || 
                        updateLocationPriorityMutation.isPending
                      }
                    />
                  ))}
                </>
              )}
            </div>
          </TableCell>
        </TableRow>
      </CollapsibleContent>
    </Collapsible>
  );
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export function UnifiedRoleQueue() {
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const queryClient = useQueryClient();
  const { isAuthenticated, isLoading: authLoading } = usePMAdminAuth();

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['all-roles', statusFilter],
    queryFn: () => globalRolesApi.getRoles({ 
      status: statusFilter === 'all' ? undefined : statusFilter,
      perPage: 100 
    }),
    staleTime: 0,
    enabled: !authLoading && isAuthenticated,
  });

  const updatePriorityMutation = useMutation({
    mutationFn: ({ roleId, priority }: { roleId: number; priority: string }) => 
      globalRolesApi.updatePriority(roleId, priority),
    onSuccess: () => {
      queryClient.refetchQueries({ queryKey: ['all-roles'] });
      toast.success("Role priority updated");
    },
    onError: () => {
      toast.error("Failed to update priority");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (roleId: number) => globalRolesApi.deleteRole(roleId),
    onSuccess: () => {
      queryClient.refetchQueries({ queryKey: ['all-roles'] });
      queryClient.refetchQueries({ queryKey: ['dashboard-stats'] });
      toast.success("Role deleted successfully");
    },
    onError: (error: unknown) => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const axiosError = error as any;
      const message = axiosError?.response?.data?.message || "Failed to delete role";
      toast.error(message);
    },
  });

  const filteredRoles = data?.roles?.filter(role =>
    role.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (role.category?.toLowerCase() || '').includes(searchTerm.toLowerCase())
  ) || [];

  // Status counts - cast to string for comparison since API may return more statuses
  const statusCounts = {
    pending: filteredRoles.filter(r => (r.status as string) === 'pending').length,
    approved: filteredRoles.filter(r => (r.status as string) === 'approved').length,
    processing: filteredRoles.filter(r => (r.status as string) === 'processing').length,
    completed: filteredRoles.filter(r => (r.status as string) === 'completed').length,
  };

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
            <p className="text-sm text-destructive">Failed to load roles</p>
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
              <PlayCircle className="h-5 w-5" />
              Scraper Queue
            </CardTitle>
            <CardDescription>
              All roles with their locations - click a role to see requested locations
            </CardDescription>
          </div>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>

        {/* Status Summary */}
        <div className="flex flex-wrap gap-2 mt-4">
          <Badge variant="secondary" className="bg-yellow-100 text-yellow-800">
            <Clock className="h-3 w-3 mr-1" />
            Pending: {statusCounts.pending}
          </Badge>
          <Badge variant="secondary" className="bg-green-100 text-green-800">
            <CheckCircle2 className="h-3 w-3 mr-1" />
            Approved: {statusCounts.approved}
          </Badge>
          <Badge variant="secondary" className="bg-blue-100 text-blue-800">
            <Loader2 className="h-3 w-3 mr-1" />
            Processing: {statusCounts.processing}
          </Badge>
          <Badge variant="secondary" className="bg-gray-100 text-gray-800">
            <CheckCircle2 className="h-3 w-3 mr-1" />
            Completed: {statusCounts.completed}
          </Badge>
        </div>

        {/* Filters */}
        <div className="flex gap-4 mt-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search roles..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-9"
            />
          </div>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[180px]">
              <ListFilter className="h-4 w-4 mr-2" />
              <SelectValue placeholder="Filter by status" />
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
      </CardHeader>
      
      <CardContent>
        {filteredRoles.length === 0 ? (
          <div className="text-center py-8">
            <PlayCircle className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
            <p className="text-sm text-muted-foreground">
              {searchTerm || statusFilter !== 'all' 
                ? "No roles match your filters" 
                : "No roles in the system yet"}
            </p>
          </div>
        ) : (
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[250px]">Role Name</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Priority</TableHead>
                  <TableHead>Category</TableHead>
                  <TableHead className="text-right">Candidates</TableHead>
                  <TableHead className="text-center">Locations</TableHead>
                  <TableHead className="text-right">Jobs</TableHead>
                  <TableHead>Last Scraped</TableHead>
                  <TableHead className="w-[120px]">Set Priority</TableHead>
                  <TableHead className="w-[80px]">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredRoles.map((role) => (
                  <ExpandableRoleRow
                    key={role.id}
                    role={role}
                    onPriorityChange={(priority) => 
                      updatePriorityMutation.mutate({ roleId: role.id, priority })
                    }
                    onDelete={() => deleteMutation.mutate(role.id)}
                    isPriorityLoading={updatePriorityMutation.isPending}
                    isDeleteLoading={deleteMutation.isPending}
                  />
                ))}
              </TableBody>
            </Table>
          </div>
        )}
        
        {data?.total && data.total > filteredRoles.length && (
          <p className="text-xs text-muted-foreground mt-4 text-center">
            Showing {filteredRoles.length} of {data.total} roles
          </p>
        )}
      </CardContent>
    </Card>
  );
}

export default UnifiedRoleQueue;
