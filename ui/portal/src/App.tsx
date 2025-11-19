import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { PortalAuthProvider, usePortalAuth } from '@/contexts/PortalAuthContext';
import { Toaster } from '@/components/ui/sonner';
import { Layout } from '@/components/Layout';
import { LoginPage } from '@/pages/LoginPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { CandidatesPage } from '@/pages/CandidatesPage';
import { AddCandidatePage } from '@/pages/AddCandidatePage';
import { EditCandidatePage } from '@/pages/EditCandidatePage';
import { CandidateDetailPage } from '@/pages/CandidateDetailPage';
import { CandidateMatchesPage } from '@/pages/CandidateMatchesPage';
import { JobDetailPage } from '@/pages/JobDetailPage';
import { JobsPage } from '@/pages/JobsPage';
import { ApplicationsPage } from '@/pages/ApplicationsPage';
import { InterviewsPage } from '@/pages/InterviewsPage';
import { UsersPage } from '@/pages/UsersPage';
import { SettingsPage } from '@/pages/SettingsPage';
import { InvitationDetailsPage, OnboardingPage } from '@/pages';
import InvitationReviewPage from '@/pages/invitations/InvitationReviewPage';
import DocumentsPage from '@/pages/DocumentsPage';
import { RolesPage } from '@/pages/RolesPage';
import { ManageTeamPage, YourCandidatesPageNew, CandidateManagementPage } from '@/pages';
import { Loader2 } from 'lucide-react';
import './App.css';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

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
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <PortalAuthProvider>
          <Routes>
            {/* Public Routes */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/onboard/:token" element={<OnboardingPage />} />

          {/* Protected Routes with Layout */}
          <Route
            path="/*"
            element={
              <ProtectedRoute>
                <Layout>
                  <Routes>
                    <Route path="/dashboard" element={<DashboardPage />} />
                    {/* Unified Candidate Management (combines candidates, onboarding, invitations) */}
                    <Route path="/candidate-management" element={<CandidateManagementPage />} />
                    {/* Legacy routes - redirect to unified page with tab param */}
                    <Route path="/candidates" element={<Navigate to="/candidate-management?tab=candidates" replace />} />
                    <Route path="/onboard-candidates" element={<Navigate to="/candidate-management?tab=onboarding" replace />} />
                    <Route path="/invitations" element={<Navigate to="/candidate-management?tab=invitations" replace />} />
                    {/* Candidate detail routes */}
                    <Route path="/candidates/new" element={<AddCandidatePage />} />
                    <Route path="/candidates/:id/edit" element={<EditCandidatePage />} />
                    <Route path="/candidates/:candidateId/matches" element={<CandidateMatchesPage />} />
                    <Route path="/candidates/:candidateId/matches/jobs/:jobId" element={<JobDetailPage />} />
                    <Route path="/candidates/:id" element={<CandidateDetailPage />} />
                    <Route path="/invitations/:id" element={<InvitationDetailsPage />} />
                    <Route path="/invitations/:id/review" element={<InvitationReviewPage />} />
                    <Route path="/jobs" element={<JobsPage />} />
                    <Route path="/applications" element={<ApplicationsPage />} />
                    <Route path="/interviews" element={<InterviewsPage />} />
                    <Route path="/documents" element={<DocumentsPage />} />
                    <Route path="/users" element={<UsersPage />} />
                    <Route path="/users/roles" element={<RolesPage />} />
                    <Route path="/manage-team" element={<ManageTeamPage />} />
                    <Route path="/your-candidates" element={<YourCandidatesPageNew />} />
                    <Route path="/settings" element={<SettingsPage />} />
                    <Route path="/" element={<Navigate to="/dashboard" replace />} />
                    <Route path="*" element={<Navigate to="/dashboard" replace />} />
                  </Routes>
                </Layout>
              </ProtectedRoute>
            }
          />
          </Routes>
          <Toaster />
        </PortalAuthProvider>
      </BrowserRouter>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}

export default App;

