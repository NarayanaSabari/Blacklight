import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { MoreHorizontal, Trash2, KeyRound, UserX, UserCheck, UserCog, Mail, Phone, Calendar } from 'lucide-react';
import { toast } from 'sonner';
import { deleteUser, toggleUserActive } from '@/lib/api/users';
import type { PortalUserFull } from '@/types';
import { usePermissions } from '@/hooks/usePermissions';
import { UserRoleAssignmentDialog } from './UserRoleAssignmentDialog';
import { format } from 'date-fns';
import { cn } from '@/lib/utils';

interface UsersTableProps {
  users: PortalUserFull[];
  onResetPassword: (user: PortalUserFull) => void;
}

export function UsersTable({ users, onResetPassword }: UsersTableProps) {
  const queryClient = useQueryClient();
  const { user: currentUser, isTenantAdmin } = usePermissions();
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [userToDelete, setUserToDelete] = useState<PortalUserFull | null>(null);
  const [assignRolesUser, setAssignRolesUser] = useState<PortalUserFull | null>(null);

  const deleteUserMutation = useMutation({
    mutationFn: (id: number) => deleteUser(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      toast.success('User deleted successfully');
      setDeleteDialogOpen(false);
      setUserToDelete(null);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to delete user');
    },
  });

  const toggleActiveMutation = useMutation({
    mutationFn: ({ id, isActive }: { id: number; isActive: boolean }) =>
      toggleUserActive(id, isActive),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      toast.success(
        variables.isActive ? 'User activated' : 'User deactivated'
      );
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to update user status');
    },
  });

  const handleDelete = (user: PortalUserFull) => {
    setUserToDelete(user);
    setDeleteDialogOpen(true);
  };

  const confirmDelete = () => {
    if (userToDelete) {
      deleteUserMutation.mutate(userToDelete.id);
    }
  };

  const handleToggleActive = (user: PortalUserFull) => {
    toggleActiveMutation.mutate({
      id: user.id,
      isActive: !user.is_active,
    });
  };

  const canManageUser = (user: PortalUserFull) => {
    if (user.id === currentUser?.id) return false;
    return isTenantAdmin;
  };

  const getInitials = (name: string) => {
    return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
  };

  const getRoleBadgeColor = (roleName: string) => {
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

  if (users.length === 0) {
    return null;
  }

  return (
    <>
      <div className="divide-y divide-slate-100">
        {users.map((user) => (
          <div 
            key={user.id}
            className={cn(
              "px-6 py-4 flex items-center gap-4 hover:bg-slate-50 transition-colors group",
              user.id === currentUser?.id && "bg-blue-50/30"
            )}
          >
            {/* Avatar */}
            <Avatar className="h-11 w-11 flex-shrink-0 border-2 border-white shadow-sm">
              <AvatarFallback className={cn(
                "text-sm font-medium",
                user.is_active 
                  ? "bg-gradient-to-br from-blue-500 to-indigo-600 text-white"
                  : "bg-slate-200 text-slate-500"
              )}>
                {getInitials(user.full_name)}
              </AvatarFallback>
            </Avatar>

            {/* User Info - Name & Email */}
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="font-medium text-slate-900">{user.full_name}</span>
                {user.id === currentUser?.id && (
                  <Badge variant="outline" className="text-[10px] px-1.5 py-0 bg-blue-50 text-blue-600 border-blue-200">
                    You
                  </Badge>
                )}
              </div>
              <div className="flex items-center gap-4 mt-1 text-sm text-slate-500">
                <span className="flex items-center gap-1.5">
                  <Mail className="h-3.5 w-3.5" />
                  {user.email}
                </span>
                {user.phone && (
                  <span className="flex items-center gap-1.5">
                    <Phone className="h-3.5 w-3.5" />
                    {user.phone}
                  </span>
                )}
              </div>
            </div>

            {/* Roles */}
            <div className="flex flex-wrap gap-1.5 flex-shrink-0 max-w-[200px] justify-end">
              {user.roles && user.roles.length > 0 ? (
                user.roles.map((role) => (
                  <Badge 
                    key={role.id} 
                    variant="outline" 
                    className={cn("text-xs font-medium", getRoleBadgeColor(role.name))}
                  >
                    {role.display_name}
                  </Badge>
                ))
              ) : (
                <Badge variant="outline" className="text-xs text-slate-400 border-dashed">
                  No Roles
                </Badge>
              )}
            </div>

            {/* Status */}
            <div className="flex-shrink-0 w-24">
              {user.is_active ? (
                <div className="flex items-center gap-1.5">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                  </span>
                  <span className="text-sm font-medium text-green-700">Active</span>
                </div>
              ) : (
                <div className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-slate-300"></span>
                  <span className="text-sm font-medium text-slate-500">Inactive</span>
                </div>
              )}
            </div>

            {/* Last Login */}
            <div className="flex-shrink-0 w-32 text-right">
              {user.last_login ? (
                <div className="flex items-center gap-1.5 justify-end text-sm text-slate-500">
                  <Calendar className="h-3.5 w-3.5" />
                  <span>{format(new Date(user.last_login), 'MMM d, yyyy')}</span>
                </div>
              ) : (
                <span className="text-sm text-slate-400">Never</span>
              )}
            </div>

            {/* Actions */}
            <div className="flex-shrink-0 w-10">
              {canManageUser(user) ? (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button 
                      variant="ghost" 
                      size="icon"
                      className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <MoreHorizontal className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-48">
                    <DropdownMenuLabel className="text-xs text-muted-foreground font-normal">
                      Manage User
                    </DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={() => onResetPassword(user)}>
                      <KeyRound className="mr-2 h-4 w-4" />
                      Reset Password
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setAssignRolesUser(user)}>
                      <UserCog className="mr-2 h-4 w-4" />
                      Manage Roles
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => handleToggleActive(user)}>
                      {user.is_active ? (
                        <>
                          <UserX className="mr-2 h-4 w-4" />
                          Deactivate User
                        </>
                      ) : (
                        <>
                          <UserCheck className="mr-2 h-4 w-4" />
                          Activate User
                        </>
                      )}
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      onClick={() => handleDelete(user)}
                      className="text-destructive focus:text-destructive"
                    >
                      <Trash2 className="mr-2 h-4 w-4" />
                      Delete User
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              ) : (
                <div className="w-8" />
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete User</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete <strong>{userToDelete?.full_name}</strong>?
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* User Role Assignment Dialog */}
      <UserRoleAssignmentDialog
        user={assignRolesUser}
        open={assignRolesUser !== null}
        onOpenChange={(open) => !open && setAssignRolesUser(null)}
      />
    </>
  );
}
