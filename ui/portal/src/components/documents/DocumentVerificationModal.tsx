/**
 * DocumentVerificationModal Component
 * Modal for HR to verify documents with notes
 */

import { useState } from 'react';
import { CheckCircle2, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import type { Document } from '@/types';
import { DOCUMENT_TYPE_LABELS, DOCUMENT_TYPE_ICONS } from '@/types';
import { documentApi } from '@/lib/documentApi';
import { getErrorMessage } from '@/lib/api-client';

interface DocumentVerificationModalProps {
  document: Document | null;
  open: boolean;
  onClose: () => void;
  onVerified?: (document: Document) => void;
}

export function DocumentVerificationModal({
  document,
  open,
  onClose,
  onVerified,
}: DocumentVerificationModalProps) {
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);

  const handleVerify = async () => {
    if (!document) return;

    setLoading(true);
    try {
      const verifiedDocument = await documentApi.verifyDocument(document.id, {
        notes: notes.trim() || undefined,
      });

      // Success notification - could be replaced with toast when available
      console.log('Document verified successfully:', verifiedDocument);

      if (onVerified) {
        onVerified(verifiedDocument);
      }

      handleClose();
    } catch (error) {
      // Error notification - could be replaced with toast when available
      console.error('Verification failed:', getErrorMessage(error));
      alert(`Verification failed: ${getErrorMessage(error)}`);
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setNotes('');
    onClose();
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
  };

  if (!document) return null;

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && handleClose()}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-primary" />
            Verify Document
          </DialogTitle>
          <DialogDescription>
            Review and verify this document. Add any notes about the verification.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Document Info */}
          <div className="rounded-lg border p-4 space-y-3">
            <div className="flex items-start gap-3">
              <div className="flex-shrink-0 h-12 w-12 rounded bg-muted flex items-center justify-center text-2xl">
                {DOCUMENT_TYPE_ICONS[document.document_type]}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium truncate" title={document.file_name}>
                  {document.file_name}
                </p>
                <div className="flex items-center gap-2 mt-1">
                  <Badge variant="outline" className="text-xs">
                    {DOCUMENT_TYPE_LABELS[document.document_type]}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    {formatFileSize(document.file_size)}
                  </span>
                </div>
              </div>
            </div>

            {document.description && (
              <div className="text-sm text-muted-foreground pt-2 border-t">
                <p className="font-medium text-foreground">Description:</p>
                <p>{document.description}</p>
              </div>
            )}

            {document.is_verified && (
              <div className="pt-2 border-t">
                <Badge variant="default" className="gap-1">
                  <CheckCircle2 className="h-3 w-3" />
                  Already Verified
                </Badge>
                {document.verification_notes && (
                  <p className="text-sm text-muted-foreground mt-2">
                    <span className="font-medium">Previous notes:</span> {document.verification_notes}
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Verification Notes */}
          <div className="space-y-2">
            <Label htmlFor="notes">Verification Notes (Optional)</Label>
            <Textarea
              id="notes"
              placeholder="Add any notes about this verification..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={4}
              disabled={loading}
            />
            <p className="text-xs text-muted-foreground">
              These notes will be saved with the verification record.
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={loading}>
            Cancel
          </Button>
          <Button onClick={handleVerify} disabled={loading || document.is_verified}>
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Verifying...
              </>
            ) : (
              <>
                <CheckCircle2 className="mr-2 h-4 w-4" />
                {document.is_verified ? 'Already Verified' : 'Verify Document'}
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
