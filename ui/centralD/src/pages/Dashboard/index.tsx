/**
 * Dashboard Page
 * Main dashboard for PM_ADMIN to monitor job matching system
 */

import { 
  StatsCards, 
  ScraperMonitoring, 
  RoleQueueTable, 
  ApiKeysManager,
  JobsPreview 
} from './components';

export function DashboardPage() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Job matching system monitoring and management
        </p>
      </div>

      {/* Stats Cards */}
      <StatsCards />

      {/* Main Content Grid */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Left Column */}
        <div className="space-y-6">
          <ScraperMonitoring />
          <JobsPreview />
        </div>

        {/* Right Column */}
        <div className="space-y-6">
          <ApiKeysManager />
        </div>
      </div>

      {/* Role Queue Table - Full Width */}
      <RoleQueueTable />
    </div>
  );
}

export default DashboardPage;
