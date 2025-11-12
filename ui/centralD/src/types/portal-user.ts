/**
 * TypeScript types for Portal Users
 */

export interface Role {
  id: number;
  name: string;
  display_name: string;
  description?: string;
  is_system_role: boolean;
  is_active: boolean;
  tenant_id?: number;
  created_at: string;
  updated_at: string;
}

export type PortalUserRole = 'TENANT_ADMIN' | 'RECRUITER' | 'HIRING_MANAGER';

export interface PortalUser {
  id: number;
  tenant_id: number;
  email: string;
  first_name: string;
  last_name: string;
  roles: Role[]; // Changed from 'role: PortalUserRole;'
  is_active: boolean;
  last_login?: string;
  created_at: string;
  updated_at: string;
}

export interface PortalUserLoginRequest {
  email: string;
  password: string;
  tenant_slug: string;
}

export interface PortalUserLoginResponse {
  message: string;
  user: PortalUser;
}

export interface PortalUserCreateRequest {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  role: PortalUserRole;
  is_active?: boolean;
}

export interface PortalUserUpdateRequest {
  email?: string;
  password?: string;
  first_name?: string;
  last_name?: string;
  role?: PortalUserRole;
  is_active?: boolean;
}

export interface PortalUserFilterParams {
  page?: number;
  per_page?: number;
  role?: PortalUserRole;
  is_active?: boolean;
  search?: string;
}

export interface PortalUserListResponse {
  users: PortalUser[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}
