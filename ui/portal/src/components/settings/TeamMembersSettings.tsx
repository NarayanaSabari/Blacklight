/**
 * Team Members Settings Component
 * Unified view for user management, team hierarchy, and manager assignments
 */

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
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
  UserCheck,
  Mail,
  X,
} from 'lucide-react';
import { toast } from 'sonner';
import { teamApi } from '@/lib/teamApi';
import { fetchUsers } from '@/lib/api/users';
import { usePermissions } from '@/hooks/usePermissions';
import { InviteUserDialog } from '@/components/InviteUserDialog';
import { UsersTable } from '@/components/UsersTable';
import { ResetPasswordDialog } from '@/components/ResetPasswordDialog';
import type { TeamMember, UserBasicInfo, PortalUserFull } from '@/types';
import { cn } from '@/lib/utils';

type TabValue = 'users' | 'hierarchy' | 'managers';

interface TabConfig {
  id: TabValue;
  label: string;
  icon: React.ElementType;
  count?: number;
}

export function TeamMembersSettings() {
  const queryClient = useQueryClient();
  const { hasPermission, canManageUsers } = usePermissions();
  
  // Active tab state
  const [activeTab, setActiveTab] = useState<TabValue>('users');
  
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

  const getInitials = (firstName: string, lastName: string) => {
    return `${firstName?.[0] || ''}${lastName?.[0] || ''}`.toUpperCase();
  };

  const getRoleBadgeStyle = (roleName: string) => {
    switch (roleName) {
      case 'TENANT_ADMIN':
        return 'bg-purple-100 text-purple-700 border-purple-200';
      case 'MANAGER':
        return 'bg-blue-100 text-blue-700 border-blue-200';
      case 'RECRUITER':
        return 'bg-green-100 text-green-700 border-green-200';
      case 'TEAM_LEAD':
        return 'bg-orange-100 text-orange-700 border-orange-200';
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  // Render team member node (recursive)
  const renderTeamMember = (member: TeamMember, level: number = 0) => {
    const hasTeamMembers = member.team_members && member.team_members.length > 0;
    const isExpanded = expandedNodes.has(member.id);

    return (
      <div key={member.id}>
        <div
          className={cn(
            "flex items-center gap-3 py-3 px-4 hover:bg-slate-50 rounded-lg group transition-colors",
            level > 0 && "ml-8 border-l-2 border-slate-200"
          )}
          style={{ marginLeft: level > 0 ? `${level * 32}px` : undefined }}
        >
          {/* Expand/Collapse Button */}
          {hasTeamMembers ? (
            <button
              onClick={() => toggleNode(member.id)}
              className="p-1 hover:bg-slate-200 rounded-md transition-colors flex-shrink-0"
            >
              {isExpanded ? (
                <ChevronDown className="h-4 w-4 text-slate-500" />
              ) : (
                <ChevronRight className="h-4 w-4 text-slate-500" />
              )}
            </button>
          ) : (
            <div className="w-6" />
          )}

          {/* Avatar */}
          <Avatar className="h-9 w-9 flex-shrink-0 border-2 border-white shadow-sm">
            <AvatarFallback className="bg-gradient-to-br from-slate-600 to-slate-800 text-white text-xs font-medium">
              {getInitials(member.first_name, member.last_name)}
            </AvatarFallback>
          </Avatar>

          {/* User Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-medium text-slate-900 truncate">
                {member.first_name} {member.last_name}
              </span>
              {hasTeamMembers && (
                <Badge variant="secondary" className="text-[10px] px-1.5 py-0 bg-blue-50 text-blue-600">
                  {member.team_members.length} {member.team_members.length === 1 ? 'report' : 'reports'}
                </Badge>
              )}
            </div>
            <span className="text-sm text-slate-500 truncate block">{member.email}</span>
          </div>

          {/* Roles */}
          <div className="flex gap-1.5 flex-shrink-0">
            {member.roles.map((role: string | { name: string; display_name: string }) => {
              const roleName = typeof role === 'string' ? role : role.name;
              const displayName = typeof role === 'string' ? role : (role.display_name || role.name);
              return (
                <Badge 
                  key={roleName} 
                  variant="outline" 
                  className={cn("text-xs font-medium", getRoleBadgeStyle(roleName))}
                >
                  {displayName}
                </Badge>
              );
            })}
          </div>

          {/* Actions */}
          {canAssignManager && (
            <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
              <Button
                size="sm"
                variant="ghost"
                onClick={() => handleAssignManager(member)}
                className="h-8 text-xs"
              >
                <UserPlus className="h-3.5 w-3.5 mr-1" />
                {member.manager_id ? 'Change' : 'Assign'}
              </Button>
              {member.manager_id && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => handleRemoveManager(member)}
                  className="h-8 text-xs text-red-600 hover:text-red-700 hover:bg-red-50"
                >
                  <UserMinus className="h-3.5 w-3.5" />
                </Button>
              )}
            </div>
          )}
        </div>

        {/* Render team members recursively */}
        {hasTeamMembers && isExpanded && (
          <div>
            {member.team_members.map((teamMember) =>
              renderTeamMember(teamMember, level + 1)
            )}
          </div>
        )}
      </div>
    );
  };

  // Tab configuration
  const tabs: TabConfig[] = [
    { id: 'users', label: 'Users', icon: Users, count: userStats.total },
    { id: 'hierarchy', label: 'Hierarchy', icon: GitBranch },
    { id: 'managers', label: 'Managers', icon: UserCog, count: managersData?.total || 0 },
  ];

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

      <Card className="border-slate-200 shadow-sm">
        {/* Header with Stats */}
        <div className="px-6 py-5 border-b border-slate-100">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Team Management</h2>
              <p className="text-sm text-slate-500 mt-0.5">Manage users, view hierarchy, and assign managers</p>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-100 rounded-lg">
                <Users className="h-4 w-4 text-slate-500" />
                <span className="text-sm font-semibold text-slate-700">{isLoadingUsers ? '...' : userStats.total}</span>
                <span className="text-sm text-slate-500">total</span>
              </div>
              <Badge className="bg-green-100 text-green-700 border-green-200 hover:bg-green-100">
                <UserCheck className="h-3 w-3 mr-1" />
                {userStats.active} active
              </Badge>
            </div>
          </div>
        </div>

        {/* Tab Navigation & Actions Bar */}
        <div className="px-6 py-3 border-b border-slate-100 bg-slate-50/50">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            {/* Custom Tabs */}
            <div className="flex items-center gap-1 p-1 bg-white rounded-lg border border-slate-200 shadow-sm">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={cn(
                      "flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all",
                      isActive 
                        ? "bg-slate-900 text-white shadow-sm" 
                        : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                    )}
                  >
                    <Icon className="h-4 w-4" />
                    {tab.label}
                    {tab.count !== undefined && (
                      <span className={cn(
                        "text-xs px-1.5 py-0.5 rounded-full",
                        isActive 
                          ? "bg-white/20 text-white" 
                          : "bg-slate-200 text-slate-600"
                      )}>
                        {tab.count}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>

            {/* Actions */}
            <div className="flex items-center gap-3">
              {/* Search */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                <Input
                  placeholder="Search users..."
                  className="pl-9 w-56 h-9 bg-white border-slate-200"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
                {searchQuery && (
                  <button 
                    onClick={() => setSearchQuery('')}
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-1 hover:bg-slate-100 rounded"
                  >
                    <X className="h-3 w-3 text-slate-400" />
                  </button>
                )}
              </div>
              
              {/* Invite Button */}
              {canManageUsers && (
                <Button onClick={() => setInviteDialogOpen(true)} className="h-9 gap-2">
                  <Plus className="h-4 w-4" />
                  Invite User
                </Button>
              )}
            </div>
          </div>
        </div>

        <CardContent className="p-0">
          {/* Users Tab */}
          {activeTab === 'users' && (
            <div>
              {isLoadingUsers ? (
                <div className="p-6 space-y-3">
                  {[...Array(5)].map((_, i) => (
                    <Skeleton key={i} className="h-16 w-full rounded-lg" />
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
                <div className="flex flex-col items-center justify-center py-20 text-center">
                  <div className="p-4 rounded-full bg-slate-100 mb-4">
                    <Users className="h-10 w-10 text-slate-400" />
                  </div>
                  <h3 className="text-lg font-semibold text-slate-900 mb-1">
                    {searchQuery ? 'No users found' : 'No team members yet'}
                  </h3>
                  <p className="text-slate-500 mb-5 max-w-sm">
                    {searchQuery
                      ? 'Try adjusting your search query'
                      : 'Invite team members to collaborate on recruiting activities'}
                  </p>
                  {canManageUsers && !searchQuery && (
                    <Button onClick={() => setInviteDialogOpen(true)} className="gap-2">
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
            </div>
          )}

          {/* Hierarchy Tab */}
          {activeTab === 'hierarchy' && (
            <div>
              {/* Hierarchy Actions */}
              <div className="px-6 py-3 border-b border-slate-100 flex justify-between items-center bg-slate-50/30">
                <p className="text-sm text-slate-500">
                  {hierarchyData?.top_level_users?.length || 0} top-level members
                </p>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={expandAll}
                    disabled={isLoadingHierarchy}
                    className="h-8 text-xs gap-1.5"
                  >
                    <Expand className="h-3.5 w-3.5" />
                    Expand All
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={collapseAll}
                    disabled={isLoadingHierarchy}
                    className="h-8 text-xs gap-1.5"
                  >
                    <Minimize2 className="h-3.5 w-3.5" />
                    Collapse All
                  </Button>
                </div>
              </div>
              
              <div className="p-4">
                {isLoadingHierarchy ? (
                  <div className="space-y-3">
                    {[...Array(4)].map((_, i) => (
                      <Skeleton key={i} className="h-14 w-full rounded-lg" />
                    ))}
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
                      <GitBranch className="h-10 w-10 text-slate-400" />
                    </div>
                    <h3 className="text-lg font-semibold text-slate-900 mb-1">No team hierarchy found</h3>
                    <p className="text-slate-500 max-w-sm">Start by adding users and assigning managers</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Managers Tab */}
          {activeTab === 'managers' && (
            <div>
              {isLoadingManagers ? (
                <div className="p-6 space-y-3">
                  {[...Array(3)].map((_, i) => (
                    <Skeleton key={i} className="h-16 w-full rounded-lg" />
                  ))}
                </div>
              ) : managersData && managersData.managers.length > 0 ? (
                <div className="divide-y divide-slate-100">
                  {managersData.managers.map((manager) => (
                    <div key={manager.id} className="px-6 py-4 flex items-center gap-4 hover:bg-slate-50 transition-colors">
                      {/* Avatar */}
                      <Avatar className="h-11 w-11 border-2 border-white shadow-sm flex-shrink-0">
                        <AvatarFallback className="bg-gradient-to-br from-blue-500 to-indigo-600 text-white text-sm font-medium">
                          {getInitials(manager.first_name, manager.last_name)}
                        </AvatarFallback>
                      </Avatar>
                      
                      {/* Info */}
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-slate-900">
                          {manager.first_name} {manager.last_name}
                        </div>
                        <div className="flex items-center gap-1.5 text-sm text-slate-500">
                          <Mail className="h-3.5 w-3.5" />
                          {manager.email}
                        </div>
                      </div>

                      {/* Roles */}
                      <div className="flex gap-1.5 flex-shrink-0">
                        {manager.roles.map((role: string | { name: string; display_name: string }) => {
                          const roleName = typeof role === 'string' ? role : role.name;
                          const displayName = typeof role === 'string' ? role : (role.display_name || role.name);
                          return (
                            <Badge 
                              key={roleName} 
                              variant="outline" 
                              className={cn("text-xs font-medium", getRoleBadgeStyle(roleName))}
                            >
                              {displayName}
                            </Badge>
                          );
                        })}
                      </div>

                      {/* Team Count */}
                      <div className="flex-shrink-0">
                        <Badge className="bg-slate-100 text-slate-700 hover:bg-slate-100 font-semibold">
                          {manager.team_count} {manager.team_count === 1 ? 'report' : 'reports'}
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <div className="p-4 rounded-full bg-slate-100 mb-4">
                    <UserCog className="h-10 w-10 text-slate-400" />
                  </div>
                  <h3 className="text-lg font-semibold text-slate-900 mb-1">No managers found</h3>
                  <p className="text-slate-500 max-w-sm">Assign managers to team members to see them here</p>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

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
