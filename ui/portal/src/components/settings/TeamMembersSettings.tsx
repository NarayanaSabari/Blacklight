/**
 * Team Members Settings Component
 * Unified view for user management, team hierarchy, and manager assignments
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  AlertCircle,
  Users,
  UserCog,
  GitBranch,
  UserPlus,
  UserMinus,
  ChevronDown,
  ChevronRight,
  Expand,
  Minimize2,
  Plus,
  Search,
  Shield,
  UserCheck,
  ArrowRight,
} from 'lucide-react';
import { toast } from 'sonner';
import { teamApi } from '@/lib/teamApi';
import { fetchUsers } from '@/lib/api/users';
import { usePermissions } from '@/hooks/usePermissions';
import { InviteUserDialog } from '@/components/InviteUserDialog';
import { UsersTable } from '@/components/UsersTable';
import { ResetPasswordDialog } from '@/components/ResetPasswordDialog';
import type { TeamMember, UserBasicInfo, PortalUserFull } from '@/types';

export function TeamMembersSettings() {
  const queryClient = useQueryClient();
  const { hasPermission, canManageUsers } = usePermissions();
  
  // State for manager assignment dialogs
  const [assignDialogOpen, setAssignDialogOpen] = useState(false);
  const [removeDialogOpen, setRemoveDialogOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<TeamMember | null>(null);
  const [selectedManagerId, setSelectedManagerId] = useState<string>('');
  const [expandedNodes, setExpandedNodes] = useState<Set<number>>(new Set());
  
  // State for users tab
  const [inviteDialogOpen, setInviteDialogOpen] = useState(false);
  const [resetPasswordUser, setResetPasswordUser] = useState<PortalUserFull | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  // Permission checks
  const canViewTeam = hasPermission('users.view_team');
  const canAssignManager = hasPermission('users.assign_manager');

  // Fetch users for Users tab
  const { data: usersData, isLoading: isLoadingUsers, error: usersError } = useQuery({
    queryKey: ['users', searchQuery],
    queryFn: () => fetchUsers({ search: searchQuery }),
  });

  const users = usersData?.items || [];

  // Calculate user stats
  const userStats = {
    total: users.length,
    active: users.filter((u) => u.is_active).length,
    recruiters: users.filter((u) => u.roles?.some(r => r.name === 'RECRUITER')).length,
    managers: users.filter((u) => u.roles?.some(r => r.name === 'MANAGER')).length,
  };

  // Fetch team hierarchy
  const {
    data: hierarchyData,
    isLoading: isLoadingHierarchy,
    error: hierarchyError,
  } = useQuery({
    queryKey: ['team-hierarchy'],
    queryFn: () => teamApi.getTeamHierarchy(),
    enabled: canViewTeam,
  });

  // Fetch managers list
  const {
    data: managersData,
    isLoading: isLoadingManagers,
  } = useQuery({
    queryKey: ['managers-list'],
    queryFn: () => teamApi.getManagersList(),
    enabled: canViewTeam,
  });

  // Fetch available managers for assignment dialog
  const {
    data: availableManagersData,
  } = useQuery({
    queryKey: ['available-managers', selectedUser?.id],
    queryFn: () => teamApi.getAvailableManagers(selectedUser?.id, selectedUser?.id),
    enabled: assignDialogOpen && canAssignManager && !!selectedUser,
  });

  // Assign manager mutation
  const assignManagerMutation = useMutation({
    mutationFn: teamApi.assignManager,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['team-hierarchy'] });
      queryClient.invalidateQueries({ queryKey: ['managers-list'] });
      toast.success('Manager assigned successfully');
      setAssignDialogOpen(false);
      setSelectedUser(null);
      setSelectedManagerId('');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to assign manager');
    },
  });

  // Remove manager mutation
  const removeManagerMutation = useMutation({
    mutationFn: teamApi.removeManager,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['team-hierarchy'] });
      queryClient.invalidateQueries({ queryKey: ['managers-list'] });
      toast.success('Manager removed successfully');
      setRemoveDialogOpen(false);
      setSelectedUser(null);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to remove manager');
    },
  });

  // Toggle node expansion
  const toggleNode = (userId: number) => {
    setExpandedNodes((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(userId)) {
        newSet.delete(userId);
      } else {
        newSet.add(userId);
      }
      return newSet;
    });
  };

  // Expand all nodes
  const expandAll = () => {
    if (!hierarchyData) return;
    const allIds = new Set<number>();
    const collectIds = (members: TeamMember[]) => {
      members.forEach((member) => {
        if (member.team_members && member.team_members.length > 0) {
          allIds.add(member.id);
          collectIds(member.team_members);
        }
      });
    };
    collectIds(hierarchyData.top_level_users);
    setExpandedNodes(allIds);
  };

  // Collapse all nodes
  const collapseAll = () => {
    setExpandedNodes(new Set());
  };

  // Open assign dialog
  const handleAssignManager = (user: TeamMember) => {
    setSelectedUser(user);
    setAssignDialogOpen(true);
  };

  // Open remove dialog
  const handleRemoveManager = (user: TeamMember) => {
    setSelectedUser(user);
    setRemoveDialogOpen(true);
  };

  // Confirm assign manager
  const confirmAssignManager = () => {
    if (!selectedUser || !selectedManagerId) return;
    assignManagerMutation.mutate({
      user_id: selectedUser.id,
      manager_id: parseInt(selectedManagerId),
    });
  };

  // Confirm remove manager
  const confirmRemoveManager = () => {
    if (!selectedUser) return;
    removeManagerMutation.mutate({
      user_id: selectedUser.id,
    });
  };

  // Render team member node (recursive)
  const renderTeamMember = (member: TeamMember, level: number = 0) => {
    const hasTeamMembers = member.team_members && member.team_members.length > 0;
    const isExpanded = expandedNodes.has(member.id);

    return (
      <div key={member.id} className="space-y-1">
        <div
          className="flex items-center gap-2 py-2 px-3 hover:bg-slate-50 rounded-lg group"
          style={{ marginLeft: `${level * 24}px` }}
        >
          {/* Expand/Collapse Button */}
          {hasTeamMembers ? (
            <button
              onClick={() => toggleNode(member.id)}
              className="p-0.5 hover:bg-slate-200 rounded transition-colors"
            >
              {isExpanded ? (
                <ChevronDown className="h-4 w-4 text-slate-600" />
              ) : (
                <ChevronRight className="h-4 w-4 text-slate-600" />
              )}
            </button>
          ) : (
            <div className="w-5" />
          )}

          {/* User Info */}
          <div className="flex-1 flex items-center gap-3">
            <div className="flex flex-col">
              <div className="flex items-center gap-2">
                <span className="font-medium text-slate-900">
                  {member.first_name} {member.last_name}
                </span>
                {hasTeamMembers && (
                  <Badge variant="secondary" className="text-xs">
                    {member.team_members.length} {member.team_members.length === 1 ? 'report' : 'reports'}
                  </Badge>
                )}
              </div>
              <span className="text-sm text-slate-600">{member.email}</span>
            </div>
          </div>

          {/* Roles */}
          <div className="flex gap-1">
            {member.roles.map((role: string | { name: string; display_name: string }) => (
              <Badge key={typeof role === 'string' ? role : role.name} variant="outline" className="text-xs">
                {typeof role === 'string' ? role : (role.display_name || role.name)}
              </Badge>
            ))}
          </div>

          {/* Actions */}
          {canAssignManager && (
            <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <Button
                size="sm"
                variant="ghost"
                onClick={() => handleAssignManager(member)}
                className="h-8"
              >
                <UserPlus className="h-3.5 w-3.5 mr-1" />
                {member.manager_id ? 'Change' : 'Assign'} Manager
              </Button>
              {member.manager_id && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => handleRemoveManager(member)}
                  className="h-8 text-red-600 hover:text-red-700 hover:bg-red-50"
                >
                  <UserMinus className="h-3.5 w-3.5 mr-1" />
                  Remove
                </Button>
              )}
            </div>
          )}
        </div>

        {/* Render team members recursively */}
        {hasTeamMembers && isExpanded && (
          <div className="space-y-1">
            {member.team_members.map((teamMember) =>
              renderTeamMember(teamMember, level + 1)
            )}
          </div>
        )}
      </div>
    );
  };

  if (!canViewTeam) {
    return (
      <Alert>
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          You don't have permission to view team information. Contact your administrator for access.
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <>
      {/* Permission Warning for non-admins */}
      {!canManageUsers && (
        <Alert className="mb-4">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Only Tenant Admins can invite and manage users. Contact your administrator for access.
          </AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader>
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <CardTitle>Team Management</CardTitle>
              <CardDescription>Manage users, view hierarchy, and assign managers</CardDescription>
            </div>
            {/* Inline Stats */}
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-md bg-blue-100">
                  <Users className="h-4 w-4 text-blue-600" />
                </div>
                <div>
                  <span className="text-xl font-bold">
                    {isLoadingUsers ? '-' : userStats.total}
                  </span>
                  <span className="text-sm text-muted-foreground ml-1">Users</span>
                </div>
              </div>
              <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                <UserCheck className="h-3 w-3 mr-1" />
                {userStats.active} Active
              </Badge>
              <Badge variant="outline" className="bg-purple-50 text-purple-700 border-purple-200">
                <UserCog className="h-3 w-3 mr-1" />
                {managersData?.total || 0} Managers
              </Badge>
            </div>
          </div>
        </CardHeader>

        <CardContent className="p-0">
          <Tabs defaultValue="users" className="w-full">
            <div className="px-6 pt-4 border-t flex items-center justify-between flex-wrap gap-4">
              <TabsList className="bg-muted/50 h-10">
                <TabsTrigger value="users" className="gap-2 px-4">
                  <Users className="h-4 w-4" />
                  Users
                </TabsTrigger>
                <TabsTrigger value="hierarchy" className="gap-2 px-4">
                  <GitBranch className="h-4 w-4" />
                  Team Hierarchy
                </TabsTrigger>
                <TabsTrigger value="managers" className="gap-2 px-4">
                  <UserCog className="h-4 w-4" />
                  Managers
                </TabsTrigger>
              </TabsList>
              
              {/* Actions - context dependent */}
              <div className="flex items-center gap-2">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                  <Input
                    placeholder="Search users..."
                    className="pl-9 w-64 bg-white"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                </div>
                {canManageUsers && (
                  <Button className="gap-2" onClick={() => setInviteDialogOpen(true)}>
                    <Plus className="h-4 w-4" />
                    Invite User
                  </Button>
                )}
              </div>
            </div>

            {/* Users Tab */}
            <TabsContent value="users" className="mt-0 border-t">
              {isLoadingUsers ? (
                <div className="p-6 space-y-3">
                  {[...Array(5)].map((_, i) => (
                    <Skeleton key={i} className="h-16 w-full" />
                  ))}
                </div>
              ) : usersError ? (
                <div className="p-6">
                  <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                      Failed to load users. Please try again later.
                    </AlertDescription>
                  </Alert>
                </div>
              ) : users.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <div className="p-4 rounded-full bg-slate-100 mb-4">
                    <UserCog className="h-12 w-12 text-slate-400" />
                  </div>
                  <h3 className="text-lg font-semibold text-slate-900 mb-2">
                    {searchQuery ? 'No users found' : 'No team members yet'}
                  </h3>
                  <p className="text-slate-600 mb-4 max-w-sm">
                    {searchQuery
                      ? 'Try adjusting your search query'
                      : 'Invite team members to collaborate on recruiting activities'}
                  </p>
                  {canManageUsers && !searchQuery && (
                    <Button className="gap-2" onClick={() => setInviteDialogOpen(true)}>
                      <Plus className="h-4 w-4" />
                      Invite Your First Team Member
                    </Button>
                  )}
                </div>
              ) : (
                <UsersTable
                  users={users}
                  onResetPassword={(user) => setResetPasswordUser(user)}
                />
              )}
            </TabsContent>

            {/* Hierarchy Tab */}
            <TabsContent value="hierarchy" className="mt-0">
              <div className="px-6 py-3 border-t flex justify-end gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={expandAll}
                  disabled={isLoadingHierarchy}
                  className="gap-1.5"
                >
                  <Expand className="h-3.5 w-3.5" />
                  Expand All
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={collapseAll}
                  disabled={isLoadingHierarchy}
                  className="gap-1.5"
                >
                  <Minimize2 className="h-3.5 w-3.5" />
                  Collapse All
                </Button>
              </div>
              <div className="p-6 border-t">
                {isLoadingHierarchy ? (
                  <div className="space-y-2">
                    <Skeleton className="h-12 w-full" />
                    <Skeleton className="h-12 w-full" />
                    <Skeleton className="h-12 w-full" />
                  </div>
                ) : hierarchyError ? (
                  <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                      Failed to load team hierarchy. Please try again.
                    </AlertDescription>
                  </Alert>
                ) : hierarchyData && hierarchyData.top_level_users.length > 0 ? (
                  <div className="space-y-1">
                    {hierarchyData.top_level_users.map((member) => renderTeamMember(member))}
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center py-16 text-center">
                    <div className="p-4 rounded-full bg-slate-100 mb-4">
                      <Users className="h-12 w-12 text-slate-400" />
                    </div>
                    <h3 className="text-lg font-semibold text-slate-900 mb-2">No team hierarchy found</h3>
                    <p className="text-slate-600 max-w-sm">Start by adding users and assigning managers</p>
                  </div>
                )}
              </div>
            </TabsContent>

            {/* Managers Tab */}
            <TabsContent value="managers" className="mt-0 border-t">
              {isLoadingManagers ? (
                <div className="p-6 space-y-2">
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                </div>
              ) : managersData && managersData.managers.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Email</TableHead>
                      <TableHead>Roles</TableHead>
                      <TableHead className="text-right">Team Size</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {managersData.managers.map((manager) => (
                      <TableRow key={manager.id}>
                        <TableCell className="font-medium">
                          {manager.first_name} {manager.last_name}
                        </TableCell>
                        <TableCell>{manager.email}</TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            {manager.roles.map((role: string | { name: string; display_name: string }) => (
                              <Badge key={typeof role === 'string' ? role : role.name} variant="outline" className="text-xs">
                                {typeof role === 'string' ? role : (role.display_name || role.name)}
                              </Badge>
                            ))}
                          </div>
                        </TableCell>
                        <TableCell className="text-right">
                          <Badge variant="secondary">
                            {manager.team_count} {manager.team_count === 1 ? 'report' : 'reports'}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <div className="p-4 rounded-full bg-slate-100 mb-4">
                    <UserCog className="h-12 w-12 text-slate-400" />
                  </div>
                  <h3 className="text-lg font-semibold text-slate-900 mb-2">No managers found</h3>
                  <p className="text-slate-600 max-w-sm">Assign managers to team members to see them here</p>
                </div>
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Roles & Permissions Link Card */}
      {canManageUsers && (
        <Link to="/users/roles" className="block group mt-6">
          <Card className="hover:shadow-md hover:border-primary/50 transition-all cursor-pointer">
            <CardHeader className="flex flex-row items-center justify-between py-4">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-lg bg-gradient-to-br from-slate-100 to-slate-50">
                  <Shield className="h-5 w-5 text-slate-600" />
                </div>
                <div>
                  <CardTitle className="text-base group-hover:text-primary transition-colors">
                    Roles & Permissions
                  </CardTitle>
                  <CardDescription>Manage custom roles and assign permissions</CardDescription>
                </div>
              </div>
              <ArrowRight className="h-5 w-5 text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all" />
            </CardHeader>
          </Card>
        </Link>
      )}

      {/* Assign Manager Dialog */}
      <Dialog open={assignDialogOpen} onOpenChange={setAssignDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Assign Manager</DialogTitle>
            <DialogDescription>
              Select a manager for {selectedUser?.first_name} {selectedUser?.last_name}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Manager</label>
              <Select value={selectedManagerId} onValueChange={setSelectedManagerId}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a manager" />
                </SelectTrigger>
                <SelectContent>
                  {availableManagersData?.managers.map((manager: UserBasicInfo) => (
                    <SelectItem key={manager.id} value={manager.id.toString()}>
                      {manager.first_name} {manager.last_name} ({manager.email})
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
                setSelectedUser(null);
                setSelectedManagerId('');
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={confirmAssignManager}
              disabled={!selectedManagerId || assignManagerMutation.isPending}
            >
              {assignManagerMutation.isPending ? 'Assigning...' : 'Assign Manager'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Remove Manager Dialog */}
      <Dialog open={removeDialogOpen} onOpenChange={setRemoveDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Remove Manager</DialogTitle>
            <DialogDescription>
              Are you sure you want to remove the manager assignment from{' '}
              {selectedUser?.first_name} {selectedUser?.last_name}?
            </DialogDescription>
          </DialogHeader>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setRemoveDialogOpen(false);
                setSelectedUser(null);
              }}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={confirmRemoveManager}
              disabled={removeManagerMutation.isPending}
            >
              {removeManagerMutation.isPending ? 'Removing...' : 'Remove Manager'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Invite User Dialog */}
      <InviteUserDialog open={inviteDialogOpen} onOpenChange={setInviteDialogOpen} />
      
      {/* Reset Password Dialog */}
      <ResetPasswordDialog
        user={resetPasswordUser}
        open={resetPasswordUser !== null}
        onOpenChange={(open) => !open && setResetPasswordUser(null)}
      />
    </>
  );
}
