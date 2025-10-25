/**
 * Portal Dashboard Page
 * Welcome page showing tenant name and user information
 */

import { usePortalAuth } from '@/contexts/PortalAuthContext';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Building2, User, Mail, Shield, LogOut } from 'lucide-react';

export function DashboardPage() {
  const { user, tenantName, logout } = usePortalAuth();

  const handleLogout = async () => {
    await logout();
  };

  if (!user) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Building2 className="h-8 w-8 text-primary" />
              <div>
                <h1 className="text-xl font-bold text-slate-900">{tenantName}</h1>
                <p className="text-sm text-slate-500">Portal</p>
              </div>
            </div>
            
            <Button
              variant="outline"
              size="sm"
              onClick={handleLogout}
              className="gap-2"
            >
              <LogOut className="h-4 w-4" />
              Sign Out
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Welcome Section */}
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-slate-900 mb-2">
            Welcome, {user.first_name}!
          </h2>
          <p className="text-lg text-slate-600">
            You're logged into {tenantName}'s portal
          </p>
        </div>

        {/* User Info Card */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="h-5 w-5" />
              Your Profile
            </CardTitle>
            <CardDescription>
              Your account information and role
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label>Full Name</Label>
                <p className="text-lg font-medium">{user.full_name}</p>
              </div>
              
              <div>
                <Label>Email</Label>
                <div className="flex items-center gap-2">
                  <Mail className="h-4 w-4 text-slate-500" />
                  <p className="text-lg font-medium">{user.email}</p>
                </div>
              </div>
              
              <div>
                <Label>Role</Label>
                <div className="flex items-center gap-2 mt-1">
                  <Shield className="h-4 w-4 text-slate-500" />
                  <Badge variant="secondary" className="text-sm">
                    {user.role.display_name}
                  </Badge>
                </div>
              </div>
              
              <div>
                <Label>Account Status</Label>
                <div className="mt-1">
                  <Badge variant={user.is_active ? "default" : "destructive"}>
                    {user.is_active ? 'Active' : 'Inactive'}
                  </Badge>
                </div>
              </div>

              {user.phone && (
                <div>
                  <Label>Phone</Label>
                  <p className="text-lg font-medium">{user.phone}</p>
                </div>
              )}

              {user.last_login && (
                <div>
                  <Label>Last Login</Label>
                  <p className="text-sm text-slate-600">
                    {new Date(user.last_login).toLocaleString()}
                  </p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Tenant Info Card */}
        {user.tenant && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Building2 className="h-5 w-5" />
                Organization Details
              </CardTitle>
              <CardDescription>
                Information about your organization
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label>Company Name</Label>
                  <p className="text-lg font-medium">{user.tenant.company_name}</p>
                </div>
                
                <div>
                  <Label>Organization ID</Label>
                  <p className="text-sm font-mono text-slate-600">{user.tenant.slug}</p>
                </div>
                
                <div>
                  <Label>Status</Label>
                  <Badge 
                    variant={user.tenant.status === 'ACTIVE' ? 'default' : 'secondary'}
                    className="mt-1"
                  >
                    {user.tenant.status}
                  </Badge>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Coming Soon Section */}
        <Card className="mt-6 border-dashed">
          <CardHeader>
            <CardTitle>More Features Coming Soon</CardTitle>
            <CardDescription>
              Additional portal features will be available here soon
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm text-slate-600">
              <li>• Candidate management</li>
              <li>• Job postings</li>
              <li>• Interview scheduling</li>
              <li>• Team collaboration</li>
              <li>• Reports and analytics</li>
            </ul>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}

function Label({ children }: { children: React.ReactNode }) {
  return <div className="text-sm font-medium text-slate-500 mb-1">{children}</div>;
}
