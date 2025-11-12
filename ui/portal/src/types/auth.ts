/**
 * Portal Authentication Types
 */

import { Role } from './entities'; // Import Role type

export interface PortalUser {
  id: number;
  tenant_id: number;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  phone: string | null;
  roles: Role[]; // Changed from single role to array of roles
  is_active: boolean;
  last_login: string | null;
  is_locked: boolean;
  locked_until: string | null;
  created_at: string;
  updated_at: string;
  tenant?: {
    id: number;
    slug: string;
    company_name: string;
    status: string;
  };
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: PortalUser;
}

export interface RefreshTokenRequest {
  refresh_token: string;
}

export interface RefreshTokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}
