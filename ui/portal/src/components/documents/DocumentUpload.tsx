/**
 * DocumentUpload Component
 * Reusable file upload with drag-drop, validation, and preview
 * Supports multiple files with progress tracking
 */

import { useCallback, useState } from 'react';
import { useDropzone, type FileRejection } from 'react-dropzone';
import { X, Upload, FileText, AlertCircle, CheckCircle2, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

export interface UploadedFile {
  file: File;
  preview?: string;
  progress: number;
  status: 'pending' | 'uploading' | 'success' | 'error';
  error?: string;
  documentType: string;
}

interface DocumentUploadProps {
  onFilesChange: (files: UploadedFile[]) => void;
  maxFiles?: number;
  maxSizeInMB?: number;
  acceptedFileTypes?: string[];
  documentType: string;
  label?: string;
  description?: string;
  disabled?: boolean;
  className?: string;
}

const DEFAULT_ACCEPTED_TYPES = [
  'application/pdf',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'image/jpeg',
  'image/png',
];

const FILE_TYPE_LABELS: Record<string, string> = {
  'application/pdf': 'PDF',
  'application/msword': 'DOC',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'DOCX',
  'image/jpeg': 'JPEG',
  'image/png': 'PNG',
};

export function DocumentUpload({
  onFilesChange,
  maxFiles = 5,
  maxSizeInMB = 10,
  acceptedFileTypes = DEFAULT_ACCEPTED_TYPES,
  documentType,
  label = 'Upload Documents',
  description = 'Drag and drop files here, or click to select',
  disabled = false,
  className,
}: DocumentUploadProps) {
  const [files, setFiles] = useState<UploadedFile[]>([]);

  const onDrop = useCallback(
    (acceptedFiles: File[], rejectedFiles: FileRejection[]) => {
      // Handle rejected files
      if (rejectedFiles.length > 0) {
        const newRejectedFiles: UploadedFile[] = rejectedFiles.map(({ file, errors }) => ({
          file,
          progress: 0,
          status: 'error' as const,
          error: errors[0]?.message || 'File rejected',
          documentType,
        }));
        setFiles((prev) => [...prev, ...newRejectedFiles]);
        setTimeout(() => {
          setFiles((prev) => prev.filter((f) => f.status !== 'error'));
        }, 5000);
      }

      // Handle accepted files
      const newFiles: UploadedFile[] = acceptedFiles.map((file) => ({
        file,
        preview: file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined,
        progress: 0,
        status: 'pending' as const,
        documentType,
      }));

      const updatedFiles = [...files, ...newFiles].slice(0, maxFiles);
      setFiles(updatedFiles);
      onFilesChange(updatedFiles);
    },
    [files, maxFiles, onFilesChange, documentType]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: acceptedFileTypes.reduce((acc, type) => ({ ...acc, [type]: [] }), {}),
    maxSize: maxSizeInMB * 1024 * 1024,
    maxFiles: maxFiles - files.length,
    disabled: disabled || files.length >= maxFiles,
  });

  const removeFile = (index: number) => {
    const updatedFiles = files.filter((_, i) => i !== index);
    setFiles(updatedFiles);
    onFilesChange(updatedFiles);
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const getFileTypeLabel = (mimeType: string): string => {
    return FILE_TYPE_LABELS[mimeType] || mimeType.split('/')[1]?.toUpperCase() || 'FILE';
  };

  const getStatusIcon = (status: UploadedFile['status']) => {
    switch (status) {
      case 'uploading':
        return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />;
      case 'success':
        return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case 'error':
        return <AlertCircle className="h-4 w-4 text-destructive" />;
      default:
        return <FileText className="h-4 w-4 text-muted-foreground" />;
    }
  };

  return (
    <div className={cn('space-y-4', className)}>
      {/* Upload Area */}
      <div
        {...getRootProps()}
        className={cn(
          'border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors',
          isDragActive && 'border-primary bg-primary/5',
          disabled || files.length >= maxFiles
            ? 'opacity-50 cursor-not-allowed bg-muted'
            : 'hover:border-primary hover:bg-accent/50',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
        )}
      >
        <input {...getInputProps()} />
        <div className="flex flex-col items-center gap-2">
          <div className="rounded-full bg-primary/10 p-4">
            <Upload className="h-6 w-6 text-primary" />
          </div>
          <div>
            <p className="font-medium">{label}</p>
            <p className="text-sm text-muted-foreground">{description}</p>
          </div>
          <div className="text-xs text-muted-foreground space-y-1">
            <p>
              Accepted: {acceptedFileTypes.map((type) => getFileTypeLabel(type)).join(', ')}
            </p>
            <p>
              Max size: {maxSizeInMB}MB • Max files: {maxFiles}
            </p>
          </div>
        </div>
      </div>

      {/* File List */}
      {files.length > 0 && (
        <div className="space-y-2">
          {files.map((uploadedFile, index) => (
            <Card key={index} className="p-4">
              <div className="flex items-start gap-3">
                {/* File Icon/Preview */}
                <div className="flex-shrink-0">
                  {uploadedFile.preview ? (
                    <img
                      src={uploadedFile.preview}
                      alt={uploadedFile.file.name}
                      className="h-12 w-12 rounded object-cover"
                    />
                  ) : (
                    <div className="h-12 w-12 rounded bg-muted flex items-center justify-center">
                      <FileText className="h-6 w-6 text-muted-foreground" />
                    </div>
                  )}
                </div>

                {/* File Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <p className="font-medium truncate">{uploadedFile.file.name}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge variant="outline" className="text-xs">
                          {getFileTypeLabel(uploadedFile.file.type)}
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          {formatFileSize(uploadedFile.file.size)}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {getStatusIcon(uploadedFile.status)}
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6"
                        onClick={() => removeFile(index)}
                        disabled={uploadedFile.status === 'uploading'}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>

                  {/* Progress Bar */}
                  {uploadedFile.status === 'uploading' && (
                    <Progress value={uploadedFile.progress} className="mt-2" />
                  )}

                  {/* Error Message */}
                  {uploadedFile.status === 'error' && uploadedFile.error && (
                    <p className="text-xs text-destructive mt-2">{uploadedFile.error}</p>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
