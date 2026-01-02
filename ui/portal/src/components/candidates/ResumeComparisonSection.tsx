/**
 * Resume Comparison Section Component
 * Shows side-by-side view of original resume (PDF) and polished markdown
 */

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import {
  FileText,
  Sparkles,
  Edit,
  RefreshCw,
  Download,
  ExternalLink,
  AlertCircle,
  Check,
} from 'lucide-react';
import { candidateApi } from '@/lib/candidateApi';
import type { Candidate, PolishedResumeData } from '@/types/candidate';
import { PolishedResumeEditor } from './PolishedResumeEditor';
import { ResumeViewer } from './ResumeViewer';
import { toast } from 'sonner';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface ResumeComparisonSectionProps {
  candidate: Candidate;
  resumeUrl?: string | null;
}

export function ResumeComparisonSection({
  candidate,
  resumeUrl,
}: ResumeComparisonSectionProps) {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<string>('polished');
  const [isEditing, setIsEditing] = useState(false);

  // Fetch polished resume data
  const {
    data: polishedData,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ['polishedResume', candidate.id],
    queryFn: () => candidateApi.getPolishedResume(candidate.id),
    staleTime: 30000, // 30 seconds
  });

  // Regenerate mutation
  const regenerateMutation = useMutation({
    mutationFn: () => candidateApi.regeneratePolishedResume(candidate.id),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['polishedResume', candidate.id] });
      queryClient.invalidateQueries({ queryKey: ['candidate', candidate.id] });
      toast.success('Resume polished successfully');
    },
    onError: (error: Error) => {
      toast.error(`Failed to regenerate: ${error.message}`);
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: (markdown: string) =>
      candidateApi.updatePolishedResume(candidate.id, markdown),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['polishedResume', candidate.id] });
      queryClient.invalidateQueries({ queryKey: ['candidate', candidate.id] });
      setIsEditing(false);
      toast.success('Resume saved successfully');
    },
    onError: (error: Error) => {
      toast.error(`Failed to save: ${error.message}`);
    },
  });

  const handleRegenerate = () => {
    if (!candidate.parsed_resume_data) {
      toast.error('No parsed resume data available. Please upload and parse a resume first.');
      return;
    }
    regenerateMutation.mutate();
  };

  const handleSave = (markdown: string) => {
    updateMutation.mutate(markdown);
  };

  const hasPolishedResume = polishedData?.has_polished_resume;
  const polishedResumeData = polishedData?.polished_resume_data;

  // Format the polished metadata
  const formatDate = (dateStr?: string | null) => {
    if (!dateStr) return null;
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <Card className="h-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-lg">
            <FileText className="h-5 w-5" />
            Resume View
          </CardTitle>
          <div className="flex items-center gap-2">
            {hasPolishedResume && polishedResumeData && (
              <Badge variant="outline" className="text-xs">
                <Check className="h-3 w-3 mr-1" />
                v{polishedResumeData.version} | {polishedResumeData.polished_by === 'ai' ? 'AI' : 'Edited'}
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="p-0">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <div className="px-6 border-b">
            <TabsList className="h-10 w-full justify-start rounded-none bg-transparent p-0">
              <TabsTrigger
                value="polished"
                className="relative h-10 rounded-none border-b-2 border-b-transparent bg-transparent px-4 pb-3 pt-2 font-medium text-muted-foreground shadow-none transition-none data-[state=active]:border-b-primary data-[state=active]:text-foreground data-[state=active]:shadow-none"
              >
                <Sparkles className="h-4 w-4 mr-2" />
                Polished Resume
              </TabsTrigger>
              <TabsTrigger
                value="original"
                className="relative h-10 rounded-none border-b-2 border-b-transparent bg-transparent px-4 pb-3 pt-2 font-medium text-muted-foreground shadow-none transition-none data-[state=active]:border-b-primary data-[state=active]:text-foreground data-[state=active]:shadow-none"
              >
                <FileText className="h-4 w-4 mr-2" />
                Original Document
              </TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="polished" className="mt-0 p-6">
            {isLoading ? (
              <div className="space-y-4">
                <Skeleton className="h-8 w-1/3" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-2/3" />
                <Skeleton className="h-4 w-3/4" />
              </div>
            ) : isError ? (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  Failed to load polished resume: {error?.message || 'Unknown error'}
                </AlertDescription>
              </Alert>
            ) : !hasPolishedResume ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <Sparkles className="h-12 w-12 text-muted-foreground mb-4" />
                <h3 className="text-lg font-medium mb-2">No Polished Resume Yet</h3>
                <p className="text-sm text-muted-foreground mb-6 max-w-md">
                  {candidate.parsed_resume_data
                    ? 'Generate a polished, AI-formatted version of this resume for better presentation and tailoring.'
                    : 'Upload and parse a resume first to enable AI polishing.'}
                </p>
                {candidate.parsed_resume_data && (
                  <Button
                    onClick={handleRegenerate}
                    disabled={regenerateMutation.isPending}
                    className="gap-2"
                  >
                    {regenerateMutation.isPending ? (
                      <RefreshCw className="h-4 w-4 animate-spin" />
                    ) : (
                      <Sparkles className="h-4 w-4" />
                    )}
                    Generate Polished Resume
                  </Button>
                )}
              </div>
            ) : isEditing ? (
              <PolishedResumeEditor
                initialContent={polishedResumeData?.markdown_content || ''}
                onSave={handleSave}
                onCancel={() => setIsEditing(false)}
                isSaving={updateMutation.isPending}
              />
            ) : (
              <div className="space-y-4">
                {/* Actions */}
                <div className="flex items-center justify-between">
                  <div className="text-xs text-muted-foreground">
                    {polishedResumeData?.last_edited_at ? (
                      <>
                        Last edited: {formatDate(polishedResumeData.last_edited_at)}
                      </>
                    ) : (
                      <>
                        Polished: {formatDate(polishedResumeData?.polished_at)} 
                        {polishedResumeData?.ai_model && ` by ${polishedResumeData.ai_model}`}
                      </>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setIsEditing(true)}
                      className="gap-2"
                    >
                      <Edit className="h-4 w-4" />
                      Edit
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleRegenerate}
                      disabled={regenerateMutation.isPending}
                      className="gap-2"
                    >
                      {regenerateMutation.isPending ? (
                        <RefreshCw className="h-4 w-4 animate-spin" />
                      ) : (
                        <RefreshCw className="h-4 w-4" />
                      )}
                      Regenerate
                    </Button>
                  </div>
                </div>

                {/* Markdown Content */}
                <div className="prose prose-sm dark:prose-invert max-w-none border rounded-lg p-6 bg-white dark:bg-gray-900 max-h-[600px] overflow-y-auto">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {polishedResumeData?.markdown_content || ''}
                  </ReactMarkdown>
                </div>
              </div>
            )}
          </TabsContent>

          <TabsContent value="original" className="mt-0">
            <div className="min-h-[600px]">
              <ResumeViewer
                resumeUrl={resumeUrl}
                resumeFileName={candidate.resume_file_key?.split('/').pop()}
                candidateName={candidate.full_name || `${candidate.first_name} ${candidate.last_name}`}
              />
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
