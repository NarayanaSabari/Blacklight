import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
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
    // Can't manage yourself
    if (user.id === currentUser?.id) return false;
    // Only tenant admin can manage users
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

  return (
    <>
      <div className="overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-slate-50/80 hover:bg-slate-50/80">
              <TableHead className="font-semibold text-slate-700">User</TableHead>
              <TableHead className="font-semibold text-slate-700">Contact</TableHead>
              <TableHead className="font-semibold text-slate-700">Roles</TableHead>
              <TableHead className="font-semibold text-slate-700">Status</TableHead>
              <TableHead className="font-semibold text-slate-700">Last Active</TableHead>
              <TableHead className="w-[60px]"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {users.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-12 text-muted-foreground">
                  No users found
                </TableCell>
              </TableRow>
            ) : (
              users.map((user) => (
                <TableRow 
                  key={user.id} 
                  className={cn(
                    "group transition-colors",
                    user.id === currentUser?.id && "bg-blue-50/50"
                  )}
                >
                  {/* User Info */}
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <Avatar className="h-10 w-10 border-2 border-white shadow-sm">
                        <AvatarFallback className={cn(
                          "text-sm font-medium",
                          user.is_active 
                            ? "bg-gradient-to-br from-blue-500 to-indigo-600 text-white"
                            : "bg-slate-200 text-slate-500"
                        )}>
                          {getInitials(user.full_name)}
                        </AvatarFallback>
                      </Avatar>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-slate-900">{user.full_name}</span>
                          {user.id === currentUser?.id && (
                            <Badge variant="outline" className="text-[10px] px-1.5 py-0 bg-blue-50 text-blue-600 border-blue-200">
                              You
                            </Badge>
                          )}
                        </div>
                        <span className="text-sm text-muted-foreground">{user.email}</span>
                      </div>
                    </div>
                  </TableCell>

                  {/* Contact */}
                  <TableCell>
                    <div className="space-y-1">
                      <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                        <Mail className="h-3.5 w-3.5" />
                        <span className="truncate max-w-[160px]">{user.email}</span>
                      </div>
                      {user.phone ? (
                        <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                          <Phone className="h-3.5 w-3.5" />
                          <span>{user.phone}</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1.5 text-sm text-slate-400">
                          <Phone className="h-3.5 w-3.5" />
                          <span>—</span>
                        </div>
                      )}
                    </div>
                  </TableCell>

                  {/* Roles */}
                  <TableCell>
                    <div className="flex flex-wrap gap-1.5">
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
                  </TableCell>

                  {/* Status */}
                  <TableCell>
                    <div className="flex items-center gap-2">
                      {user.is_active ? (
                        <div className="flex items-center gap-1.5">
                          <span className="relative flex h-2.5 w-2.5">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-green-500"></span>
                          </span>
                          <span className="text-sm font-medium text-green-700">Active</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1.5">
                          <span className="h-2.5 w-2.5 rounded-full bg-slate-300"></span>
                          <span className="text-sm font-medium text-slate-500">Inactive</span>
                        </div>
                      )}
                      {user.is_locked && (
                        <Badge variant="outline" className="text-[10px] px-1.5 py-0 bg-red-50 text-red-600 border-red-200">
                          Locked
                        </Badge>
                      )}
                    </div>
                  </TableCell>

                  {/* Last Login */}
                  <TableCell>
                    {user.last_login ? (
                      <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                        <Calendar className="h-3.5 w-3.5" />
                        <span>{format(new Date(user.last_login), 'MMM d, yyyy')}</span>
                      </div>
                    ) : (
                      <span className="text-sm text-slate-400 italic">Never logged in</span>
                    )}
                  </TableCell>

                  {/* Actions */}
                  <TableCell>
                    {canManageUser(user) && (
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
                    )}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
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
