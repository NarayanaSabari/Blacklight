/**
 * Users Page (Tenant Admin Only)
 * Manage team members and users
 */

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { UserCog, Plus, Search, Filter } from 'lucide-react';

export function UsersPage() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Team Members</h1>
          <p className="text-slate-600 mt-1">Manage users and roles</p>
        </div>
        <Button className="gap-2">
          <Plus className="h-4 w-4" />
          Invite User
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Users</CardDescription>
            <CardTitle className="text-3xl">0</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Active</CardDescription>
            <CardTitle className="text-3xl">0</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Recruiters</CardDescription>
            <CardTitle className="text-3xl">0</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Hiring Managers</CardDescription>
            <CardTitle className="text-3xl">0</CardTitle>
          </CardHeader>
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
              <Button variant="outline" size="sm" className="gap-2">
                <Search className="h-4 w-4" />
                Search
              </Button>
              <Button variant="outline" size="sm" className="gap-2">
                <Filter className="h-4 w-4" />
                Filter
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <UserCog className="h-12 w-12 text-slate-400 mb-4" />
            <h3 className="text-lg font-semibold text-slate-900 mb-2">No team members yet</h3>
            <p className="text-slate-600 mb-4 max-w-sm">
              Invite team members to collaborate on recruiting activities
            </p>
            <Button className="gap-2">
              <Plus className="h-4 w-4" />
              Invite Your First Team Member
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Role Management Section */}
      <Card>
        <CardHeader>
          <CardTitle>Roles & Permissions</CardTitle>
          <CardDescription>Manage custom roles for your organization</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex items-center justify-between p-4 border border-slate-200 rounded-lg">
              <div>
                <div className="font-medium">Tenant Admin</div>
                <div className="text-sm text-slate-600">Full access to all features</div>
              </div>
              <Badge>System Role</Badge>
            </div>
            <div className="flex items-center justify-between p-4 border border-slate-200 rounded-lg">
              <div>
                <div className="font-medium">Recruiter</div>
                <div className="text-sm text-slate-600">Manage candidates and jobs</div>
              </div>
              <Badge>System Role</Badge>
            </div>
            <div className="flex items-center justify-between p-4 border border-slate-200 rounded-lg">
              <div>
                <div className="font-medium">Hiring Manager</div>
                <div className="text-sm text-slate-600">Review candidates and provide feedback</div>
              </div>
              <Badge>System Role</Badge>
            </div>
          </div>
          <div className="mt-4">
            <Button variant="outline" className="w-full gap-2">
              <Plus className="h-4 w-4" />
              Create Custom Role
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
