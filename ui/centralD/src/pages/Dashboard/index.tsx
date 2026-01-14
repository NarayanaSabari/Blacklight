/**
 * Dashboard Module Exports
 * Exports dashboard layout and all sub-route page components
 */

// Layout
export { DashboardLayout } from './DashboardLayout';

// Pages
export { 
  OverviewPage, 
  ScraperPage, 
  ApiKeysPage, 
  JobsOverviewPage, 
  QueuePage, 
  PlatformsPage,
  ActiveSessionsPage,
  RecentActivityPage,
  LocationAnalyticsPage
} from './pages';

// Legacy export for backwards compatibility (can be removed once App.tsx is updated)
export { DashboardLayout as DashboardPage } from './DashboardLayout';
