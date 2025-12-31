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
      <DialogContent className="sm:max-w-[500px] border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] rounded-lg">
        <DialogHeader className="border-b-2 border-black pb-4">
          <DialogTitle className="flex items-center gap-2 text-xl font-bold">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center border-2 border-black">
              <CheckCircle2 className="h-4 w-4" />
            </div>
            Verify Document
          </DialogTitle>
          <DialogDescription className="text-slate-600 mt-1">
            Review and verify this document. Add any notes about the verification.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Document Info Card */}
          <div className="rounded-lg border-2 border-black bg-slate-50 p-4 shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]">
            <div className="flex items-start gap-4">
              <div className="flex-shrink-0 h-14 w-14 rounded-lg bg-white border-2 border-black flex items-center justify-center text-2xl shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]">
                {DOCUMENT_TYPE_ICONS[document.document_type] || <FileText className="h-6 w-6" />}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-bold text-slate-900 truncate text-base" title={document.file_name}>
                  {document.file_name}
                </p>
                <div className="flex flex-wrap items-center gap-2 mt-2">
                  <Badge variant="outline" className="text-xs border-2 border-black font-medium">
                    {DOCUMENT_TYPE_LABELS[document.document_type]}
                  </Badge>
                  <span className="text-sm text-slate-600 font-medium">
                    {formatFileSize(document.file_size)}
                  </span>
                </div>
              </div>
            </div>

            {document.description && (
              <div className="text-sm text-slate-600 pt-3 mt-3 border-t-2 border-dashed border-slate-300">
                <p className="font-bold text-slate-700 mb-1">Description:</p>
                <p>{document.description}</p>
              </div>
            )}

            {document.is_verified && (
              <div className="pt-3 mt-3 border-t-2 border-dashed border-slate-300">
                <Badge className="gap-1 bg-green-500 text-white border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]">
                  <CheckCircle2 className="h-3 w-3" />
                  Already Verified
                </Badge>
                {document.verification_notes && (
                  <p className="text-sm text-slate-600 mt-2">
                    <span className="font-bold text-slate-700">Previous notes:</span> {document.verification_notes}
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Verification Notes */}
          {!document.is_verified && (
            <div className="space-y-2">
              <Label htmlFor="notes" className="text-sm font-bold text-slate-700">
                Verification Notes (Optional)
              </Label>
              <Textarea
                id="notes"
                placeholder="Add any notes about this verification..."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={4}
                disabled={loading}
                className="border-2 border-black focus:ring-2 focus:ring-primary shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]"
              />
              <p className="text-xs text-slate-500">
                These notes will be saved with the verification record.
              </p>
            </div>
          )}

          {/* Already Verified Warning */}
          {document.is_verified && (
            <div className="flex items-start gap-3 p-3 bg-amber-50 border-2 border-amber-500 rounded-lg">
              <AlertCircle className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-amber-800">
                <p className="font-bold">This document has already been verified.</p>
                <p className="mt-1">No further action is required.</p>
              </div>
            </div>
          )}
        </div>

        <DialogFooter className="border-t-2 border-black pt-4 gap-2">
          <Button 
            variant="outline" 
            onClick={handleClose} 
            disabled={loading}
            className="border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:translate-x-[-2px] hover:translate-y-[-2px] transition-all"
          >
            Cancel
          </Button>
          {!document.is_verified && (
            <Button 
              onClick={handleVerify} 
              disabled={loading}
              className="border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:translate-x-[-2px] hover:translate-y-[-2px] transition-all bg-green-600 hover:bg-green-700"
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
