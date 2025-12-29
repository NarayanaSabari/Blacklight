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
import { UserCog, Plus, Search, Shield, Users, UserCheck, AlertCircle, ArrowRight, GitBranch } from 'lucide-react';
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
      {/* Permission Warning */}
      {!canManageUsers && (
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Only Tenant Admins can invite and manage users. Contact your administrator for access.
          </AlertDescription>
        </Alert>
      )}

      {/* Main Card with Integrated Header */}
      <Card>
        <CardHeader className="border-b bg-slate-50/50">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            {/* Inline Stats */}
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-md bg-blue-100">
                  <Users className="h-4 w-4 text-blue-600" />
                </div>
                <div>
                  <span className="text-2xl font-bold">{isLoading ? '-' : stats.total}</span>
                  <span className="text-sm text-muted-foreground ml-1.5">Total</span>
                </div>
              </div>
              <div className="h-8 w-px bg-border" />
              <div className="flex items-center gap-4 text-sm">
                <div className="flex items-center gap-1.5">
                  <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                    <UserCheck className="h-3 w-3 mr-1" />
                    {stats.active} Active
                  </Badge>
                </div>
                <div className="flex items-center gap-1.5">
                  <Badge variant="outline" className="bg-purple-50 text-purple-700 border-purple-200">
                    <UserCog className="h-3 w-3 mr-1" />
                    {stats.recruiters} Recruiters
                  </Badge>
                </div>
                <div className="flex items-center gap-1.5">
                  <Badge variant="outline" className="bg-orange-50 text-orange-700 border-orange-200">
                    <Shield className="h-3 w-3 mr-1" />
                    {stats.managers} Managers
                  </Badge>
                </div>
              </div>
            </div>

            {/* Search and Actions */}
            <div className="flex items-center gap-3">
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
            <UsersTable
              users={users}
              onResetPassword={(user) => setResetPasswordUser(user)}
            />
          )}
        </CardContent>
      </Card>

      {/* Roles Management Link */}
      {canManageUsers && (
        <>
          <Link to="/settings/team" className="block group">
            <Card className="hover:shadow-md hover:border-primary/50 transition-all cursor-pointer">
              <CardHeader className="flex flex-row items-center justify-between py-4">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-lg bg-gradient-to-br from-purple-100 to-purple-50">
                    <GitBranch className="h-5 w-5 text-purple-600" />
                  </div>
                  <div>
                    <CardTitle className="text-base group-hover:text-primary transition-colors">
                      Team Hierarchy
                    </CardTitle>
                    <CardDescription>View organizational structure and manager assignments</CardDescription>
                  </div>
                </div>
                <ArrowRight className="h-5 w-5 text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all" />
              </CardHeader>
            </Card>
          </Link>

          <Link to="/users/roles" className="block group">
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
        </>
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
