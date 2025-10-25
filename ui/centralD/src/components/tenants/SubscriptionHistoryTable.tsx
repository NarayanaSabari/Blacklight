/**
 * Subscription History Table Component
 * Displays timeline of subscription plan changes for a tenant
 */

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ArrowRight, Calendar } from 'lucide-react';
import type { TenantSubscriptionHistory } from '@/types';

interface SubscriptionHistoryTableProps {
  history: TenantSubscriptionHistory[];
  isLoading?: boolean;
}

export function SubscriptionHistoryTable({ history, isLoading }: SubscriptionHistoryTableProps) {
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const getBillingCycleBadge = (cycle: string | null) => {
    if (!cycle) return null;
    return (
      <Badge variant="outline" className="text-xs">
        {cycle === 'YEARLY' ? 'Yearly' : 'Monthly'}
      </Badge>
    );
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Calendar className="h-5 w-5 text-muted-foreground" />
          <div>
            <CardTitle>Subscription History</CardTitle>
            <CardDescription>Timeline of plan changes and modifications</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="text-center text-muted-foreground py-8">
            Loading subscription history...
          </div>
        ) : history.length === 0 ? (
          <div className="text-center text-muted-foreground py-8">
            No subscription history found
          </div>
        ) : (
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Plan Change</TableHead>
                  <TableHead>Billing Cycle</TableHead>
                  <TableHead>Changed By</TableHead>
                  <TableHead>Duration</TableHead>
                  <TableHead>Notes</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {history.map((entry, index) => {
                  const isCurrentPlan = !entry.ended_at;
                  const duration = entry.ended_at
                    ? Math.ceil(
                        (new Date(entry.ended_at).getTime() -
                          new Date(entry.started_at).getTime()) /
                          (1000 * 60 * 60 * 24)
                      )
                    : null;

                  return (
                    <TableRow key={entry.id}>
                      <TableCell className="font-medium">
                        <div className="flex flex-col gap-1">
                          <span>{formatDate(entry.started_at)}</span>
                          {isCurrentPlan && (
                            <Badge variant="default" className="w-fit text-xs">
                              Current
                            </Badge>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          {index < history.length - 1 && (
                            <>
                              <span className="text-sm text-muted-foreground">
                                {history[index + 1].subscription_plan?.display_name || 'Unknown'}
                              </span>
                              <ArrowRight className="h-4 w-4 text-muted-foreground" />
                            </>
                          )}
                          <span className="font-medium">
                            {entry.subscription_plan?.display_name || 'Unknown Plan'}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell>{getBillingCycleBadge(entry.billing_cycle)}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {entry.changed_by_admin
                          ? `${entry.changed_by_admin.first_name} ${entry.changed_by_admin.last_name}`
                          : 'System'}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {isCurrentPlan ? (
                          <span className="text-green-600 font-medium">Active</span>
                        ) : duration !== null ? (
                          `${duration} day${duration !== 1 ? 's' : ''}`
                        ) : (
                          '-'
                        )}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground max-w-xs truncate">
                        {entry.notes || '-'}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
