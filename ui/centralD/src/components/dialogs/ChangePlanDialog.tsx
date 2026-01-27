/**
 * Change Subscription Plan Dialog
 * Allows PM admins to change a tenant's subscription plan
 */

import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { AlertTriangle, ArrowRight, Check } from 'lucide-react';
import type { Tenant, SubscriptionPlan, TenantStats } from '@/types';

const changePlanSchema = z.object({
  new_plan_id: z.number().min(1, 'Please select a plan'),
  billing_cycle: z.enum(['MONTHLY', 'YEARLY']),
});

type ChangePlanFormData = z.infer<typeof changePlanSchema>;

interface ChangePlanDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  tenant: Tenant;
  stats: TenantStats | null;
  plans: SubscriptionPlan[];
  onSubmit: (data: ChangePlanFormData) => Promise<void>;
  isLoading?: boolean;
}

export function ChangePlanDialog({
  open,
  onOpenChange,
  tenant,
  stats,
  plans,
  onSubmit,
  isLoading = false,
}: ChangePlanDialogProps) {
  const [selectedPlanId, setSelectedPlanId] = useState<number | null>(null);
  const [violations, setViolations] = useState<string[]>([]);

  const form = useForm<ChangePlanFormData>({
    resolver: zodResolver(changePlanSchema),
    defaultValues: {
      new_plan_id: tenant.subscription_plan_id,
      billing_cycle: tenant.billing_cycle || 'MONTHLY',
    },
  });

  const watchedPlanId = form.watch('new_plan_id');
  const watchedBillingCycle = form.watch('billing_cycle');

  const currentPlan = plans.find((p) => p.id === tenant.subscription_plan_id);
  const selectedPlan = plans.find((p) => p.id === selectedPlanId);

  // Check for limit violations when plan changes
  useEffect(() => {
    if (!selectedPlanId || !stats || selectedPlanId === tenant.subscription_plan_id) {
      setViolations([]);
      return;
    }

    const newPlan = plans.find((p) => p.id === selectedPlanId);
    if (!newPlan) return;

    const newViolations: string[] = [];

    if (stats.user_count > newPlan.max_users) {
      newViolations.push(
        `You have ${stats.user_count} users but the new plan allows only ${newPlan.max_users}`
      );
    }

    if (stats.candidates_count > newPlan.max_candidates) {
      newViolations.push(
        `You have ${stats.candidates_count} candidates but the new plan allows only ${newPlan.max_candidates}`
      );
    }

    if (stats.jobs_count > newPlan.max_jobs) {
      newViolations.push(
        `You have ${stats.jobs_count} jobs but the new plan allows only ${newPlan.max_jobs}`
      );
    }

    // Note: Storage validation will be added when storage stats are available
    // if (stats.storage_gb > newPlan.max_storage_gb) {
    //   newViolations.push(
    //     `You are using ${stats.storage_gb}GB storage but the new plan allows only ${newPlan.max_storage_gb}GB`
    //   );
    // }

    setViolations(newViolations);
  }, [selectedPlanId, stats, plans, tenant.subscription_plan_id]);

  useEffect(() => {
    setSelectedPlanId(watchedPlanId || null);
  }, [watchedPlanId]);

  const handleSubmit = async (data: ChangePlanFormData) => {
    if (violations.length > 0) {
      return;
    }
    await onSubmit(data);
  };

  const getPlanPrice = (plan: SubscriptionPlan, cycle: 'MONTHLY' | 'YEARLY') => {
    const price = cycle === 'YEARLY' ? plan.price_yearly : plan.price_monthly;
    if (typeof price === 'string') {
      return parseFloat(price);
    }
    return price;
  };

  const currentPrice = currentPlan
    ? getPlanPrice(currentPlan, watchedBillingCycle) || 0
    : 0;
  const newPrice = selectedPlan ? getPlanPrice(selectedPlan, watchedBillingCycle) || 0 : 0;
  const priceDifference = newPrice - currentPrice;

  const isPlanChanged = selectedPlanId && selectedPlanId !== tenant.subscription_plan_id;
  const canSubmit = isPlanChanged && violations.length === 0 && !isLoading;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Change Subscription Plan</DialogTitle>
          <DialogDescription>
            Update the subscription plan for {tenant.name}
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
            {/* Plan Selector */}
            <FormField
              control={form.control}
              name="new_plan_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Subscription Plan</FormLabel>
                  <Select
                    value={field.value?.toString()}
                    onValueChange={(value) => field.onChange(parseInt(value, 10))}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Select a plan" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {plans.map((plan) => {
                        const price = getPlanPrice(plan, watchedBillingCycle) || 0;
                        return (
                          <SelectItem key={plan.id} value={plan.id.toString()}>
                            <div className="flex items-center justify-between gap-4">
                              <div className="flex items-center gap-2">
                                <span className="font-medium">{plan.display_name}</span>
                                {plan.is_custom && (
                                  <Badge variant="outline" className="text-xs">
                                    Custom
                                  </Badge>
                                )}
                              </div>
                              <span className="text-sm text-muted-foreground">
                                ${price.toFixed(2)}/
                                {watchedBillingCycle === 'YEARLY' ? 'year' : 'month'}
                              </span>
                            </div>
                          </SelectItem>
                        );
                      })}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Billing Cycle */}
            <FormField
              control={form.control}
              name="billing_cycle"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Billing Cycle</FormLabel>
                  <FormControl>
                    <RadioGroup
                      value={field.value}
                      onValueChange={field.onChange}
                      className="flex gap-4"
                    >
                      <div className="flex items-center space-x-2">
                        <RadioGroupItem value="MONTHLY" id="monthly" />
                        <Label htmlFor="monthly" className="cursor-pointer">
                          Monthly
                        </Label>
                      </div>
                      <div className="flex items-center space-x-2">
                        <RadioGroupItem value="YEARLY" id="yearly" />
                        <Label htmlFor="yearly" className="cursor-pointer">
                          Yearly (Save ~17%)
                        </Label>
                      </div>
                    </RadioGroup>
                  </FormControl>
                  <FormDescription>
                    Choose your billing frequency
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Plan Comparison */}
            {currentPlan && selectedPlan && isPlanChanged && (
              <div className="rounded-lg border p-4 space-y-4">
                <h3 className="font-semibold">Plan Comparison</h3>
                
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div className="font-medium text-muted-foreground">Feature</div>
                  <div className="font-medium text-center">Current Plan</div>
                  <div className="font-medium text-center">New Plan</div>

                  {/* Users */}
                  <div className="text-muted-foreground">Users</div>
                  <div className="text-center">{currentPlan.max_users}</div>
                  <div className="text-center font-semibold">
                    {selectedPlan.max_users}
                    {selectedPlan.max_users > currentPlan.max_users && (
                      <ArrowRight className="inline h-3 w-3 ml-1 text-green-600" />
                    )}
                  </div>

                  {/* Candidates */}
                  <div className="text-muted-foreground">Candidates</div>
                  <div className="text-center">{currentPlan.max_candidates.toLocaleString()}</div>
                  <div className="text-center font-semibold">
                    {selectedPlan.max_candidates.toLocaleString()}
                    {selectedPlan.max_candidates > currentPlan.max_candidates && (
                      <ArrowRight className="inline h-3 w-3 ml-1 text-green-600" />
                    )}
                  </div>

                  {/* Jobs */}
                  <div className="text-muted-foreground">Jobs</div>
                  <div className="text-center">{currentPlan.max_jobs.toLocaleString()}</div>
                  <div className="text-center font-semibold">
                    {selectedPlan.max_jobs.toLocaleString()}
                    {selectedPlan.max_jobs > currentPlan.max_jobs && (
                      <ArrowRight className="inline h-3 w-3 ml-1 text-green-600" />
                    )}
                  </div>

                  {/* Storage */}
                  <div className="text-muted-foreground">Storage</div>
                  <div className="text-center">{currentPlan.max_storage_gb}GB</div>
                  <div className="text-center font-semibold">
                    {selectedPlan.max_storage_gb}GB
                    {selectedPlan.max_storage_gb > currentPlan.max_storage_gb && (
                      <ArrowRight className="inline h-3 w-3 ml-1 text-green-600" />
                    )}
                  </div>

                  {/* Price */}
                  <div className="text-muted-foreground">Price</div>
                  <div className="text-center">
                    ${currentPrice.toFixed(2)}/{watchedBillingCycle === 'YEARLY' ? 'yr' : 'mo'}
                  </div>
                  <div className="text-center font-semibold">
                    ${newPrice.toFixed(2)}/{watchedBillingCycle === 'YEARLY' ? 'yr' : 'mo'}
                    {priceDifference > 0 && (
                      <span className="text-red-600 text-xs ml-1">
                        (+${priceDifference.toFixed(2)})
                      </span>
                    )}
                    {priceDifference < 0 && (
                      <span className="text-green-600 text-xs ml-1">
                        ({priceDifference.toFixed(2)})
                      </span>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Downgrade Warnings */}
            {violations.length > 0 && (
              <Alert variant="destructive">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>
                  <div className="font-semibold mb-2">Cannot change to this plan:</div>
                  <ul className="list-disc list-inside space-y-1">
                    {violations.map((violation, index) => (
                      <li key={index} className="text-sm">{violation}</li>
                    ))}
                  </ul>
                  <p className="mt-2 text-sm">
                    Please reduce usage to fit within the new plan's limits before downgrading.
                  </p>
                </AlertDescription>
              </Alert>
            )}

            {/* Success Indicator */}
            {isPlanChanged && violations.length === 0 && (
              <Alert>
                <Check className="h-4 w-4" />
                <AlertDescription>
                  This plan change is valid. Current usage fits within the new plan limits.
                </AlertDescription>
              </Alert>
            )}

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={isLoading}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={!canSubmit}>
                {isLoading ? 'Changing Plan...' : 'Change Plan'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
