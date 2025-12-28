/**
 * Users Page (Tenant Admin Only)
 * Manage team members and users
 */

import { Link } from 'react-router-dom';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
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

  const users = usersData?.items || [];

  // Calculate stats
  const stats = {
    total: users.length,
    active: users.filter((u) => u.is_active).length,
    recruiters: users.filter((u) => u.roles?.some(r => r.name === 'RECRUITER')).length,
    managers: users.filter((u) => u.roles?.some(r => r.name === 'MANAGER')).length,
  };

  return (
    <div className="space-y-6">
      {/* Header with Search and Actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Team Members</h1>
          <p className="text-slate-600 mt-1">Manage your organization's users and permissions</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <Input
              placeholder="Search users..."
              className="pl-9 w-64"
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
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="bg-gradient-to-br from-blue-50 to-white border-blue-100">
          <CardHeader className="pb-2 flex flex-row items-center justify-between">
            <CardDescription className="font-medium text-slate-600">Total Users</CardDescription>
            <div className="p-2 rounded-lg bg-blue-100">
              <Users className="h-4 w-4 text-blue-600" />
            </div>
          </CardHeader>
          <CardContent>
            <CardTitle className="text-3xl text-slate-900">
              {isLoading ? <Skeleton className="h-9 w-12" /> : stats.total}
            </CardTitle>
          </CardContent>
        </Card>
        <Card className="bg-gradient-to-br from-green-50 to-white border-green-100">
          <CardHeader className="pb-2 flex flex-row items-center justify-between">
            <CardDescription className="font-medium text-slate-600">Active</CardDescription>
            <div className="p-2 rounded-lg bg-green-100">
              <UserCheck className="h-4 w-4 text-green-600" />
            </div>
          </CardHeader>
          <CardContent>
            <CardTitle className="text-3xl text-slate-900">
              {isLoading ? <Skeleton className="h-9 w-12" /> : stats.active}
            </CardTitle>
          </CardContent>
        </Card>
        <Card className="bg-gradient-to-br from-purple-50 to-white border-purple-100">
          <CardHeader className="pb-2 flex flex-row items-center justify-between">
            <CardDescription className="font-medium text-slate-600">Recruiters</CardDescription>
            <div className="p-2 rounded-lg bg-purple-100">
              <UserCog className="h-4 w-4 text-purple-600" />
            </div>
          </CardHeader>
          <CardContent>
            <CardTitle className="text-3xl text-slate-900">
              {isLoading ? <Skeleton className="h-9 w-12" /> : stats.recruiters}
            </CardTitle>
          </CardContent>
        </Card>
        <Card className="bg-gradient-to-br from-orange-50 to-white border-orange-100">
          <CardHeader className="pb-2 flex flex-row items-center justify-between">
            <CardDescription className="font-medium text-slate-600">Managers</CardDescription>
            <div className="p-2 rounded-lg bg-orange-100">
              <Shield className="h-4 w-4 text-orange-600" />
            </div>
          </CardHeader>
          <CardContent>
            <CardTitle className="text-3xl text-slate-900">
              {isLoading ? <Skeleton className="h-9 w-12" /> : stats.managers}
            </CardTitle>
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <Card>
        <CardHeader className="border-b">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>All Users</CardTitle>
              <CardDescription>Manage users and their permissions</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6 space-y-3">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : error ? (
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
            <div className="p-0">
              <UsersTable
                users={users}
                onResetPassword={(user) => setResetPasswordUser(user)}
              />
            </div>
          )}
        </CardContent>
      </Card>

      {/* Roles Management Link */}
      {canManageUsers && (
        <Card className="bg-gradient-to-r from-slate-50 to-white">
          <CardHeader className="flex flex-row items-center justify-between py-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-slate-100">
                <Shield className="h-5 w-5 text-slate-600" />
              </div>
              <div>
                <CardTitle className="text-base">Roles & Permissions</CardTitle>
                <CardDescription>Manage custom roles and assign permissions</CardDescription>
              </div>
            </div>
            <Button asChild variant="outline">
              <Link to="/users/roles">
                Manage Roles
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
