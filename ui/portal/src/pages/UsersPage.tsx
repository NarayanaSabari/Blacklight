/**
 * Users Page (Tenant Admin Only)
 * Manage team members and users
 */

import { Link } from 'react-router-dom';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { UserCog, Plus, Search, Shield, Users, UserCheck, AlertCircle } from 'lucide-react';
import { InviteUserDialog } from '@/components/InviteUserDialog';
import { UsersTable } from '@/components/UsersTable';
import { ResetPasswordDialog } from '@/components/ResetPasswordDialog';
import { fetchUsers } from '@/lib/api/users';
import { usePermissions } from '@/hooks/usePermissions';
import type { PortalUserFull } from '@/types';

export function UsersPage() {
  const { canManageUsers } = usePermissions();
  const [inviteDialogOpen, setInviteDialogOpen] = useState(false);
  const [resetPasswordUser, setResetPasswordUser] = useState<PortalUserFull | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  // Fetch users
  const { data: usersData, isLoading, error } = useQuery({
    queryKey: ['users', searchQuery],
    queryFn: () => fetchUsers({ search: searchQuery }),
  });

  const users = usersData?.users || [];

  // Calculate stats
  const stats = {
    total: users.length,
    active: users.filter((u) => u.is_active).length,
    recruiters: users.filter((u) => u.role.name === 'RECRUITER').length,
    hiring_managers: users.filter((u) => u.role.name === 'HIRING_MANAGER').length,
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Team Members</h1>
          <p className="text-slate-600 mt-1">Manage users and roles</p>
        </div>
        {canManageUsers && (
          <Button className="gap-2" onClick={() => setInviteDialogOpen(true)}>
            <Plus className="h-4 w-4" />
            Invite User
          </Button>
        )}
      </div>

      {/* Permission Warning */}
      {!canManageUsers && (
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Only Tenant Admins can invite and manage users. Contact your administrator for access.
          </AlertDescription>
        </Alert>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2 flex flex-row items-center justify-between">
            <CardDescription>Total Users</CardDescription>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <CardTitle className="text-3xl">
              {isLoading ? <Skeleton className="h-9 w-12" /> : stats.total}
            </CardTitle>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2 flex flex-row items-center justify-between">
            <CardDescription>Active</CardDescription>
            <UserCheck className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <CardTitle className="text-3xl">
              {isLoading ? <Skeleton className="h-9 w-12" /> : stats.active}
            </CardTitle>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2 flex flex-row items-center justify-between">
            <CardDescription>Recruiters</CardDescription>
            <UserCog className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <CardTitle className="text-3xl">
              {isLoading ? <Skeleton className="h-9 w-12" /> : stats.recruiters}
            </CardTitle>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2 flex flex-row items-center justify-between">
            <CardDescription>Hiring Managers</CardDescription>
            <Shield className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <CardTitle className="text-3xl">
              {isLoading ? <Skeleton className="h-9 w-12" /> : stats.hiring_managers}
            </CardTitle>
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Team Members</CardTitle>
              <CardDescription>Manage users and their permissions</CardDescription>
            </div>
            <div className="flex gap-2">
              <div className="relative">
                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search users..."
                  className="pl-8 w-[200px]"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : error ? (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                Failed to load users. Please try again later.
              </AlertDescription>
            </Alert>
          ) : users.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <UserCog className="h-12 w-12 text-slate-400 mb-4" />
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
        </CardContent>
      </Card>

      {/* Link to Roles Management Page */}
      {canManageUsers && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Roles & Permissions</CardTitle>
              <CardDescription>Manage custom roles and assign permissions.</CardDescription>
            </div>
            <Button asChild>
              <Link to="/users/roles">
                <UserCog className="mr-2 h-4 w-4" /> Manage Roles
              </Link>
            </Button>
          </CardHeader>
        </Card>
      )}

      {/* Dialogs */}
      <InviteUserDialog open={inviteDialogOpen} onOpenChange={setInviteDialogOpen} />
      <ResetPasswordDialog
        user={resetPasswordUser}
        open={resetPasswordUser !== null}
        onOpenChange={(open) => !open && setResetPasswordUser(null)}
      />
    </div>
  );
}
