/**
 * Documents Page
 * Admin view for managing all documents across candidates
 */

import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { RefreshCw } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
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
    <div className="container mx-auto p-6 space-y-6">
      {/* Action Bar */}
      <div className="flex justify-end">
        <Button variant="outline" size="sm" onClick={handleRefresh}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Stats Cards */}
      {stats && stats.total_documents !== undefined && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Total Documents</CardDescription>
              <CardTitle className="text-3xl">{formatNumber(stats.total_documents || 0)}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground">
                {formatBytes(stats.total_size_bytes || 0)} total size
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Verified</CardDescription>
              <CardTitle className="text-3xl text-green-600">
                {formatNumber(stats.verified_count || 0)}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground">
                {(stats.total_documents || 0) > 0
                  ? Math.round(((stats.verified_count || 0) / (stats.total_documents || 1)) * 100)
                  : 0}
                % verification rate
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Pending Verification</CardDescription>
              <CardTitle className="text-3xl text-orange-600">
                {formatNumber(stats.unverified_count || 0)}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground">Require attention</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Storage</CardDescription>
              <CardTitle className="text-3xl">
                {(stats.by_storage?.gcs || 0) > 0 ? 'GCS' : 'Local'}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex gap-2 text-xs text-muted-foreground">
                {stats.by_storage?.gcs && (
                  <Badge variant="outline">GCS: {stats.by_storage.gcs}</Badge>
                )}
                {stats.by_storage?.local && (
                  <Badge variant="outline">Local: {stats.by_storage.local}</Badge>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Error State */}
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{getErrorMessage(error)}</AlertDescription>
        </Alert>
      )}

      {/* Documents List */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>All Documents</CardTitle>
              <CardDescription>
                {documentsResponse
                  ? `Showing ${documentsResponse.documents.length} of ${documentsResponse.total} documents`
                  : 'Loading...'}
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-4">
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
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
        <div className="flex items-center justify-center gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={filters.page === 1}
            onClick={() => setFilters({ ...filters, page: filters.page - 1 })}
          >
            Previous
          </Button>
          <span className="text-sm text-muted-foreground">
            Page {filters.page} of {documentsResponse.pages}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={filters.page === documentsResponse.pages}
            onClick={() => setFilters({ ...filters, page: filters.page + 1 })}
          >
            Next
          </Button>
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
