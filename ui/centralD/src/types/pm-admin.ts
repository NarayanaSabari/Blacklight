/**
 * TypeScript types for PM Admin operations
 */

export interface PMAdmin {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  phone?: string;
  is_active: boolean;
  last_login?: string;
  failed_login_attempts: number;
  locked_until?: string;
  created_at: string;
  updated_at: string;
}

export interface PMAdminLoginRequest {
  email: string;
  password: string;
}

export interface PMAdminLoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  admin: PMAdmin;
}

export interface PMAdminCreateRequest {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  phone?: string;
  is_active?: boolean;
}

export interface PMAdminUpdateRequest {
  email?: string;
  first_name?: string;
  last_name?: string;
  phone?: string;
  is_active?: boolean;
}

export interface ResetTenantAdminPasswordRequest {
  portal_user_id: number;
  new_password: string;
}
