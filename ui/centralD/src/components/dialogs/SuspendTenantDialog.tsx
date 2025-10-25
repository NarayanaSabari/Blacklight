/**
 * Suspend Tenant Dialog
 * Confirmation dialog for suspending a tenant
 */

import { useState } from 'react';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertTriangle, Loader2 } from 'lucide-react';
import type { Tenant } from '@/types';

interface SuspendTenantDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  tenant: Tenant;
  onConfirm: (reason: string) => Promise<void>;
  isSuspending?: boolean;
}

export function SuspendTenantDialog({
  open,
  onOpenChange,
  tenant,
  onConfirm,
  isSuspending,
}: SuspendTenantDialogProps) {
  const [reason, setReason] = useState('');

  const isValid = reason.trim().length > 0;

  const handleConfirm = async () => {
    if (isValid) {
      await onConfirm(reason);
      // Reset state
      setReason('');
    }
  };

  const handleCancel = () => {
    // Reset state
    setReason('');
    onOpenChange(false);
  };

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent className="max-w-2xl">
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-warning" />
            Suspend Tenant - {tenant.name}
          </AlertDialogTitle>
          <AlertDialogDescription className="space-y-4 pt-4">
            <Alert>
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                <div className="font-semibold mb-2">This will suspend the tenant</div>
                <div className="space-y-1 text-sm">
                  <div>• All portal users will lose access immediately</div>
                  <div>• The tenant can be reactivated later</div>
                  <div>• No data will be deleted</div>
                  <div>• Subscription billing will continue</div>
                </div>
              </AlertDescription>
            </Alert>

            <div className="space-y-2">
              <Label htmlFor="suspend-reason">Reason for Suspension *</Label>
              <Textarea
                id="suspend-reason"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Explain why this tenant is being suspended (e.g., payment failure, policy violation, customer request)..."
                rows={4}
                disabled={isSuspending}
              />
              <p className="text-xs text-muted-foreground">
                Minimum 10 characters. This will be logged for audit purposes and shown to the tenant.
              </p>
            </div>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel onClick={handleCancel} disabled={isSuspending}>
            Cancel
          </AlertDialogCancel>
          <AlertDialogAction
            onClick={handleConfirm}
            disabled={!isValid || isSuspending}
            className="bg-warning text-warning-foreground hover:bg-warning/90"
          >
            {isSuspending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Suspend Tenant
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
