/**
 * Tenant Detail Page
 * Shows detailed information about a specific tenant
 */

/**
 * Tenant Detail Page
 * Displays comprehensive information about a single tenant
 */

import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { TenantInfoCard } from '@/components/tenants/TenantInfoCard';
import { CurrentPlanCard } from '@/components/tenants/CurrentPlanCard';
import { TenantStatsCard } from '@/components/tenants/TenantStatsCard';
import { DangerZone } from '@/components/tenants/DangerZone';
import { TenantUsersTable } from '@/components/tenants/TenantUsersTable';
import { DeleteTenantDialog } from '@/components/dialogs/DeleteTenantDialog';
import { SuspendTenantDialog } from '@/components/dialogs/SuspendTenantDialog';
import { ChangePlanDialog } from '@/components/dialogs/ChangePlanDialog';
import { CustomPlanDialog } from '@/components/dialogs/CustomPlanDialog';
import { useTenant } from '@/hooks/api/useTenant';
import { useTenantStats } from '@/hooks/api/useTenantStats';
import { usePortalUsers } from '@/hooks/api/usePortalUsers';
import { useSuspendTenant } from '@/hooks/api/useSuspendTenant';
import { useActivateTenant } from '@/hooks/api/useActivateTenant';
import { useDeleteTenant } from '@/hooks/api/useDeleteTenant';
import { useChangeTenantPlan } from '@/hooks/api/useChangeTenantPlan';
import { subscriptionPlansApi } from '@/lib/dashboard-api';
import { toast } from 'sonner';

export function TenantDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();

  const { data: tenant, isLoading, error } = useTenant(slug || '');
  const tenantId = tenant?.id || 0;
  
  const { data: stats } = useTenantStats(slug);
  const { data: plans = [] } = useQuery({
    queryKey: ['subscription-plans', tenantId],
    queryFn: () => subscriptionPlansApi.listForTenant(tenantId),
    staleTime: 0,
    enabled: !!tenantId,
  });
  const { data: portalUsers = [], isLoading: isLoadingUsers } = usePortalUsers(slug);
  
  const suspendTenant = useSuspendTenant(tenantId);
  const activateTenant = useActivateTenant(tenantId);
  const deleteTenant = useDeleteTenant(tenantId);
  const changePlan = useChangeTenantPlan(tenantId);

  const [showSuspendDialog, setShowSuspendDialog] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [showChangePlanDialog, setShowChangePlanDialog] = useState(false);
  const [showCustomPlanDialog, setShowCustomPlanDialog] = useState(false);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !tenant) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate('/tenants')}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <h1 className="text-3xl font-bold tracking-tight">Tenant Not Found</h1>
        </div>
        <p className="text-muted-foreground">
          The tenant you're looking for doesn't exist or you don't have permission to view it.
        </p>
      </div>
    );
  }

  const handleSuspend = async (reason: string) => {
    try {
      await suspendTenant.mutateAsync({ reason });
      toast.success('Tenant suspended successfully');
      setShowSuspendDialog(false);
    } catch (error) {
      console.error('Failed to suspend tenant:', error);
    }
  };

  const handleActivate = async () => {
    try {
      await activateTenant.mutateAsync();
      toast.success('Tenant activated successfully');
    } catch (error) {
      console.error('Failed to activate tenant:', error);
    }
  };

  const handleDelete = async (reason: string) => {
    try {
      await deleteTenant.mutateAsync({ reason });
      toast.success('Tenant deleted successfully');
      setShowDeleteDialog(false);
      navigate('/tenants');
    } catch (error) {
      console.error('Failed to delete tenant:', error);
    }
  };

  const handleChangePlan = async (data: { new_plan_id: number; billing_cycle: 'MONTHLY' | 'YEARLY' }) => {
    try {
      await changePlan.mutateAsync(data);
      setShowChangePlanDialog(false);
    } catch (error) {
      console.error('Failed to change plan:', error);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate('/tenants')}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="flex-1">
          <h1 className="text-3xl font-bold tracking-tight">{tenant.name}</h1>
          <p className="text-muted-foreground">Manage tenant information and settings</p>
        </div>
      </div>

      {/* Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Main Info */}
        <div className="lg:col-span-2 space-y-6">
          <TenantInfoCard tenant={tenant} />
          <TenantUsersTable 
            tenantId={tenantId} 
            users={portalUsers} 
            isLoading={isLoadingUsers}
          />
          <DangerZone
            tenant={tenant}
            onSuspend={() => setShowSuspendDialog(true)}
            onActivate={handleActivate}
            onDelete={() => setShowDeleteDialog(true)}
          />
        </div>

        {/* Right Column - Subscription & Stats */}
        <div className="space-y-6">
          <CurrentPlanCard
            tenant={tenant}
            onChangePlan={() => setShowChangePlanDialog(true)}
            onCreateCustomPlan={() => setShowCustomPlanDialog(true)}
            onEditCustomPlan={() => setShowCustomPlanDialog(true)}
          />
          <TenantStatsCard tenant={tenant} stats={stats} />
        </div>
      </div>

      {/* Dialogs */}
      <ChangePlanDialog
        open={showChangePlanDialog}
        onOpenChange={setShowChangePlanDialog}
        tenant={tenant}
        stats={stats || null}
        plans={plans}
        onSubmit={handleChangePlan}
        isLoading={changePlan.isPending}
      />

      <SuspendTenantDialog
        open={showSuspendDialog}
        onOpenChange={setShowSuspendDialog}
        tenant={tenant}
        onConfirm={handleSuspend}
        isSuspending={suspendTenant.isPending}
      />

      <DeleteTenantDialog
        open={showDeleteDialog}
        onOpenChange={setShowDeleteDialog}
        tenant={tenant}
        onConfirm={handleDelete}
        isDeleting={deleteTenant.isPending}
      />

      <CustomPlanDialog
        open={showCustomPlanDialog}
        onOpenChange={setShowCustomPlanDialog}
        tenantId={tenant.id}
        tenantName={tenant.name}
        existingPlan={tenant.subscription_plan?.is_custom ? tenant.subscription_plan : undefined}
      />
    </div>
  );
}
