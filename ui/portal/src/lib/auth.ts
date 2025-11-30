/**
 * Authentication Utilities
 * Handles login, logout, and token management
 */

import { apiRequest, tokenManager } from './api-client';
import { env } from '@/lib/env';

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  user: {
    id: number;
    email: string;
    full_name: string;
    role: string;
    tenant_id: number;
  };
}

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: string;
  tenant_id: number;
}

/**
 * Login user and store tokens
 */
export async function login(credentials: LoginCredentials): Promise<User> {
  const response = await apiRequest.post<LoginResponse>(
    '/api/auth/login',
    credentials
  );

  // Store tokens
  tokenManager.setTokens(response.access_token, response.refresh_token);

  // Store user info
  localStorage.setItem('portal_user', JSON.stringify(response.user));

  return response.user;
}

/**
 * Logout user and clear tokens
 */
export async function logout(): Promise<void> {
  try {
    // Call logout endpoint (optional - backend can invalidate refresh token)
    await apiRequest.post('/api/auth/logout');
  } catch (error) {
    console.error('Logout error:', error);
  } finally {
    // Always clear local storage
    tokenManager.clearTokens();
    
    // Redirect to login with basePath
    const loginPath = `${env.basePath}/login`;
    window.location.href = loginPath;
  }
}

/**
 * Get current user from localStorage
 */
export function getCurrentUser(): User | null {
  const userJson = localStorage.getItem('portal_user');
  if (!userJson) return null;

  try {
    return JSON.parse(userJson) as User;
  } catch {
    return null;
  }
}

/**
 * Check if user is authenticated
 */
export function isAuthenticated(): boolean {
  return tokenManager.isAuthenticated();
}

/**
 * Refresh authentication tokens
 */
export async function refreshAuth(): Promise<void> {
  // This is handled automatically by the apiClient interceptor
  // But you can call this manually if needed
  const refreshToken = tokenManager.getRefreshToken();
  
  if (!refreshToken) {
    throw new Error('No refresh token available');
  }

  const response = await apiRequest.post<LoginResponse>(
    '/api/auth/refresh',
    { refresh_token: refreshToken }
  );

  tokenManager.setTokens(response.access_token, response.refresh_token);
}

export { tokenManager };
