/**
 * Queue Page
 * Full page view for scraper queue management
 * Combines RoleQueueTable and UnifiedRoleQueue
 */

import { RoleQueueTable, UnifiedRoleQueue } from '../components';

export function QueuePage() {
  return (
    <div className="space-y-6">
      <RoleQueueTable />
      <UnifiedRoleQueue />
    </div>
  );
}

export default QueuePage;
