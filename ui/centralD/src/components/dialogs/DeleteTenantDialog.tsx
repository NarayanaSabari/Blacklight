/**
 * Delete Tenant Dialog
 * Confirmation dialog with type-to-confirm for deleting a tenant
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
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertTriangle, Loader2 } from 'lucide-react';
import type { Tenant } from '@/types';

interface DeleteTenantDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  tenant: Tenant;
  onConfirm: (reason: string) => Promise<void>;
  isDeleting?: boolean;
}

export function DeleteTenantDialog({
  open,
  onOpenChange,
  tenant,
  onConfirm,
  isDeleting,
}: DeleteTenantDialogProps) {
  const [confirmText, setConfirmText] = useState('');
  const [reason, setReason] = useState('');
  const [understood, setUnderstood] = useState(false);

  const expectedText = tenant.slug;
  const isConfirmValid = confirmText === expectedText && understood && reason.trim().length > 0;

  const handleConfirm = async () => {
    if (isConfirmValid) {
      await onConfirm(reason);
      // Reset state
      setConfirmText('');
      setReason('');
      setUnderstood(false);
    }
  };

  const handleCancel = () => {
    // Reset state
    setConfirmText('');
    setReason('');
    setUnderstood(false);
    onOpenChange(false);
  };

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent className="max-w-2xl">
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2 text-destructive">
            <AlertTriangle className="h-5 w-5" />
            Delete Tenant - {tenant.name}
          </AlertDialogTitle>
          <AlertDialogDescription className="space-y-4 pt-4">
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                <div className="font-semibold mb-2">This action is permanent and cannot be undone!</div>
                <div className="space-y-1 text-sm">
                  <div>• All tenant data will be permanently deleted</div>
                  <div>• All portal users ({tenant.name}) will be removed</div>
                  <div>• All candidates, jobs, and applications will be lost</div>
                  <div>• This cannot be recovered</div>
                </div>
              </AlertDescription>
            </Alert>

            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="reason">Reason for Deletion *</Label>
                <Textarea
                  id="reason"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="Explain why this tenant is being deleted..."
                  rows={3}
                  disabled={isDeleting}
                />
                <p className="text-xs text-muted-foreground">
                  Minimum 10 characters. This will be logged for audit purposes.
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirm-text">
                  Type <span className="font-mono font-bold">{expectedText}</span> to confirm
                </Label>
                <Input
                  id="confirm-text"
                  value={confirmText}
                  onChange={(e) => setConfirmText(e.target.value)}
                  placeholder={expectedText}
                  disabled={isDeleting}
                  className="font-mono"
                />
              </div>

              <div className="flex items-start space-x-2">
                <Checkbox
                  id="understood"
                  checked={understood}
                  onCheckedChange={(checked) => setUnderstood(checked as boolean)}
                  disabled={isDeleting}
                />
                <label
                  htmlFor="understood"
                  className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                >
                  I understand this action cannot be undone and will permanently delete all tenant data
                </label>
              </div>
            </div>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel onClick={handleCancel} disabled={isDeleting}>
            Cancel
          </AlertDialogCancel>
          <AlertDialogAction
            onClick={handleConfirm}
            disabled={!isConfirmValid || isDeleting}
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          >
            {isDeleting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Delete Tenant Permanently
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
