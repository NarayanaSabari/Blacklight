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
  max_jobs: number;
  max_storage_gb: number;
  features?: Record<string, boolean | string>;
  is_active: boolean;
  sort_order: number;
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
