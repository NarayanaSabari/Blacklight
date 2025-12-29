/**
 * Organization Settings Component
 * Displays organization details and subscription information
 */

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { 
  Building2, 
  Users, 
  Calendar,
  Globe,
  Hash,
  CheckCircle2,
  Clock,
  CreditCard
} from 'lucide-react';
import { usePortalAuth } from '@/contexts/PortalAuthContext';

export function OrganizationSettings() {
  const { user } = usePortalAuth();
  
  const tenant = user?.tenant;
  const tenantName = tenant?.name || 'Your Organization';
  const tenantSlug = tenant?.slug || 'N/A';

  // Format date
  const formatDate = (dateString?: string) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  // Get status badge variant
  const getStatusBadge = (status?: string) => {
    switch (status?.toLowerCase()) {
      case 'active':
        return (
          <Badge className="bg-green-100 text-green-700 hover:bg-green-100">
            <CheckCircle2 className="h-3 w-3 mr-1" />
            Active
          </Badge>
        );
      case 'trial':
        return (
          <Badge className="bg-blue-100 text-blue-700 hover:bg-blue-100">
            <Clock className="h-3 w-3 mr-1" />
            Trial
          </Badge>
        );
      case 'suspended':
        return (
          <Badge className="bg-red-100 text-red-700 hover:bg-red-100">
            Suspended
          </Badge>
        );
      default:
        return (
          <Badge variant="secondary">
            {status || 'Unknown'}
          </Badge>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Organization Header */}
      <Card className="border-0 shadow-sm bg-gradient-to-r from-blue-50 to-indigo-50">
        <CardContent className="pt-6">
          <div className="flex items-start gap-6">
            {/* Company Icon */}
            <div className="flex-shrink-0">
              <div className="w-16 h-16 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white shadow-lg">
                <Building2 className="h-8 w-8" />
              </div>
            </div>
            
            {/* Company Info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-3 mb-2">
                <h2 className="text-2xl font-bold text-slate-900">
                  {tenantName || 'Your Organization'}
                </h2>
                {getStatusBadge(tenant?.status)}
              </div>
              <div className="flex items-center gap-2 text-slate-600">
                <Globe className="h-4 w-4" />
                <span className="font-mono text-sm">{tenantSlug || 'N/A'}</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Organization Details */}
      <Card>
        <CardHeader>
          <CardTitle>Organization Details</CardTitle>
          <CardDescription>Information about your organization</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Details Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Company Name */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-500 flex items-center gap-2">
                <Building2 className="h-4 w-4" />
                Company Name
              </label>
              <p className="text-lg font-medium text-slate-900">
                {tenantName || 'Not set'}
              </p>
            </div>

            {/* Organization ID */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-500 flex items-center gap-2">
                <Hash className="h-4 w-4" />
                Organization ID
              </label>
              <p className="font-mono text-lg text-slate-900">
                {tenantSlug || 'N/A'}
              </p>
            </div>

            {/* Status */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-500 flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4" />
                Status
              </label>
              <div>
                {getStatusBadge(tenant?.status)}
              </div>
            </div>

            {/* Created Date */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-500 flex items-center gap-2">
                <Calendar className="h-4 w-4" />
                Created
              </label>
              <p className="text-lg text-slate-900">
                {formatDate(tenant?.created_at)}
              </p>
            </div>
          </div>

          <Separator />

          {/* Subscription Info */}
          <div>
            <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
              <CreditCard className="h-5 w-5" />
              Subscription
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Plan */}
              <div className="p-4 bg-slate-50 rounded-lg">
                <label className="text-sm font-medium text-slate-500">Current Plan</label>
                <p className="text-xl font-semibold text-slate-900 mt-1">
                  {tenant?.subscription_plan?.display_name || tenant?.subscription_plan?.name || 'N/A'}
                </p>
              </div>

              {/* User Limit */}
              <div className="p-4 bg-slate-50 rounded-lg">
                <label className="text-sm font-medium text-slate-500 flex items-center gap-1">
                  <Users className="h-3.5 w-3.5" />
                  User Limit
                </label>
                <p className="text-xl font-semibold text-slate-900 mt-1">
                  {tenant?.stats?.user_count || 0} / {tenant?.stats?.max_users || tenant?.subscription_plan?.max_users || 'Unlimited'}
                </p>
              </div>

              {/* Candidate Limit */}
              <div className="p-4 bg-slate-50 rounded-lg">
                <label className="text-sm font-medium text-slate-500">Candidate Limit</label>
                <p className="text-xl font-semibold text-slate-900 mt-1">
                  {tenant?.stats?.max_candidates || tenant?.subscription_plan?.max_candidates || 'Unlimited'}
                </p>
              </div>
            </div>
          </div>

          <Separator />

          {/* Contact Support */}
          <div className="bg-blue-50 border border-blue-100 rounded-lg p-4">
            <p className="text-sm text-blue-800">
              Need to update your organization details or subscription? 
              <a href="mailto:support@blacklight.com" className="font-medium underline ml-1">
                Contact Support
              </a>
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
