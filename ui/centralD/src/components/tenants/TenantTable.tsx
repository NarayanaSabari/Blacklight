/**
 * Tenant Table Component
 */

import { useNavigate } from 'react-router-dom';
import { format } from 'date-fns';
import { AlertCircle, Building2, ChevronLeft, ChevronRight, MoreVertical } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import type { TenantListResponse, TenantStatus } from '@/types';

interface TenantTableProps {
  data: TenantListResponse | undefined;
  isLoading: boolean;
  error: unknown;
  currentPage: number;
  onPageChange: (page: number) => void;
}

export function TenantTable({ data, isLoading, error, currentPage, onPageChange }: TenantTableProps) {
  const navigate = useNavigate();

  const getStatusBadgeVariant = (status: TenantStatus) => {
    switch (status) {
      case 'ACTIVE':
        return 'default';
      case 'SUSPENDED':
        return 'destructive';
      case 'INACTIVE':
        return 'secondary';
      default:
        return 'outline';
    }
  };

  // Loading State
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-32" />
          <Skeleton className="h-4 w-64" />
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="h-16 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  // Error State
  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          Failed to load tenants. Please try again later.
        </AlertDescription>
      </Alert>
    );
  }

  // Empty State
  if (!data || data.items.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12 text-center">
          <div className="rounded-full bg-muted p-4 mb-4">
            <Building2 className="h-8 w-8 text-muted-foreground" />
          </div>
          <h3 className="text-lg font-semibold mb-2">No tenants found</h3>
          <p className="text-sm text-muted-foreground mb-4">
            Try adjusting your filters or create a new tenant
          </p>
          <Button onClick={() => navigate('/tenants/new')}>
            Create Tenant
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>All Tenants</CardTitle>
        <CardDescription>
          {data.total} tenant{data.total !== 1 ? 's' : ''} found
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Company</TableHead>
              <TableHead>Slug</TableHead>
              <TableHead>Plan</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Created</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.items.map((tenant) => (
              <TableRow
                key={tenant.id}
                className="cursor-pointer hover:bg-muted/50"
                onClick={() => navigate(`/tenants/${tenant.slug}`)}
              >
                <TableCell className="font-medium">{tenant.name}</TableCell>
                <TableCell>
                  <code className="text-xs bg-muted px-2 py-1 rounded">{tenant.slug}</code>
                </TableCell>
                <TableCell>
                  {tenant.subscription_plan?.name || 'Unknown'}
                </TableCell>
                <TableCell>
                  <Badge variant={getStatusBadgeVariant(tenant.status)}>
                    {tenant.status}
                  </Badge>
                </TableCell>
                <TableCell className="text-muted-foreground text-sm">
                  {format(new Date(tenant.created_at), 'MMM dd, yyyy')}
                </TableCell>
                <TableCell className="text-right">
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                      <Button variant="ghost" size="icon">
                        <MoreVertical className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuLabel>Actions</DropdownMenuLabel>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/tenants/${tenant.slug}`);
                      }}>
                        View Details
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={(e) => e.stopPropagation()}>
                        Change Plan
                      </DropdownMenuItem>
                      {tenant.status === 'ACTIVE' ? (
                        <DropdownMenuItem onClick={(e) => e.stopPropagation()}>
                          Suspend
                        </DropdownMenuItem>
                      ) : tenant.status === 'SUSPENDED' ? (
                        <DropdownMenuItem onClick={(e) => e.stopPropagation()}>
                          Reactivate
                        </DropdownMenuItem>
                      ) : null}
                      <DropdownMenuSeparator />
                      <DropdownMenuItem
                        onClick={(e) => e.stopPropagation()}
                        className="text-destructive"
                      >
                        Delete
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>

        {/* Pagination */}
        {data.total > data.per_page && (
          <div className="flex items-center justify-between mt-4 pt-4 border-t">
            <div className="text-sm text-muted-foreground">
              Page {currentPage} of {Math.ceil(data.total / data.per_page)}
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => onPageChange(currentPage - 1)}
                disabled={currentPage === 1}
              >
                <ChevronLeft className="h-4 w-4" />
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => onPageChange(currentPage + 1)}
                disabled={currentPage >= Math.ceil(data.total / data.per_page)}
              >
                Next
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
