/**
 * Page exports
 * Centralized exports for all pages
 */

// Auth
export { LoginPage } from './auth/LoginPage';

// Dashboard
export { DashboardPage } from './dashboard/DashboardPage';

// Candidates
export { CandidateDetailPage } from './candidates/CandidateDetailPage';
export { AddCandidatePage } from './candidates/AddCandidatePage';
export { EditCandidatePage } from './candidates/EditCandidatePage';
export { CandidateManagementPage } from './candidates/CandidateManagementPage';

// Jobs
export { TeamJobsPage } from './jobs/TeamJobsPage';
export { JobDetailPage } from './jobs/JobDetailPage';
export { EmailJobsPage } from './jobs/EmailJobsPage';
export { AllJobsPage } from './jobs/AllJobsPage';
export { ResumeTailorPage } from './jobs/ResumeTailorPage';

// Settings & Admin
export { UsersPage } from './settings/UsersPage';
export { RolesPage } from './settings/RolesPage';
export { SettingsPage } from './settings/SettingsPage';
export { default as DocumentsPage } from './settings/DocumentsPage';

// Invitations
export { default as InvitationDetailsPage } from './invitations/InvitationDetailsPage';
export { default as InvitationReviewPage } from './invitations/InvitationReviewPage';

// Submissions
export { SubmissionsPage } from './submissions/SubmissionsPage';
export { SubmissionDetailPage } from './submissions/SubmissionDetailPage';

// Public Pages
export { default as OnboardingPage } from './public/OnboardingPage';
