/**
 * TypeScript types for Subscription Plans
 */

export interface SubscriptionPlan {
  id: number;
  name: string;
  display_name: string;
  description?: string;
  price_monthly: number;
  price_yearly?: number;
  max_users: number;
  max_candidates: number;
  max_storage_gb: number;
  features?: Record<string, boolean | string>;
  is_active: boolean;
  sort_order: number;
  is_custom: boolean;
  custom_for_tenant_id: number | null;
  custom_for_tenant_name?: string;
  custom_for_tenant_slug?: string;
  assigned_tenants_count?: number;
  created_at: string;
  updated_at: string;
}

export interface SubscriptionPlanListResponse {
  plans: SubscriptionPlan[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface SubscriptionPlanUsageResponse {
  plan: SubscriptionPlan;
  active_tenants_count: number;
  total_tenants_count: number;
}

export interface CustomPlanCreateRequest {
  tenant_id: number;
  base_plan_id?: number;
  display_name: string;
  description?: string;
  price_monthly: number;
  price_yearly?: number;
  max_users: number;
  max_candidates: number;
  max_storage_gb: number;
  features?: Record<string, boolean | string>;
}

export interface CustomPlanUpdateRequest {
  display_name?: string;
  description?: string;
  price_monthly?: number;
  price_yearly?: number;
  max_users?: number;
  max_candidates?: number;
  max_storage_gb?: number;
  features?: Record<string, boolean | string>;
}
