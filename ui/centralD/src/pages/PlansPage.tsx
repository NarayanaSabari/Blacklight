/**
 * Subscription Plans Page (Read-only)
 */

import { CheckCircle2, CreditCard, AlertCircle } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { usePlans } from '@/hooks/api';
import { Skeleton } from '@/components/ui/skeleton';

export function PlansPage() {
  const { data: plans, isLoading, error } = usePlans();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Subscription Plans</h1>
        <p className="text-muted-foreground">
          View all available subscription plans and their features
        </p>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-6 w-32" />
                <Skeleton className="h-4 w-48" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-12 w-24 mb-4" />
                <div className="space-y-2">
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-3/4" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Error State */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Failed to load subscription plans. Please try again later.
          </AlertDescription>
        </Alert>
      )}

      {/* Plans Grid */}
      {plans && plans.length > 0 && (
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {plans.map((plan) => (
            <Card key={plan.id} className={plan.is_active ? '' : 'opacity-60'}>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <CreditCard className="h-5 w-5 text-primary" />
                  <CardTitle>{plan.name}</CardTitle>
                </div>
                <CardDescription>{plan.description || 'No description'}</CardDescription>
                {!plan.is_active && (
                  <Badge variant="secondary" className="w-fit">Inactive</Badge>
                )}
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <span className="text-4xl font-bold">${plan.price_monthly}</span>
                    <span className="text-muted-foreground">/month</span>
                  </div>
                  
                  {plan.price_yearly && (
                    <div className="space-y-2 text-sm">
                      <div className="flex items-center justify-between">
                        <span className="text-muted-foreground">Yearly:</span>
                        <span className="font-medium">${plan.price_yearly}/year</span>
                      </div>
                    </div>
                  )}

                  <div className="border-t pt-4 space-y-2">{/* continuation */}
                    <p className="text-sm font-medium text-muted-foreground">Limits:</p>
                    <ul className="space-y-2 text-sm">
                      <li className="flex items-center gap-2">
                        <CheckCircle2 className="h-4 w-4 text-primary" />
                        <span>
                          {plan.max_users === -1 ? 'Unlimited' : plan.max_users} users
                        </span>
                      </li>
                      <li className="flex items-center gap-2">
                        <CheckCircle2 className="h-4 w-4 text-primary" />
                        <span>
                          {plan.max_candidates === -1 ? 'Unlimited' : plan.max_candidates} candidates
                        </span>
                      </li>
                      <li className="flex items-center gap-2">
                        <CheckCircle2 className="h-4 w-4 text-primary" />
                        <span>
                          {plan.max_jobs === -1 ? 'Unlimited' : plan.max_jobs} jobs
                        </span>
                      </li>
                    </ul>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Empty State */}
      {plans && plans.length === 0 && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12 text-center">
            <CreditCard className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No subscription plans</h3>
            <p className="text-sm text-muted-foreground">
              There are no subscription plans configured yet.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
