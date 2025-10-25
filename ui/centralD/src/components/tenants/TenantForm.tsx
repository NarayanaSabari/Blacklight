/**
 * Tenant Form Component
 * Used for creating and editing tenants
 */

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, Building2, CreditCard, UserPlus, AlertCircle } from 'lucide-react';
import { usePlans } from '@/hooks/api/usePlans';
import type { BillingCycle } from '@/types';

const tenantFormSchema = z.object({
  // Company Information
  name: z.string().min(2, 'Company name must be at least 2 characters').max(200),
  company_email: z.string().email('Invalid email address'),
  company_phone: z.string().optional(),
  
  // Subscription
  subscription_plan_id: z.string().min(1, 'Please select a subscription plan'),
  billing_cycle: z.enum(['MONTHLY', 'YEARLY']),
  
  // Tenant Admin Account
  tenant_admin_email: z.string().email('Invalid email address'),
  tenant_admin_password: z.string().min(8, 'Password must be at least 8 characters'),
  tenant_admin_confirm_password: z.string(),
  tenant_admin_first_name: z.string().min(1, 'First name is required').max(100),
  tenant_admin_last_name: z.string().min(1, 'Last name is required').max(100),
}).refine((data) => data.tenant_admin_password === data.tenant_admin_confirm_password, {
  message: "Passwords don't match",
  path: ['tenant_admin_confirm_password'],
});

export type TenantFormData = z.infer<typeof tenantFormSchema>;

interface TenantFormProps {
  onSubmit: (data: TenantFormData) => Promise<void>;
  isSubmitting?: boolean;
  defaultValues?: Partial<TenantFormData>;
  mode?: 'create' | 'edit';
}

export function TenantForm({ onSubmit, isSubmitting, defaultValues, mode = 'create' }: TenantFormProps) {
  const { data: plansData, isLoading: plansLoading } = usePlans();
  
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<TenantFormData>({
    resolver: zodResolver(tenantFormSchema),
    defaultValues: defaultValues || {
      billing_cycle: 'MONTHLY',
    },
  });

  const selectedPlanId = watch('subscription_plan_id');
  const billingCycle = watch('billing_cycle');
  
  const selectedPlan = plansData?.find((p) => p.id.toString() === selectedPlanId);

  const getPrice = () => {
    if (!selectedPlan) return null;
    const price = billingCycle === 'YEARLY' 
      ? selectedPlan.price_yearly 
      : selectedPlan.price_monthly;
    // Convert to number if it's a string
    return typeof price === 'string' ? parseFloat(price) : price;
  };

  const handleFormSubmit = async (data: TenantFormData) => {
    await onSubmit(data);
  };

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-6">
      {/* Company Information Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Building2 className="h-5 w-5" />
            Company Information
          </CardTitle>
          <CardDescription>Basic information about the company</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Company Name *</Label>
            <Input
              id="name"
              {...register('name')}
              placeholder="Acme Corporation"
              disabled={isSubmitting}
            />
            {errors.name && (
              <p className="text-sm text-destructive">{errors.name.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="company_email">Company Email *</Label>
            <Input
              id="company_email"
              type="email"
              {...register('company_email')}
              placeholder="contact@acme.com"
              disabled={isSubmitting}
            />
            {errors.company_email && (
              <p className="text-sm text-destructive">{errors.company_email.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="company_phone">Company Phone</Label>
            <Input
              id="company_phone"
              {...register('company_phone')}
              placeholder="+1 (555) 123-4567"
              disabled={isSubmitting}
            />
            {errors.company_phone && (
              <p className="text-sm text-destructive">{errors.company_phone.message}</p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Subscription Plan Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CreditCard className="h-5 w-5" />
            Subscription Plan
          </CardTitle>
          <CardDescription>Choose a plan and billing cycle</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="subscription_plan_id">Plan *</Label>
            {plansLoading ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading plans...
              </div>
            ) : (
              <Select
                value={selectedPlanId}
                onValueChange={(value) => setValue('subscription_plan_id', value)}
                disabled={isSubmitting}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a plan" />
                </SelectTrigger>
                <SelectContent>
                  {plansData?.map((plan) => (
                    <SelectItem key={plan.id} value={plan.id.toString()}>
                      <div className="flex flex-col">
                        <span className="font-medium">{plan.name}</span>
                        <span className="text-sm text-muted-foreground">
                          {plan.max_users} users • {plan.max_candidates} candidates • {plan.max_jobs} jobs
                        </span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
            {errors.subscription_plan_id && (
              <p className="text-sm text-destructive">{errors.subscription_plan_id.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label>Billing Cycle *</Label>
            <RadioGroup
              value={billingCycle}
              onValueChange={(value) => setValue('billing_cycle', value as BillingCycle)}
              disabled={isSubmitting}
              className="flex gap-4"
            >
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="MONTHLY" id="monthly" />
                <Label htmlFor="monthly" className="font-normal cursor-pointer">
                  Monthly
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="YEARLY" id="yearly" />
                <Label htmlFor="yearly" className="font-normal cursor-pointer">
                  Yearly (Save {selectedPlan ? Math.round((1 - (selectedPlan.price_yearly || 0) / ((selectedPlan.price_monthly || 0) * 12)) * 100) : 0}%)
                </Label>
              </div>
            </RadioGroup>
          </div>

          {selectedPlan && (
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                <div className="font-semibold mb-2">Selected Plan: {selectedPlan.name}</div>
                <div className="space-y-1 text-sm">
                  <div>Price: ${getPrice()?.toFixed(2)} / {billingCycle === 'YEARLY' ? 'year' : 'month'}</div>
                  <div>Users: {selectedPlan.max_users}</div>
                  <div>Candidates: {selectedPlan.max_candidates}</div>
                  <div>Jobs: {selectedPlan.max_jobs}</div>
                  <div>Storage: {selectedPlan.max_storage_gb} GB</div>
                </div>
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Tenant Admin Account Section (only for create mode) */}
      {mode === 'create' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <UserPlus className="h-5 w-5" />
              Tenant Administrator Account
            </CardTitle>
            <CardDescription>
              This will be the primary administrator for this tenant
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="tenant_admin_first_name">First Name *</Label>
                <Input
                  id="tenant_admin_first_name"
                  {...register('tenant_admin_first_name')}
                  placeholder="John"
                  disabled={isSubmitting}
                />
                {errors.tenant_admin_first_name && (
                  <p className="text-sm text-destructive">{errors.tenant_admin_first_name.message}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="tenant_admin_last_name">Last Name *</Label>
                <Input
                  id="tenant_admin_last_name"
                  {...register('tenant_admin_last_name')}
                  placeholder="Doe"
                  disabled={isSubmitting}
                />
                {errors.tenant_admin_last_name && (
                  <p className="text-sm text-destructive">{errors.tenant_admin_last_name.message}</p>
                )}
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="tenant_admin_email">Admin Email *</Label>
              <Input
                id="tenant_admin_email"
                type="email"
                {...register('tenant_admin_email')}
                placeholder="admin@acme.com"
                disabled={isSubmitting}
              />
              {errors.tenant_admin_email && (
                <p className="text-sm text-destructive">{errors.tenant_admin_email.message}</p>
              )}
              <p className="text-sm text-muted-foreground">
                This email must be globally unique across all tenants
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="tenant_admin_password">Password *</Label>
              <Input
                id="tenant_admin_password"
                type="password"
                {...register('tenant_admin_password')}
                placeholder="••••••••"
                disabled={isSubmitting}
              />
              {errors.tenant_admin_password && (
                <p className="text-sm text-destructive">{errors.tenant_admin_password.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="tenant_admin_confirm_password">Confirm Password *</Label>
              <Input
                id="tenant_admin_confirm_password"
                type="password"
                {...register('tenant_admin_confirm_password')}
                placeholder="••••••••"
                disabled={isSubmitting}
              />
              {errors.tenant_admin_confirm_password && (
                <p className="text-sm text-destructive">{errors.tenant_admin_confirm_password.message}</p>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Submit Button */}
      <div className="flex justify-end gap-4">
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {mode === 'create' ? 'Create Tenant' : 'Update Tenant'}
        </Button>
      </div>
    </form>
  );
}
