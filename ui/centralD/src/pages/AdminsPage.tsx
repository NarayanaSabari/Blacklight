/**
 * PM Admin Users Management Page
 */

import { useState } from 'react';
import { Plus, Search, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { usePMAdmins } from '@/hooks/api';
import { AdminTable } from '@/components/admins/AdminTable';

export function AdminsPage() {
  const [search, setSearch] = useState('');
  const { data: admins, isLoading, error } = usePMAdmins();

  const filteredAdmins = admins?.filter((admin) =>
    admin.email.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Platform Admins</h1>
          <p className="text-muted-foreground">
            Manage platform administrator accounts
          </p>
        </div>
        <Button>
          <Plus className="mr-2 h-4 w-4" />
          Create Admin
        </Button>
      </div>

      {/* Search */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-medium">Search</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search by email..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9"
            />
          </div>
        </CardContent>
      </Card>

      {/* Loading State */}
      {isLoading && (
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-48" />
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Error State */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Failed to load administrators. Please try again later.
          </AlertDescription>
        </Alert>
      )}

      {/* Admins Table */}
      {!isLoading && !error && filteredAdmins && (
        <AdminTable admins={filteredAdmins} />
      )}
    </div>
  );
}
