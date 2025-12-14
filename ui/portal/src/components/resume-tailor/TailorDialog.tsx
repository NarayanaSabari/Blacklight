/**
 * TailorDialog Component
 * Dialog to initiate resume tailoring for a job match
 * Uses simple REST API (no streaming)
 */

import { useState, useCallback } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  FileText,
  Sparkles,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  Loader2,
} from 'lucide-react';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';

import { resumeTailorApi } from '@/lib/resumeTailorApi';
import type { TailoredResume } from '@/types/tailoredResume';

interface TailorDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  candidateId: number;
  jobMatchId?: number;
  jobPostingId?: number;
  jobTitle: string;
  company: string;
  currentScore: number;
  onComplete?: (tailoredResume: TailoredResume) => void;
}

type TailorPhase = 'confirm' | 'processing' | 'complete' | 'error';

export function TailorDialog({
  open,
  onOpenChange,
  candidateId,
  jobMatchId,
  jobPostingId,
  jobTitle,
  company,
  currentScore,
  onComplete,
}: TailorDialogProps) {
  const queryClient = useQueryClient();
  
  const [phase, setPhase] = useState<TailorPhase>('confirm');
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TailoredResume | null>(null);

  // Simple REST API mutation
  const tailorMutation = useMutation({
    mutationFn: async () => {
      if (jobMatchId) {
        return resumeTailorApi.tailorFromMatch(candidateId, jobMatchId);
      } else if (jobPostingId) {
        return resumeTailorApi.tailorResume(candidateId, jobPostingId);
      }
      throw new Error('Either jobMatchId or jobPostingId is required');
    },
    onSuccess: (data) => {
      // The API returns the tailored resume directly (not wrapped)
      const tailoredResume = data as unknown as TailoredResume;
      setResult(tailoredResume);
      setPhase('complete');
      queryClient.invalidateQueries({ queryKey: ['candidateMatches', candidateId] });
      queryClient.invalidateQueries({ queryKey: ['tailoredResumes', candidateId] });
    },
    onError: (error: Error) => {
      setError(error.message || 'Failed to tailor resume');
      setPhase('error');
    },
  });

  const startTailoring = useCallback(() => {
    setPhase('processing');
    setError(null);
    tailorMutation.mutate();
  }, [tailorMutation]);

  const handleClose = useCallback(() => {
    setPhase('confirm');
    setError(null);
    setResult(null);
    onOpenChange(false);
  }, [onOpenChange]);

  const handleViewResult = useCallback(() => {
    if (result) {
      onComplete?.(result);
    }
    handleClose();
  }, [result, onComplete, handleClose]);

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        {/* Confirm Phase */}
        {phase === 'confirm' && (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-primary" />
                Tailor Resume
              </DialogTitle>
              <DialogDescription>
                AI will optimize the resume to better match this job posting
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <div className="rounded-lg border p-4 space-y-3">
                <div className="flex items-start gap-3">
                  <FileText className="h-5 w-5 text-muted-foreground mt-0.5" />
                  <div className="flex-1">
                    <p className="font-medium">{jobTitle}</p>
                    <p className="text-sm text-muted-foreground">{company}</p>
                  </div>
                  <Badge variant="secondary" className="text-sm">
                    {Math.round(currentScore)}% match
                  </Badge>
                </div>
              </div>

              <div className="space-y-2 text-sm text-muted-foreground">
                <p className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-green-600" />
                  Optimize keywords for ATS systems
                </p>
                <p className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-green-600" />
                  Highlight relevant skills & experience
                </p>
                <p className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-green-600" />
                  Improve match score with AI suggestions
                </p>
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={handleClose}>
                Cancel
              </Button>
              <Button onClick={startTailoring}>
                <Sparkles className="h-4 w-4 mr-2" />
                Start Tailoring
              </Button>
            </DialogFooter>
          </>
        )}

        {/* Processing Phase */}
        {phase === 'processing' && (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Loader2 className="h-5 w-5 text-primary animate-spin" />
                Tailoring Resume
              </DialogTitle>
              <DialogDescription>
                Please wait while AI optimizes the resume
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-6 py-6">
              <div className="flex flex-col items-center justify-center gap-4">
                <Loader2 className="h-12 w-12 text-primary animate-spin" />
                <p className="text-sm text-muted-foreground text-center">
                  Analyzing job requirements and optimizing resume...
                  <br />
                  This typically takes 15-30 seconds
                </p>
              </div>
            </div>
          </>
        )}

        {/* Complete Phase */}
        {phase === 'complete' && result && (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 text-green-600">
                <CheckCircle2 className="h-5 w-5" />
                Resume Tailored Successfully
              </DialogTitle>
              <DialogDescription>
                Your resume has been optimized for this job
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              {/* Score Improvement */}
              <div className="rounded-lg border bg-gradient-to-r from-green-50 to-emerald-50 p-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Match Score</p>
                    <div className="flex items-center gap-2">
                      <span className="text-lg font-semibold text-muted-foreground">
                        {Math.round(result.original_match_score)}%
                      </span>
                      <ArrowRight className="h-4 w-4 text-muted-foreground" />
                      <span className="text-2xl font-bold text-green-600">
                        {Math.round(result.tailored_match_score)}%
                      </span>
                    </div>
                  </div>
                  <Badge className="bg-green-600 text-lg px-3 py-1">
                    +{Math.round(result.score_improvement)}%
                  </Badge>
                </div>
              </div>

              {/* Skills Added */}
              {result.added_skills && result.added_skills.length > 0 && (
                <div className="space-y-2">
                  <p className="text-sm font-medium">Skills Highlighted</p>
                  <div className="flex flex-wrap gap-1.5">
                    {result.added_skills.slice(0, 6).map((skill, idx) => (
                      <Badge key={idx} variant="secondary" className="bg-green-50 text-green-700">
                        + {skill}
                      </Badge>
                    ))}
                    {result.added_skills.length > 6 && (
                      <Badge variant="outline">
                        +{result.added_skills.length - 6} more
                      </Badge>
                    )}
                  </div>
                </div>
              )}
            </div>

            <DialogFooter className="flex-col sm:flex-row gap-2">
              <Button variant="outline" onClick={handleClose} className="flex-1">
                Close
              </Button>
              <Button onClick={handleViewResult} className="flex-1">
                View Tailored Resume
              </Button>
            </DialogFooter>
          </>
        )}

        {/* Error Phase */}
        {phase === 'error' && (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 text-destructive">
                <AlertCircle className="h-5 w-5" />
                Tailoring Failed
              </DialogTitle>
            </DialogHeader>

            <div className="py-4">
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  {error || 'An unexpected error occurred'}
                </AlertDescription>
              </Alert>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={handleClose}>
                Close
              </Button>
              <Button onClick={startTailoring}>Try Again</Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
