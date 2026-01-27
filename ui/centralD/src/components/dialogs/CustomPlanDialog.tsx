import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
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
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, AlertTriangle } from 'lucide-react';
import { subscriptionPlansApi } from '@/lib/dashboard-api';
import type { CustomPlanCreateRequest, CustomPlanUpdateRequest, SubscriptionPlan } from '@/types/subscription-plan';

const customPlanSchema = z.object({
  display_name: z.string().min(1, 'Display name is required'),
  description: z.string().optional(),
  base_plan_id: z.number().optional(),
  price_monthly: z.number().min(0, 'Monthly price must be at least 0'),
  price_yearly: z.number().min(0, 'Yearly price must be at least 0').optional(),
  max_users: z.number().min(1, 'Must allow at least 1 user'),
  max_candidates: z.number().min(1, 'Must allow at least 1 candidate'),
  max_jobs: z.number().min(1, 'Must allow at least 1 job'),
  max_storage_gb: z.number().min(1, 'Must allow at least 1 GB'),
});

type CustomPlanFormData = z.infer<typeof customPlanSchema>;

interface CustomPlanDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  tenantId: number;
  tenantName: string;
  existingPlan?: SubscriptionPlan;
}

export function CustomPlanDialog({
  open,
  onOpenChange,
  tenantId,
  tenantName,
  existingPlan,
}: CustomPlanDialogProps) {
  const queryClient = useQueryClient();
  const [errorMessage, setErrorMessage] = useState<string>('');
  const isEditMode = !!existingPlan;

  const { data: standardPlans, isLoading: plansLoading } = useQuery({
    queryKey: ['subscription-plans'],
    queryFn: () => subscriptionPlansApi.list(),
    staleTime: 0,
    enabled: !isEditMode,
  });

  const form = useForm<CustomPlanFormData>({
    resolver: zodResolver(customPlanSchema),
    defaultValues: existingPlan
      ? {
          display_name: existingPlan.display_name,
          description: existingPlan.description || '',
          price_monthly: existingPlan.price_monthly,
          price_yearly: existingPlan.price_yearly || 0,
          max_users: existingPlan.max_users,
          max_candidates: existingPlan.max_candidates,
          max_jobs: existingPlan.max_jobs,
          max_storage_gb: existingPlan.max_storage_gb,
        }
      : {
          display_name: '',
          description: '',
          price_monthly: 0,
          price_yearly: 0,
          max_users: 10,
          max_candidates: 1000,
          max_jobs: 50,
          max_storage_gb: 10,
        },
  });

  const watchedBasePlanId = form.watch('base_plan_id');

  useEffect(() => {
    if (!isEditMode && watchedBasePlanId && standardPlans?.plans) {
      const basePlan = standardPlans.plans.find(
        (p: SubscriptionPlan) => p.id === watchedBasePlanId && !p.is_custom
      );
      if (basePlan) {
        form.setValue('price_monthly', basePlan.price_monthly);
        form.setValue('price_yearly', basePlan.price_yearly || 0);
        form.setValue('max_users', basePlan.max_users);
        form.setValue('max_candidates', basePlan.max_candidates);
        form.setValue('max_jobs', basePlan.max_jobs);
        form.setValue('max_storage_gb', basePlan.max_storage_gb);
      }
    }
  }, [watchedBasePlanId, standardPlans, form, isEditMode]);

  const createMutation = useMutation({
    mutationFn: (data: CustomPlanCreateRequest) =>
      subscriptionPlansApi.createCustom(data),
    onSuccess: async () => {
      await queryClient.refetchQueries({ queryKey: ['subscription-plans'] });
      await queryClient.refetchQueries({ queryKey: ['subscription-plans', tenantId] });
      await queryClient.refetchQueries({ queryKey: ['tenants'] });
      onOpenChange(false);
      form.reset();
      setErrorMessage('');
    },
    onError: (error: Error) => {
      const apiError = error as { response?: { data?: { message?: string } } };
      setErrorMessage(apiError.response?.data?.message || 'Failed to create custom plan');
    },
  });

  const updateMutation = useMutation({
    mutationFn: (data: CustomPlanUpdateRequest) =>
      subscriptionPlansApi.updateCustom(existingPlan!.id, data),
    onSuccess: async () => {
      await queryClient.refetchQueries({ queryKey: ['subscription-plans'] });
      await queryClient.refetchQueries({ queryKey: ['subscription-plans', tenantId] });
      await queryClient.refetchQueries({ queryKey: ['tenants'] });
      onOpenChange(false);
      form.reset();
      setErrorMessage('');
    },
    onError: (error: Error) => {
      const apiError = error as { response?: { data?: { message?: string } } };
      setErrorMessage(
        apiError.response?.data?.message || 'Failed to update custom plan'
      );
    },
  });

  const onSubmit = (data: CustomPlanFormData) => {
    setErrorMessage('');

    if (isEditMode) {
      const updateData: CustomPlanUpdateRequest = {
        display_name: data.display_name,
        description: data.description || undefined,
        price_monthly: data.price_monthly,
        price_yearly: data.price_yearly || undefined,
        max_users: data.max_users,
        max_candidates: data.max_candidates,
        max_jobs: data.max_jobs,
        max_storage_gb: data.max_storage_gb,
      };
      updateMutation.mutate(updateData);
    } else {
      const createData: CustomPlanCreateRequest = {
        tenant_id: tenantId,
        base_plan_id: data.base_plan_id,
        display_name: data.display_name,
        description: data.description || undefined,
        price_monthly: data.price_monthly,
        price_yearly: data.price_yearly || undefined,
        max_users: data.max_users,
        max_candidates: data.max_candidates,
        max_jobs: data.max_jobs,
        max_storage_gb: data.max_storage_gb,
      };
      createMutation.mutate(createData);
    }
  };

  const isSubmitting = createMutation.isPending || updateMutation.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {isEditMode ? 'Edit Custom Plan' : 'Create Custom Plan'}
          </DialogTitle>
          <DialogDescription>
            {isEditMode
              ? `Edit custom plan for ${tenantName}`
              : `Create a custom subscription plan for ${tenantName}`}
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            {errorMessage && (
              <Alert variant="destructive">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>{errorMessage}</AlertDescription>
              </Alert>
            )}

            <FormField
              control={form.control}
              name="display_name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Display Name *</FormLabel>
                  <FormControl>
                    <Input placeholder="e.g., Acme Corp Special Plan" {...field} />
                  </FormControl>
                  <FormDescription>
                    The name shown to the tenant
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Description</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="Optional description..."
                      rows={3}
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {!isEditMode && (
              <FormField
                control={form.control}
                name="base_plan_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Base Plan (Optional)</FormLabel>
                    <Select
                      onValueChange={(value) =>
                        field.onChange(value === "none" ? undefined : Number(value))
                      }
                      value={field.value?.toString() ?? "none"}
                      disabled={plansLoading}
                    >
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select a standard plan to clone from" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="none">None</SelectItem>
                        {standardPlans?.plans
                          .filter((p: SubscriptionPlan) => !p.is_custom)
                          .map((plan: SubscriptionPlan) => (
                            <SelectItem key={plan.id} value={plan.id.toString()}>
                              {plan.display_name}
                            </SelectItem>
                          ))}
                      </SelectContent>
                    </Select>
                    <FormDescription>
                      Clone limits and features from a standard plan
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            )}

            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="price_monthly"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Monthly Price ($) *</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        step="0.01"
                        min="0"
                        {...field}
                        onChange={(e) => field.onChange(Number(e.target.value))}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="price_yearly"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Yearly Price ($)</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        step="0.01"
                        min="0"
                        {...field}
                        onChange={(e) => field.onChange(Number(e.target.value))}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <div className="space-y-4">
              <h3 className="text-sm font-medium">Limits</h3>
              <div className="grid grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="max_users"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Max Users *</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          min="1"
                          {...field}
                          onChange={(e) => field.onChange(Number(e.target.value))}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="max_candidates"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Max Candidates *</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          min="1"
                          {...field}
                          onChange={(e) => field.onChange(Number(e.target.value))}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="max_jobs"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Max Jobs *</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          min="1"
                          {...field}
                          onChange={(e) => field.onChange(Number(e.target.value))}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="max_storage_gb"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Max Storage (GB) *</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          min="1"
                          {...field}
                          onChange={(e) => field.onChange(Number(e.target.value))}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={isSubmitting}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {isEditMode ? 'Update Plan' : 'Create Plan'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
