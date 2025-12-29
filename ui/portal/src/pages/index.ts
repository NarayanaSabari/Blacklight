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
export { YourCandidatesPage } from './candidates/YourCandidatesPage';
export { YourCandidatesPageNew } from './candidates/YourCandidatesPageNew';
export { KanbanBoardPage } from './candidates/KanbanBoardPage';

// Jobs
export { JobsPage } from './jobs/JobsPage';
export { JobDetailPage } from './jobs/JobDetailPage';
export { EmailJobsPage } from './jobs/EmailJobsPage';
export { ResumeTailorPage } from './jobs/ResumeTailorPage';

// Settings & Admin
export { UsersPage } from './settings/UsersPage';
export { RolesPage } from './settings/RolesPage';
export { SettingsPage } from './settings/SettingsPage';
export { default as DocumentsPage } from './settings/DocumentsPage';

// Invitations
export { default as InvitationDetailsPage } from './invitations/InvitationDetailsPage';
export { default as InvitationReviewPage } from './invitations/InvitationReviewPage';

// Public Pages
export { default as OnboardingPage } from './public/OnboardingPage';
