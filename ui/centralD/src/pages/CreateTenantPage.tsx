/**
 * Create Tenant Page
 * Allows PM admins to create new tenants
 */

import { useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { TenantForm, type TenantFormData } from '@/components/tenants/TenantForm';
import { useCreateTenant } from '@/hooks/api/useCreateTenant';
import { toast } from 'sonner';
import type { TenantCreateRequest } from '@/types';

export function CreateTenantPage() {
  const navigate = useNavigate();
  const createTenant = useCreateTenant();

  const handleSubmit = async (data: TenantFormData) => {
    try {
      // Transform form data to API request format
      const requestData: TenantCreateRequest = {
        name: data.name,
        company_email: data.company_email,
        company_phone: data.company_phone,
        subscription_plan_id: parseInt(data.subscription_plan_id, 10),
        billing_cycle: data.billing_cycle,
        tenant_admin_email: data.tenant_admin_email,
        tenant_admin_password: data.tenant_admin_password,
        tenant_admin_first_name: data.tenant_admin_first_name,
        tenant_admin_last_name: data.tenant_admin_last_name,
      };
      
      await createTenant.mutateAsync(requestData);
      toast.success('Tenant created successfully');
      navigate('/tenants');
    } catch (error) {
      console.error('Failed to create tenant:', error);
      // Error toast is already shown by the mutation hook
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => navigate('/tenants')}
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <h1 className="text-3xl font-bold tracking-tight">Create New Tenant</h1>
          </div>
          <p className="text-muted-foreground">
            Set up a new tenant with company information, subscription plan, and admin account
          </p>
        </div>
      </div>

      {/* Form */}
      <div className="max-w-4xl">
        <TenantForm
          onSubmit={handleSubmit}
          isSubmitting={createTenant.isPending}
          mode="create"
        />
      </div>
    </div>
  );
}
