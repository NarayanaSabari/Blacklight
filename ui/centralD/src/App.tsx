/**
 * Main Application Component with Routing
 */

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { Toaster } from '@/components/ui/sonner';
import { PMAdminAuthProvider } from '@/contexts/PMAdminAuthContext';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { AppLayout } from '@/components/layout/AppLayout';
import { LoginPage } from '@/pages/LoginPage';
import { 
  DashboardLayout, 
  OverviewPage, 
  ScraperPage, 
  ApiKeysPage, 
  JobsOverviewPage, 
  QueuePage, 
  PlatformsPage 
} from '@/pages/Dashboard';
import { TenantsPage } from '@/pages/TenantsPage';
import { CreateTenantPage } from '@/pages/CreateTenantPage';
import { TenantDetailPage } from '@/pages/TenantDetailPage';
import { PlansPage } from '@/pages/PlansPage';
import { ProfilePage } from '@/pages/ProfilePage';
import { AdminsPage } from '@/pages/AdminsPage';
import { JobsPage } from '@/pages/JobsPage';
import { SessionDetailPage } from '@/pages/SessionDetailPage';
import { 
  CredentialsLayout, 
  LinkedInCredentialsPage, 
  GlassdoorCredentialsPage, 
  TechfetchCredentialsPage 
} from '@/pages/Credentials';
import { env } from '@/lib/env';

// Create React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter basename={env.basePath}>
        <PMAdminAuthProvider>
          <Routes>
            {/* Public routes */}
            <Route path="/login" element={<LoginPage />} />

            {/* Protected routes */}
            <Route element={<ProtectedRoute />}>
              <Route element={<AppLayout />}>
                <Route path="/" element={<Navigate to="/dashboard" replace />} />
                
                {/* Dashboard with nested sub-routes */}
                <Route path="/dashboard" element={<DashboardLayout />}>
                  <Route index element={<OverviewPage />} />
                  <Route path="scraper" element={<ScraperPage />} />
                  <Route path="api-keys" element={<ApiKeysPage />} />
                  <Route path="jobs" element={<JobsOverviewPage />} />
                  <Route path="queue" element={<QueuePage />} />
                  <Route path="platforms" element={<PlatformsPage />} />
                </Route>
                <Route path="/tenants" element={<TenantsPage />} />
                <Route path="/tenants/new" element={<CreateTenantPage />} />
                <Route path="/tenants/:slug" element={<TenantDetailPage />} />
                <Route path="/plans" element={<PlansPage />} />
                <Route path="/profile" element={<ProfilePage />} />
                <Route path="/admins" element={<AdminsPage />} />
                <Route path="/jobs" element={<JobsPage />} />
                <Route path="/credentials" element={<CredentialsLayout />}>
                  <Route index element={<Navigate to="/credentials/linkedin" replace />} />
                  <Route path="linkedin" element={<LinkedInCredentialsPage />} />
                  <Route path="glassdoor" element={<GlassdoorCredentialsPage />} />
                  <Route path="techfetch" element={<TechfetchCredentialsPage />} />
                </Route>
                <Route path="/sessions/:sessionId" element={<SessionDetailPage />} />
              </Route>
            </Route>
          </Routes>

          {/* Toast notifications */}
          <Toaster position="top-right" />
        </PMAdminAuthProvider>
      </BrowserRouter>

      {/* React Query Devtools (only in development) */}
      {env.enableQueryDevtools && <ReactQueryDevtools initialIsOpen={false} />}
    </QueryClientProvider>
  );
}

export default App;
