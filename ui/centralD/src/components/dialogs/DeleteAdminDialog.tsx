/**
 * Delete PM Admin Dialog
 */

import { useState } from 'react';
import { Loader2, AlertTriangle } from 'lucide-react';
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
import { useDeletePMAdmin } from '@/hooks/api';
import type { PMAdmin } from '@/types';

interface DeleteAdminDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  admin: PMAdmin | null;
}

export function DeleteAdminDialog({ open, onOpenChange, admin }: DeleteAdminDialogProps) {
  const [confirmEmail, setConfirmEmail] = useState('');
  
  const deleteAdmin = useDeletePMAdmin(admin?.id ?? 0);

  const isConfirmValid = confirmEmail === admin?.email;

  const handleConfirm = async () => {
    if (!isConfirmValid || !admin) return;

    try {
      await deleteAdmin.mutateAsync();
      handleClose();
    } catch {
      // Error handled by mutation
    }
  };

  const handleClose = () => {
    setConfirmEmail('');
    onOpenChange(false);
  };

  if (!admin) return null;

  return (
    <AlertDialog open={open} onOpenChange={handleClose}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-destructive" />
            Delete Administrator
          </AlertDialogTitle>
          <AlertDialogDescription asChild>
            <div className="space-y-4">
              <p>
                Are you sure you want to delete the administrator account for{' '}
                <span className="font-semibold">{admin.email}</span>?
              </p>
              <p className="text-destructive font-medium">
                This action cannot be undone. The admin will lose all access to the platform.
              </p>

              <div className="space-y-2 pt-2">
                <Label htmlFor="confirm-email">
                  Type <span className="font-mono font-bold">{admin.email}</span> to confirm
                </Label>
                <Input
                  id="confirm-email"
                  value={confirmEmail}
                  onChange={(e) => setConfirmEmail(e.target.value)}
                  placeholder={admin.email}
                  disabled={deleteAdmin.isPending}
                  className="font-mono"
                />
              </div>
            </div>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel onClick={handleClose} disabled={deleteAdmin.isPending}>
            Cancel
          </AlertDialogCancel>
          <AlertDialogAction
            onClick={handleConfirm}
            disabled={!isConfirmValid || deleteAdmin.isPending}
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          >
            {deleteAdmin.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Delete Admin
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
