/**
 * Universal API Client for Portal
 * Handles authentication, token refresh, interceptors, and error handling
 */

import axios, { AxiosError } from 'axios';
import type { InternalAxiosRequestConfig, AxiosRequestConfig } from 'axios';
import { env } from '@/lib/env';

// Token storage keys (consistent across app)
const TOKEN_KEYS = {
  ACCESS_TOKEN: 'portal_access_token',
  REFRESH_TOKEN: 'portal_refresh_token',
  USER: 'portal_user',
} as const;

// Create axios instance
export const apiClient = axios.create({
  baseURL: env.apiBaseUrl,
  timeout: env.apiTimeout,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Enable httpOnly cookies
});

// Flag to prevent multiple refresh attempts
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value?: unknown) => void;
  reject: (reason?: unknown) => void;
}> = [];

// Process queued requests after token refresh
const processQueue = (error: Error | null, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

/**
 * Token Management
 */
export const tokenManager = {
  getAccessToken: (): string | null => {
    return localStorage.getItem(TOKEN_KEYS.ACCESS_TOKEN);
  },

  getRefreshToken: (): string | null => {
    return localStorage.getItem(TOKEN_KEYS.REFRESH_TOKEN);
  },

  setTokens: (accessToken: string, refreshToken: string) => {
    localStorage.setItem(TOKEN_KEYS.ACCESS_TOKEN, accessToken);
    localStorage.setItem(TOKEN_KEYS.REFRESH_TOKEN, refreshToken);
  },

  clearTokens: () => {
    localStorage.removeItem(TOKEN_KEYS.ACCESS_TOKEN);
    localStorage.removeItem(TOKEN_KEYS.REFRESH_TOKEN);
    localStorage.removeItem(TOKEN_KEYS.USER);
  },

  isAuthenticated: (): boolean => {
    return !!tokenManager.getAccessToken();
  },
};

/**
 * Refresh access token using refresh token
 */
const refreshAccessToken = async (): Promise<string> => {
  const refreshToken = tokenManager.getRefreshToken();
  
  if (!refreshToken) {
    throw new Error('No refresh token available');
  }

  try {
    const response = await axios.post(
      `${env.apiBaseUrl}/api/auth/refresh`,
      { refresh_token: refreshToken },
      { withCredentials: true }
    );

    const { access_token, refresh_token } = response.data;
    tokenManager.setTokens(access_token, refresh_token);
    
    return access_token;
  } catch (error) {
    tokenManager.clearTokens();
    throw error;
  }
};

// Request interceptor - Add auth token
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = tokenManager.getAccessToken();
    
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor - Handle errors and token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    // Handle 401 Unauthorized
    if (error.response?.status === 401 && !originalRequest._retry) {
      // Prevent retry if already refreshing or no refresh token
      if (isRefreshing) {
        // Queue this request
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${token}`;
            }
            return apiClient(originalRequest);
          })
          .catch((err) => {
            return Promise.reject(err);
          });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const newToken = await refreshAccessToken();
        processQueue(null, newToken);
        
        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
        }
        
        return apiClient(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError as Error, null);
        tokenManager.clearTokens();
        
        // Redirect to login if not already there
        const loginPath = `${env.basePath}/login`;
        if (!window.location.pathname.endsWith('/login')) {
          window.location.href = loginPath;
        }
        
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    // Handle 403 Forbidden
    if (error.response?.status === 403) {
      console.error('Access forbidden:', error.response.data);
      // Could redirect to unauthorized page
    }

    // Handle server errors (5xx)
    if (error.response?.status && error.response.status >= 500) {
      console.error('Server error:', error.response.data);
    }

    return Promise.reject(error);
  }
);

/**
 * Universal API request wrapper
 */
export const apiRequest = {
  /**
   * GET request
   */
  get: <T = unknown>(url: string, config?: AxiosRequestConfig): Promise<T> => {
    return apiClient.get<T>(url, config).then((res) => res.data);
  },

  /**
   * POST request
   */
  post: <T = unknown>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig
  ): Promise<T> => {
    return apiClient.post<T>(url, data, config).then((res) => res.data);
  },

  /**
   * PUT request
   */
  put: <T = unknown>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig
  ): Promise<T> => {
    return apiClient.put<T>(url, data, config).then((res) => res.data);
  },

  /**
   * PATCH request
   */
  patch: <T = unknown>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig
  ): Promise<T> => {
    return apiClient.patch<T>(url, data, config).then((res) => res.data);
  },

  /**
   * DELETE request
   */
  delete: <T = unknown>(url: string, config?: AxiosRequestConfig): Promise<T> => {
    return apiClient.delete<T>(url, config).then((res) => res.data);
  },

  /**
   * POST request with FormData (for file uploads)
   */
  postForm: <T = unknown>(url: string, formData: FormData, config?: AxiosRequestConfig): Promise<T> => {
    return apiClient.post<T>(url, formData, {
      ...config,
      headers: {
        'Content-Type': 'multipart/form-data',
        ...config?.headers,
      },
    }).then((res) => res.data);
  },

  /**
   * GET request for binary data (file downloads)
   */
  getBlob: (url: string, config?: AxiosRequestConfig): Promise<Blob> => {
    return apiClient.get(url, {
      ...config,
      responseType: 'blob',
    }).then((res) => res.data);
  },
};

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

