/**
 * PM Admin Authentication Context
 * Provides authentication state and methods for the Central Dashboard
 */

import { createContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';
import { apiClient } from '@/lib/api-client';
import type { PMAdmin, PMAdminLoginRequest } from '@/types';

interface PMAdminAuthContextValue {
  currentAdmin: PMAdmin | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: PMAdminLoginRequest) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
}

const PMAdminAuthContext = createContext<PMAdminAuthContextValue | undefined>(undefined);

// Export context for use in custom hook
export { PMAdminAuthContext };

interface PMAdminAuthProviderProps {
  children: ReactNode;
}

export function PMAdminAuthProvider({ children }: PMAdminAuthProviderProps) {
  const [currentAdmin, setCurrentAdmin] = useState<PMAdmin | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Initialize auth state on mount
  useEffect(() => {
    checkAuthStatus();
  }, []);

  // Check if user is authenticated by fetching current admin
  const checkAuthStatus = async () => {
    try {
      const response = await apiClient.get('/api/pm-admin/current');
      setCurrentAdmin(response.data);
    } catch {
      setCurrentAdmin(null);
      localStorage.removeItem('pm_admin_token');
    } finally {
      setIsLoading(false);
    }
  };

  // Login with email and password
  const login = async (credentials: PMAdminLoginRequest) => {
    const response = await apiClient.post('/api/pm-admin/auth/login', credentials);
    
    // Store access token in localStorage
    if (response.data.access_token) {
      localStorage.setItem('pm_admin_token', response.data.access_token);
    }
    
    setCurrentAdmin(response.data.admin);
  };

  // Logout and clear auth state
  const logout = async () => {
    try {
      await apiClient.post('/api/pm-admin/auth/logout');
    } finally {
      setCurrentAdmin(null);
      localStorage.removeItem('pm_admin_token');
    }
  };

  // Refresh access token
  const refreshToken = async () => {
    try {
      await apiClient.post('/api/pm-admin/auth/refresh');
      await checkAuthStatus();
    } catch (error) {
      setCurrentAdmin(null);
      throw error;
    }
  };

  const value: PMAdminAuthContextValue = {
    currentAdmin,
    isAuthenticated: !!currentAdmin,
    isLoading,
    login,
    logout,
    refreshToken,
  };

  return (
    <PMAdminAuthContext.Provider value={value}>
      {children}
    </PMAdminAuthContext.Provider>
  );
}
