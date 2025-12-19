/**
 * Email Integrations Settings Component
 * Allows users to connect their Gmail or Outlook accounts for job email scanning
 */

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { toast } from 'sonner';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { 
  Mail,
  Loader2,
  RefreshCw,
  Link2,
  Link2Off,
  CheckCircle2,
  AlertCircle,
  Clock,
} from 'lucide-react';
import { emailIntegrationApi, type IntegrationStatus } from '@/lib/emailIntegrationApi';

// Gmail icon component
const GmailIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M24 5.457v13.909c0 .904-.732 1.636-1.636 1.636h-3.819V11.73L12 16.64l-6.545-4.91v9.273H1.636A1.636 1.636 0 0 1 0 19.366V5.457c0-2.023 2.309-3.178 3.927-1.964L5.455 4.64 12 9.548l6.545-4.91 1.528-1.145C21.69 2.28 24 3.434 24 5.457z" fill="#EA4335"/>
  </svg>
);

// Outlook icon component
const OutlookIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M24 7.387v10.478c0 .23-.08.424-.238.576-.158.154-.352.23-.58.23h-8.547v-6.959l1.6 1.229c.101.072.216.109.344.109.128 0 .239-.037.332-.109l6.855-5.455c.109-.089.164-.207.164-.352v-.109c0-.191-.123-.345-.371-.463-.245-.116-.482-.116-.71 0l-8.214 6.572-3.635-2.836v7.373H.818c-.228 0-.418-.076-.572-.23A.772.772 0 0 1 0 17.865V7.387c0-.135.042-.25.123-.348.083-.098.186-.158.311-.182v.018l7.936 5.126L.434 6.854v-.018c-.125.024-.228.084-.311.182A.472.472 0 0 0 0 7.387" fill="#0078D4"/>
    <path d="M7.646 14.578c-.606.406-1.343.609-2.211.609-.879 0-1.618-.203-2.218-.609-.6-.406-.9-1.064-.9-1.973s.3-1.566.9-1.971c.6-.406 1.339-.609 2.218-.609.868 0 1.605.203 2.211.609.606.405.909 1.062.909 1.971s-.303 1.567-.909 1.973zm-.652-3.294c-.377-.296-.857-.444-1.441-.444-.585 0-1.066.148-1.443.444-.377.295-.566.748-.566 1.357 0 .611.189 1.064.566 1.359.377.296.858.443 1.443.443.584 0 1.064-.147 1.441-.443.377-.295.565-.748.565-1.359 0-.609-.188-1.062-.565-1.357z" fill="#0078D4"/>
  </svg>
);

export function EmailIntegrationsSettings() {
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const [disconnectDialogOpen, setDisconnectDialogOpen] = useState(false);
  const [integrationToDisconnect, setIntegrationToDisconnect] = useState<{
    id: number;
    provider: 'gmail' | 'outlook';
    email: string;
  } | null>(null);

  // Handle OAuth callback results
  useEffect(() => {
    const success = searchParams.get('success');
    const error = searchParams.get('error');
    const provider = searchParams.get('provider');
    const email = searchParams.get('email');

    if (success === 'true' && provider) {
      toast.success(`${provider === 'gmail' ? 'Gmail' : 'Outlook'} connected successfully!`, {
        description: email ? `Connected to ${email}` : undefined,
      });
      // Clear params
      searchParams.delete('success');
      searchParams.delete('provider');
      searchParams.delete('email');
      setSearchParams(searchParams);
      // Refetch status
      queryClient.invalidateQueries({ queryKey: ['email-integration-status'] });
    } else if (error && provider) {
      toast.error(`Failed to connect ${provider === 'gmail' ? 'Gmail' : 'Outlook'}`, {
        description: error,
      });
      searchParams.delete('error');
      searchParams.delete('provider');
      setSearchParams(searchParams);
    }
  }, [searchParams, setSearchParams, queryClient]);

  // Query for integration status
  const { data: status, isLoading, error, refetch } = useQuery({
    queryKey: ['email-integration-status'],
    queryFn: emailIntegrationApi.getStatus,
    staleTime: 30000, // 30 seconds
  });

  // Connect Gmail mutation
  const connectGmailMutation = useMutation({
    mutationFn: emailIntegrationApi.connectGmail,
    onSuccess: (data) => {
      // Redirect to Google OAuth
      window.location.href = data.authorization_url;
    },
    onError: (error: Error) => {
      toast.error('Failed to initiate Gmail connection', {
        description: error.message,
      });
    },
  });

  // Connect Outlook mutation
  const connectOutlookMutation = useMutation({
    mutationFn: emailIntegrationApi.connectOutlook,
    onSuccess: (data) => {
      // Redirect to Microsoft OAuth
      window.location.href = data.authorization_url;
    },
    onError: (error: Error) => {
      toast.error('Failed to initiate Outlook connection', {
        description: error.message,
      });
    },
  });

  // Disconnect mutation
  const disconnectMutation = useMutation({
    mutationFn: (integrationId: number) => emailIntegrationApi.disconnect(integrationId),
    onSuccess: () => {
      toast.success('Integration disconnected');
      setDisconnectDialogOpen(false);
      setIntegrationToDisconnect(null);
      queryClient.invalidateQueries({ queryKey: ['email-integration-status'] });
    },
    onError: (error: Error) => {
      toast.error('Failed to disconnect', {
        description: error.message,
      });
    },
  });

  // Toggle active mutation
  const toggleMutation = useMutation({
    mutationFn: ({ integrationId, isActive }: { integrationId: number; isActive: boolean }) =>
      emailIntegrationApi.toggle(integrationId, isActive),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email-integration-status'] });
    },
    onError: (error: Error) => {
      toast.error('Failed to toggle integration', {
        description: error.message,
      });
    },
  });

  // Sync mutation
  const syncMutation = useMutation({
    mutationFn: (integrationId: number) => emailIntegrationApi.triggerSync(integrationId),
    onSuccess: () => {
      toast.success('Sync triggered', {
        description: 'Emails will be processed in the background',
      });
    },
    onError: (error: Error) => {
      toast.error('Failed to trigger sync', {
        description: error.message,
      });
    },
  });

  const handleDisconnect = (provider: 'gmail' | 'outlook', integrationId: number, email: string) => {
    setIntegrationToDisconnect({ id: integrationId, provider, email });
    setDisconnectDialogOpen(true);
  };

  const confirmDisconnect = () => {
    if (integrationToDisconnect) {
      disconnectMutation.mutate(integrationToDisconnect.id);
    }
  };

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="py-6">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Error</AlertTitle>
            <AlertDescription>
              Failed to load email integration status. Please try again.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Mail className="h-5 w-5" />
                Email Integrations
              </CardTitle>
              <CardDescription className="mt-1">
                Connect your email accounts to automatically discover job postings from your inbox
              </CardDescription>
            </div>
            <Button variant="ghost" size="sm" onClick={() => refetch()}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* How it works info */}
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>How it works</AlertTitle>
            <AlertDescription>
              When you connect your email, we scan your inbox for job requirement emails.
              Jobs matching your candidates' preferred roles are automatically parsed and added to your Email Jobs list.
              Your email credentials are encrypted and never shared.
            </AlertDescription>
          </Alert>

          {/* Gmail Integration */}
          <IntegrationCard
            provider="gmail"
            icon={<GmailIcon className="h-8 w-8" />}
            title="Gmail"
            description="Connect your Google account to scan for job emails"
            status={status?.gmail}
            onConnect={() => connectGmailMutation.mutate()}
            onDisconnect={(id, email) => handleDisconnect('gmail', id, email)}
            onToggle={(id, isActive) => toggleMutation.mutate({ integrationId: id, isActive })}
            onSync={(id) => syncMutation.mutate(id)}
            isConnecting={connectGmailMutation.isPending}
            isToggling={toggleMutation.isPending}
            isSyncing={syncMutation.isPending}
          />

          {/* Outlook Integration */}
          <IntegrationCard
            provider="outlook"
            icon={<OutlookIcon className="h-8 w-8" />}
            title="Outlook / Microsoft 365"
            description="Connect your Microsoft account to scan for job emails"
            status={status?.outlook}
            onConnect={() => connectOutlookMutation.mutate()}
            onDisconnect={(id, email) => handleDisconnect('outlook', id, email)}
            onToggle={(id, isActive) => toggleMutation.mutate({ integrationId: id, isActive })}
            onSync={(id) => syncMutation.mutate(id)}
            isConnecting={connectOutlookMutation.isPending}
            isToggling={toggleMutation.isPending}
            isSyncing={syncMutation.isPending}
          />
        </CardContent>
      </Card>

      {/* Disconnect Confirmation Dialog */}
      <Dialog open={disconnectDialogOpen} onOpenChange={setDisconnectDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Disconnect {integrationToDisconnect?.provider === 'gmail' ? 'Gmail' : 'Outlook'}?</DialogTitle>
            <DialogDescription>
              This will disconnect {integrationToDisconnect?.email} and stop scanning for job emails.
              Previously discovered jobs will remain in your system.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDisconnectDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={confirmDisconnect}
              disabled={disconnectMutation.isPending}
            >
              {disconnectMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Disconnect
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

// Individual integration card component
interface IntegrationCardProps {
  provider: 'gmail' | 'outlook';
  icon: React.ReactNode;
  title: string;
  description: string;
  status?: IntegrationStatus['gmail'] | IntegrationStatus['outlook'];
  onConnect: () => void;
  onDisconnect: (integrationId: number, email: string) => void;
  onToggle: (integrationId: number, isActive: boolean) => void;
  onSync: (integrationId: number) => void;
  isConnecting: boolean;
  isToggling: boolean;
  isSyncing: boolean;
}

function IntegrationCard({
  icon,
  title,
  description,
  status,
  onConnect,
  onDisconnect,
  onToggle,
  onSync,
  isConnecting,
  isToggling,
  isSyncing,
}: IntegrationCardProps) {
  const isConnected = status?.connected;
  const isConfigured = status?.is_configured;
  const integrationId = status?.integration_id;
  const email = status?.email || '';

  if (!isConfigured) {
    return (
      <div className="flex items-center gap-4 p-4 border rounded-lg bg-slate-50">
        <div className="flex-shrink-0 opacity-50">{icon}</div>
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-slate-700">{title}</h3>
          <p className="text-sm text-slate-500">
            Not configured. Contact your administrator to enable {title} integration.
          </p>
        </div>
        <Badge variant="secondary">Not Available</Badge>
      </div>
    );
  }

  if (!isConnected) {
    return (
      <div className="flex items-center gap-4 p-4 border rounded-lg hover:bg-slate-50 transition-colors">
        <div className="flex-shrink-0">{icon}</div>
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-slate-900">{title}</h3>
          <p className="text-sm text-slate-600">{description}</p>
        </div>
        <Button onClick={onConnect} disabled={isConnecting}>
          {isConnecting ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Link2 className="mr-2 h-4 w-4" />
          )}
          Connect
        </Button>
      </div>
    );
  }

  // Connected state
  return (
    <div className="border rounded-lg overflow-hidden">
      <div className="flex items-center gap-4 p-4 bg-green-50">
        <div className="flex-shrink-0">{icon}</div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-slate-900">{title}</h3>
            <Badge variant="default" className="bg-green-600">
              <CheckCircle2 className="mr-1 h-3 w-3" />
              Connected
            </Badge>
          </div>
          <p className="text-sm text-slate-600 truncate">{email}</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-slate-600">Active</span>
          <Switch
            checked={status?.is_active}
            onCheckedChange={(checked) => integrationId && onToggle(integrationId, checked)}
            disabled={isToggling}
          />
        </div>
      </div>

      {/* Stats and actions */}
      <div className="p-4 space-y-4">
        {/* Stats */}
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <div className="text-2xl font-bold text-slate-900">
              {status?.emails_processed || 0}
            </div>
            <div className="text-xs text-slate-500">Emails Scanned</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-blue-600">
              {status?.jobs_created || 0}
            </div>
            <div className="text-xs text-slate-500">Jobs Created</div>
          </div>
          <div>
            <div className="text-sm font-medium text-slate-700">
              {status?.last_synced ? (
                <span className="flex items-center justify-center gap-1">
                  <Clock className="h-3 w-3" />
                  {new Date(status.last_synced).toLocaleTimeString()}
                </span>
              ) : (
                'Never'
              )}
            </div>
            <div className="text-xs text-slate-500">Last Synced</div>
          </div>
        </div>

        {/* Error display */}
        {status?.last_error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription className="text-sm">
              {status.last_error}
            </AlertDescription>
          </Alert>
        )}

        {/* Actions */}
        <div className="flex items-center justify-between pt-2 border-t">
          <Button
            variant="outline"
            size="sm"
            onClick={() => integrationId && onSync(integrationId)}
            disabled={isSyncing || !status?.is_active}
          >
            {isSyncing ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="mr-2 h-4 w-4" />
            )}
            Sync Now
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="text-red-600 hover:text-red-700 hover:bg-red-50"
            onClick={() => integrationId && onDisconnect(integrationId, email)}
          >
            <Link2Off className="mr-2 h-4 w-4" />
            Disconnect
          </Button>
        </div>
      </div>
    </div>
  );
}
