/**
 * Subscription Plans Page (Read-only)
 */

import { useState } from 'react';
import { CheckCircle2, CreditCard, AlertCircle, Check, X } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { usePlans } from '@/hooks/api';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';
import type { BillingCycle } from '@/types/tenant';

export function PlansPage() {
  const [billingCycle, setBillingCycle] = useState<BillingCycle>('MONTHLY');
  const { data: plans, isLoading, error } = usePlans();

  const getPlanPrice = (priceMonthly: number | null, priceYearly: number | null | undefined) => {
    if (billingCycle === 'MONTHLY') {
      return priceMonthly || 0;
    }
    return priceYearly || 0;
  };

  const getSavingsPercent = (priceMonthly: number | null, priceYearly: number | null | undefined) => {
    if (!priceMonthly || !priceYearly) return 0;
    const yearlyMonthly = priceYearly / 12;
    return Math.round(((priceMonthly - yearlyMonthly) / priceMonthly) * 100);
  };

  const additionalFeatures = [
    { feature: 'Custom Domain', plans: ['ENTERPRISE'] },
    { feature: 'API Access', plans: ['PROFESSIONAL', 'ENTERPRISE'] },
    { feature: 'Advanced Analytics', plans: ['PROFESSIONAL', 'ENTERPRISE'] },
    { feature: 'Priority Support', plans: ['PROFESSIONAL', 'ENTERPRISE'] },
    { feature: 'Dedicated Account Manager', plans: ['ENTERPRISE'] },
    { feature: 'SLA Guarantee', plans: ['ENTERPRISE'] },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Subscription Plans</h1>
        <p className="text-muted-foreground">
          View all available subscription plans and their features
        </p>
      </div>

      {/* Billing Cycle Toggle */}
      {!isLoading && !error && (
        <div className="flex items-center justify-center gap-4 py-4">
          <Label 
            htmlFor="billing-cycle" 
            className={cn(
              "text-sm font-medium cursor-pointer",
              billingCycle === 'MONTHLY' ? "text-foreground" : "text-muted-foreground"
            )}
          >
            Monthly
          </Label>
          <Switch
            id="billing-cycle"
            checked={billingCycle === 'YEARLY'}
            onCheckedChange={(checked) => setBillingCycle(checked ? 'YEARLY' : 'MONTHLY')}
          />
          <Label 
            htmlFor="billing-cycle" 
            className={cn(
              "text-sm font-medium cursor-pointer",
              billingCycle === 'YEARLY' ? "text-foreground" : "text-muted-foreground"
            )}
          >
            Yearly
            {plans && plans.length > 0 && getSavingsPercent(plans[0].price_monthly, plans[0].price_yearly) > 0 && (
              <Badge variant="secondary" className="ml-2">
                Save {getSavingsPercent(plans[0].price_monthly, plans[0].price_yearly)}%
              </Badge>
            )}
          </Label>
        </div>
      )}

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
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {plans.map((plan) => {
            const isPopular = plan.name === 'PROFESSIONAL';
            const price = getPlanPrice(plan.price_monthly, plan.price_yearly);
            
            return (
              <Card 
                key={plan.id} 
                className={cn(
                  'relative flex flex-col',
                  !plan.is_active && 'opacity-60',
                  isPopular && 'border-primary shadow-lg'
                )}
              >
                {isPopular && plan.is_active && (
                  <Badge className="absolute -top-3 left-1/2 -translate-x-1/2">
                    Most Popular
                  </Badge>
                )}
                
                <CardHeader>
                  <div className="flex items-center gap-2">
                    <CreditCard className="h-5 w-5 text-primary" />
                    <CardTitle className="capitalize">{plan.name.toLowerCase()}</CardTitle>
                  </div>
                  <CardDescription>{plan.description || 'No description'}</CardDescription>
                  {!plan.is_active && (
                    <Badge variant="secondary" className="w-fit">Inactive</Badge>
                  )}
                </CardHeader>
                
                <CardContent className="flex-1 flex flex-col">
                  {/* Pricing */}
                  <div className="mb-6">
                    <div className="text-4xl font-bold">
                      ${price}
                      <span className="text-sm font-normal text-muted-foreground">
                        /{billingCycle === 'MONTHLY' ? 'mo' : 'yr'}
                      </span>
                    </div>
                    {billingCycle === 'YEARLY' && price > 0 && (
                      <div className="text-sm text-muted-foreground mt-1">
                        ${(price / 12).toFixed(2)}/month billed annually
                      </div>
                    )}
                  </div>

                  {/* Plan Limits */}
                  <div className="space-y-3 mb-6">
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
                      <li className="flex items-center gap-2">
                        <CheckCircle2 className="h-4 w-4 text-primary" />
                        <span>
                          {plan.max_storage_gb === -1 ? 'Unlimited' : `${plan.max_storage_gb}GB`} storage
                        </span>
                      </li>
                    </ul>
                  </div>

                  {/* Additional Features */}
                  <div className="space-y-2 pt-4 border-t mt-auto">
                    <p className="text-sm font-medium text-muted-foreground mb-3">Features:</p>
                    {additionalFeatures.map(({ feature, plans: includedPlans }) => {
                      const isIncluded = includedPlans.includes(plan.name);
                      
                      return (
                        <div
                          key={feature}
                          className={cn(
                            'flex items-start gap-2 text-sm',
                            !isIncluded && 'text-muted-foreground'
                          )}
                        >
                          {isIncluded ? (
                            <Check className="h-4 w-4 text-green-600 mt-0.5 flex-shrink-0" />
                          ) : (
                            <X className="h-4 w-4 text-muted-foreground/40 mt-0.5 flex-shrink-0" />
                          )}
                          <span className={!isIncluded ? 'line-through' : ''}>
                            {feature}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>
            );
          })}
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
