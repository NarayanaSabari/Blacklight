/**
 * ResumeCompareDialog Component
 * Side-by-side comparison of original and tailored resume
 */

import { useQuery } from '@tanstack/react-query';
import {
  FileText,
  ArrowRight,
  CheckCircle2,
  XCircle,
  Plus,
  Sparkles,
  TrendingUp,
  Loader2,
} from 'lucide-react';

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import { Separator } from '@/components/ui/separator';

import { resumeTailorApi } from '@/lib/resumeTailorApi';
import { ExportMenu } from './ExportMenu';
import type { TailoredResume, TailorImprovement } from '@/types/tailoredResume';

interface ResumeCompareDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  tailoredResume: TailoredResume;
}

function ImprovementItem({ improvement }: { improvement: TailorImprovement }) {
  const typeConfig = {
    added: { icon: Plus, color: 'text-green-600', bg: 'bg-green-50' },
    enhanced: { icon: TrendingUp, color: 'text-blue-600', bg: 'bg-blue-50' },
    reworded: { icon: Sparkles, color: 'text-purple-600', bg: 'bg-purple-50' },
    removed: { icon: XCircle, color: 'text-red-600', bg: 'bg-red-50' },
  };

  const config = typeConfig[improvement.type] || typeConfig.enhanced;
  const Icon = config.icon;

  return (
    <div className={`rounded-lg border p-3 ${config.bg}`}>
      <div className="flex items-start gap-2">
        <Icon className={`h-4 w-4 mt-0.5 ${config.color}`} />
        <div className="flex-1 space-y-1">
          <div className="flex items-center gap-2">
            <span className="font-medium text-sm">{improvement.section}</span>
            <Badge variant="outline" className="text-xs capitalize">
              {improvement.type}
            </Badge>
          </div>
          {improvement.original && (
            <div className="text-sm text-muted-foreground line-through">
              {improvement.original}
            </div>
          )}
          <div className="text-sm">{improvement.improved}</div>
          <p className="text-xs text-muted-foreground italic">{improvement.reason}</p>
        </div>
      </div>
    </div>
  );
}

function SkillBadge({
  skill,
  type,
}: {
  skill: string;
  type: 'kept' | 'added' | 'enhanced' | 'removed';
}) {
  const styles = {
    kept: 'bg-gray-100 text-gray-700',
    added: 'bg-green-100 text-green-700',
    enhanced: 'bg-blue-100 text-blue-700',
    removed: 'bg-red-100 text-red-700 line-through',
  };

  return (
    <Badge variant="secondary" className={styles[type]}>
      {type === 'added' && '+ '}
      {skill}
    </Badge>
  );
}

export function ResumeCompareDialog({
  open,
  onOpenChange,
  tailoredResume,
}: ResumeCompareDialogProps) {
  // Fetch detailed comparison data
  const { data: comparison, isLoading } = useQuery({
    queryKey: ['resumeCompare', tailoredResume.tailor_id],
    queryFn: () => resumeTailorApi.compareResumes(tailoredResume.tailor_id),
    enabled: open && !!tailoredResume.tailor_id,
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl max-h-[90vh]">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <DialogTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Resume Comparison
            </DialogTitle>
            <ExportMenu tailorId={tailoredResume.tailor_id} />
          </div>
        </DialogHeader>

        {isLoading ? (
          <div className="space-y-4 p-4">
            <Skeleton className="h-8 w-48" />
            <Skeleton className="h-64" />
          </div>
        ) : (
          <Tabs defaultValue="comparison" className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="comparison">Side by Side</TabsTrigger>
              <TabsTrigger value="improvements">Improvements</TabsTrigger>
              <TabsTrigger value="skills">Skills Analysis</TabsTrigger>
            </TabsList>

            {/* Side by Side Comparison */}
            <TabsContent value="comparison" className="mt-4">
              {/* Score Summary */}
              <div className="rounded-lg border bg-gradient-to-r from-slate-50 to-slate-100 p-4 mb-4">
                <div className="flex items-center justify-center gap-4">
                  <div className="text-center">
                    <p className="text-sm text-muted-foreground">Original</p>
                    <p className="text-2xl font-bold">
                      {Math.round(tailoredResume.original_match_score)}%
                    </p>
                  </div>
                  <ArrowRight className="h-6 w-6 text-muted-foreground" />
                  <div className="text-center">
                    <p className="text-sm text-muted-foreground">Tailored</p>
                    <p className="text-2xl font-bold text-green-600">
                      {Math.round(tailoredResume.tailored_match_score)}%
                    </p>
                  </div>
                  <Badge className="bg-green-600 text-lg px-3 py-1 ml-4">
                    +{Math.round(tailoredResume.score_improvement)}%
                  </Badge>
                </div>
              </div>

              {/* Side by Side Content */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <h4 className="font-medium text-sm text-muted-foreground flex items-center gap-2">
                    <FileText className="h-4 w-4" />
                    Original Resume
                  </h4>
                  <ScrollArea className="h-[400px] rounded-lg border p-4 bg-slate-50">
                    <pre className="text-sm whitespace-pre-wrap font-mono">
                      {comparison?.original.content || tailoredResume.original_resume_content}
                    </pre>
                  </ScrollArea>
                </div>
                <div className="space-y-2">
                  <h4 className="font-medium text-sm text-green-600 flex items-center gap-2">
                    <Sparkles className="h-4 w-4" />
                    Tailored Resume
                  </h4>
                  <ScrollArea className="h-[400px] rounded-lg border p-4 bg-green-50">
                    <pre className="text-sm whitespace-pre-wrap font-mono">
                      {comparison?.tailored.content || tailoredResume.tailored_resume_content}
                    </pre>
                  </ScrollArea>
                </div>
              </div>
            </TabsContent>

            {/* Improvements List */}
            <TabsContent value="improvements" className="mt-4">
              <ScrollArea className="h-[500px]">
                <div className="space-y-3 pr-4">
                  {(comparison?.improvements || tailoredResume.improvements || []).length > 0 ? (
                    (comparison?.improvements || tailoredResume.improvements).map(
                      (improvement, idx) => (
                        <ImprovementItem key={idx} improvement={improvement} />
                      )
                    )
                  ) : (
                    <div className="text-center py-8 text-muted-foreground">
                      <Loader2 className="h-8 w-8 mx-auto mb-2 animate-spin" />
                      <p>Loading improvements...</p>
                    </div>
                  )}
                </div>
              </ScrollArea>
            </TabsContent>

            {/* Skills Analysis */}
            <TabsContent value="skills" className="mt-4">
              <ScrollArea className="h-[500px]">
                <div className="space-y-6 pr-4">
                  {/* Matched Skills */}
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                      <span className="font-medium">
                        Matched Skills ({tailoredResume.matched_skills?.length || 0})
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {tailoredResume.matched_skills?.map((skill, idx) => (
                        <Badge key={idx} variant="secondary" className="bg-green-50 text-green-700">
                          {skill}
                        </Badge>
                      ))}
                    </div>
                  </div>

                  <Separator />

                  {/* Skills Added */}
                  {tailoredResume.added_skills && tailoredResume.added_skills.length > 0 && (
                    <div className="space-y-2">
                      <div className="flex items-center gap-2">
                        <Plus className="h-4 w-4 text-blue-600" />
                        <span className="font-medium">
                          Skills Highlighted ({tailoredResume.added_skills.length})
                        </span>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        These skills were emphasized or added to improve match
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {tailoredResume.added_skills.map((skill, idx) => (
                          <SkillBadge key={idx} skill={skill} type="added" />
                        ))}
                      </div>
                    </div>
                  )}

                  <Separator />

                  {/* Missing Skills */}
                  {tailoredResume.missing_skills && tailoredResume.missing_skills.length > 0 && (
                    <div className="space-y-2">
                      <div className="flex items-center gap-2">
                        <XCircle className="h-4 w-4 text-orange-600" />
                        <span className="font-medium">
                          Skills to Develop ({tailoredResume.missing_skills.length})
                        </span>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        These skills from the job posting aren't in the candidate's profile
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {tailoredResume.missing_skills.map((skill, idx) => (
                          <Badge key={idx} variant="outline" className="text-orange-600">
                            {skill}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  <Separator />

                  {/* Skill Comparison Detail */}
                  {(comparison?.skill_comparison || tailoredResume.skill_comparison) && (
                    <div className="space-y-4">
                      <h4 className="font-medium">Skill Transformation</h4>
                      
                      {(comparison?.skill_comparison || tailoredResume.skill_comparison).kept?.length > 0 && (
                        <div className="space-y-2">
                          <span className="text-sm text-muted-foreground">Kept as-is:</span>
                          <div className="flex flex-wrap gap-1.5">
                            {(comparison?.skill_comparison || tailoredResume.skill_comparison).kept.map(
                              (skill, idx) => (
                                <SkillBadge key={idx} skill={skill} type="kept" />
                              )
                            )}
                          </div>
                        </div>
                      )}

                      {(comparison?.skill_comparison || tailoredResume.skill_comparison).enhanced?.length > 0 && (
                        <div className="space-y-2">
                          <span className="text-sm text-muted-foreground">Enhanced:</span>
                          <div className="flex flex-wrap gap-1.5">
                            {(comparison?.skill_comparison || tailoredResume.skill_comparison).enhanced.map(
                              (skill, idx) => (
                                <SkillBadge key={idx} skill={skill} type="enhanced" />
                              )
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </ScrollArea>
            </TabsContent>
          </Tabs>
        )}

        <div className="flex justify-end gap-2 mt-4">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
