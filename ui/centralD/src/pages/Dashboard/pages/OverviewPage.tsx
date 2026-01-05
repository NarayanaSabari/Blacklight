/**
 * Overview Page
 * Combined dashboard view with grid layout of main components
 */

import { 
  ScraperMonitoring, 
  ApiKeysManager, 
  JobsPreview, 
  RoleQueueTable 
} from '../components';

export function OverviewPage() {
  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-2">
        <ScraperMonitoring />
        <ApiKeysManager />
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <JobsPreview />
        <RoleQueueTable />
      </div>
    </div>
  );
}

export default OverviewPage;
