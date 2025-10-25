/**
 * Tenants List Page
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Search, Filter } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useTenants } from '@/hooks/api';
import { TenantTable } from '@/components/tenants/TenantTable';
import type { TenantStatus, TenantFilterParams } from '@/types';

export function TenantsPage() {
  const navigate = useNavigate();
  const [filters, setFilters] = useState<TenantFilterParams>({
    page: 1,
    per_page: 10,
  });

  const { data, isLoading, error } = useTenants(filters);

  const handleSearchChange = (search: string) => {
    setFilters((prev) => ({ ...prev, search: search || undefined, page: 1 }));
  };

  const handleStatusChange = (status: string) => {
    setFilters((prev) => ({
      ...prev,
      status: status === 'ALL' ? undefined : (status as TenantStatus),
      page: 1,
    }));
  };

  const handlePageChange = (page: number) => {
    setFilters((prev) => ({ ...prev, page }));
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Tenants</h1>
          <p className="text-muted-foreground">
            Manage all tenant organizations and their subscriptions
          </p>
        </div>
        <Button onClick={() => navigate('/tenants/new')}>
          <Plus className="mr-2 h-4 w-4" />
          Create Tenant
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-medium">Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-4 sm:flex-row">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search by company name or slug..."
                  value={filters.search || ''}
                  onChange={(e) => handleSearchChange(e.target.value)}
                  className="pl-9"
                />
              </div>
            </div>
            <div className="w-full sm:w-48">
              <Select
                value={filters.status || 'ALL'}
                onValueChange={handleStatusChange}
              >
                <SelectTrigger>
                  <Filter className="mr-2 h-4 w-4" />
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">All Status</SelectItem>
                  <SelectItem value="ACTIVE">Active</SelectItem>
                  <SelectItem value="SUSPENDED">Suspended</SelectItem>
                  <SelectItem value="INACTIVE">Inactive</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tenants Table */}
      <TenantTable
        data={data}
        isLoading={isLoading}
        error={error}
        currentPage={filters.page || 1}
        onPageChange={handlePageChange}
      />
    </div>
  );
}
