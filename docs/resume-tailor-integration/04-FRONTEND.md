# Resume Tailor Integration - Frontend Components

## Overview

The Resume Tailor feature will be integrated into the Portal UI (`ui/portal`) using React, TypeScript, TanStack Query, and shadcn/ui components. This document outlines all new pages and components.

---

## Pages

### 1. Resume Tailor Page

**Route:** `/candidates/:candidateId/tailor/:jobId`

**Purpose:** Main page for tailoring a candidate's resume for a specific job posting.

```tsx
// src/pages/candidates/ResumeTailorPage.tsx

import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { ResumeTailorProvider, useResumeTailor } from "@/context/ResumeTailorContext";
import { MatchScoreDisplay } from "@/components/resume-tailor/MatchScoreDisplay";
import { SkillGapAnalysis } from "@/components/resume-tailor/SkillGapAnalysis";
import { ResumePreview } from "@/components/resume-tailor/ResumePreview";
import { ImprovementsList } from "@/components/resume-tailor/ImprovementsList";
import { TailoringProgress } from "@/components/resume-tailor/TailoringProgress";
import { ExportOptionsMenu } from "@/components/resume-tailor/ExportOptionsMenu";

export function ResumeTailorPage() {
  const { candidateId, jobId } = useParams<{ candidateId: string; jobId: string }>();

  return (
    <ResumeTailorProvider candidateId={candidateId!} jobId={jobId!}>
      <ResumeTailorContent />
    </ResumeTailorProvider>
  );
}

function ResumeTailorContent() {
  const { candidate, job, tailorResult, isProcessing, startTailoring } = useResumeTailor();

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Resume Tailor</h1>
          <p className="text-muted-foreground">
            Tailoring {candidate?.name}'s resume for {job?.title}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {!isProcessing && !tailorResult && (
            <Button onClick={startTailoring}>Start Tailoring</Button>
          )}
          {tailorResult && (
            <ExportOptionsMenu tailorId={tailorResult.tailor_id} />
          )}
        </div>
      </div>

      {/* Progress Indicator */}
      {isProcessing && <TailoringProgress />}

      {/* Results */}
      {tailorResult && (
        <>
          {/* Score Comparison */}
          <Card>
            <CardHeader>
              <CardTitle>Match Score Improvement</CardTitle>
            </CardHeader>
            <CardContent>
              <MatchScoreDisplay
                originalScore={tailorResult.original.match_score}
                tailoredScore={tailorResult.tailored.match_score}
              />
            </CardContent>
          </Card>

          {/* Resume Comparison */}
          <Tabs defaultValue="side-by-side" className="w-full">
            <TabsList>
              <TabsTrigger value="side-by-side">Side by Side</TabsTrigger>
              <TabsTrigger value="diff">Differences</TabsTrigger>
              <TabsTrigger value="tailored-only">Tailored Only</TabsTrigger>
            </TabsList>
            
            <TabsContent value="side-by-side">
              <div className="grid grid-cols-2 gap-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Original Resume</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ResumePreview content={tailorResult.original.content_markdown} />
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg text-green-600">Tailored Resume</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ResumePreview content={tailorResult.tailored.content_markdown} />
                  </CardContent>
                </Card>
              </div>
            </TabsContent>
            
            <TabsContent value="diff">
              <ResumeDiffView
                original={tailorResult.original.content_markdown}
                tailored={tailorResult.tailored.content_markdown}
              />
            </TabsContent>
            
            <TabsContent value="tailored-only">
              <Card>
                <CardContent className="pt-6">
                  <ResumePreview content={tailorResult.tailored.content_markdown} />
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>

          {/* Improvements & Skills */}
          <div className="grid grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle>Improvements Made</CardTitle>
              </CardHeader>
              <CardContent>
                <ImprovementsList improvements={tailorResult.improvements} />
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Skill Gap Analysis</CardTitle>
              </CardHeader>
              <CardContent>
                <SkillGapAnalysis
                  matchedSkills={tailorResult.tailored.keywords}
                  missingSkills={[]}
                  extraSkills={tailorResult.original.keywords}
                />
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
```

---

## Components

### 1. JobSelectorDialog

**Purpose:** Modal to select a job posting for resume tailoring.

```tsx
// src/components/resume-tailor/JobSelectorDialog.tsx

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Search, Sparkles } from "lucide-react";
import { jobPostingsApi } from "@/api/job-postings";

interface JobSelectorDialogProps {
  candidateId: number;
  onSelect: (jobId: number) => void;
  trigger?: React.ReactNode;
}

export function JobSelectorDialog({ candidateId, onSelect, trigger }: JobSelectorDialogProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");

  const { data: jobs, isLoading } = useQuery({
    queryKey: ["job-postings", { search, limit: 20 }],
    queryFn: () => jobPostingsApi.list({ search, per_page: 20 }),
    enabled: open,
  });

  const handleSelect = (jobId: number) => {
    onSelect(jobId);
    setOpen(false);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || (
          <Button variant="outline" size="sm">
            <Sparkles className="mr-2 h-4 w-4" />
            Tailor Resume
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Select Job to Tailor Resume For</DialogTitle>
        </DialogHeader>
        
        <div className="space-y-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search jobs..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-10"
            />
          </div>
          
          <ScrollArea className="h-[400px]">
            <div className="space-y-2">
              {jobs?.items.map((job) => (
                <div
                  key={job.id}
                  className="flex items-center justify-between p-4 border rounded-lg hover:bg-accent cursor-pointer"
                  onClick={() => handleSelect(job.id)}
                >
                  <div className="space-y-1">
                    <p className="font-medium">{job.title}</p>
                    <p className="text-sm text-muted-foreground">{job.company}</p>
                    <div className="flex gap-1 flex-wrap">
                      {job.skills?.slice(0, 5).map((skill) => (
                        <Badge key={skill} variant="secondary" className="text-xs">
                          {skill}
                        </Badge>
                      ))}
                    </div>
                  </div>
                  <Button size="sm">Select</Button>
                </div>
              ))}
            </div>
          </ScrollArea>
        </div>
      </DialogContent>
    </Dialog>
  );
}
```

---

### 2. MatchScoreDisplay

**Purpose:** Visual comparison of match scores before and after tailoring.

```tsx
// src/components/resume-tailor/MatchScoreDisplay.tsx

import { ArrowRight, TrendingUp } from "lucide-react";
import { cn } from "@/lib/utils";

interface MatchScoreDisplayProps {
  originalScore: number;
  tailoredScore: number;
}

export function MatchScoreDisplay({ originalScore, tailoredScore }: MatchScoreDisplayProps) {
  const improvement = tailoredScore - originalScore;
  const improvementPercent = Math.round(improvement * 100);

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return "text-green-600";
    if (score >= 0.6) return "text-yellow-600";
    return "text-red-600";
  };

  const getScoreBg = (score: number) => {
    if (score >= 0.8) return "bg-green-100";
    if (score >= 0.6) return "bg-yellow-100";
    return "bg-red-100";
  };

  return (
    <div className="flex items-center justify-center gap-8 py-6">
      {/* Original Score */}
      <div className="text-center">
        <p className="text-sm text-muted-foreground mb-2">Original Score</p>
        <div
          className={cn(
            "inline-flex items-center justify-center w-24 h-24 rounded-full",
            getScoreBg(originalScore)
          )}
        >
          <span className={cn("text-3xl font-bold", getScoreColor(originalScore))}>
            {Math.round(originalScore * 100)}%
          </span>
        </div>
      </div>

      {/* Arrow & Improvement */}
      <div className="flex flex-col items-center gap-2">
        <ArrowRight className="h-8 w-8 text-muted-foreground" />
        <div className="flex items-center gap-1 text-green-600">
          <TrendingUp className="h-4 w-4" />
          <span className="text-sm font-medium">+{improvementPercent}%</span>
        </div>
      </div>

      {/* Tailored Score */}
      <div className="text-center">
        <p className="text-sm text-muted-foreground mb-2">Tailored Score</p>
        <div
          className={cn(
            "inline-flex items-center justify-center w-24 h-24 rounded-full",
            getScoreBg(tailoredScore)
          )}
        >
          <span className={cn("text-3xl font-bold", getScoreColor(tailoredScore))}>
            {Math.round(tailoredScore * 100)}%
          </span>
        </div>
      </div>
    </div>
  );
}
```

---

### 3. SkillGapAnalysis

**Purpose:** Table showing matched, missing, and extra skills.

```tsx
// src/components/resume-tailor/SkillGapAnalysis.tsx

import { Badge } from "@/components/ui/badge";
import { Check, X, Plus } from "lucide-react";

interface SkillGapAnalysisProps {
  matchedSkills: string[];
  missingSkills: string[];
  extraSkills: string[];
}

export function SkillGapAnalysis({
  matchedSkills,
  missingSkills,
  extraSkills,
}: SkillGapAnalysisProps) {
  return (
    <div className="space-y-4">
      {/* Matched Skills */}
      <div>
        <div className="flex items-center gap-2 mb-2">
          <Check className="h-4 w-4 text-green-600" />
          <p className="text-sm font-medium">Matched Skills ({matchedSkills.length})</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {matchedSkills.map((skill) => (
            <Badge key={skill} variant="outline" className="border-green-300 text-green-700">
              {skill}
            </Badge>
          ))}
        </div>
      </div>

      {/* Missing Skills */}
      {missingSkills.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-2">
            <X className="h-4 w-4 text-red-600" />
            <p className="text-sm font-medium">Missing Skills ({missingSkills.length})</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {missingSkills.map((skill) => (
              <Badge key={skill} variant="outline" className="border-red-300 text-red-700">
                {skill}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* Extra Skills */}
      {extraSkills.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Plus className="h-4 w-4 text-blue-600" />
            <p className="text-sm font-medium">Additional Skills ({extraSkills.length})</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {extraSkills.map((skill) => (
              <Badge key={skill} variant="outline" className="border-blue-300 text-blue-700">
                {skill}
              </Badge>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
```

---

### 4. ImprovementsList

**Purpose:** List of improvements made to the resume.

```tsx
// src/components/resume-tailor/ImprovementsList.tsx

import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { FileEdit, Tag, Layout, Sparkles } from "lucide-react";

interface Improvement {
  section: string;
  type: string;
  description: string;
  before?: string;
  after?: string;
}

interface ImprovementsListProps {
  improvements: Improvement[];
}

const typeIcons: Record<string, React.ReactNode> = {
  keyword_addition: <Tag className="h-4 w-4" />,
  skill_reorganization: <Layout className="h-4 w-4" />,
  content_enhancement: <Sparkles className="h-4 w-4" />,
  default: <FileEdit className="h-4 w-4" />,
};

const typeColors: Record<string, string> = {
  keyword_addition: "bg-blue-100 text-blue-800",
  skill_reorganization: "bg-purple-100 text-purple-800",
  content_enhancement: "bg-green-100 text-green-800",
  default: "bg-gray-100 text-gray-800",
};

export function ImprovementsList({ improvements }: ImprovementsListProps) {
  return (
    <ScrollArea className="h-[300px]">
      <div className="space-y-4">
        {improvements.map((improvement, index) => (
          <div key={index} className="border rounded-lg p-4 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {typeIcons[improvement.type] || typeIcons.default}
                <span className="font-medium">{improvement.section}</span>
              </div>
              <Badge className={typeColors[improvement.type] || typeColors.default}>
                {improvement.type.replace(/_/g, " ")}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground">{improvement.description}</p>
            {improvement.before && improvement.after && (
              <div className="grid grid-cols-2 gap-2 text-xs mt-2">
                <div className="p-2 bg-red-50 rounded border border-red-200">
                  <p className="font-medium text-red-700 mb-1">Before:</p>
                  <p className="text-red-600">{improvement.before}</p>
                </div>
                <div className="p-2 bg-green-50 rounded border border-green-200">
                  <p className="font-medium text-green-700 mb-1">After:</p>
                  <p className="text-green-600">{improvement.after}</p>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </ScrollArea>
  );
}
```

---

### 5. TailoringProgress

**Purpose:** SSE-based progress indicator during tailoring.

```tsx
// src/components/resume-tailor/TailoringProgress.tsx

import { useResumeTailor } from "@/context/ResumeTailorContext";
import { Progress } from "@/components/ui/progress";
import { Card, CardContent } from "@/components/ui/card";
import { Loader2 } from "lucide-react";

const stepLabels: Record<string, string> = {
  parsing_resume: "Parsing resume...",
  parsing_job: "Analyzing job description...",
  extracting_keywords: "Extracting keywords...",
  calculating_score: "Calculating initial score...",
  improving: "Generating improvements...",
  calculating_final_score: "Calculating final score...",
};

export function TailoringProgress() {
  const { progress } = useResumeTailor();

  return (
    <Card className="border-blue-200 bg-blue-50">
      <CardContent className="pt-6">
        <div className="flex items-center gap-4">
          <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
          <div className="flex-1">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm font-medium text-blue-900">
                {stepLabels[progress.step] || "Processing..."}
              </p>
              <span className="text-sm text-blue-700">{progress.progress}%</span>
            </div>
            <Progress value={progress.progress} className="h-2" />
            {progress.iteration && (
              <p className="text-xs text-blue-600 mt-1">
                Improvement iteration {progress.iteration}/5
              </p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
```

---

### 6. ResumePreview

**Purpose:** Render markdown resume as formatted HTML.

```tsx
// src/components/resume-tailor/ResumePreview.tsx

import { useMemo } from "react";
import { marked } from "marked";
import { ScrollArea } from "@/components/ui/scroll-area";

interface ResumePreviewProps {
  content: string;
}

export function ResumePreview({ content }: ResumePreviewProps) {
  const html = useMemo(() => {
    return marked.parse(content, { breaks: true, gfm: true });
  }, [content]);

  return (
    <ScrollArea className="h-[500px]">
      <div
        className="prose prose-sm max-w-none dark:prose-invert"
        dangerouslySetInnerHTML={{ __html: html }}
      />
    </ScrollArea>
  );
}
```

---

### 7. ExportOptionsMenu

**Purpose:** Dropdown menu for export options.

```tsx
// src/components/resume-tailor/ExportOptionsMenu.tsx

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { Download, FileText, FileType, File } from "lucide-react";
import { resumeTailorApi } from "@/api/resume-tailor";

interface ExportOptionsMenuProps {
  tailorId: string;
}

export function ExportOptionsMenu({ tailorId }: ExportOptionsMenuProps) {
  const handleExport = async (format: "pdf" | "docx" | "md") => {
    const blob = await resumeTailorApi.export(tailorId, format);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `tailored_resume.${format}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button>
          <Download className="mr-2 h-4 w-4" />
          Export
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent>
        <DropdownMenuItem onClick={() => handleExport("pdf")}>
          <FileText className="mr-2 h-4 w-4" />
          Export as PDF
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => handleExport("docx")}>
          <FileType className="mr-2 h-4 w-4" />
          Export as DOCX
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => handleExport("md")}>
          <File className="mr-2 h-4 w-4" />
          Export as Markdown
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
```

---

## Context Provider

```tsx
// src/context/ResumeTailorContext.tsx

import { createContext, useContext, useState, useCallback, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { resumeTailorApi } from "@/api/resume-tailor";
import { candidatesApi } from "@/api/candidates";
import { jobPostingsApi } from "@/api/job-postings";

interface Progress {
  status: string;
  step: string;
  progress: number;
  iteration?: number;
}

interface ResumeTailorContextValue {
  candidate: any;
  job: any;
  tailorResult: any;
  progress: Progress;
  isProcessing: boolean;
  error: string | null;
  startTailoring: () => void;
}

const ResumeTailorContext = createContext<ResumeTailorContextValue | null>(null);

export function ResumeTailorProvider({
  candidateId,
  jobId,
  children,
}: {
  candidateId: string;
  jobId: string;
  children: React.ReactNode;
}) {
  const [tailorId, setTailorId] = useState<string | null>(null);
  const [tailorResult, setTailorResult] = useState<any>(null);
  const [progress, setProgress] = useState<Progress>({ status: "idle", step: "", progress: 0 });
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data: candidate } = useQuery({
    queryKey: ["candidate", candidateId],
    queryFn: () => candidatesApi.get(candidateId),
  });

  const { data: job } = useQuery({
    queryKey: ["job-posting", jobId],
    queryFn: () => jobPostingsApi.get(jobId),
  });

  const tailorMutation = useMutation({
    mutationFn: () => resumeTailorApi.startTailor({
      candidate_id: parseInt(candidateId),
      job_posting_id: parseInt(jobId),
    }),
    onSuccess: (data) => {
      setTailorId(data.tailor_id);
      setIsProcessing(true);
    },
    onError: (err: Error) => {
      setError(err.message);
    },
  });

  // SSE stream for progress
  useEffect(() => {
    if (!tailorId || !isProcessing) return;

    const eventSource = resumeTailorApi.streamProgress(tailorId);
    
    eventSource.addEventListener("progress", (event) => {
      const data = JSON.parse(event.data);
      setProgress(data);
    });

    eventSource.addEventListener("completed", (event) => {
      const data = JSON.parse(event.data);
      setIsProcessing(false);
      // Fetch full result
      resumeTailorApi.get(data.tailor_id).then(setTailorResult);
    });

    eventSource.addEventListener("error", (event) => {
      setIsProcessing(false);
      setError("Tailoring failed");
    });

    return () => eventSource.close();
  }, [tailorId, isProcessing]);

  const startTailoring = useCallback(() => {
    tailorMutation.mutate();
  }, [tailorMutation]);

  return (
    <ResumeTailorContext.Provider
      value={{
        candidate,
        job,
        tailorResult,
        progress,
        isProcessing,
        error,
        startTailoring,
      }}
    >
      {children}
    </ResumeTailorContext.Provider>
  );
}

export function useResumeTailor() {
  const context = useContext(ResumeTailorContext);
  if (!context) {
    throw new Error("useResumeTailor must be used within ResumeTailorProvider");
  }
  return context;
}
```

---

## API Client

```tsx
// src/api/resume-tailor.ts

import { apiClient } from "./client";

export const resumeTailorApi = {
  startTailor: async (data: { candidate_id: number; job_posting_id: number }) => {
    const response = await apiClient.post("/resume-tailor/tailor", data);
    return response.data;
  },

  get: async (tailorId: string) => {
    const response = await apiClient.get(`/resume-tailor/tailor/${tailorId}`);
    return response.data;
  },

  streamProgress: (tailorId: string): EventSource => {
    const token = localStorage.getItem("token");
    return new EventSource(
      `${import.meta.env.VITE_API_URL}/resume-tailor/tailor/${tailorId}/stream?token=${token}`
    );
  },

  export: async (tailorId: string, format: "pdf" | "docx" | "md"): Promise<Blob> => {
    const response = await apiClient.get(
      `/resume-tailor/${tailorId}/export?format=${format}`,
      { responseType: "blob" }
    );
    return response.data;
  },

  listForCandidate: async (candidateId: string) => {
    const response = await apiClient.get(`/candidates/${candidateId}/tailored-resumes`);
    return response.data;
  },

  apply: async (tailorId: string, options: { update_embedding?: boolean }) => {
    const response = await apiClient.post(`/resume-tailor/${tailorId}/apply`, options);
    return response.data;
  },
};
```

---

## File Structure

```
ui/portal/src/
├── pages/
│   └── candidates/
│       └── ResumeTailorPage.tsx        # Main tailor page
├── components/
│   └── resume-tailor/
│       ├── JobSelectorDialog.tsx
│       ├── ResumeTailorCard.tsx
│       ├── MatchScoreDisplay.tsx
│       ├── SkillGapAnalysis.tsx
│       ├── ImprovementsList.tsx
│       ├── ResumePreview.tsx
│       ├── ResumeDiffView.tsx
│       ├── TailoringProgress.tsx
│       └── ExportOptionsMenu.tsx
├── context/
│   └── ResumeTailorContext.tsx
├── api/
│   └── resume-tailor.ts
└── hooks/
    └── useResumeTailor.ts              # Optional hook if not using context
```

---

## Dependencies to Add

```json
{
  "dependencies": {
    "marked": "^12.0.0"        // Markdown to HTML
  }
}
```

---

**Document Status**: Draft - Pending Approval  
**Last Updated**: 2025-12-14
