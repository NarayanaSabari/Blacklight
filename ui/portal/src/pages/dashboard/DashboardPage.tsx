/**
 * Portal Dashboard Page
 * Shows role-specific statistics and recent activity
 */

import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { usePortalAuth } from '@/contexts/PortalAuthContext';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert';
import {
  Users,
  UserCheck,
  ClipboardList,
  Clock,
  Mail,
  TrendingUp,
  ArrowRight,
  Briefcase,
  UserPlus,
  CheckCircle,
  AlertCircle,
  AlertTriangle,
  XCircle,
} from 'lucide-react';
import { dashboardApi } from '@/lib/dashboardApi';
import { emailIntegrationApi, type EmailIntegration } from '@/lib/emailIntegrationApi';

const ONBOARDING_STATUS_COLORS: Record<string, string> = {
  PENDING_ASSIGNMENT: 'bg-gray-100 text-gray-700',
  ASSIGNED: 'bg-blue-100 text-blue-700',
  PENDING_ONBOARDING: 'bg-yellow-100 text-yellow-700',
  ONBOARDED: 'bg-purple-100 text-purple-700',
  APPROVED: 'bg-green-100 text-green-700',
  REJECTED: 'bg-red-100 text-red-700',
};

export function DashboardPage() {
  const { user, tenantName } = usePortalAuth();

  // Fetch dashboard stats
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: dashboardApi.getStats,
    refetchInterval: 60000, // Refresh every minute
  });

  // Fetch recent activity
  const { data: activity, isLoading: activityLoading } = useQuery({
    queryKey: ['dashboard-activity'],
    queryFn: dashboardApi.getRecentActivity,
    refetchInterval: 60000,
  });

  // Fetch integration status to show warnings for failed integrations
  const { data: integrations } = useQuery({
    queryKey: ['email-integrations-dashboard'],
    queryFn: emailIntegrationApi.listIntegrations,
    refetchInterval: 300000, // Check every 5 minutes
    staleTime: 60000,
  });

  // Filter integrations that have errors
  const failedIntegrations = integrations?.filter(
    (i: EmailIntegration) => i.last_error !== null
  ) ?? [];

  if (!user) {
    return null;
  }

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffHours / 24);
    
    if (diffHours < 1) return 'Just now';
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className="space-y-6">
      {/* Integration Failure Warning */}
      {failedIntegrations.length > 0 && (
        <Alert className="border-amber-300 bg-amber-50 text-amber-900">
          <AlertTriangle className="h-4 w-4 text-amber-600" />
          <AlertTitle className="text-amber-900 font-semibold">
            {failedIntegrations.length === 1
              ? 'Email integration issue'
              : `${failedIntegrations.length} email integration issues`}
          </AlertTitle>
          <AlertDescription className="text-amber-800">
            <div className="mt-1 space-y-1.5">
              {failedIntegrations.map((integration: EmailIntegration) => (
                <div key={integration.id} className="flex items-start gap-2 text-sm">
                  <XCircle className="h-3.5 w-3.5 mt-0.5 shrink-0 text-amber-600" />
                  <span>
                    <span className="font-medium capitalize">{integration.provider}</span>
                    {integration.email_address && (
                      <span className="text-amber-700"> ({integration.email_address})</span>
                    )}
                    {!integration.is_active && (
                      <span className="text-red-700 font-medium"> - Deactivated</span>
                    )}
                    <span className="text-amber-700"> — {integration.last_error}</span>
                  </span>
                </div>
              ))}
            </div>
            <Link to="/settings/integrations">
              <Button
                variant="outline"
                size="sm"
                className="mt-3 border-amber-400 text-amber-900 hover:bg-amber-100"
              >
                View Integrations
                <ArrowRight className="ml-1.5 h-3.5 w-3.5" />
              </Button>
            </Link>
          </AlertDescription>
        </Alert>
      )}

      {/* Welcome Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            Welcome back, {user.first_name}!
          </h1>
          <p className="text-slate-600 mt-1">
            Here's what's happening at {tenantName}
          </p>
        </div>
        <Badge variant="outline" className="text-sm">
          {stats?.user_role?.replace('_', ' ') || 'Loading...'}
        </Badge>
      </div>

      {/* My Stats Section */}
      <div>
        <h2 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
          <Briefcase className="h-5 w-5 text-primary" />
          Your Candidates
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {/* My Assigned Candidates */}
          <Card className="bg-gradient-to-br from-blue-50 to-white border-blue-100">
            <CardContent className="pt-5">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-600">Assigned to You</p>
                  <p className="text-3xl font-bold text-slate-900 mt-1">
                    {statsLoading ? <Skeleton className="h-9 w-12" /> : stats?.my_stats.assigned_candidates || 0}
                  </p>
                </div>
                <div className="p-3 rounded-xl bg-blue-100">
                  <Users className="h-6 w-6 text-blue-600" />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Approved */}
          <Card className="bg-gradient-to-br from-green-50 to-white border-green-100">
            <CardContent className="pt-5">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-600">Approved</p>
                  <p className="text-3xl font-bold text-green-600 mt-1">
                    {statsLoading ? <Skeleton className="h-9 w-12" /> : stats?.my_stats.by_status?.APPROVED || 0}
                  </p>
                </div>
                <div className="p-3 rounded-xl bg-green-100">
                  <UserCheck className="h-6 w-6 text-green-600" />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Pending Onboarding */}
          <Card className="bg-gradient-to-br from-orange-50 to-white border-orange-100">
            <CardContent className="pt-5">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-600">Pending</p>
                  <p className="text-3xl font-bold text-orange-600 mt-1">
                    {statsLoading ? (
                      <Skeleton className="h-9 w-12" />
                    ) : (
                      (stats?.my_stats.by_status?.PENDING_ONBOARDING || 0) +
                      (stats?.my_stats.by_status?.ASSIGNED || 0) +
                      (stats?.my_stats.by_status?.PENDING_ASSIGNMENT || 0)
                    )}
                  </p>
                </div>
                <div className="p-3 rounded-xl bg-orange-100">
                  <Clock className="h-6 w-6 text-orange-600" />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Recent Assignments */}
          <Card className="bg-gradient-to-br from-purple-50 to-white border-purple-100">
            <CardContent className="pt-5">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-600">New This Week</p>
                  <p className="text-3xl font-bold text-purple-600 mt-1">
                    {statsLoading ? <Skeleton className="h-9 w-12" /> : stats?.my_stats.recent_assignments || 0}
                  </p>
                </div>
                <div className="p-3 rounded-xl bg-purple-100">
                  <TrendingUp className="h-6 w-6 text-purple-600" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Team Stats (for managers) */}
      {stats?.team_stats && (
        <div>
          <h2 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
            <Users className="h-5 w-5 text-primary" />
            Your Team
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-2 gap-4">
            <Card>
              <CardContent className="pt-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-slate-600">Team Members</p>
                    <p className="text-3xl font-bold text-slate-900 mt-1">
                      {stats.team_stats.team_members}
                    </p>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-100">
                    <Users className="h-6 w-6 text-slate-600" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-slate-600">Team's Candidates</p>
                    <p className="text-3xl font-bold text-slate-900 mt-1">
                      {stats.team_stats.team_candidates}
                    </p>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-100">
                    <Briefcase className="h-6 w-6 text-slate-600" />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {/* Tenant Overview (for all users) */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
            <ClipboardList className="h-5 w-5 text-primary" />
            Organization Overview
          </h2>
          <Link to="/candidates">
            <Button variant="ghost" size="sm" className="gap-1">
              View All <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-5">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-lg bg-blue-100">
                  <Users className="h-5 w-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-slate-900">
                    {statsLoading ? '-' : stats?.tenant_stats.total_candidates || 0}
                  </p>
                  <p className="text-xs text-slate-600">Total Candidates</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-5">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-lg bg-green-100">
                  <UserPlus className="h-5 w-5 text-green-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-green-600">
                    {statsLoading ? '-' : stats?.tenant_stats.new_candidates_7d || 0}
                  </p>
                  <p className="text-xs text-slate-600">New This Week</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-5">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-lg bg-orange-100">
                  <Mail className="h-5 w-5 text-orange-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-orange-600">
                    {statsLoading ? '-' : stats?.tenant_stats.pending_invitations || 0}
                  </p>
                  <p className="text-xs text-slate-600">Pending Invites</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-5">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-lg bg-purple-100">
                  <ClipboardList className="h-5 w-5 text-purple-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-purple-600">
                    {statsLoading ? '-' : stats?.tenant_stats.pending_review || 0}
                  </p>
                  <p className="text-xs text-slate-600">Needs Review</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Two Column Layout: Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Candidates */}
        <Card>
          <CardHeader className="border-b bg-slate-50/50 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Users className="h-5 w-5 text-primary" />
                <h3 className="font-semibold text-slate-900">Recent Candidates</h3>
              </div>
              <Link to="/candidates">
                <Button variant="ghost" size="sm" className="gap-1 text-xs">
                  View All <ArrowRight className="h-3.5 w-3.5" />
                </Button>
              </Link>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            {activityLoading ? (
              <div className="p-4 space-y-3">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-16 w-full" />
                ))}
              </div>
            ) : activity?.recent_candidates.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <div className="p-3 rounded-full bg-slate-100 mb-3">
                  <Users className="h-8 w-8 text-slate-400" />
                </div>
                <p className="text-slate-600 font-medium">No candidates yet</p>
                <p className="text-sm text-slate-500 mt-1">Candidates will appear here</p>
              </div>
            ) : (
              <div className="divide-y">
                {activity?.recent_candidates.slice(0, 5).map((candidate) => (
                  <Link
                    key={candidate.id}
                    to={`/candidates/${candidate.id}`}
                    className="flex items-center justify-between px-4 py-3 hover:bg-slate-50 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <div className="h-9 w-9 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-semibold text-sm">
                        {candidate.name.charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <p className="font-medium text-slate-900 text-sm">{candidate.name}</p>
                        <p className="text-xs text-slate-500">{candidate.email || 'No email'}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge className={`text-xs ${ONBOARDING_STATUS_COLORS[candidate.status] || 'bg-gray-100 text-gray-700'}`}>
                        {candidate.status.replace(/_/g, ' ')}
                      </Badge>
                      <span className="text-xs text-slate-400">{formatDate(candidate.created_at)}</span>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* My Recent Assignments */}
        <Card>
          <CardHeader className="border-b bg-slate-50/50 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CheckCircle className="h-5 w-5 text-primary" />
                <h3 className="font-semibold text-slate-900">Your Recent Assignments</h3>
              </div>
              <Link to="/your-candidates">
                <Button variant="ghost" size="sm" className="gap-1 text-xs">
                  View All <ArrowRight className="h-3.5 w-3.5" />
                </Button>
              </Link>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            {activityLoading ? (
              <div className="p-4 space-y-3">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-16 w-full" />
                ))}
              </div>
            ) : activity?.my_recent_assignments.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <div className="p-3 rounded-full bg-slate-100 mb-3">
                  <AlertCircle className="h-8 w-8 text-slate-400" />
                </div>
                <p className="text-slate-600 font-medium">No assignments yet</p>
                <p className="text-sm text-slate-500 mt-1">Candidates assigned to you will appear here</p>
              </div>
            ) : (
              <div className="divide-y">
                {activity?.my_recent_assignments.map((assignment) => (
                  <Link
                    key={assignment.id}
                    to={`/candidates/${assignment.candidate_id}`}
                    className="flex items-center justify-between px-4 py-3 hover:bg-slate-50 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <div className="h-9 w-9 rounded-full bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-white font-semibold text-sm">
                        {assignment.candidate_name.charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <p className="font-medium text-slate-900 text-sm">{assignment.candidate_name}</p>
                        <p className="text-xs text-slate-500">Assigned by {assignment.assigned_by}</p>
                      </div>
                    </div>
                    <span className="text-xs text-slate-400">{formatDate(assignment.assigned_at)}</span>
                  </Link>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader className="border-b bg-slate-50/50 py-4">
          <h3 className="font-semibold text-slate-900">Quick Actions</h3>
        </CardHeader>
        <CardContent className="p-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Link to="/candidates">
              <Button variant="outline" className="w-full justify-start gap-2 h-auto py-3">
                <Users className="h-4 w-4" />
                <span>All Candidates</span>
              </Button>
            </Link>
            <Link to="/candidates?tab=email-invitations">
              <Button variant="outline" className="w-full justify-start gap-2 h-auto py-3">
                <Mail className="h-4 w-4" />
                <span>Send Invitation</span>
              </Button>
            </Link>
            <Link to="/candidates?tab=review-submissions">
              <Button variant="outline" className="w-full justify-start gap-2 h-auto py-3">
                <ClipboardList className="h-4 w-4" />
                <span>Review Submissions</span>
              </Button>
            </Link>
            <Link to="/your-candidates">
              <Button variant="outline" className="w-full justify-start gap-2 h-auto py-3">
                <UserCheck className="h-4 w-4" />
                <span>Your Candidates</span>
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
