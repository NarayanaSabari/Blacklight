/**
 * Documents Page
 * Admin view for managing all documents across candidates
 * Includes a Storage Browser to view all files in GCS/local storage
 */

import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  RefreshCw,
  FileText,
  CheckCircle2,
  Clock,
  Database,
  ChevronLeft,
  ChevronRight,
  Folder,
  FolderOpen,
  File,
  Download,
  HardDrive,
  Home,
  Cloud,
  Image,
  FileCode,
  FileSpreadsheet,
} from 'lucide-react';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  DocumentList,
  DocumentViewer,
  DocumentVerificationModal,
} from '@/components/documents';
import { documentApi } from '@/lib/documentApi';
import { getErrorMessage } from '@/lib/api-client';
import { toast } from 'sonner';
import type { Document, DocumentListItem, DocumentType, StorageFile, StorageFolder } from '@/types';
import { formatDistanceToNow } from 'date-fns';

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

  // Storage browser state
  const [currentPath, setCurrentPath] = useState('');
  const [activeTab, setActiveTab] = useState('documents');

  const queryClient = useQueryClient();

  // Fetch documents (database records)
  const { data: documentsResponse, isLoading, error } = useQuery({
    queryKey: ['documents', 'all', filters],
    queryFn: () => documentApi.listDocuments(filters),
  });

  // Fetch stats
  const { data: stats } = useQuery({
    queryKey: ['documents', 'stats'],
    queryFn: () => documentApi.getStats(),
  });

  // Fetch storage files (GCS/local browser)
  const { data: storageData, isLoading: storageLoading, error: storageError } = useQuery({
    queryKey: ['storage', 'browse', currentPath],
    queryFn: () => documentApi.browseStorage(currentPath, false),
    enabled: activeTab === 'storage',
  });

  // Document handlers
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
    queryClient.invalidateQueries({ queryKey: ['storage'] });
    toast.success('Refreshed');
  };

  // Storage browser handlers
  const handleFolderClick = (folder: StorageFolder) => {
    setCurrentPath(folder.relative_path);
  };

  const handleDownloadStorageFile = async (file: StorageFile) => {
    try {
      const blob = await documentApi.downloadStorageFile(file.relative_path);
      const url = window.URL.createObjectURL(blob);
      const link = window.document.createElement('a');
      link.href = url;
      link.download = file.name;
      window.document.body.appendChild(link);
      link.click();
      window.document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      toast.success('File downloaded successfully');
    } catch {
      toast.error('Failed to download file');
    }
  };

  const navigateToPath = (path: string) => {
    setCurrentPath(path);
  };

  // Build breadcrumb parts
  const pathParts = currentPath ? currentPath.split('/').filter(Boolean) : [];
  const breadcrumbItems = pathParts.map((part, index) => ({
    name: part,
    path: pathParts.slice(0, index + 1).join('/'),
  }));

  // Helpers
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

  const getFileIcon = (contentType: string, name: string) => {
    if (contentType.startsWith('image/')) {
      return <Image className="h-4 w-4 text-purple-500" />;
    }
    if (contentType === 'application/pdf') {
      return <FileText className="h-4 w-4 text-red-500" />;
    }
    if (contentType.includes('word') || name.endsWith('.doc') || name.endsWith('.docx')) {
      return <FileText className="h-4 w-4 text-blue-500" />;
    }
    if (contentType.includes('spreadsheet') || name.endsWith('.xls') || name.endsWith('.xlsx')) {
      return <FileSpreadsheet className="h-4 w-4 text-green-500" />;
    }
    if (contentType.includes('json') || contentType.includes('javascript') || contentType.includes('text')) {
      return <FileCode className="h-4 w-4 text-yellow-500" />;
    }
    return <File className="h-4 w-4 text-slate-500" />;
  };

  return (
    <div className="space-y-6">
      {/* Error State */}
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{getErrorMessage(error)}</AlertDescription>
        </Alert>
      )}

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <div className="flex items-center justify-between mb-4">
          <TabsList>
            <TabsTrigger value="documents" className="gap-2">
              <FileText className="h-4 w-4" />
              Documents
            </TabsTrigger>
            <TabsTrigger value="storage" className="gap-2">
              <HardDrive className="h-4 w-4" />
              Storage Browser
            </TabsTrigger>
          </TabsList>
          <Button variant="outline" size="sm" onClick={handleRefresh} className="gap-1.5">
            <RefreshCw className="h-4 w-4" />
            Refresh
          </Button>
        </div>

        {/* Documents Tab - existing document list */}
        <TabsContent value="documents" className="mt-0">
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
        </TabsContent>

        {/* Storage Browser Tab */}
        <TabsContent value="storage" className="mt-0">
          <Card>
            <CardHeader className="border-b bg-slate-50/50">
              <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                {/* Storage info */}
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <div className="p-1.5 rounded-md bg-indigo-100">
                      {storageData?.storage_backend === 'gcs' ? (
                        <Cloud className="h-4 w-4 text-indigo-600" />
                      ) : (
                        <HardDrive className="h-4 w-4 text-indigo-600" />
                      )}
                    </div>
                    <div>
                      <span className="text-sm font-medium">
                        {storageData?.storage_backend === 'gcs' ? 'Google Cloud Storage' : 'Local Storage'}
                      </span>
                    </div>
                  </div>
                  {storageData && (
                    <>
                      <div className="h-6 w-px bg-border" />
                      <div className="flex items-center gap-3 text-sm">
                        <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
                          <File className="h-3 w-3 mr-1" />
                          {formatNumber(storageData.total_count)} files
                        </Badge>
                        <Badge variant="outline" className="bg-purple-50 text-purple-700 border-purple-200">
                          <Database className="h-3 w-3 mr-1" />
                          {formatBytes(storageData.total_size_bytes)}
                        </Badge>
                      </div>
                    </>
                  )}
                </div>
              </div>
            </CardHeader>

            <CardContent className="p-4">
              {/* Breadcrumb navigation */}
              <div className="mb-4 flex items-center gap-2 p-2 bg-slate-50 rounded-lg">
                <Breadcrumb>
                  <BreadcrumbList>
                    <BreadcrumbItem>
                      <BreadcrumbLink
                        onClick={() => navigateToPath('')}
                        className="cursor-pointer hover:text-primary flex items-center gap-1"
                      >
                        <Home className="h-3.5 w-3.5" />
                        Root
                      </BreadcrumbLink>
                    </BreadcrumbItem>
                    {breadcrumbItems.map((item, index) => (
                      <BreadcrumbItem key={item.path}>
                        <BreadcrumbSeparator />
                        {index === breadcrumbItems.length - 1 ? (
                          <BreadcrumbPage className="flex items-center gap-1">
                            <FolderOpen className="h-3.5 w-3.5" />
                            {item.name}
                          </BreadcrumbPage>
                        ) : (
                          <BreadcrumbLink
                            onClick={() => navigateToPath(item.path)}
                            className="cursor-pointer hover:text-primary flex items-center gap-1"
                          >
                            <Folder className="h-3.5 w-3.5" />
                            {item.name}
                          </BreadcrumbLink>
                        )}
                      </BreadcrumbItem>
                    ))}
                  </BreadcrumbList>
                </Breadcrumb>
              </div>

              {/* Storage error */}
              {storageError && (
                <Alert variant="destructive" className="mb-4">
                  <AlertDescription>{getErrorMessage(storageError)}</AlertDescription>
                </Alert>
              )}

              {/* Loading state */}
              {storageLoading ? (
                <div className="space-y-3">
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                </div>
              ) : (
                <>
                  {/* Empty state */}
                  {(!storageData?.folders?.length && !storageData?.files?.length) ? (
                    <div className="flex flex-col items-center justify-center py-12 text-center">
                      <FolderOpen className="h-12 w-12 text-muted-foreground mb-4" />
                      <h3 className="text-lg font-medium mb-1">No files or folders</h3>
                      <p className="text-muted-foreground text-sm">
                        This directory is empty
                      </p>
                    </div>
                  ) : (
                    <div className="rounded-md border">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead className="w-[40%]">Name</TableHead>
                            <TableHead className="w-[15%]">Size</TableHead>
                            <TableHead className="w-[15%]">Type</TableHead>
                            <TableHead className="w-[20%]">Modified</TableHead>
                            <TableHead className="w-[10%]">Actions</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {/* Folders first */}
                          {storageData?.folders?.map((folder) => (
                            <TableRow
                              key={folder.full_path}
                              className="cursor-pointer hover:bg-muted/50"
                              onClick={() => handleFolderClick(folder)}
                            >
                              <TableCell>
                                <div className="flex items-center gap-2">
                                  <Folder className="h-5 w-5 text-amber-500" />
                                  <span className="font-medium">{folder.name}</span>
                                </div>
                              </TableCell>
                              <TableCell className="text-muted-foreground">—</TableCell>
                              <TableCell>
                                <Badge variant="secondary" className="text-xs">Folder</Badge>
                              </TableCell>
                              <TableCell className="text-muted-foreground">—</TableCell>
                              <TableCell>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleFolderClick(folder);
                                  }}
                                >
                                  Open
                                </Button>
                              </TableCell>
                            </TableRow>
                          ))}

                          {/* Files */}
                          {storageData?.files?.map((file) => (
                            <TableRow key={file.full_path}>
                              <TableCell>
                                <div className="flex items-center gap-2">
                                  {getFileIcon(file.content_type, file.name)}
                                  <span className="font-medium truncate max-w-[300px]" title={file.name}>
                                    {file.name}
                                  </span>
                                </div>
                              </TableCell>
                              <TableCell className="text-muted-foreground">
                                {formatBytes(file.size)}
                              </TableCell>
                              <TableCell>
                                <Badge variant="outline" className="text-xs font-normal">
                                  {file.content_type.split('/')[1] || file.content_type}
                                </Badge>
                              </TableCell>
                              <TableCell className="text-muted-foreground text-sm">
                                {file.updated_at
                                  ? formatDistanceToNow(new Date(file.updated_at), { addSuffix: true })
                                  : '—'}
                              </TableCell>
                              <TableCell>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="h-8 w-8"
                                  onClick={() => handleDownloadStorageFile(file)}
                                  title="Download"
                                >
                                  <Download className="h-4 w-4" />
                                </Button>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  )}
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

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
