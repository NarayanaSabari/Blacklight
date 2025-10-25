/**
 * Danger Zone Component
 * Contains dangerous actions like suspend and delete
 */

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { AlertTriangle, Ban, Trash2, PlayCircle } from 'lucide-react';
import type { Tenant } from '@/types';

interface DangerZoneProps {
  tenant: Tenant;
  onSuspend: () => void;
  onActivate: () => void;
  onDelete: () => void;
}

export function DangerZone({ tenant, onSuspend, onActivate, onDelete }: DangerZoneProps) {
  const isSuspended = tenant.status === 'SUSPENDED';
  const isActive = tenant.status === 'ACTIVE';

  return (
    <Card className="border-destructive/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-destructive">
          <AlertTriangle className="h-5 w-5" />
          Danger Zone
        </CardTitle>
        <CardDescription>
          Irreversible and dangerous actions. Proceed with caution.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {isActive && (
          <div className="flex items-start justify-between p-4 border border-warning/50 rounded-lg bg-warning/5">
            <div className="space-y-1 flex-1">
              <div className="font-medium">Suspend Tenant</div>
              <div className="text-sm text-muted-foreground">
                Temporarily disable access for all users. The tenant can be reactivated later.
              </div>
            </div>
            <Button variant="outline" onClick={onSuspend} className="ml-4">
              <Ban className="mr-2 h-4 w-4" />
              Suspend
            </Button>
          </div>
        )}

        {isSuspended && (
          <div className="flex items-start justify-between p-4 border border-green-500/50 rounded-lg bg-green-500/5">
            <div className="space-y-1 flex-1">
              <div className="font-medium">Activate Tenant</div>
              <div className="text-sm text-muted-foreground">
                Restore access for all users. The tenant will become active immediately.
              </div>
            </div>
            <Button variant="outline" onClick={onActivate} className="ml-4">
              <PlayCircle className="mr-2 h-4 w-4" />
              Activate
            </Button>
          </div>
        )}

        <div className="flex items-start justify-between p-4 border border-destructive/50 rounded-lg bg-destructive/5">
          <div className="space-y-1 flex-1">
            <div className="font-medium text-destructive">Delete Tenant</div>
            <div className="text-sm text-muted-foreground">
              Permanently delete this tenant and all associated data. This action cannot be undone.
            </div>
          </div>
          <Button variant="destructive" onClick={onDelete} className="ml-4">
            <Trash2 className="mr-2 h-4 w-4" />
            Delete
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
