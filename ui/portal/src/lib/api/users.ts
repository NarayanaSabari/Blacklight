/**
 * Users API Functions
 */

import { apiClient } from '@/lib/api-client';
import type {
  PortalUserFull,
  UserCreateRequest,
  UserUpdateRequest,
  UserListResponse,
  ResetPasswordRequest,
  FilterParams,
} from '@/types';

const BASE_URL = '/api/portal/users';

/**
 * Get all users with pagination and filters
 */
export async function fetchUsers(params?: FilterParams): Promise<UserListResponse> {
  const response = await apiClient.get<UserListResponse>(BASE_URL, { params });
  return response.data;
}

/**
 * Get single user by ID
 */
export async function fetchUser(id: number): Promise<PortalUserFull> {
  const response = await apiClient.get<PortalUserFull>(`${BASE_URL}/${id}`);
  return response.data;
}

/**
 * Create new user (TENANT_ADMIN only)
 */
export async function createUser(data: UserCreateRequest): Promise<PortalUserFull> {
  const response = await apiClient.post<PortalUserFull>(BASE_URL, data);
  return response.data;
}

/**
 * Update existing user
 */
export async function updateUser(id: number, data: UserUpdateRequest): Promise<PortalUserFull> {
  const response = await apiClient.put<PortalUserFull>(`${BASE_URL}/${id}`, data);
  return response.data;
}

/**
 * Delete user (TENANT_ADMIN only)
 */
export async function deleteUser(id: number): Promise<void> {
  await apiClient.delete(`${BASE_URL}/${id}`);
}

/**
 * Reset user password (TENANT_ADMIN only)
 */
export async function resetUserPassword(id: number, data: ResetPasswordRequest): Promise<void> {
  await apiClient.post(`${BASE_URL}/${id}/reset-password`, data);
}

/**
 * Activate/deactivate user (TENANT_ADMIN only)
 */
export async function toggleUserActive(id: number, isActive: boolean): Promise<PortalUserFull> {
  const response = await apiClient.patch<PortalUserFull>(`${BASE_URL}/${id}/status`, { is_active: isActive });
  return response.data;
}

/**
 * Get current user profile
 */
export async function fetchCurrentUser(): Promise<PortalUserFull> {
  const response = await apiClient.get<PortalUserFull>('/api/portal/auth/me');
  return response.data;
}

/**
 * Update current user profile
 */
export async function updateCurrentUser(data: {
  first_name?: string;
  last_name?: string;
  phone?: string;
}): Promise<PortalUserFull> {
  const response = await apiClient.put<PortalUserFull>('/api/portal/auth/me', data);
  return response.data;
}

/**
 * Change current user password
 */
export async function changeCurrentUserPassword(data: {
  current_password: string;
  new_password: string;
}): Promise<void> {
  await apiClient.post('/api/portal/auth/change-password', data);
}
