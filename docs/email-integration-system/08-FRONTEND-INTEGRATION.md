# Frontend Integration

## Overview

This document describes the frontend implementation for the Email Integration feature in the Portal UI.

## Page Structure

```
Settings Page (/settings)
├── Profile Tab
├── Security Tab
└── Integrations Tab (NEW)
    ├── Gmail Integration Card
    │   ├── Connect Button (if not connected)
    │   └── Status Card (if connected)
    │       ├── Email address
    │       ├── Last sync time
    │       ├── Stats (emails processed, jobs created)
    │       ├── Sync Now button
    │       └── Disconnect button
    └── Outlook Integration Card
        └── (same structure)

Email Jobs Page (/email-jobs) (NEW)
├── Header with stats
├── Filter bar
└── Jobs table with source attribution
```

## Components

### 1. Settings Integrations Tab

```tsx
// src/pages/SettingsPage/IntegrationsTab.tsx
import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Loader2, Mail, Check, X, RefreshCw, Unlink } from 'lucide-react';
import { integrationApi } from '@/api/integrationApi';
import { toast } from 'sonner';

interface EmailIntegration {
  id: number;
  provider: 'gmail' | 'outlook';
  email_address: string;
  is_active: boolean;
  last_synced_at: string | null;
  last_sync_status: string;
  last_sync_error: string | null;
  emails_processed_count: number;
  jobs_created_count: number;
  created_at: string;
}

export function IntegrationsTab() {
  const queryClient = useQueryClient();
  const [connectingProvider, setConnectingProvider] = useState<string | null>(null);

  // Check URL params for OAuth callback status
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const status = params.get('status');
    const provider = params.get('provider');
    const message = params.get('message');

    if (status === 'success' && provider) {
      toast.success(`${provider.charAt(0).toUpperCase() + provider.slice(1)} connected successfully!`);
      queryClient.invalidateQueries({ queryKey: ['email-integrations'] });
      // Clean URL
      window.history.replaceState({}, '', '/settings/integrations');
    } else if (status === 'error') {
      toast.error(`Connection failed: ${message || 'Unknown error'}`);
      window.history.replaceState({}, '', '/settings/integrations');
    }
  }, []);

  // Fetch integrations
  const { data: integrations, isLoading } = useQuery({
    queryKey: ['email-integrations'],
    queryFn: () => integrationApi.listIntegrations(),
  });

  // Initiate OAuth mutation
  const initiateMutation = useMutation({
    mutationFn: (provider: 'gmail' | 'outlook') => integrationApi.initiateOAuth(provider),
    onSuccess: (data) => {
      // Redirect to OAuth provider
      window.location.href = data.authorization_url;
    },
    onError: (error) => {
      setConnectingProvider(null);
      toast.error('Failed to initiate connection');
    },
  });

  // Disconnect mutation
  const disconnectMutation = useMutation({
    mutationFn: (integrationId: number) => integrationApi.disconnect(integrationId),
    onSuccess: () => {
      toast.success('Integration disconnected');
      queryClient.invalidateQueries({ queryKey: ['email-integrations'] });
    },
    onError: () => {
      toast.error('Failed to disconnect');
    },
  });

  // Manual sync mutation
  const syncMutation = useMutation({
    mutationFn: (integrationId: number) => integrationApi.triggerSync(integrationId),
    onSuccess: () => {
      toast.success('Sync started! Check back in a few minutes.');
      queryClient.invalidateQueries({ queryKey: ['email-integrations'] });
    },
    onError: () => {
      toast.error('Failed to trigger sync');
    },
  });

  const handleConnect = (provider: 'gmail' | 'outlook') => {
    setConnectingProvider(provider);
    initiateMutation.mutate(provider);
  };

  const getIntegration = (provider: 'gmail' | 'outlook') => {
    return integrations?.integrations.find(i => i.provider === provider);
  };

  const gmailIntegration = getIntegration('gmail');
  const outlookIntegration = getIntegration('outlook');

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium">Email Integrations</h3>
        <p className="text-sm text-muted-foreground">
          Connect your email accounts to automatically discover job requirements from your inbox.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Gmail Card */}
        <IntegrationCard
          provider="gmail"
          providerName="Gmail"
          providerIcon="/icons/gmail.svg"
          integration={gmailIntegration}
          isConnecting={connectingProvider === 'gmail'}
          onConnect={() => handleConnect('gmail')}
          onDisconnect={(id) => disconnectMutation.mutate(id)}
          onSync={(id) => syncMutation.mutate(id)}
          isSyncing={syncMutation.isPending}
        />

        {/* Outlook Card */}
        <IntegrationCard
          provider="outlook"
          providerName="Outlook"
          providerIcon="/icons/outlook.svg"
          integration={outlookIntegration}
          isConnecting={connectingProvider === 'outlook'}
          onConnect={() => handleConnect('outlook')}
          onDisconnect={(id) => disconnectMutation.mutate(id)}
          onSync={(id) => syncMutation.mutate(id)}
          isSyncing={syncMutation.isPending}
        />
      </div>

      {/* How it works */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">How Email Integration Works</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground space-y-2">
          <p>1. Connect your Gmail or Outlook account using secure OAuth (we only request read access)</p>
          <p>2. We automatically scan your inbox every 15 minutes for job requirement emails</p>
          <p>3. Emails are matched based on your candidates' preferred job roles</p>
          <p>4. AI extracts job details and creates structured job postings</p>
          <p>5. Jobs appear in "Email Jobs" with your name as the source</p>
        </CardContent>
      </Card>
    </div>
  );
}

interface IntegrationCardProps {
  provider: 'gmail' | 'outlook';
  providerName: string;
  providerIcon: string;
  integration: EmailIntegration | undefined;
  isConnecting: boolean;
  onConnect: () => void;
  onDisconnect: (id: number) => void;
  onSync: (id: number) => void;
  isSyncing: boolean;
}

function IntegrationCard({
  provider,
  providerName,
  providerIcon,
  integration,
  isConnecting,
  onConnect,
  onDisconnect,
  onSync,
  isSyncing,
}: IntegrationCardProps) {
  const isConnected = !!integration;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center gap-4">
        <div className="h-12 w-12 rounded-lg bg-muted flex items-center justify-center">
          <img src={providerIcon} alt={providerName} className="h-8 w-8" />
        </div>
        <div className="flex-1">
          <CardTitle className="text-lg">{providerName}</CardTitle>
          <CardDescription>
            {isConnected
              ? integration.email_address
              : `Connect your ${providerName} account`}
          </CardDescription>
        </div>
        {isConnected && (
          <Badge variant={integration.is_active ? 'default' : 'secondary'}>
            {integration.is_active ? 'Active' : 'Inactive'}
          </Badge>
        )}
      </CardHeader>
      <CardContent>
        {!isConnected ? (
          <Button
            onClick={onConnect}
            disabled={isConnecting}
            className="w-full"
          >
            {isConnecting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Connecting...
              </>
            ) : (
              <>
                <Mail className="mr-2 h-4 w-4" />
                Connect {providerName}
              </>
            )}
          </Button>
        ) : (
          <div className="space-y-4">
            {/* Stats */}
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground">Emails Processed</p>
                <p className="text-lg font-semibold">{integration.emails_processed_count}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Jobs Created</p>
                <p className="text-lg font-semibold">{integration.jobs_created_count}</p>
              </div>
            </div>

            {/* Last Sync */}
            <div className="text-sm">
              <p className="text-muted-foreground">Last Sync</p>
              <div className="flex items-center gap-2">
                {integration.last_sync_status === 'success' ? (
                  <Check className="h-4 w-4 text-green-500" />
                ) : integration.last_sync_status === 'failed' ? (
                  <X className="h-4 w-4 text-red-500" />
                ) : null}
                <span>
                  {integration.last_synced_at
                    ? new Date(integration.last_synced_at).toLocaleString()
                    : 'Never'}
                </span>
              </div>
              {integration.last_sync_error && (
                <p className="text-red-500 text-xs mt-1">{integration.last_sync_error}</p>
              )}
            </div>

            {/* Actions */}
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => onSync(integration.id)}
                disabled={isSyncing || !integration.is_active}
              >
                {isSyncing ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="mr-2 h-4 w-4" />
                )}
                Sync Now
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => onDisconnect(integration.id)}
              >
                <Unlink className="mr-2 h-4 w-4" />
                Disconnect
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

### 2. Email Jobs Page

```tsx
// src/pages/EmailJobsPage.tsx
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { 
  Card, CardContent, CardHeader, CardTitle 
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { 
  Mail, Search, User, Building2, MapPin, DollarSign,
  ExternalLink, Loader2 
} from 'lucide-react';
import { emailJobsApi } from '@/api/emailJobsApi';
import { formatDistanceToNow } from 'date-fns';

export function EmailJobsPage() {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);

  const { data: stats } = useQuery({
    queryKey: ['email-jobs-stats'],
    queryFn: () => emailJobsApi.getStats(),
  });

  const { data: jobsData, isLoading } = useQuery({
    queryKey: ['email-jobs', { search, page }],
    queryFn: () => emailJobsApi.listJobs({ search, page, per_page: 20 }),
  });

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Mail className="h-6 w-6" />
          Email Jobs
        </h1>
        <p className="text-muted-foreground">
          Jobs discovered from team email integrations
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Jobs
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{stats?.total_jobs || 0}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Added Today
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{stats?.jobs_today || 0}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              This Week
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{stats?.jobs_this_week || 0}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Top Contributor
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-lg font-semibold">
              {stats?.jobs_by_user?.[0]?.user_name || 'N/A'}
            </p>
            <p className="text-sm text-muted-foreground">
              {stats?.jobs_by_user?.[0]?.job_count || 0} jobs
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Search */}
      <div className="flex gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search jobs..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
      </div>

      {/* Jobs Table */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Job</TableHead>
                  <TableHead>Company</TableHead>
                  <TableHead>Location</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Sourced By</TableHead>
                  <TableHead>Email Date</TableHead>
                  <TableHead></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {jobsData?.jobs.map((job) => (
                  <TableRow key={job.id}>
                    <TableCell>
                      <div>
                        <p className="font-medium">{job.title}</p>
                        {job.skills?.slice(0, 3).map((skill) => (
                          <Badge key={skill} variant="secondary" className="mr-1 mt-1">
                            {skill}
                          </Badge>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Building2 className="h-4 w-4 text-muted-foreground" />
                        {job.company || 'Unknown'}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <MapPin className="h-4 w-4 text-muted-foreground" />
                        {job.location || 'Remote'}
                        {job.is_remote && (
                          <Badge variant="outline">Remote</Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={job.job_type === 'Contract' ? 'secondary' : 'default'}>
                        {job.job_type || 'Unknown'}
                      </Badge>
                      {job.salary_range && (
                        <p className="text-xs text-muted-foreground mt-1">
                          {job.salary_range}
                        </p>
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <User className="h-4 w-4 text-muted-foreground" />
                        <div>
                          <p className="text-sm">
                            {job.sourced_by?.first_name} {job.sourced_by?.last_name}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {job.sourced_by?.email}
                          </p>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <p className="text-sm">
                        {job.source_email_date
                          ? formatDistanceToNow(new Date(job.source_email_date), { addSuffix: true })
                          : 'Unknown'}
                      </p>
                      <p className="text-xs text-muted-foreground truncate max-w-[200px]">
                        {job.source_email_subject}
                      </p>
                    </TableCell>
                    <TableCell>
                      <Button variant="ghost" size="sm">
                        <ExternalLink className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Pagination */}
      {jobsData && jobsData.pagination.pages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={page === 1}
            onClick={() => setPage(p => p - 1)}
          >
            Previous
          </Button>
          <span className="text-sm text-muted-foreground">
            Page {page} of {jobsData.pagination.pages}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={page === jobsData.pagination.pages}
            onClick={() => setPage(p => p + 1)}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
}
```

### 3. API Client

```tsx
// src/api/integrationApi.ts
import { apiClient } from './client';

export const integrationApi = {
  listIntegrations: async () => {
    const response = await apiClient.get('/api/integrations/email');
    return response.data;
  },

  initiateOAuth: async (provider: 'gmail' | 'outlook') => {
    const response = await apiClient.post('/api/integrations/email/initiate', { provider });
    return response.data;
  },

  disconnect: async (integrationId: number) => {
    const response = await apiClient.delete(`/api/integrations/email/${integrationId}`);
    return response.data;
  },

  triggerSync: async (integrationId: number) => {
    const response = await apiClient.post(`/api/integrations/email/${integrationId}/sync`);
    return response.data;
  },

  updateSettings: async (integrationId: number, settings: object) => {
    const response = await apiClient.patch(`/api/integrations/email/${integrationId}`, settings);
    return response.data;
  },
};

// src/api/emailJobsApi.ts
import { apiClient } from './client';

interface ListJobsParams {
  search?: string;
  page?: number;
  per_page?: number;
  sourced_by_user_id?: number;
}

export const emailJobsApi = {
  listJobs: async (params: ListJobsParams) => {
    const response = await apiClient.get('/api/email-jobs', { params });
    return response.data;
  },

  getJob: async (jobId: number) => {
    const response = await apiClient.get(`/api/email-jobs/${jobId}`);
    return response.data;
  },

  getStats: async () => {
    const response = await apiClient.get('/api/email-jobs/stats');
    return response.data;
  },

  deleteJob: async (jobId: number) => {
    const response = await apiClient.delete(`/api/email-jobs/${jobId}`);
    return response.data;
  },
};
```

### 4. Router Updates

```tsx
// src/router/index.tsx
// Add new routes

import { EmailJobsPage } from '@/pages/EmailJobsPage';
import { SettingsPage } from '@/pages/SettingsPage';

// In routes array:
{
  path: '/settings',
  element: <SettingsPage />,
  children: [
    { path: 'profile', element: <ProfileTab /> },
    { path: 'security', element: <SecurityTab /> },
    { path: 'integrations', element: <IntegrationsTab /> },  // NEW
  ]
},
{
  path: '/email-jobs',  // NEW
  element: <EmailJobsPage />,
},
```

### 5. Navigation Updates

```tsx
// Add to sidebar navigation
{
  name: 'Email Jobs',
  href: '/email-jobs',
  icon: Mail,
  badge: stats?.jobs_today > 0 ? stats.jobs_today : undefined,
}
```

## Icons

Add provider icons to `public/icons/`:
- `gmail.svg` - Gmail logo
- `outlook.svg` - Outlook logo

## Environment Variables

```env
# Frontend .env
VITE_API_URL=http://localhost:5001
```

## Testing

1. **OAuth Flow Test**:
   - Click "Connect Gmail" → redirects to Google
   - After auth, redirects back with `?status=success`
   - Integration appears in list

2. **Sync Test**:
   - Click "Sync Now" → toast "Sync started"
   - After ~30 seconds, stats update

3. **Email Jobs Test**:
   - Navigate to `/email-jobs`
   - Jobs appear with source attribution
   - Search and pagination work
