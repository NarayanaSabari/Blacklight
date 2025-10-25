import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { PortalAuthProvider, usePortalAuth } from '@/contexts/PortalAuthContext';
import { Layout } from '@/components/Layout';
import { LoginPage } from '@/pages/LoginPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { CandidatesPage } from '@/pages/CandidatesPage';
import { JobsPage } from '@/pages/JobsPage';
import { ApplicationsPage } from '@/pages/ApplicationsPage';
import { InterviewsPage } from '@/pages/InterviewsPage';
import { UsersPage } from '@/pages/UsersPage';
import { SettingsPage } from '@/pages/SettingsPage';
import { Loader2 } from 'lucide-react';
import './App.css';

/**
 * Protected Route Component
 * Redirects to login if not authenticated
 */
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = usePortalAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

function App() {
  return (
    <BrowserRouter>
      <PortalAuthProvider>
        <Routes>
          {/* Public Routes */}
          <Route path="/login" element={<LoginPage />} />

          {/* Protected Routes with Layout */}
          <Route
            path="/*"
            element={
              <ProtectedRoute>
                <Layout>
                  <Routes>
                    <Route path="/dashboard" element={<DashboardPage />} />
                    <Route path="/candidates" element={<CandidatesPage />} />
                    <Route path="/jobs" element={<JobsPage />} />
                    <Route path="/applications" element={<ApplicationsPage />} />
                    <Route path="/interviews" element={<InterviewsPage />} />
                    <Route path="/users" element={<UsersPage />} />
                    <Route path="/settings" element={<SettingsPage />} />
                    <Route path="/" element={<Navigate to="/dashboard" replace />} />
                    <Route path="*" element={<Navigate to="/dashboard" replace />} />
                  </Routes>
                </Layout>
              </ProtectedRoute>
            }
          />
        </Routes>
      </PortalAuthProvider>
    </BrowserRouter>
  );
}

export default App;

