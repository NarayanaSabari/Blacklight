/**
 * DocumentVerificationModal Component
 * Modal for HR to verify documents with notes
 * Updated with neobrutalist styling
 */

import { useState } from 'react';
import { CheckCircle2, Loader2, FileText, AlertCircle } from 'lucide-react';
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
import { toast } from 'sonner';

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

      toast.success('Document verified successfully');

      if (onVerified) {
        onVerified(verifiedDocument);
      }

      handleClose();
    } catch (error) {
      toast.error(`Verification failed: ${getErrorMessage(error)}`);
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
      <DialogContent className="sm:max-w-[480px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-green-600" />
            Verify Document
          </DialogTitle>
          <DialogDescription>
            Review and verify this document. Add any notes about the verification.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Document Info Card */}
          <div className="rounded-md border bg-muted/50 p-3">
            <div className="flex items-center gap-3">
              <div className="flex-shrink-0 h-10 w-10 rounded bg-background border flex items-center justify-center text-xl">
                {DOCUMENT_TYPE_ICONS[document.document_type] || <FileText className="h-5 w-5" />}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium text-sm truncate" title={document.file_name}>
                  {document.file_name}
                </p>
                <div className="flex items-center gap-2 mt-1">
                  <Badge variant="secondary" className="text-xs">
                    {DOCUMENT_TYPE_LABELS[document.document_type]}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    {formatFileSize(document.file_size)}
                  </span>
                </div>
              </div>
            </div>

            {document.description && (
              <p className="text-sm text-muted-foreground mt-3 pt-3 border-t">
                {document.description}
              </p>
            )}

            {document.is_verified && (
              <div className="mt-3 pt-3 border-t">
                <Badge className="bg-green-600">
                  <CheckCircle2 className="h-3 w-3 mr-1" />
                  Already Verified
                </Badge>
                {document.verification_notes && (
                  <p className="text-sm text-muted-foreground mt-2">
                    <span className="font-medium">Notes:</span> {document.verification_notes}
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Verification Notes */}
          {!document.is_verified && (
            <div className="space-y-2">
              <Label htmlFor="verification-notes">
                Verification Notes (Optional)
              </Label>
              <Textarea
                id="verification-notes"
                placeholder="Add any notes about this verification..."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={3}
                disabled={loading}
                className="resize-none w-full"
              />
              <p className="text-xs text-muted-foreground">
                These notes will be saved with the verification record.
              </p>
            </div>
          )}

          {/* Already Verified Notice */}
          {document.is_verified && (
            <div className="flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded-md text-sm">
              <AlertCircle className="h-4 w-4 text-amber-600 flex-shrink-0 mt-0.5" />
              <p className="text-amber-800">
                This document has already been verified. No further action is required.
              </p>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={loading}>
            Cancel
          </Button>
          {!document.is_verified && (
            <Button 
              onClick={handleVerify} 
              disabled={loading}
              className="bg-green-600 hover:bg-green-700"
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Verifying...
                </>
              ) : (
                <>
                  <CheckCircle2 className="mr-2 h-4 w-4" />
                  Verify Document
                </>
              )}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
