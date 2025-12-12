/**
 * Dashboard Page
 * Main dashboard for PM_ADMIN to monitor job matching system
 * Features 5 tabs: Overview, Scraper Monitoring, API Keys, Jobs Overview, Role Queue, Scraper Queue
 */

import { 
  StatsCards, 
  ScraperMonitoring, 
  RoleQueueTable, 
  ApiKeysManager,
  JobsPreview,
  GlobalRolesQueue
} from './components';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { 
  LayoutDashboard, 
  Activity, 
  Key, 
  Briefcase, 
  Tags
} from "lucide-react";

export function DashboardPage() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="space-y-2">
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Job matching system monitoring and management
        </p>
      </div>

      {/* Stats Cards - Always visible */}
      <StatsCards />

      {/* Tabbed Content */}
      <Tabs defaultValue="overview" className="space-y-6">
        <TabsList className="inline-flex h-11 items-center justify-center rounded-md bg-muted p-1 text-muted-foreground w-full max-w-full overflow-x-auto">
          <TabsTrigger value="overview" className="flex items-center gap-2 px-4">
            <LayoutDashboard className="h-4 w-4" />
            <span>Overview</span>
          </TabsTrigger>
          <TabsTrigger value="scraper" className="flex items-center gap-2 px-4">
            <Activity className="h-4 w-4" />
            <span>Scraper Monitoring</span>
          </TabsTrigger>
          <TabsTrigger value="api-keys" className="flex items-center gap-2 px-4">
            <Key className="h-4 w-4" />
            <span>API Keys</span>
          </TabsTrigger>
          <TabsTrigger value="jobs" className="flex items-center gap-2 px-4">
            <Briefcase className="h-4 w-4" />
            <span>Jobs Overview</span>
          </TabsTrigger>
          <TabsTrigger value="role-queue" className="flex items-center gap-2 px-4">
            <Tags className="h-4 w-4" />
            <span>Role Queue</span>
          </TabsTrigger>
        </TabsList>

        {/* Tab 1: Overview - Combined view */}
        <TabsContent value="overview" className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-2">
            <ScraperMonitoring />
            <ApiKeysManager />
          </div>
          <div className="grid gap-6 lg:grid-cols-2">
            <JobsPreview />
            <RoleQueueTable />
          </div>
        </TabsContent>

        {/* Tab 2: Scraper Monitoring */}
        <TabsContent value="scraper" className="space-y-6">
          <ScraperMonitoring />
        </TabsContent>

        {/* Tab 3: API Keys Management */}
        <TabsContent value="api-keys" className="space-y-6">
          <ApiKeysManager />
        </TabsContent>

        {/* Tab 4: Jobs Overview */}
        <TabsContent value="jobs" className="space-y-6">
          <JobsPreview />
        </TabsContent>

        {/* Tab 5: Role Queue (Pending Review) */}
        <TabsContent value="role-queue" className="space-y-6">
          <RoleQueueTable />
          {/* Global Roles Queue - All roles with status */}
          <GlobalRolesQueue />
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default DashboardPage;
