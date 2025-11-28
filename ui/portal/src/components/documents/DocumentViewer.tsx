/**
 * DocumentViewer Component
 * Modal for viewing and downloading documents with signed URL support
 */

import { useState, useEffect } from 'react';
import { X, Download, ExternalLink, Loader2, FileText, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import type { Document } from '@/types';
import { DOCUMENT_TYPE_LABELS, DOCUMENT_TYPE_ICONS } from '@/types';
import { documentApi } from '@/lib/documentApi';
import { getErrorMessage } from '@/lib/api-client';
import { formatDistanceToNow } from 'date-fns';

interface DocumentViewerProps {
  document: Document | null;
  open: boolean;
  onClose: () => void;
  onDownload?: (document: Document) => void;
}

export function DocumentViewer({ document, open, onClose, onDownload }: DocumentViewerProps) {
  const [signedUrl, setSignedUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load signed URL when document changes (for GCS backend)
  useEffect(() => {
    if (!document || !open) {
      setSignedUrl(null);
      setError(null);
      return;
    }

    // For GCS backend, fetch signed URL
    if (document.storage_backend === 'gcs') {
      setLoading(true);
      setError(null);
      
      documentApi
        .getDocumentUrl(document.id)
        .then((response) => {
          setSignedUrl(response.url);
        })
        .catch((err) => {
          setError(getErrorMessage(err));
        })
        .finally(() => {
          setLoading(false);
        });
    } else {
      // For local storage, we can use the file_path directly
      setSignedUrl(`/api/documents/${document.id}/download`);
    }
  }, [document, open]);

  const handleDownload = () => {
    if (!document) return;
    
    if (onDownload) {
      onDownload(document);
    } else {
      // Default download behavior
      window.open(signedUrl || `/api/documents/${document.id}/download`, '_blank');
    }
  };

  const canPreview = (mimeType: string | undefined): boolean => {
    if (!mimeType) return false;
    return ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png'].includes(mimeType);
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
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="max-w-4xl h-[90vh] flex flex-col">
        <DialogHeader>
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0 pr-6">
              <DialogTitle className="flex items-center gap-2">
                <span className="text-2xl">{DOCUMENT_TYPE_ICONS[document.document_type]}</span>
                <span className="truncate">{document.file_name}</span>
              </DialogTitle>
              <DialogDescription asChild>
                <div className="mt-2 space-y-1">
                  <div className="flex items-center gap-2 flex-wrap text-sm text-muted-foreground">
                    <Badge variant="outline">
                      {DOCUMENT_TYPE_LABELS[document.document_type]}
                    </Badge>
                    <span className="text-xs">•</span>
                    <span>{formatFileSize(document.file_size)}</span>
                    <span className="text-xs">•</span>
                    <span>
                      Uploaded {formatDistanceToNow(new Date(document.uploaded_at), { addSuffix: true })}
                    </span>
                  </div>
                  {document.is_verified && document.verified_at && (
                    <div className="flex items-center gap-1 text-green-600">
                      <span className="text-xs">
                        ✓ Verified {formatDistanceToNow(new Date(document.verified_at), { addSuffix: true })}
                      </span>
                    </div>
                  )}
                </div>
              </DialogDescription>
            </div>
            <Button variant="ghost" size="icon" onClick={onClose}>
              <X className="h-4 w-4" />
            </Button>
          </div>
        </DialogHeader>

        {/* Document Preview/Content */}
        <div className="flex-1 overflow-hidden rounded-lg border bg-muted/20">
          {loading ? (
            <div className="h-full flex items-center justify-center">
              <div className="flex flex-col items-center gap-2">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                <p className="text-sm text-muted-foreground">Loading document...</p>
              </div>
            </div>
          ) : error ? (
            <div className="h-full flex items-center justify-center p-6">
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            </div>
          ) : canPreview(document.mime_type) && signedUrl ? (
            <div className="h-full w-full">
              {document.mime_type === 'application/pdf' ? (
                <iframe
                  src={signedUrl}
                  className="w-full h-full"
                  title={document.file_name}
                />
              ) : (
                <div className="h-full w-full flex items-center justify-center p-4">
                  <img
                    src={signedUrl}
                    alt={document.file_name}
                    className="max-w-full max-h-full object-contain"
                  />
                </div>
              )}
            </div>
          ) : (
            <div className="h-full flex items-center justify-center">
              <div className="text-center space-y-4">
                <div className="flex justify-center">
                  <div className="rounded-full bg-muted p-6">
                    <FileText className="h-12 w-12 text-muted-foreground" />
                  </div>
                </div>
                <div>
                  <p className="font-medium">Preview not available</p>
                  <p className="text-sm text-muted-foreground mt-1">
                    This file type cannot be previewed in the browser
                  </p>
                </div>
                <Button onClick={handleDownload} className="gap-2">
                  <Download className="h-4 w-4" />
                  Download to View
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center justify-between pt-4 border-t">
          <div className="flex items-center gap-2">
            {document.description && (
              <p className="text-sm text-muted-foreground">{document.description}</p>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={handleDownload} className="gap-2">
              <Download className="h-4 w-4" />
              Download
            </Button>
            {signedUrl && document.storage_backend === 'gcs' && (
              <Button variant="outline" asChild className="gap-2">
                <a href={signedUrl} target="_blank" rel="noopener noreferrer">
                  <ExternalLink className="h-4 w-4" />
                  Open in New Tab
                </a>
              </Button>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
