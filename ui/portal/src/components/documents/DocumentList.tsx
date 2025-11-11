/**
 * DocumentList Component
 * Displays a table of documents with filters, pagination, and verification status
 */

import { useState } from 'react';
import {
  FileText,
  Download,
  Eye,
  Trash2,
  CheckCircle2,
  XCircle,
  Filter,
  Search,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import type { DocumentListItem, DocumentType } from '@/types';
import { DOCUMENT_TYPE_LABELS, DOCUMENT_TYPE_ICONS } from '@/types';
import { formatDistanceToNow } from 'date-fns';

interface DocumentListProps {
  documents: DocumentListItem[];
  loading?: boolean;
  onView?: (document: DocumentListItem) => void;
  onDownload?: (document: DocumentListItem) => void;
  onVerify?: (document: DocumentListItem) => void;
  onDelete?: (document: DocumentListItem) => void;
  showFilters?: boolean;
  showActions?: boolean;
  emptyMessage?: string;
}

export function DocumentList({
  documents,
  loading = false,
  onView,
  onDownload,
  onVerify,
  onDelete,
  showFilters = true,
  showActions = true,
  emptyMessage = 'No documents found',
}: DocumentListProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [typeFilter, setTypeFilter] = useState<DocumentType | 'all'>('all');
  const [verificationFilter, setVerificationFilter] = useState<'all' | 'verified' | 'unverified'>('all');

  // Filter documents
  const filteredDocuments = documents.filter((doc) => {
    const matchesSearch = doc.file_name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesType = typeFilter === 'all' || doc.document_type === typeFilter;
    const matchesVerification =
      verificationFilter === 'all' ||
      (verificationFilter === 'verified' && doc.is_verified) ||
      (verificationFilter === 'unverified' && !doc.is_verified);

    return matchesSearch && matchesType && matchesVerification;
  });

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
  };

  const getFileExtension = (filename: string): string => {
    return filename.split('.').pop()?.toUpperCase() || '';
  };

  return (
    <Card className="p-6">
      {/* Filters */}
      {showFilters && (
        <div className="flex flex-col sm:flex-row gap-4 mb-6">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search documents..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-9"
            />
          </div>

          <Select
            value={typeFilter}
            onValueChange={(value) => setTypeFilter(value as DocumentType | 'all')}
          >
            <SelectTrigger className="w-full sm:w-[200px]">
              <SelectValue placeholder="Document Type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">
                <div className="flex items-center gap-2">
                  <Filter className="h-4 w-4" />
                  <span>All Types</span>
                </div>
              </SelectItem>
              {Object.entries(DOCUMENT_TYPE_LABELS).map(([key, label]) => (
                <SelectItem key={key} value={key}>
                  <div className="flex items-center gap-2">
                    <span>{DOCUMENT_TYPE_ICONS[key as DocumentType]}</span>
                    <span>{label}</span>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select
            value={verificationFilter}
            onValueChange={(value) => setVerificationFilter(value as 'all' | 'verified' | 'unverified')}
          >
            <SelectTrigger className="w-full sm:w-[180px]">
              <SelectValue placeholder="Verification" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Documents</SelectItem>
              <SelectItem value="verified">Verified Only</SelectItem>
              <SelectItem value="unverified">Unverified Only</SelectItem>
            </SelectContent>
          </Select>
        </div>
      )}

      {/* Results Count */}
      {showFilters && (
        <div className="mb-4 text-sm text-muted-foreground">
          Showing {filteredDocuments.length} of {documents.length} documents
        </div>
      )}

      {/* Table */}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-12"></TableHead>
              <TableHead>File Name</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Size</TableHead>
              <TableHead>Uploaded</TableHead>
              <TableHead>Status</TableHead>
              {showActions && <TableHead className="text-right">Actions</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={showActions ? 7 : 6} className="text-center py-8">
                  <div className="flex items-center justify-center gap-2">
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                    <span>Loading documents...</span>
                  </div>
                </TableCell>
              </TableRow>
            ) : filteredDocuments.length === 0 ? (
              <TableRow>
                <TableCell colSpan={showActions ? 7 : 6} className="text-center py-8">
                  <div className="flex flex-col items-center gap-2 text-muted-foreground">
                    <FileText className="h-12 w-12 opacity-20" />
                    <p>{emptyMessage}</p>
                  </div>
                </TableCell>
              </TableRow>
            ) : (
              filteredDocuments.map((document) => (
                <TableRow key={document.id}>
                  {/* File Icon */}
                  <TableCell>
                    <div className="flex items-center justify-center h-10 w-10 rounded bg-muted">
                      <span className="text-lg">
                        {DOCUMENT_TYPE_ICONS[document.document_type]}
                      </span>
                    </div>
                  </TableCell>

                  {/* File Name */}
                  <TableCell>
                    <div className="flex flex-col">
                      <span className="font-medium truncate max-w-[300px]" title={document.file_name}>
                        {document.file_name}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {getFileExtension(document.file_name)}
                      </span>
                    </div>
                  </TableCell>

                  {/* Document Type */}
                  <TableCell>
                    <Badge variant="outline">
                      {DOCUMENT_TYPE_LABELS[document.document_type]}
                    </Badge>
                  </TableCell>

                  {/* File Size */}
                  <TableCell className="text-muted-foreground">
                    {formatFileSize(document.file_size)}
                  </TableCell>

                  {/* Upload Time */}
                  <TableCell className="text-muted-foreground">
                    {formatDistanceToNow(new Date(document.uploaded_at), { addSuffix: true })}
                  </TableCell>

                  {/* Verification Status */}
                  <TableCell>
                    {document.is_verified ? (
                      <Badge variant="default" className="gap-1">
                        <CheckCircle2 className="h-3 w-3" />
                        Verified
                      </Badge>
                    ) : (
                      <Badge variant="secondary" className="gap-1">
                        <XCircle className="h-3 w-3" />
                        Pending
                      </Badge>
                    )}
                  </TableCell>

                  {/* Actions */}
                  {showActions && (
                    <TableCell className="text-right">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="sm">
                            Actions
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          {onView && (
                            <DropdownMenuItem onClick={() => onView(document)}>
                              <Eye className="mr-2 h-4 w-4" />
                              View
                            </DropdownMenuItem>
                          )}
                          {onDownload && (
                            <DropdownMenuItem onClick={() => onDownload(document)}>
                              <Download className="mr-2 h-4 w-4" />
                              Download
                            </DropdownMenuItem>
                          )}
                          {onVerify && !document.is_verified && (
                            <DropdownMenuItem onClick={() => onVerify(document)}>
                              <CheckCircle2 className="mr-2 h-4 w-4" />
                              Verify
                            </DropdownMenuItem>
                          )}
                          {onDelete && (
                            <DropdownMenuItem
                              onClick={() => onDelete(document)}
                              className="text-destructive"
                            >
                              <Trash2 className="mr-2 h-4 w-4" />
                              Delete
                            </DropdownMenuItem>
                          )}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  )}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </Card>
  );
}
