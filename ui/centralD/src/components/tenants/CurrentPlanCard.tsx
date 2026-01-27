/**
 * Current Plan Card
 * Displays current subscription plan with change plan option
 */

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { CreditCard, Calendar, ArrowRight, Plus, Edit } from 'lucide-react';
import type { Tenant } from '@/types';

interface CurrentPlanCardProps {
  tenant: Tenant;
  onChangePlan: () => void;
  onCreateCustomPlan?: () => void;
  onEditCustomPlan?: () => void;
}

export function CurrentPlanCard({ 
  tenant, 
  onChangePlan, 
  onCreateCustomPlan, 
  onEditCustomPlan 
}: CurrentPlanCardProps) {
  const plan = tenant.subscription_plan;
  const isCustomPlan = plan?.is_custom || false;

  if (!plan) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CreditCard className="h-5 w-5" />
            Subscription Plan
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">No subscription plan assigned</p>
        </CardContent>
      </Card>
    );
  }

  const price = tenant.billing_cycle === 'YEARLY' ? plan.price_yearly : plan.price_monthly;
  const billingPeriod = tenant.billing_cycle === 'YEARLY' ? 'year' : 'month';
  
  // Convert price to number if it's a string
  const priceValue = typeof price === 'string' ? parseFloat(price) : price;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <CreditCard className="h-5 w-5" />
            Current Subscription
          </CardTitle>
          <div className="flex items-center gap-2">
            {isCustomPlan && onEditCustomPlan ? (
              <Button variant="outline" size="sm" onClick={onEditCustomPlan}>
                <Edit className="mr-2 h-4 w-4" />
                Edit Custom Plan
              </Button>
            ) : onCreateCustomPlan ? (
              <Button variant="outline" size="sm" onClick={onCreateCustomPlan}>
                <Plus className="mr-2 h-4 w-4" />
                Create Custom Plan
              </Button>
            ) : null}
            <Button variant="outline" size="sm" onClick={onChangePlan}>
              Change Plan
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <div className="text-2xl font-bold">{plan.name}</div>
              {isCustomPlan && (
                <Badge variant="secondary">Custom</Badge>
              )}
            </div>
            <div className="text-lg text-muted-foreground">
              ${priceValue?.toFixed(2)} / {billingPeriod}
            </div>
          </div>
          {tenant.billing_cycle && (
            <Badge variant="secondary">{tenant.billing_cycle}</Badge>
          )}
        </div>

        <div className="grid grid-cols-2 gap-4 pt-4 border-t">
          <div className="space-y-1">
            <div className="text-sm text-muted-foreground">Max Users</div>
            <div className="font-medium">{plan.max_users}</div>
          </div>
          <div className="space-y-1">
            <div className="text-sm text-muted-foreground">Max Candidates</div>
            <div className="font-medium">{plan.max_candidates}</div>
          </div>
          <div className="space-y-1">
            <div className="text-sm text-muted-foreground">Storage</div>
            <div className="font-medium">{plan.max_storage_gb} GB</div>
          </div>
        </div>

        <div className="pt-4 border-t space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              Subscription Start
            </span>
            <span className="font-medium">
              {new Date(tenant.subscription_start_date).toLocaleDateString()}
            </span>
          </div>
          {tenant.next_billing_date && (
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground flex items-center gap-1">
                <ArrowRight className="h-3 w-3" />
                Next Billing
              </span>
              <span className="font-medium">
                {new Date(tenant.next_billing_date).toLocaleDateString()}
              </span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
