/**
 * Role Queue Table Component
 * Displays pending roles for review/approval
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import { globalRolesApi, type GlobalRole } from "@/lib/dashboard-api";
import { usePMAdminAuth } from "@/hooks/usePMAdminAuth";
import { 
  Check, 
  GitMerge, 
  X, 
  Search,
  Tags,
  RefreshCw
} from "lucide-react";
import { toast } from "sonner";

function PriorityBadge({ priority }: { priority: GlobalRole['queuePriority'] }) {
  const variants: Record<GlobalRole['queuePriority'], { variant: "default" | "secondary" | "destructive" | "outline"; className: string }> = {
    urgent: { variant: "destructive", className: "" },
    high: { variant: "default", className: "bg-amber-500 hover:bg-amber-600" },
    normal: { variant: "secondary", className: "" },
    low: { variant: "outline", className: "" },
  };

  const { variant, className } = variants[priority];
  return (
    <Badge variant={variant} className={className}>
      {priority}
    </Badge>
  );
}

interface MergeDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  sourceRole: GlobalRole | null;
  onMerge: (targetRoleId: number) => void;
  isLoading: boolean;
}

function MergeDialog({ open, onOpenChange, sourceRole, onMerge, isLoading }: MergeDialogProps) {
  const [targetRoleId, setTargetRoleId] = useState<number | null>(null);
  
  const { data: roles } = useQuery({
    queryKey: ['approved-roles'],
    queryFn: () => globalRolesApi.getRoles({ status: 'approved' }),
    enabled: open,
  });

  const handleMerge = () => {
    if (targetRoleId) {
      onMerge(targetRoleId);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Merge Role</DialogTitle>
          <DialogDescription>
            Merge "{sourceRole?.name}" into an existing approved role. 
            All candidates and jobs will be transferred.
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label>Source Role (will be merged)</Label>
            <Input value={sourceRole?.name || ''} disabled />
          </div>
          
          <div className="space-y-2">
            <Label>Target Role (merge into)</Label>
            <Select 
              value={targetRoleId?.toString() || ''} 
              onValueChange={(val) => setTargetRoleId(parseInt(val))}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select target role..." />
              </SelectTrigger>
              <SelectContent>
                <ScrollArea className="h-[200px]">
                  {roles?.roles
                    .filter(r => r.id !== sourceRole?.id)
                    .map((role) => (
                      <SelectItem key={role.id} value={role.id.toString()}>
                        {role.name} ({role.candidateCount} candidates)
                      </SelectItem>
                    ))
                  }
                </ScrollArea>
              </SelectContent>
            </Select>
          </div>

          {sourceRole?.similarRoles && sourceRole.similarRoles.length > 0 && (
            <div className="space-y-2">
              <Label className="text-muted-foreground">Similar Roles Found</Label>
              <div className="flex flex-wrap gap-2">
                {sourceRole.similarRoles.map((similar) => (
                  <Badge 
                    key={similar.id} 
                    variant="outline"
                    className="cursor-pointer hover:bg-accent"
                    onClick={() => setTargetRoleId(similar.id)}
                  >
                    {similar.name} ({Math.round(similar.similarity * 100)}%)
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleMerge} disabled={!targetRoleId || isLoading}>
            {isLoading ? (
              <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <GitMerge className="h-4 w-4 mr-2" />
            )}
            Merge Role
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function RoleQueueTable() {
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedRole, setSelectedRole] = useState<GlobalRole | null>(null);
  const [mergeDialogOpen, setMergeDialogOpen] = useState(false);
  const queryClient = useQueryClient();
  const { isAuthenticated, isLoading: authLoading } = usePMAdminAuth();

  const { data: roles, isLoading, error, refetch } = useQuery({
    queryKey: ['pending-roles'],
    queryFn: globalRolesApi.getPendingRoles,
    staleTime: 0,
    enabled: !authLoading && isAuthenticated, // Only fetch when auth is complete and user is authenticated
  });

  const approveMutation = useMutation({
    mutationFn: (roleId: number) => globalRolesApi.approveRole(roleId),
    onSuccess: () => {
      queryClient.refetchQueries({ queryKey: ['pending-roles'] });
      queryClient.refetchQueries({ queryKey: ['dashboard-stats'] });
      toast.success("Role approved successfully");
    },
    onError: () => {
      toast.error("Failed to approve role");
    },
  });

  const rejectMutation = useMutation({
    mutationFn: (roleId: number) => globalRolesApi.rejectRole(roleId),
    onSuccess: () => {
      queryClient.refetchQueries({ queryKey: ['pending-roles'] });
      queryClient.refetchQueries({ queryKey: ['dashboard-stats'] });
      toast.success("Role rejected");
    },
    onError: () => {
      toast.error("Failed to reject role");
    },
  });

  const mergeMutation = useMutation({
    mutationFn: ({ sourceId, targetId }: { sourceId: number; targetId: number }) => 
      globalRolesApi.mergeRoles(sourceId, targetId),
    onSuccess: () => {
      setMergeDialogOpen(false);
      setSelectedRole(null);
      queryClient.refetchQueries({ queryKey: ['pending-roles'] });
      queryClient.refetchQueries({ queryKey: ['dashboard-stats'] });
      toast.success("Roles merged successfully");
    },
    onError: () => {
      toast.error("Failed to merge roles");
    },
  });

  const handleMerge = (role: GlobalRole) => {
    setSelectedRole(role);
    setMergeDialogOpen(true);
  };

  const filteredRoles = roles?.filter(role =>
    role.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    role.normalizedName.toLowerCase().includes(searchTerm.toLowerCase())
  );

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
            <p className="text-sm text-destructive">Failed to load pending roles</p>
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
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Tags className="h-5 w-5" />
                Role Queue
              </CardTitle>
              <CardDescription>
                {roles?.length || 0} roles pending review
              </CardDescription>
            </div>
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </div>
          <div className="relative mt-4">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search roles..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-9"
            />
          </div>
        </CardHeader>
        <CardContent>
          {filteredRoles?.length === 0 ? (
            <div className="text-center py-8">
              <Tags className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
              <p className="text-sm text-muted-foreground">
                {searchTerm ? "No roles match your search" : "No roles pending review"}
              </p>
            </div>
          ) : (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[250px]">Role Name</TableHead>
                    <TableHead>Category</TableHead>
                    <TableHead>Priority</TableHead>
                    <TableHead className="text-right">Candidates</TableHead>
                    <TableHead>Similar Roles</TableHead>
                    <TableHead className="text-right w-[140px]">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredRoles?.map((role) => (
                    <TableRow key={role.id}>
                      <TableCell>
                        <div>
                          <p className="font-medium">{role.name}</p>
                          <p className="text-xs text-muted-foreground">
                            {role.normalizedName}
                          </p>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">
                          {role.category || 'Uncategorized'}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <PriorityBadge priority={role.queuePriority} />
                      </TableCell>
                      <TableCell className="text-right">
                        {role.candidateCount}
                      </TableCell>
                      <TableCell>
                        {role.similarRoles && role.similarRoles.length > 0 ? (
                          <div className="flex items-center gap-1">
                            <Badge variant="secondary" className="text-xs">
                              {role.similarRoles[0].name}
                            </Badge>
                            {role.similarRoles.length > 1 && (
                              <span className="text-xs text-muted-foreground">
                                +{role.similarRoles.length - 1}
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className="text-xs text-muted-foreground">None</span>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => approveMutation.mutate(role.id)}
                            disabled={approveMutation.isPending}
                            title="Approve"
                          >
                            <Check className="h-4 w-4 text-green-600" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleMerge(role)}
                            title="Merge"
                          >
                            <GitMerge className="h-4 w-4 text-blue-600" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => rejectMutation.mutate(role.id)}
                            disabled={rejectMutation.isPending}
                            title="Reject"
                          >
                            <X className="h-4 w-4 text-red-600" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      <MergeDialog
        open={mergeDialogOpen}
        onOpenChange={setMergeDialogOpen}
        sourceRole={selectedRole}
        onMerge={(targetId) => {
          if (selectedRole) {
            mergeMutation.mutate({ 
              sourceId: selectedRole.id, 
              targetId 
            });
          }
        }}
        isLoading={mergeMutation.isPending}
      />
    </>
  );
}
