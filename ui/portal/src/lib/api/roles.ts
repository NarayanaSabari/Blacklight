/**
 * Roles API Functions
 */

import { apiClient } from '@/lib/api-client';
import type { Role, RoleListResponse, Permission } from '@/types';

// Using /api/portal prefix to avoid conflict with centralD's /api/roles (PM_ADMIN global roles)
const BASE_URL = '/api/portal/roles';

/**
 * Get all roles for current tenant
 */
export async function fetchRoles(includePermissions: boolean = false, includeUserCounts: boolean = true): Promise<RoleListResponse> {
  const params: Record<string, string> = {};
  if (includePermissions) params.include_permissions = 'true';
  if (includeUserCounts) params.include_user_counts = 'true';

  const response = await apiClient.get<RoleListResponse>(BASE_URL, { params });
  return response.data;
}

/**
 * Get single role by ID
 */
export async function fetchRole(id: number): Promise<Role> {
  const response = await apiClient.get<Role>(`${BASE_URL}/${id}`);
  return response.data;
}

/**
 * Get all available permissions
 */
export async function fetchPermissions(): Promise<Permission[]> {
  const response = await apiClient.get<{ permissions: Permission[] }>('/api/portal/permissions');
  return response.data.permissions;
}

/**
 * Create custom role (TENANT_ADMIN only)
 */
export async function createRole(data: {
  name: string;
  display_name: string;
  description?: string;
  permission_ids: number[];
}): Promise<Role> {
  const response = await apiClient.post<Role>(BASE_URL, data);
  return response.data;
}

/**
 * Update custom role (TENANT_ADMIN only)
 */
export async function updateRole(
  id: number,
  data: {
    display_name?: string;
    description?: string;
    permission_ids?: number[];
  }
): Promise<Role> {
  const response = await apiClient.put<Role>(`${BASE_URL}/${id}`, data);
  return response.data;
}

/**
 * Delete custom role (TENANT_ADMIN only)
 */
export async function deleteRole(id: number): Promise<void> {
  await apiClient.delete(`${BASE_URL}/${id}`);
}
