/**
 * Resume Upload Component
 * Drag-and-drop file upload with preview
 */

import { useState, useCallback, useRef } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileText, X, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import type { UploadResumeResponse } from '@/types/candidate';

interface ResumeUploadProps {
  onUploadSuccess: (result: UploadResumeResponse) => void;
  onUploadError?: (error: string) => void;
  candidateId?: number; // If provided, uploads for existing candidate
}

// Global debounce to prevent multiple uploads from any instance
let lastUploadTime = 0;

export function ResumeUpload({ onUploadSuccess, onUploadError, candidateId }: ResumeUploadProps) {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      const selectedFile = acceptedFiles[0];

      // Validate file size (10MB max)
      const maxSize = 10 * 1024 * 1024; // 10MB
      if (selectedFile.size > maxSize) {
        setError('File size must be less than 10MB');
        return;
      }

      setFile(selectedFile);
      setError(null);
      setSuccess(false);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    },
    maxFiles: 1,
    multiple: false,
  });

  const removeFile = () => {
    setFile(null);
    setError(null);
    setSuccess(false);
    setProgress(0);
  };

  const uploadingRef = useRef(false);
  const uploadRequestIdRef = useRef<string | null>(null);

  const uploadFile = async (e?: React.MouseEvent) => {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }

    // Check if already uploading (synchronous check first)
    if (uploadingRef.current) {
      console.log('Upload blocked: already uploading');
      return;
    }

    // Global debounce check (2 second cooldown for safety)
    const now = Date.now();
    if (now - lastUploadTime < 2000) {
      console.log('Upload blocked: global debounce (too soon)');
      return;
    }

    if (!file) {
      console.log('Upload blocked: no file selected');
      return;
    }

    // Generate unique request ID
    const requestId = `${Date.now()}-${Math.random()}`;
    
    // Check if there's already a pending upload with a different request ID
    if (uploadRequestIdRef.current !== null) {
      console.log('Upload blocked: pending request exists');
      return;
    }

    // Lock the upload
    uploadingRef.current = true;
    uploadRequestIdRef.current = requestId;
    lastUploadTime = now;

    setUploading(true);
    setError(null);
    setProgress(0);

    console.log('Starting upload:', { file: file.name, requestId });

    try {
      // Simulate progress
      const progressInterval = setInterval(() => {
        setProgress((prev) => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 200);

      // Import API dynamically to avoid circular dependency
      const { candidateApi } = await import('@/lib/candidateApi');

      let result: UploadResumeResponse;

      if (candidateId) {
        result = await candidateApi.uploadResumeForCandidate(candidateId, file);
      } else {
        result = await candidateApi.uploadResume(file);
      }

      clearInterval(progressInterval);
      setProgress(100);

      console.log('Upload completed:', { requestId, status: result.status });

      // Success includes both immediate success and async processing
      if (result.status === 'success' || result.status === 'processing') {
        setSuccess(true);
        // Keep the lock during the success callback
        setTimeout(() => {
          onUploadSuccess(result);
        }, 500);
      } else {
        // Only 'error' status reaches here
        throw new Error(result.error || 'Upload failed');
      }
    } catch (err) {
      console.error('Upload error:', { requestId, error: err });
      const errorMessage = err instanceof Error ? err.message : 'Failed to upload resume';
      setError(errorMessage);
      if (onUploadError) {
        onUploadError(errorMessage);
      }
      // Reset locks on error
      uploadingRef.current = false;
      uploadRequestIdRef.current = null;
    } finally {
      setUploading(false);
      // Only reset locks if there was an error (not success)
      if (!success) {
        uploadingRef.current = false;
        uploadRequestIdRef.current = null;
      }
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <div className="space-y-4">
      {/* Dropzone */}
      {!file && (
        <div
          {...getRootProps()}
          className={`
            border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
            ${isDragActive
              ? 'border-primary bg-primary/5'
              : 'border-slate-300 hover:border-primary/50 hover:bg-slate-50'
            }
          `}
        >
          <input {...getInputProps()} />
          <Upload className="h-12 w-12 text-slate-400 mx-auto mb-4" />
          {isDragActive ? (
            <p className="text-lg font-medium text-primary">Drop resume here...</p>
          ) : (
            <>
              <p className="text-lg font-medium text-slate-900 mb-1">
                Drag & drop resume here
              </p>
              <p className="text-sm text-slate-600 mb-4">
                or click to browse files
              </p>
              <p className="text-xs text-slate-500">
                Supports PDF and DOCX files (max 10MB)
              </p>
            </>
          )}
        </div>
      )}

      {/* File Preview */}
      {file && (
        <div className="border border-slate-200 rounded-lg p-4 space-y-4">
          <div className="flex items-start gap-4">
            <div className="flex-shrink-0">
              <FileText className="h-10 w-10 text-primary" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-medium text-slate-900 truncate">{file.name}</p>
              <p className="text-sm text-slate-600">{formatFileSize(file.size)}</p>
            </div>
            {!uploading && !success && (
              <Button
                variant="ghost"
                size="sm"
                onClick={removeFile}
                className="flex-shrink-0"
              >
                <X className="h-4 w-4" />
              </Button>
            )}
          </div>

          {/* Progress Bar */}
          {uploading && (
            <div className="space-y-2">
              <Progress value={progress} className="h-2" />
              <p className="text-sm text-slate-600 text-center">
                {progress < 90 ? 'Uploading resume...' : 'Finalizing upload...'}
              </p>
            </div>
          )}

          {/* Success Message */}
          {success && (
            <Alert className="bg-green-50 border-green-200">
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              <AlertDescription className="text-green-800">
                <div className="space-y-1">
                  <p className="font-medium">Resume uploaded successfully!</p>
                  <p className="text-sm text-green-700">
                    AI parsing in progress. Check "Pending Review" in a moment.
                  </p>
                </div>
              </AlertDescription>
            </Alert>
          )}

          {/* Upload Button */}
          {!uploading && !success && (
            <Button
              type="button"
              onClick={uploadFile}
              disabled={!file || uploading}
              className="w-full gap-2"
            >
              <Upload className="h-4 w-4" />
              Upload & Parse Resume
            </Button>
          )}
        </div>
      )}

      {/* Error Message */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
    </div>
  );
}
