/**
 * ResumeCompareDialog Component
 * Side-by-side comparison of original and tailored resume with markdown rendering
 * and diff highlighting
 */

import React, { useMemo, useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  FileText,
  ArrowRight,
  CheckCircle2,
  XCircle,
  Plus,
  Sparkles,
  TrendingUp,
  Eye,
  Code,
  Download,
  FileType,
  Loader2,
  ChevronDown,
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
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

import { resumeTailorApi } from '@/lib/resumeTailorApi';
import type { TailoredResume, TailorImprovement, ExportFormat } from '@/types/tailoredResume';

interface ResumeCompareDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  tailoredResume: TailoredResume;
}

/**
 * Simple markdown renderer using regex patterns
 * Converts markdown to styled HTML elements
 */
function MarkdownRenderer({ content, className = '' }: { content: string; className?: string }) {
  const renderedContent = useMemo(() => {
    if (!content) return null;
    
    // Split content into lines for processing
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
      // Process inline elements: bold, italic, code, links
      const parts: React.ReactNode[] = [];
      let remaining = text;
      let key = 0;
      
      while (remaining.length > 0) {
        // Bold **text** or __text__
        const boldMatch = remaining.match(/^(.*?)(\*\*|__)(.+?)\2(.*)$/s);
        if (boldMatch) {
          if (boldMatch[1]) parts.push(boldMatch[1]);
          parts.push(<strong key={key++} className="font-semibold">{boldMatch[3]}</strong>);
          remaining = boldMatch[4];
          continue;
        }
        
        // Italic *text* or _text_
        const italicMatch = remaining.match(/^(.*?)(\*|_)(.+?)\2(.*)$/s);
        if (italicMatch && !italicMatch[1].endsWith('*') && !italicMatch[1].endsWith('_')) {
          if (italicMatch[1]) parts.push(italicMatch[1]);
          parts.push(<em key={key++} className="italic">{italicMatch[3]}</em>);
          remaining = italicMatch[4];
          continue;
        }
        
        // Inline code `text`
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
        
        // No more matches, add remaining text
        parts.push(remaining);
        break;
      }
      
      return parts.length === 1 ? parts[0] : <>{parts}</>;
    };
    
    lines.forEach((line, index) => {
      // Code block start/end
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
      
      // Empty line
      if (!line.trim()) {
        flushList();
        elements.push(<div key={`empty-${index}`} className="h-2" />);
        return;
      }
      
      // Headers
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
      
      // Horizontal rule
      if (line.match(/^(-{3,}|\*{3,}|_{3,})$/)) {
        flushList();
        elements.push(<Separator key={`hr-${index}`} className="my-3" />);
        return;
      }
      
      // Unordered list
      const ulMatch = line.match(/^(\s*)[-*+]\s+(.+)$/);
      if (ulMatch) {
        if (listType !== 'ul') {
          flushList();
          listType = 'ul';
        }
        listItems.push(ulMatch[2]);
        return;
      }
      
      // Ordered list
      const olMatch = line.match(/^(\s*)\d+\.\s+(.+)$/);
      if (olMatch) {
        if (listType !== 'ol') {
          flushList();
          listType = 'ol';
        }
        listItems.push(olMatch[2]);
        return;
      }
      
      // Blockquote
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
      
      // Regular paragraph
      flushList();
      elements.push(
        <p key={`p-${index}`} className="text-sm text-gray-700 my-1 leading-relaxed">
          {processInlineMarkdown(line)}
        </p>
      );
    });
    
    // Flush any remaining list
    flushList();
    
    return elements;
  }, [content]);
  
  return (
    <div className={`prose prose-sm max-w-none ${className}`}>
      {renderedContent}
    </div>
  );
}

/**
 * Unified diff view showing changes between original and tailored
 */
function DiffView({ original, tailored }: { original: string; tailored: string }) {
  const diffLines = useMemo(() => {
    const originalLines = original?.split('\n') || [];
    const tailoredLines = tailored?.split('\n') || [];
    
    // Simple line-by-line diff
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
        // Lines are different
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
        
        // Changed - show both
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

/**
 * Inline Export Dropdown for Resume Export
 */
function ExportDropdown({ tailorId }: { tailorId: string }) {
  const [exportingFormat, setExportingFormat] = useState<ExportFormat | null>(null);

  const exportMutation = useMutation({
    mutationFn: async (format: ExportFormat) => {
      setExportingFormat(format);
      await resumeTailorApi.downloadResume(tailorId, format);
    },
    onSuccess: () => {
      toast.success('Resume exported successfully');
      setExportingFormat(null);
    },
    onError: (error: Error) => {
      toast.error(`Export failed: ${error.message}`);
      setExportingFormat(null);
    },
  });

  const formats: { value: ExportFormat; label: string; icon: typeof FileText }[] = [
    { value: 'pdf', label: 'PDF Document', icon: FileText },
    { value: 'docx', label: 'Word Document', icon: FileType },
    { value: 'markdown', label: 'Markdown', icon: Code },
  ];

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm" disabled={exportMutation.isPending}>
          {exportMutation.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin mr-2" />
          ) : (
            <Download className="h-4 w-4 mr-2" />
          )}
          Export
          <ChevronDown className="h-4 w-4 ml-2" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuLabel>Export Format</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {formats.map(({ value, label, icon: Icon }) => (
          <DropdownMenuItem
            key={value}
            onClick={() => exportMutation.mutate(value)}
            disabled={exportMutation.isPending}
          >
            {exportingFormat === value ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Icon className="h-4 w-4 mr-2" />
            )}
            {label}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export function ResumeCompareDialog({
  open,
  onOpenChange,
  tailoredResume,
}: ResumeCompareDialogProps) {
  const [viewMode, setViewMode] = useState<'rendered' | 'raw' | 'diff'>('rendered');
  
  // Fetch detailed comparison data
  const { data: comparison, isLoading } = useQuery({
    queryKey: ['resumeCompare', tailoredResume.tailor_id],
    queryFn: () => resumeTailorApi.compareResumes(tailoredResume.tailor_id),
    enabled: open && !!tailoredResume.tailor_id,
  });

  const originalContent = comparison?.original.content || tailoredResume.original_resume_content || '';
  const tailoredContent = comparison?.tailored.content || tailoredResume.tailored_resume_content || '';

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-6xl max-h-[90vh]">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <DialogTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Resume Comparison
            </DialogTitle>
            <ExportDropdown tailorId={tailoredResume.tailor_id} />
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
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
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
                  
                  {/* View Mode Toggle */}
                  <ToggleGroup type="single" value={viewMode} onValueChange={(v) => v && setViewMode(v as typeof viewMode)}>
                    <ToggleGroupItem value="rendered" aria-label="Rendered view" title="Rendered Markdown">
                      <Eye className="h-4 w-4" />
                    </ToggleGroupItem>
                    <ToggleGroupItem value="raw" aria-label="Raw view" title="Raw Markdown">
                      <Code className="h-4 w-4" />
                    </ToggleGroupItem>
                    <ToggleGroupItem value="diff" aria-label="Diff view" title="Unified Diff">
                      <FileText className="h-4 w-4" />
                    </ToggleGroupItem>
                  </ToggleGroup>
                </div>
              </div>

              {/* Diff View */}
              {viewMode === 'diff' ? (
                <div className="space-y-2">
                  <h4 className="font-medium text-sm text-muted-foreground flex items-center gap-2">
                    <FileText className="h-4 w-4" />
                    Unified Diff View
                    <span className="text-xs">
                      (<span className="text-red-600">- removed</span> / <span className="text-green-600">+ added</span>)
                    </span>
                  </h4>
                  <ScrollArea className="h-[450px] rounded-lg border bg-white">
                    <DiffView original={originalContent} tailored={tailoredContent} />
                  </ScrollArea>
                </div>
              ) : (
                /* Side by Side Content */
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <h4 className="font-medium text-sm text-muted-foreground flex items-center gap-2">
                      <FileText className="h-4 w-4" />
                      Original Resume
                    </h4>
                    <ScrollArea className="h-[450px] rounded-lg border p-4 bg-slate-50">
                      {viewMode === 'rendered' ? (
                        <MarkdownRenderer content={originalContent} />
                      ) : (
                        <pre className="text-sm whitespace-pre-wrap font-mono text-gray-700">
                          {originalContent}
                        </pre>
                      )}
                    </ScrollArea>
                  </div>
                  <div className="space-y-2">
                    <h4 className="font-medium text-sm text-green-600 flex items-center gap-2">
                      <Sparkles className="h-4 w-4" />
                      Tailored Resume
                    </h4>
                    <ScrollArea className="h-[450px] rounded-lg border p-4 bg-green-50/50">
                      {viewMode === 'rendered' ? (
                        <MarkdownRenderer content={tailoredContent} />
                      ) : (
                        <pre className="text-sm whitespace-pre-wrap font-mono text-gray-700">
                          {tailoredContent}
                        </pre>
                      )}
                    </ScrollArea>
                  </div>
                </div>
              )}
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
                      <Sparkles className="h-8 w-8 mx-auto mb-2" />
                      <p>No detailed improvements recorded</p>
                      <p className="text-sm">View the diff to see changes</p>
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
