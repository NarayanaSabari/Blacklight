/**
 * Protected Route component
 * Redirects to login if user is not authenticated
 */

import { Navigate, Outlet } from 'react-router-dom';
import { usePMAdminAuth } from '@/hooks/usePMAdminAuth';

export function ProtectedRoute() {
  const { isAuthenticated, isLoading } = usePMAdminAuth();

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <p className="mt-4 text-sm text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
