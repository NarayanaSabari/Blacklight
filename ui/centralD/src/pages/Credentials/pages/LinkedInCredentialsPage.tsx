/**
 * LinkedIn Credentials Page
 * Manage email/password credentials for LinkedIn scraper
 */

import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { scraperCredentialsApi } from '@/lib/dashboard-api';
import { CredentialTable, AddCredentialDialog, Plus, RefreshCw } from '../components';

export function LinkedInCredentialsPage() {
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const queryClient = useQueryClient();

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['credentials', 'linkedin'],
    queryFn: () => scraperCredentialsApi.getByPlatform('linkedin'),
    staleTime: 30000,
  });

  const handleRefresh = () => {
    refetch();
    queryClient.invalidateQueries({ queryKey: ['credentials-stats'] });
  };

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="py-8 text-center">
          <p className="text-red-600">Failed to load LinkedIn credentials</p>
          <Button variant="ghost" onClick={() => refetch()} className="mt-2">
            <RefreshCw className="h-4 w-4 mr-2" />
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>LinkedIn Credentials</CardTitle>
              <CardDescription>
                Manage email/password login credentials for LinkedIn scraper
              </CardDescription>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => refetch()}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh
              </Button>
              <Button size="sm" onClick={() => setAddDialogOpen(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Add Credential
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {data && (
            <CredentialTable
              platform="linkedin"
              credentials={data.credentials}
              onRefresh={handleRefresh}
            />
          )}
        </CardContent>
      </Card>

      <AddCredentialDialog
        platform="linkedin"
        open={addDialogOpen}
        onOpenChange={setAddDialogOpen}
        onSuccess={handleRefresh}
      />
    </div>
  );
}

export default LinkedInCredentialsPage;
