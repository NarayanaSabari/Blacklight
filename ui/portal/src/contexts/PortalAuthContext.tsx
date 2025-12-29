/**
 * Portal Authentication Context
 * Manages Portal user authentication state and tenant information
 */

import React, { createContext, useContext, useState, useEffect } from 'react';
import { apiClient, getErrorMessage } from '@/lib/api-client';
import type { PortalUser, LoginRequest, LoginResponse } from '@/types';

interface PortalAuthContextType {
  user: PortalUser | null;
  tenantName: string | null;
  tenantSlug: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  accessToken: string | null;
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => Promise<void>;
  error: string | null;
}

const PortalAuthContext = createContext<PortalAuthContextType | undefined>(undefined);

export function PortalAuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<PortalUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);

  // Derived state from user
  const isAuthenticated = user !== null;
  const tenantName = user?.tenant?.name || null;
  const tenantSlug = user?.tenant?.slug || null;

  /**
   * Check authentication status on mount
   */
  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      const token = localStorage.getItem('portal_access_token');
      const storedUser = localStorage.getItem('portal_user');

      if (!token || !storedUser) {
        setIsLoading(false);
        setAccessToken(null);
        return;
      }

      // Parse stored user
      const parsedUser = JSON.parse(storedUser) as PortalUser;
      setUser(parsedUser);
      setAccessToken(token);
      
      // Optionally validate token with backend
      // For now, we'll just trust the stored token until it expires
      
    } catch (err) {
      console.error('Auth check failed:', err);
      localStorage.removeItem('portal_access_token');
      localStorage.removeItem('portal_refresh_token');
      localStorage.removeItem('portal_user');
      setAccessToken(null);
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (credentials: LoginRequest) => {
    try {
      setError(null);
      setIsLoading(true);

      const response = await apiClient.post<LoginResponse>(
        '/api/portal/auth/login',
        credentials
      );

      const { access_token, refresh_token, user: userData } = response.data;

      // Store tokens
      localStorage.setItem('portal_access_token', access_token);
      localStorage.setItem('portal_refresh_token', refresh_token);
      localStorage.setItem('portal_user', JSON.stringify(userData));

      setUser(userData);
      setAccessToken(access_token);
      
    } catch (err) {
      const errorMessage = getErrorMessage(err);
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    try {
      setIsLoading(true);
      
      // Call logout endpoint (optional - backend will blacklist token)
      await apiClient.post('/api/portal/auth/logout');
      
    } catch (err) {
      console.error('Logout error:', err);
    } finally {
      // Clear state regardless of API call success
      localStorage.removeItem('portal_access_token');
      localStorage.removeItem('portal_refresh_token');
      localStorage.removeItem('portal_user');
      setUser(null);
      setError(null);
      setAccessToken(null);
      setIsLoading(false);
    }
  };

  return (
    <PortalAuthContext.Provider
      value={{
        user,
        tenantName,
        tenantSlug,
        isAuthenticated,
        isLoading,
        accessToken,
        login,
        logout,
        error,
      }}
    >
      {children}
    </PortalAuthContext.Provider>
  );
}

/**
 * Hook to use Portal auth context
 */
export function usePortalAuth() {
  const context = useContext(PortalAuthContext);
  if (context === undefined) {
    throw new Error('usePortalAuth must be used within a PortalAuthProvider');
  }
  return context;
}
