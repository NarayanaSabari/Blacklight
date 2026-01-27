/**
 * TypeScript types for Tenants
 */

import type { SubscriptionPlan } from './subscription-plan';

export type TenantStatus = 'ACTIVE' | 'SUSPENDED' | 'INACTIVE';
export type BillingCycle = 'MONTHLY' | 'YEARLY';

export interface Tenant {
  id: number;
  name: string;
  slug: string;
  company_email: string;
  company_phone: string | null;
  status: TenantStatus;
  subscription_plan_id: number;
  subscription_start_date: string;
  subscription_end_date: string | null;
  billing_cycle: BillingCycle | null;
  next_billing_date: string | null;
  settings: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  subscription_plan?: SubscriptionPlan;
  tenant_admin_email?: string;
}

export interface TenantCreateRequest {
  // Company Information
  name: string;
  slug?: string;
  company_email: string;
  company_phone?: string;
  
  // Subscription
  subscription_plan_id: number;
  billing_cycle?: BillingCycle;
  
  // Tenant Admin Account
  tenant_admin_email: string;
  tenant_admin_password: string;
  tenant_admin_first_name: string;
  tenant_admin_last_name: string;
  
  // Metadata
  settings?: Record<string, unknown>;
}

export interface TenantFormData {
  // Company Information
  name: string;
  company_email: string;
  company_phone?: string;
  
  // Subscription
  subscription_plan_id: string;
  billing_cycle: BillingCycle;
  
  // Tenant Admin Account (only for create)
  tenant_admin_email: string;
  tenant_admin_password: string;
  tenant_admin_confirm_password: string;
  tenant_admin_first_name: string;
  tenant_admin_last_name: string;
}

export interface TenantUpdateRequest {
  name?: string;
  company_email?: string;
  company_phone?: string;
  settings?: Record<string, unknown>;
}

export interface TenantChangePlanRequest {
  new_plan_id: number;
  billing_cycle?: BillingCycle;
}

export interface TenantSuspendRequest {
  reason: string;
}

export interface TenantDeleteRequest {
  reason: string;
}

export interface TenantFilterParams {
  page?: number;
  per_page?: number;
  status?: TenantStatus;
  subscription_plan_id?: number;
  search?: string;
}

export interface TenantListResponse {
  items: Tenant[];
  total: number;
  page: number;
  per_page: number;
}

export interface TenantStats {
  tenant_id: number;
  user_count: number;
  candidate_count: number;
  storage_used_gb: number;
  max_users: number;
  max_candidates: number;
  max_storage_gb: number;
}

export interface TenantDeleteResponse {
  message: string;
  users_deleted: number;
}

export interface TenantSubscriptionHistory {
  id: number;
  tenant_id: number;
  subscription_plan_id: number;
  subscription_plan?: SubscriptionPlan;
  billing_cycle: BillingCycle | null;
  started_at: string;
  ended_at: string | null;
  changed_by: string;
  changed_by_admin?: {
    id: number;
    first_name: string;
    last_name: string;
    email: string;
  };
  notes: string | null;
  created_at: string;
}
