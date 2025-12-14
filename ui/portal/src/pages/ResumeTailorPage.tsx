/**
 * Resume Tailor Page
 * 
 * Dedicated page for AI-powered resume tailoring with:
 * - Step-by-step tailoring process visualization
 * - Side-by-side comparison with diff highlighting
 * - Export options (PDF, DOCX, Markdown)
 * - Progress tracking and status updates
 */

import React, { useState, useMemo, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  ArrowLeft,
  Sparkles,
  FileText,
  CheckCircle2,
  XCircle,
  Plus,
  TrendingUp,
  Download,
  FileType,
  Eye,
  Code,
  Loader2,
  RefreshCw,
  Briefcase,
  Building2,
  MapPin,
  Zap,
  ArrowRight,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

import { resumeTailorApi } from '@/lib/resumeTailorApi';
import { jobMatchApi } from '@/lib/jobMatchApi';
import { candidateApi } from '@/lib/candidateApi';
import type { TailoredResume, ExportFormat } from '@/types/tailoredResume';

// ============================================================================
// Markdown Renderer Component
// ============================================================================
function MarkdownRenderer({ content, className = '' }: { content: string; className?: string }) {
  const renderedContent = useMemo(() => {
    if (!content) return null;
    
    const lines = content.split('\n');
    const elements: React.ReactElement[] = [];
    let inCodeBlock = false;
    let codeBlockContent: string[] = [];
    let listItems: string[] = [];
    let listType: 'ul' | 'ol' | null = null;
    
    const flushList = () => {
      if (listItems.length > 0 && listType) {
        const ListTag = listType;
        elements.push(
          <ListTag key={`list-${elements.length}`} className={listType === 'ul' ? 'list-disc ml-6 my-2 space-y-1' : 'list-decimal ml-6 my-2 space-y-1'}>
            {listItems.map((item, i) => (
              <li key={i} className="text-sm text-gray-700">{processInlineMarkdown(item)}</li>
            ))}
          </ListTag>
        );
        listItems = [];
        listType = null;
      }
    };
    
    const processInlineMarkdown = (text: string): React.ReactNode => {
      const parts: React.ReactNode[] = [];
      let remaining = text;
      let key = 0;
      
      while (remaining.length > 0) {
        const boldMatch = remaining.match(/^(.*?)(\*\*|__)(.+?)\2(.*)$/s);
        if (boldMatch) {
          if (boldMatch[1]) parts.push(boldMatch[1]);
          parts.push(<strong key={key++} className="font-semibold">{boldMatch[3]}</strong>);
          remaining = boldMatch[4];
          continue;
        }
        
        const codeMatch = remaining.match(/^(.*?)`([^`]+)`(.*)$/s);
        if (codeMatch) {
          if (codeMatch[1]) parts.push(codeMatch[1]);
          parts.push(
            <code key={key++} className="bg-gray-100 px-1.5 py-0.5 rounded text-sm font-mono text-pink-600">
              {codeMatch[2]}
            </code>
          );
          remaining = codeMatch[3];
          continue;
        }
        
        parts.push(remaining);
        break;
      }
      
      return parts.length === 1 ? parts[0] : <>{parts}</>;
    };
    
    lines.forEach((line, index) => {
      if (line.startsWith('```')) {
        if (inCodeBlock) {
          elements.push(
            <pre key={`code-${index}`} className="bg-gray-900 text-gray-100 p-3 rounded-lg my-2 overflow-x-auto text-sm font-mono">
              {codeBlockContent.join('\n')}
            </pre>
          );
          codeBlockContent = [];
          inCodeBlock = false;
        } else {
          flushList();
          inCodeBlock = true;
        }
        return;
      }
      
      if (inCodeBlock) {
        codeBlockContent.push(line);
        return;
      }
      
      if (!line.trim()) {
        flushList();
        elements.push(<div key={`empty-${index}`} className="h-2" />);
        return;
      }
      
      const headerMatch = line.match(/^(#{1,6})\s+(.+)$/);
      if (headerMatch) {
        flushList();
        const level = headerMatch[1].length;
        const text = headerMatch[2];
        const headerClasses: Record<number, string> = {
          1: 'text-2xl font-bold text-gray-900 mt-4 mb-2 border-b pb-2',
          2: 'text-xl font-bold text-gray-800 mt-3 mb-2',
          3: 'text-lg font-semibold text-gray-800 mt-2 mb-1',
          4: 'text-base font-semibold text-gray-700 mt-2 mb-1',
          5: 'text-sm font-semibold text-gray-700 mt-1 mb-1',
          6: 'text-sm font-medium text-gray-600 mt-1 mb-1',
        };
        elements.push(
          <div key={`h-${index}`} className={headerClasses[level]}>
            {processInlineMarkdown(text)}
          </div>
        );
        return;
      }
      
      if (line.match(/^(-{3,}|\*{3,}|_{3,})$/)) {
        flushList();
        elements.push(<Separator key={`hr-${index}`} className="my-3" />);
        return;
      }
      
      const ulMatch = line.match(/^(\s*)[-*+]\s+(.+)$/);
      if (ulMatch) {
        if (listType !== 'ul') {
          flushList();
          listType = 'ul';
        }
        listItems.push(ulMatch[2]);
        return;
      }
      
      const olMatch = line.match(/^(\s*)\d+\.\s+(.+)$/);
      if (olMatch) {
        if (listType !== 'ol') {
          flushList();
          listType = 'ol';
        }
        listItems.push(olMatch[2]);
        return;
      }
      
      if (line.startsWith('>')) {
        flushList();
        const quoteText = line.replace(/^>\s*/, '');
        elements.push(
          <blockquote key={`quote-${index}`} className="border-l-4 border-gray-300 pl-4 py-1 my-2 text-gray-600 italic">
            {processInlineMarkdown(quoteText)}
          </blockquote>
        );
        return;
      }
      
      flushList();
      elements.push(
        <p key={`p-${index}`} className="text-sm text-gray-700 my-1 leading-relaxed">
          {processInlineMarkdown(line)}
        </p>
      );
    });
    
    flushList();
    return elements;
  }, [content]);
  
  return <div className={`prose prose-sm max-w-none ${className}`}>{renderedContent}</div>;
}

// ============================================================================
// Diff View Component
// ============================================================================
function DiffView({ original, tailored }: { original: string; tailored: string }) {
  const diffLines = useMemo(() => {
    const originalLines = original?.split('\n') || [];
    const tailoredLines = tailored?.split('\n') || [];
    const result: Array<{ type: 'same' | 'added' | 'removed' | 'changed'; original?: string; tailored?: string }> = [];
    const maxLen = Math.max(originalLines.length, tailoredLines.length);
    
    for (let i = 0; i < maxLen; i++) {
      const origLine = originalLines[i];
      const tailLine = tailoredLines[i];
      
      if (origLine === tailLine) {
        result.push({ type: 'same', original: origLine });
      } else if (origLine === undefined) {
        result.push({ type: 'added', tailored: tailLine });
      } else if (tailLine === undefined) {
        result.push({ type: 'removed', original: origLine });
      } else {
        result.push({ type: 'changed', original: origLine, tailored: tailLine });
      }
    }
    return result;
  }, [original, tailored]);
  
  return (
    <div className="font-mono text-sm">
      {diffLines.map((line, idx) => {
        if (line.type === 'same') {
          return (
            <div key={idx} className="px-3 py-0.5 text-gray-600 hover:bg-gray-50">
              <span className="select-none text-gray-400 mr-3">{' '}</span>
              {line.original}
            </div>
          );
        }
        if (line.type === 'removed') {
          return (
            <div key={idx} className="px-3 py-0.5 bg-red-50 text-red-800 border-l-4 border-red-400">
              <span className="select-none text-red-400 mr-3">-</span>
              {line.original}
            </div>
          );
        }
        if (line.type === 'added') {
          return (
            <div key={idx} className="px-3 py-0.5 bg-green-50 text-green-800 border-l-4 border-green-400">
              <span className="select-none text-green-400 mr-3">+</span>
              {line.tailored}
            </div>
          );
        }
        return (
          <div key={idx}>
            <div className="px-3 py-0.5 bg-red-50 text-red-800 border-l-4 border-red-400">
              <span className="select-none text-red-400 mr-3">-</span>
              {line.original}
            </div>
            <div className="px-3 py-0.5 bg-green-50 text-green-800 border-l-4 border-green-400">
              <span className="select-none text-green-400 mr-3">+</span>
              {line.tailored}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ============================================================================
// Processing Steps Component
// ============================================================================
const TAILOR_STEPS = [
  { id: 'analyzing', label: 'Analyzing Job Requirements', icon: Briefcase },
  { id: 'evaluating', label: 'Evaluating Resume', icon: FileText },
  { id: 'generating', label: 'AI Generating Improvements', icon: Sparkles },
  { id: 'applying', label: 'Applying Enhancements', icon: Zap },
  { id: 'scoring', label: 'Calculating New Score', icon: TrendingUp },
  { id: 'complete', label: 'Complete!', icon: CheckCircle2 },
];

function ProcessingSteps({ currentStep, progress }: { currentStep: number; progress: number }) {
  return (
    <div className="space-y-4">
      {TAILOR_STEPS.map((step, idx) => {
        const Icon = step.icon;
        const isActive = idx === currentStep;
        const isComplete = idx < currentStep;
        
        return (
          <div key={step.id} className={`flex items-center gap-4 p-3 rounded-lg transition-all ${
            isActive ? 'bg-primary/10 border border-primary/30' : 
            isComplete ? 'bg-green-50' : 'bg-gray-50'
          }`}>
            <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
              isActive ? 'bg-primary text-white' :
              isComplete ? 'bg-green-500 text-white' : 'bg-gray-200 text-gray-500'
            }`}>
              {isActive ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : isComplete ? (
                <CheckCircle2 className="h-5 w-5" />
              ) : (
                <Icon className="h-5 w-5" />
              )}
            </div>
            <div className="flex-1">
              <p className={`font-medium ${
                isActive ? 'text-primary' :
                isComplete ? 'text-green-700' : 'text-gray-500'
              }`}>
                {step.label}
              </p>
              {isActive && (
                <Progress value={progress} className="h-1.5 mt-2" />
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ============================================================================
// Main Page Component
// ============================================================================
export function ResumeTailorPage() {
  const { candidateId, matchId } = useParams<{ candidateId: string; matchId: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  
  // State
  const [phase, setPhase] = useState<'ready' | 'processing' | 'complete' | 'error'>('ready');
  const [currentStep, setCurrentStep] = useState(0);
  const [progress, setProgress] = useState(0);
  const [viewMode, setViewMode] = useState<'rendered' | 'raw' | 'diff'>('diff');
  const [tailoredResume, setTailoredResume] = useState<TailoredResume | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  const candidateIdNum = parseInt(candidateId || '0', 10);
  const matchIdNum = parseInt(matchId || '0', 10);
  const existingTailorId = searchParams.get('tailorId');

  // Fetch match data
  const { data: matchData, isLoading: matchLoading } = useQuery({
    queryKey: ['jobMatch', matchIdNum],
    queryFn: async () => {
      const matches = await jobMatchApi.getCandidateMatches(candidateIdNum, { page: 1, per_page: 100 });
      return matches.matches.find(m => m.id === matchIdNum);
    },
    enabled: !!matchIdNum && !!candidateIdNum,
  });

  // Fetch candidate data (for future use)
  useQuery({
    queryKey: ['candidate', candidateIdNum],
    queryFn: () => candidateApi.getCandidate(candidateIdNum),
    enabled: !!candidateIdNum,
  });

  // Fetch existing tailored resume if tailorId provided
  const { data: existingTailored, isLoading: existingLoading } = useQuery({
    queryKey: ['tailoredResume', existingTailorId],
    queryFn: () => resumeTailorApi.getTailoredResume(existingTailorId!),
    enabled: !!existingTailorId,
  });

  // Set existing resume and skip to complete phase
  useEffect(() => {
    if (existingTailored && !tailoredResume) {
      setTailoredResume(existingTailored);
      setPhase('complete');
    }
  }, [existingTailored, tailoredResume]);

  // Tailor mutation
  const tailorMutation = useMutation({
    mutationFn: () => resumeTailorApi.tailorFromMatch(matchIdNum),
    onSuccess: (data: TailoredResume | { tailored_resume: TailoredResume }) => {
      const result = 'tailored_resume' in data ? data.tailored_resume : data;
      setTailoredResume(result);
      setPhase('complete');
      setCurrentStep(5);
      setProgress(100);
      queryClient.invalidateQueries({ queryKey: ['candidateMatches', candidateIdNum] });
      toast.success('Resume tailored successfully!');
    },
    onError: (err: Error & { response?: { data?: { message?: string } } }) => {
      setError(err?.response?.data?.message || err.message || 'Failed to tailor resume');
      setPhase('error');
      toast.error('Tailoring failed');
    },
  });

  // Export mutation
  const exportMutation = useMutation({
    mutationFn: ({ format }: { format: ExportFormat }) => 
      resumeTailorApi.downloadResume(tailoredResume!.tailor_id, format),
    onSuccess: (_, { format }) => {
      toast.success(`Downloaded as ${format.toUpperCase()}`);
    },
    onError: () => {
      toast.error('Export failed');
    },
  });

  // Start tailoring process
  const startTailoring = () => {
    setPhase('processing');
    setError(null);
    setCurrentStep(0);
    setProgress(0);
    
    // Simulate step progress
    const stepDurations = [3000, 4000, 8000, 3000, 5000];
    let totalTime = 0;
    
    stepDurations.forEach((duration, idx) => {
      setTimeout(() => {
        setCurrentStep(idx);
        // Animate progress within step
        const stepProgress = setInterval(() => {
          setProgress(prev => Math.min(prev + 5, 100));
        }, duration / 20);
        
        setTimeout(() => clearInterval(stepProgress), duration);
      }, totalTime);
      totalTime += duration;
    });
    
    tailorMutation.mutate();
  };

  const handleBack = () => {
    navigate(`/candidates/${candidateIdNum}/matches`);
  };

  const job = matchData?.job || matchData?.job_posting;

  if (matchLoading || existingLoading) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        <Skeleton className="h-8 w-32 mb-6" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Skeleton className="h-96" />
          <Skeleton className="h-96 lg:col-span-2" />
        </div>
      </div>
    );
  }

  if (!matchData || !job) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        <Button variant="ghost" onClick={handleBack} className="mb-6">
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Matches
        </Button>
        <Alert variant="destructive">
          <XCircle className="h-4 w-4" />
          <AlertTitle>Match Not Found</AlertTitle>
          <AlertDescription>The job match could not be found.</AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" onClick={handleBack}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Sparkles className="h-6 w-6 text-primary" />
              Resume Tailor
            </h1>
            <p className="text-muted-foreground">
              AI-powered resume optimization for {job.title} at {job.company}
            </p>
          </div>
        </div>
        
        {phase === 'complete' && tailoredResume && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button>
                <Download className="h-4 w-4 mr-2" />
                Export
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuItem onClick={() => exportMutation.mutate({ format: 'pdf' })}>
                <FileText className="h-4 w-4 mr-2" />
                Download PDF
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => exportMutation.mutate({ format: 'docx' })}>
                <FileType className="h-4 w-4 mr-2" />
                Download Word
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => exportMutation.mutate({ format: 'markdown' })}>
                <Code className="h-4 w-4 mr-2" />
                Download Markdown
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Panel - Job Info & Controls */}
        <div className="space-y-6">
          {/* Job Card */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">{job.title}</CardTitle>
              <CardDescription className="flex items-center gap-2">
                <Building2 className="h-4 w-4" />
                {job.company}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <MapPin className="h-4 w-4" />
                {job.location}
                {job.is_remote && <Badge variant="secondary">Remote</Badge>}
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Current Match</span>
                <Badge variant="outline" className="text-lg font-bold">
                  {Math.round(matchData.match_score)}%
                </Badge>
              </div>
              {phase === 'complete' && tailoredResume && (
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">After Tailoring</span>
                  <Badge className="bg-green-600 text-lg font-bold">
                    {Math.round(tailoredResume.tailored_match_score)}%
                  </Badge>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Processing Steps or Controls */}
          {phase === 'ready' && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Sparkles className="h-5 w-5" />
                  Ready to Optimize
                </CardTitle>
                <CardDescription>
                  AI will analyze the job requirements and enhance your resume to better match this position.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button onClick={startTailoring} className="w-full" size="lg">
                  <Sparkles className="h-5 w-5 mr-2" />
                  Start Tailoring
                </Button>
              </CardContent>
            </Card>
          )}

          {phase === 'processing' && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Loader2 className="h-5 w-5 animate-spin" />
                  Tailoring in Progress
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ProcessingSteps currentStep={currentStep} progress={progress} />
              </CardContent>
            </Card>
          )}

          {phase === 'complete' && tailoredResume && (
            <Card className="border-green-200 bg-green-50/50">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2 text-green-700">
                  <CheckCircle2 className="h-5 w-5" />
                  Tailoring Complete
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div>
                    <p className="text-2xl font-bold">{Math.round(tailoredResume.original_match_score)}%</p>
                    <p className="text-xs text-muted-foreground">Original</p>
                  </div>
                  <div className="flex items-center justify-center">
                    <ArrowRight className="h-5 w-5 text-muted-foreground" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-green-600">{Math.round(tailoredResume.tailored_match_score)}%</p>
                    <p className="text-xs text-muted-foreground">Tailored</p>
                  </div>
                </div>
                <div className="text-center">
                  <Badge className="bg-green-600 text-lg px-4 py-1">
                    +{Math.round(tailoredResume.score_improvement)}% Improvement
                  </Badge>
                </div>
                <Separator />
                <Button variant="outline" className="w-full" onClick={() => {
                  setPhase('ready');
                  setTailoredResume(null);
                }}>
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Tailor Again
                </Button>
              </CardContent>
            </Card>
          )}

          {phase === 'error' && (
            <Alert variant="destructive">
              <XCircle className="h-4 w-4" />
              <AlertTitle>Tailoring Failed</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
              <Button variant="outline" size="sm" className="mt-3" onClick={() => setPhase('ready')}>
                Try Again
              </Button>
            </Alert>
          )}

          {/* Skills Summary */}
          {phase === 'complete' && tailoredResume && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <TrendingUp className="h-5 w-5" />
                  Skills Analysis
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {tailoredResume.matched_skills && tailoredResume.matched_skills.length > 0 && (
                  <div>
                    <p className="text-sm font-medium text-green-700 mb-2 flex items-center gap-1">
                      <CheckCircle2 className="h-4 w-4" />
                      Matched ({tailoredResume.matched_skills.length})
                    </p>
                    <div className="flex flex-wrap gap-1">
                      {tailoredResume.matched_skills.slice(0, 6).map((skill, i) => (
                        <Badge key={i} variant="secondary" className="bg-green-100 text-green-700">
                          {skill}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
                {tailoredResume.added_skills && tailoredResume.added_skills.length > 0 && (
                  <div>
                    <p className="text-sm font-medium text-blue-700 mb-2 flex items-center gap-1">
                      <Plus className="h-4 w-4" />
                      Highlighted ({tailoredResume.added_skills.length})
                    </p>
                    <div className="flex flex-wrap gap-1">
                      {tailoredResume.added_skills.map((skill, i) => (
                        <Badge key={i} variant="secondary" className="bg-blue-100 text-blue-700">
                          + {skill}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
                {tailoredResume.missing_skills && tailoredResume.missing_skills.length > 0 && (
                  <div>
                    <p className="text-sm font-medium text-orange-700 mb-2 flex items-center gap-1">
                      <XCircle className="h-4 w-4" />
                      To Develop ({tailoredResume.missing_skills.length})
                    </p>
                    <div className="flex flex-wrap gap-1">
                      {tailoredResume.missing_skills.slice(0, 6).map((skill, i) => (
                        <Badge key={i} variant="outline" className="text-orange-600">
                          {skill}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right Panel - Resume Comparison */}
        <div className="lg:col-span-2">
          <Card className="h-full">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">Resume Comparison</CardTitle>
                {phase === 'complete' && (
                  <ToggleGroup type="single" value={viewMode} onValueChange={(v) => v && setViewMode(v as typeof viewMode)}>
                    <ToggleGroupItem value="diff" title="Diff View">
                      <FileText className="h-4 w-4" />
                    </ToggleGroupItem>
                    <ToggleGroupItem value="rendered" title="Rendered">
                      <Eye className="h-4 w-4" />
                    </ToggleGroupItem>
                    <ToggleGroupItem value="raw" title="Raw">
                      <Code className="h-4 w-4" />
                    </ToggleGroupItem>
                  </ToggleGroup>
                )}
              </div>
            </CardHeader>
            <CardContent>
              {phase === 'ready' && (
                <div className="h-[600px] flex items-center justify-center border-2 border-dashed rounded-lg bg-gray-50">
                  <div className="text-center space-y-4">
                    <Sparkles className="h-16 w-16 text-muted-foreground mx-auto" />
                    <div>
                      <p className="text-lg font-medium">Ready to Optimize Your Resume</p>
                      <p className="text-sm text-muted-foreground mt-1">
                        Click "Start Tailoring" to begin the AI optimization process
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {phase === 'processing' && (
                <div className="h-[600px] flex items-center justify-center border-2 border-dashed rounded-lg bg-gray-50">
                  <div className="text-center space-y-4">
                    <Loader2 className="h-16 w-16 text-primary mx-auto animate-spin" />
                    <div>
                      <p className="text-lg font-medium">AI is Optimizing Your Resume</p>
                      <p className="text-sm text-muted-foreground mt-1">
                        This may take up to 2 minutes...
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {phase === 'error' && (
                <div className="h-[600px] flex items-center justify-center border-2 border-dashed border-red-200 rounded-lg bg-red-50">
                  <div className="text-center space-y-4">
                    <XCircle className="h-16 w-16 text-red-500 mx-auto" />
                    <div>
                      <p className="text-lg font-medium text-red-700">Tailoring Failed</p>
                      <p className="text-sm text-red-600 mt-1">{error}</p>
                    </div>
                  </div>
                </div>
              )}

              {phase === 'complete' && tailoredResume && (
                <>
                  {viewMode === 'diff' ? (
                    <ScrollArea className="h-[600px] rounded-lg border">
                      <DiffView 
                        original={tailoredResume.original_resume_content || ''} 
                        tailored={tailoredResume.tailored_resume_content || ''} 
                      />
                    </ScrollArea>
                  ) : (
                    <div className="grid grid-cols-2 gap-4 h-[600px]">
                      <div className="space-y-2">
                        <p className="text-sm font-medium text-muted-foreground">Original</p>
                        <ScrollArea className="h-[560px] rounded-lg border p-4 bg-gray-50">
                          {viewMode === 'rendered' ? (
                            <MarkdownRenderer content={tailoredResume.original_resume_content || ''} />
                          ) : (
                            <pre className="text-xs whitespace-pre-wrap font-mono">
                              {tailoredResume.original_resume_content}
                            </pre>
                          )}
                        </ScrollArea>
                      </div>
                      <div className="space-y-2">
                        <p className="text-sm font-medium text-green-600">Tailored</p>
                        <ScrollArea className="h-[560px] rounded-lg border p-4 bg-green-50/50">
                          {viewMode === 'rendered' ? (
                            <MarkdownRenderer content={tailoredResume.tailored_resume_content || ''} />
                          ) : (
                            <pre className="text-xs whitespace-pre-wrap font-mono">
                              {tailoredResume.tailored_resume_content}
                            </pre>
                          )}
                        </ScrollArea>
                      </div>
                    </div>
                  )}
                </>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
