/**
 * Tenant Users Table Component
 * Displays portal users for a specific tenant
 */

import { useState } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { MoreVertical, Search, KeyRound, UserX, CheckCircle, XCircle } from 'lucide-react';
import { ResetPasswordDialog } from '@/components/dialogs/ResetPasswordDialog';
import type { PortalUser } from '@/types';

interface TenantUsersTableProps {
  tenantId: number;
  users: PortalUser[];
  isLoading?: boolean;
}

export function TenantUsersTable({ tenantId, users, isLoading }: TenantUsersTableProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedUser, setSelectedUser] = useState<PortalUser | null>(null);
  const [showResetPasswordDialog, setShowResetPasswordDialog] = useState(false);

  const filteredUsers = users.filter((user) => {
    const query = searchQuery.toLowerCase();
    return (
      user.email.toLowerCase().includes(query) ||
      user.first_name.toLowerCase().includes(query) ||
      user.last_name.toLowerCase().includes(query)
    );
  });

  const handleResetPassword = (user: PortalUser) => {
    setSelectedUser(user);
    setShowResetPasswordDialog(true);
  };

  const getRoleBadgeVariant = (roleName: string) => {
    switch (roleName) {
      case 'TENANT_ADMIN':
        return 'default';
      case 'RECRUITER':
        return 'secondary';
      case 'MANAGER':
        return 'outline';
      case 'TEAM_LEAD':
        return 'outline';
      default:
        return 'outline';
    }
  };

  const getRoleLabel = (roleName: string) => {
    switch (roleName) {
      case 'TENANT_ADMIN':
        return 'Admin';
      case 'RECRUITER':
        return 'Recruiter';
      case 'MANAGER':
        return 'Manager';
      case 'TEAM_LEAD':
        return 'Team Lead';
      default:
        return roleName;
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Portal Users</CardTitle>
            <CardDescription>
              Manage users who have access to this tenant's portal
            </CardDescription>
          </div>
          <Badge variant="outline">
            {users.length} user{users.length !== 1 ? 's' : ''}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search users by name or email..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>

        {/* Table */}
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Last Login</TableHead>
                <TableHead className="w-[70px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-muted-foreground">
                    Loading users...
                  </TableCell>
                </TableRow>
              ) : filteredUsers.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-muted-foreground">
                    {searchQuery ? 'No users found matching your search' : 'No users found'}
                  </TableCell>
                </TableRow>
              ) : (
                filteredUsers.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell className="font-medium">
                      {user.first_name} {user.last_name}
                    </TableCell>
                    <TableCell className="text-muted-foreground">{user.email}</TableCell>
                    <TableCell>
                      {user.roles && user.roles.length > 0 ? (
                        <Badge variant={getRoleBadgeVariant(user.roles[0].name)}>
                          {getRoleLabel(user.roles[0].display_name)}
                        </Badge>
                      ) : (
                        <Badge variant="outline">N/A</Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      {user.is_active ? (
                        <div className="flex items-center gap-1 text-green-600">
                          <CheckCircle className="h-4 w-4" />
                          <span className="text-sm">Active</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1 text-muted-foreground">
                          <XCircle className="h-4 w-4" />
                          <span className="text-sm">Inactive</span>
                        </div>
                      )}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {user.last_login
                        ? new Date(user.last_login).toLocaleDateString()
                        : 'Never'}
                    </TableCell>
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <MoreVertical className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          {user.roles && user.roles.some(role => role.name === 'TENANT_ADMIN') && (
                            <DropdownMenuItem onClick={() => handleResetPassword(user)}>
                              <KeyRound className="mr-2 h-4 w-4" />
                              Reset Password
                            </DropdownMenuItem>
                          )}
                          <DropdownMenuItem className="text-destructive">
                            <UserX className="mr-2 h-4 w-4" />
                            Deactivate User
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </CardContent>

      {/* Reset Password Dialog */}
      {selectedUser && (
        <ResetPasswordDialog
          open={showResetPasswordDialog}
          onOpenChange={setShowResetPasswordDialog}
          user={selectedUser}
          tenantId={tenantId}
        />
      )}
    </Card>
  );
}
