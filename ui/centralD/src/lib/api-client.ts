/**
 * Axios API Client Configuration
 * Handles authentication, interceptors, and base configuration
 */

import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios';
import { env } from '@/lib/env';

// Create axios instance
export const apiClient = axios.create({
  baseURL: env.apiBaseUrl,
  timeout: env.apiTimeout,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Enable httpOnly cookies
});

// Request interceptor - Add auth token from localStorage as fallback
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Token will be in httpOnly cookie, but we can add Authorization header as fallback
    const token = localStorage.getItem('pm_admin_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Build login path with basePath
const getLoginPath = () => `${env.basePath}/login`;

// Response interceptor - Handle errors globally
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const loginPath = getLoginPath();
    // Handle authentication errors
    if (error.response?.status === 401) {
      // Clear auth state
      localStorage.removeItem('pm_admin_token');
      // Redirect to login if not already there
      if (!window.location.pathname.endsWith('/login')) {
        window.location.href = loginPath;
      }
    }

    // Handle forbidden errors
    if (error.response?.status === 403) {
      console.error('Access forbidden:', error.response.data);
    }

    // Handle server errors
    if (error.response?.status && error.response.status >= 500) {
      console.error('Server error:', error.response.data);
    }

    return Promise.reject(error);
  }
);

/**
 * Helper function to extract error message from API response
 */
export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as { message?: string; error?: string };
    return data?.message || data?.error || error.message || 'An error occurred';
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'An unknown error occurred';
}

export default apiClient;
