/**
 * Resume List Component
 * Shows all resumes for a candidate with primary badge and actions
 */

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  FileText,
  Star,
  StarOff,
  Download,
  Trash2,
  RefreshCw,
  Upload,
  Loader2,
  AlertCircle,
  CheckCircle,
  Clock,
  XCircle,
  ShieldCheck,
  ShieldX,
} from 'lucide-react';
import { toast } from 'sonner';

import { candidateApi } from '@/lib/candidateApi';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import type { CandidateResume, ResumeProcessingStatus } from '@/types/candidate';

interface ResumeListProps {
  candidateId: number;
  onUpload?: () => void;
  showUploadButton?: boolean;
}

const STATUS_CONFIG: Record<ResumeProcessingStatus, { icon: React.ReactNode; color: string; label: string }> = {
  pending: { icon: <Clock className="h-4 w-4" />, color: 'bg-yellow-100 text-yellow-800', label: 'Pending' },
  processing: { icon: <Loader2 className="h-4 w-4 animate-spin" />, color: 'bg-blue-100 text-blue-800', label: 'Processing' },
  completed: { icon: <CheckCircle className="h-4 w-4" />, color: 'bg-green-100 text-green-800', label: 'Completed' },
  failed: { icon: <XCircle className="h-4 w-4" />, color: 'bg-red-100 text-red-800', label: 'Failed' },
};

export function ResumeList({ candidateId, onUpload, showUploadButton = true }: ResumeListProps) {
  const queryClient = useQueryClient();
  const [deleteResumeId, setDeleteResumeId] = useState<number | null>(null);

  // Fetch resumes
  const { data, isLoading, error } = useQuery({
    queryKey: ['candidate-resumes', candidateId],
    queryFn: () => candidateApi.listResumes(candidateId),
    staleTime: 0,
  });

  // Set primary mutation
  const setPrimaryMutation = useMutation({
    mutationFn: (resumeId: number) => candidateApi.setResumePrimary(candidateId, resumeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['candidate-resumes', candidateId] });
      queryClient.invalidateQueries({ queryKey: ['candidate', candidateId] });
      toast.success('Resume set as primary');
    },
    onError: (error: Error) => {
      toast.error(`Failed to set primary: ${error.message}`);
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (resumeId: number) => candidateApi.deleteResume(candidateId, resumeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['candidate-resumes', candidateId] });
      queryClient.invalidateQueries({ queryKey: ['candidate', candidateId] });
      toast.success('Resume deleted');
      setDeleteResumeId(null);
    },
    onError: (error: Error) => {
      toast.error(`Failed to delete: ${error.message}`);
      setDeleteResumeId(null);
    },
  });

  // Reparse mutation
  const reparseMutation = useMutation({
    mutationFn: (resumeId: number) => candidateApi.reparseSpecificResume(candidateId, resumeId, true),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['candidate-resumes', candidateId] });
      queryClient.invalidateQueries({ queryKey: ['candidate', candidateId] });
      toast.success('Resume re-parsing started');
    },
    onError: (error: Error) => {
      toast.error(`Failed to reparse: ${error.message}`);
    },
  });

  // Download handler
  const handleDownload = async (resume: CandidateResume) => {
    try {
      const url = await candidateApi.getResumeDownloadUrl(candidateId, resume.id);
      window.open(url, '_blank');
    } catch (error) {
      toast.error('Failed to download resume');
    }
  };

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return 'Unknown size';
    const mb = bytes / (1024 * 1024);
    return mb >= 1 ? `${mb.toFixed(1)} MB` : `${(bytes / 1024).toFixed(1)} KB`;
  };

  const formatDate = (dateStr?: string | null) => {
    if (!dateStr) return 'Unknown';
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  if (isLoading) {
    return (
      <Card className="border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Resumes
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Resumes
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2 text-red-600">
            <AlertCircle className="h-5 w-5" />
            <span>Failed to load resumes</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  const resumes = data?.resumes || [];

  return (
    <>
      <Card className="border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Resumes
              {resumes.length > 0 && (
                <Badge variant="secondary" className="ml-2">
                  {resumes.length}
                </Badge>
              )}
            </CardTitle>
            {showUploadButton && onUpload && (
              <Button variant="outline" size="sm" onClick={onUpload}>
                <Upload className="h-4 w-4 mr-2" />
                Upload New
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {resumes.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <FileText className="h-12 w-12 mx-auto mb-2 opacity-50" />
              <p>No resumes uploaded yet</p>
              {showUploadButton && onUpload && (
                <Button variant="outline" size="sm" className="mt-4" onClick={onUpload}>
                  <Upload className="h-4 w-4 mr-2" />
                  Upload Resume
                </Button>
              )}
            </div>
          ) : (
            <div className="space-y-3">
              {resumes.map((resume) => {
                const statusConfig = STATUS_CONFIG[resume.processing_status];
                return (
                  <div
                    key={resume.id}
                    className={`p-4 rounded-lg border-2 ${
                      resume.is_primary
                        ? 'border-primary bg-primary/5'
                        : 'border-gray-200 bg-white'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-medium text-sm truncate max-w-[200px]">
                            {resume.original_filename}
                          </span>
                          {resume.is_primary && (
                            <Badge className="bg-primary text-primary-foreground">
                              <Star className="h-3 w-3 mr-1" />
                              Primary
                            </Badge>
                          )}
                          <Badge className={statusConfig.color}>
                            {statusConfig.icon}
                            <span className="ml-1">{statusConfig.label}</span>
                          </Badge>
                          {/* Document verification status */}
                          {resume.is_verified === true && (
                            <Badge className="bg-emerald-100 text-emerald-800">
                              <ShieldCheck className="h-4 w-4" />
                              <span className="ml-1">Verified</span>
                            </Badge>
                          )}
                          {resume.is_verified === false && (
                            <Badge className="bg-orange-100 text-orange-800">
                              <ShieldX className="h-4 w-4" />
                              <span className="ml-1">Unverified</span>
                            </Badge>
                          )}
                        </div>
                        <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                          <span>{formatFileSize(resume.file_size)}</span>
                          <span>Uploaded {formatDate(resume.uploaded_at)}</span>
                          {resume.uploaded_by_candidate && (
                            <Badge variant="outline" className="text-xs">
                              By Candidate
                            </Badge>
                          )}
                        </div>
                        {resume.processing_error && (
                          <p className="text-xs text-red-600 mt-1">{resume.processing_error}</p>
                        )}
                      </div>

                      <div className="flex items-center gap-1">
                        <TooltipProvider>
                          {!resume.is_primary && (
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="h-8 w-8"
                                  onClick={() => setPrimaryMutation.mutate(resume.id)}
                                  disabled={setPrimaryMutation.isPending}
                                >
                                  <StarOff className="h-4 w-4" />
                                </Button>
                              </TooltipTrigger>
                              <TooltipContent>Set as Primary</TooltipContent>
                            </Tooltip>
                          )}

                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8"
                                onClick={() => handleDownload(resume)}
                              >
                                <Download className="h-4 w-4" />
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>Download</TooltipContent>
                          </Tooltip>

                          {resume.processing_status !== 'processing' && (
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="h-8 w-8"
                                  onClick={() => reparseMutation.mutate(resume.id)}
                                  disabled={reparseMutation.isPending}
                                >
                                  <RefreshCw
                                    className={`h-4 w-4 ${reparseMutation.isPending ? 'animate-spin' : ''}`}
                                  />
                                </Button>
                              </TooltipTrigger>
                              <TooltipContent>Re-parse</TooltipContent>
                            </Tooltip>
                          )}

                          {resumes.length > 1 && (
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="h-8 w-8 text-red-600 hover:text-red-700"
                                  onClick={() => setDeleteResumeId(resume.id)}
                                >
                                  <Trash2 className="h-4 w-4" />
                                </Button>
                              </TooltipTrigger>
                              <TooltipContent>Delete</TooltipContent>
                            </Tooltip>
                          )}
                        </TooltipProvider>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteResumeId !== null} onOpenChange={(open) => !open && setDeleteResumeId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Resume</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this resume? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-red-600 hover:bg-red-700"
              onClick={() => deleteResumeId && deleteMutation.mutate(deleteResumeId)}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : null}
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
