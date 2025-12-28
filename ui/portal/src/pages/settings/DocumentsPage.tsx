/**
 * Documents Page
 * Admin view for managing all documents across candidates
 */

import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { RefreshCw, FileText, CheckCircle2, Clock, Database, ChevronLeft, ChevronRight } from 'lucide-react';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  DocumentList,
  DocumentViewer,
  DocumentVerificationModal,
} from '@/components/documents';
import { documentApi } from '@/lib/documentApi';
import { getErrorMessage } from '@/lib/api-client';
import { toast } from 'sonner';
import type { Document, DocumentListItem, DocumentType } from '@/types';

export default function DocumentsPage() {
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);
  const [showDocumentViewer, setShowDocumentViewer] = useState(false);
  const [showVerificationModal, setShowVerificationModal] = useState(false);
  const [filters, setFilters] = useState({
    page: 1,
    per_page: 20,
    document_type: undefined as DocumentType | undefined,
    is_verified: undefined as boolean | undefined,
  });

  const queryClient = useQueryClient();

  // Fetch documents
  const { data: documentsResponse, isLoading, error } = useQuery({
    queryKey: ['documents', 'all', filters],
    queryFn: () => documentApi.listDocuments(filters),
  });

  // Fetch stats
  const { data: stats } = useQuery({
    queryKey: ['documents', 'stats'],
    queryFn: () => documentApi.getStats(),
  });

  // Handlers
  const handleViewDocument = (document: DocumentListItem) => {
    documentApi.getDocument(document.id).then((fullDoc) => {
      setSelectedDocument(fullDoc);
      setShowDocumentViewer(true);
    });
  };

  const handleDownloadDocument = async (document: DocumentListItem) => {
    try {
      const blob = await documentApi.downloadDocument(document.id);
      const url = window.URL.createObjectURL(blob);
      const link = window.document.createElement('a');
      link.href = url;
      link.download = document.file_name;
      window.document.body.appendChild(link);
      link.click();
      window.document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      toast.success('Document downloaded successfully');
    } catch {
      toast.error('Failed to download document');
    }
  };

  const handleVerifyDocument = (document: DocumentListItem) => {
    documentApi.getDocument(document.id).then((fullDoc) => {
      setSelectedDocument(fullDoc);
      setShowVerificationModal(true);
    });
  };

  const handleDeleteDocument = async (document: DocumentListItem) => {
    if (confirm(`Are you sure you want to delete ${document.file_name}?`)) {
      try {
        await documentApi.deleteDocument(document.id);
        queryClient.invalidateQueries({ queryKey: ['documents'] });
        toast.success('Document deleted successfully');
      } catch {
        toast.error('Failed to delete document');
      }
    }
  };

  const handleDocumentVerified = () => {
    queryClient.invalidateQueries({ queryKey: ['documents'] });
    setShowVerificationModal(false);
    setSelectedDocument(null);
  };

  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ['documents'] });
    toast.success('Documents refreshed');
  };

  const formatNumber = (num: number): string => {
    return new Intl.NumberFormat().format(num);
  };

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <div className="space-y-6">
      {/* Error State */}
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{getErrorMessage(error)}</AlertDescription>
        </Alert>
      )}

      {/* Main Card with Integrated Header */}
      <Card>
        <CardHeader className="border-b bg-slate-50/50">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            {/* Inline Stats */}
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-md bg-blue-100">
                  <FileText className="h-4 w-4 text-blue-600" />
                </div>
                <div>
                  <span className="text-2xl font-bold">{formatNumber(stats?.total_documents || 0)}</span>
                  <span className="text-sm text-muted-foreground ml-1.5">Documents</span>
                </div>
              </div>
              <div className="h-8 w-px bg-border" />
              <div className="flex items-center gap-4 text-sm">
                <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                  <CheckCircle2 className="h-3 w-3 mr-1" />
                  {formatNumber(stats?.verified_count || 0)} Verified
                </Badge>
                <Badge variant="outline" className="bg-orange-50 text-orange-700 border-orange-200">
                  <Clock className="h-3 w-3 mr-1" />
                  {formatNumber(stats?.unverified_count || 0)} Pending
                </Badge>
                <Badge variant="outline" className="bg-purple-50 text-purple-700 border-purple-200">
                  <Database className="h-3 w-3 mr-1" />
                  {formatBytes(stats?.total_size_bytes || 0)}
                </Badge>
              </div>
            </div>

            {/* Actions */}
            <Button variant="outline" size="sm" onClick={handleRefresh} className="gap-1.5">
              <RefreshCw className="h-4 w-4" />
              Refresh
            </Button>
          </div>
        </CardHeader>

        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6 space-y-4">
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
            </div>
          ) : (
            <DocumentList
              documents={documentsResponse?.documents || []}
              loading={isLoading}
              onView={handleViewDocument}
              onDownload={handleDownloadDocument}
              onVerify={handleVerifyDocument}
              onDelete={handleDeleteDocument}
              showFilters={true}
              emptyMessage="No documents found"
            />
          )}
        </CardContent>
      </Card>

      {/* Pagination */}
      {documentsResponse && documentsResponse.pages > 1 && (
        <div className="flex items-center justify-between pt-4 border-t">
          <p className="text-sm text-slate-600">
            Page {filters.page} of {documentsResponse.pages}
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={filters.page === 1}
              onClick={() => setFilters({ ...filters, page: filters.page - 1 })}
            >
              <ChevronLeft className="h-4 w-4 mr-1" />
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={filters.page === documentsResponse.pages}
              onClick={() => setFilters({ ...filters, page: filters.page + 1 })}
            >
              Next
              <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          </div>
        </div>
      )}

      {/* Document Viewer Modal */}
      <DocumentViewer
        document={selectedDocument}
        open={showDocumentViewer}
        onClose={() => {
          setShowDocumentViewer(false);
          setSelectedDocument(null);
        }}
        onDownload={handleDownloadDocument}
      />

      {/* Document Verification Modal */}
      <DocumentVerificationModal
        document={selectedDocument}
        open={showVerificationModal}
        onClose={() => {
          setShowVerificationModal(false);
          setSelectedDocument(null);
        }}
        onVerified={handleDocumentVerified}
      />
    </div>
  );
}
