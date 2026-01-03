import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { PortalAuthProvider, usePortalAuth } from '@/contexts/PortalAuthContext';
import { Toaster } from '@/components/ui/sonner';
import { Layout } from '@/components/Layout';
import { Loader2 } from 'lucide-react';
import { env } from '@/lib/env';
import './App.css';

// Page imports from centralized index
import {
  LoginPage,
  DashboardPage,
  AddCandidatePage,
  EditCandidatePage,
  CandidateDetailPage,
  CandidateManagementPage,
  TeamJobsPage,
  JobDetailPage,
  AllJobsPage,
  ResumeTailorPage,
  RolesPage,
  SettingsPage,
  DocumentsPage,
  InvitationDetailsPage,
  InvitationReviewPage,
  OnboardingPage,
  SubmissionsPage,
  SubmissionDetailPage,
} from '@/pages';

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
      <BrowserRouter basename={env.basePath}>
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
                      <Route path="/invitations" element={<Navigate to="/candidate-management?tab=email-invitations" replace />} />
                      {/* Candidate detail routes */}
                      <Route path="/candidates/new" element={<AddCandidatePage />} />
                      <Route path="/candidates/:id/edit" element={<EditCandidatePage />} />
                      <Route path="/candidates/:id" element={<CandidateDetailPage />} />
                      <Route path="/invitations/:id" element={<InvitationDetailsPage />} />
                      <Route path="/invitations/:id/review" element={<InvitationReviewPage />} />
                      {/* Candidate job routes - now uses TeamJobsPage with role-based UI */}
                      <Route path="/candidate/jobs/:candidateId" element={<TeamJobsPage />} />
                      <Route path="/candidate/jobs/:candidateId/job/:jobId" element={<JobDetailPage />} />
                      <Route path="/candidate/jobs/:candidateId/job/:jobId/tailor/:matchId" element={<ResumeTailorPage />} />
                      {/* General job routes - redirects to team jobs page */}
                      <Route path="/jobs/:jobId" element={<JobDetailPage />} />
                      <Route path="/jobs" element={<TeamJobsPage />} />
                      <Route path="/documents" element={<DocumentsPage />} />
                      <Route path="/users" element={<Navigate to="/settings/team" replace />} />
                      <Route path="/users/roles" element={<RolesPage />} />
                      <Route path="/manage-team" element={<Navigate to="/settings/team" replace />} />
                      {/* Legacy route - redirect to new jobs page */}
                      <Route path="/your-candidates" element={<Navigate to="/jobs" replace />} />
                      {/* All Jobs Browser - unified view of scraped + email jobs */}
                      <Route path="/all-jobs" element={<AllJobsPage />} />
                      {/* Email jobs - redirect to all-jobs with email filter */}
                      <Route path="/email-jobs" element={<Navigate to="/all-jobs?source=email" replace />} />
                      <Route path="/email-jobs/:jobId" element={<JobDetailPage />} />
                      <Route path="/submissions" element={<SubmissionsPage />} />
                      <Route path="/submissions/:id" element={<SubmissionDetailPage />} />
                      <Route path="/settings" element={<SettingsPage />} />
                      <Route path="/settings/:tab" element={<SettingsPage />} />
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

