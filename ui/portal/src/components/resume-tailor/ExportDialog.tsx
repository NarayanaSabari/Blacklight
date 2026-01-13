/**
 * ExportDialog Component
 * Dialog for exporting tailored resume with template selection and preview
 */

import { useState, useEffect } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  Download,
  FileText,
  FileType,
  Loader2,
  Eye,
  Check,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';

import { resumeTailorApi } from '@/lib/resumeTailorApi';
import type { ExportFormat, ResumeTemplate, TemplateInfo } from '@/types/tailoredResume';

interface ExportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  tailorId: string;
  candidateName?: string;
}

const FORMAT_CONFIG: Record<
  ExportFormat,
  { label: string; icon: typeof FileText; extension: string }
> = {
  pdf: {
    label: 'PDF Document',
    icon: FileText,
    extension: 'pdf',
  },
  docx: {
    label: 'Word Document',
    icon: FileType,
    extension: 'docx',
  },
  markdown: {
    label: 'Markdown',
    icon: FileText,
    extension: 'md',
  },
};

const TEMPLATE_PREVIEWS: Record<ResumeTemplate, string> = {
  modern: `
    <div style="font-family: Arial, sans-serif; padding: 20px; max-width: 400px; border: 1px solid #e5e7eb; border-radius: 8px;">
      <h3 style="font-size: 18px; font-weight: bold; margin-bottom: 4px; color: #000;">John Doe</h3>
      <p style="font-size: 11px; color: #666; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid #000;">john@email.com | (555) 123-4567 | linkedin.com/in/johndoe</p>
      <h4 style="font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; padding-bottom: 4px; border-bottom: 1px solid #000;">Experience</h4>
      <p style="font-size: 10px; font-weight: 600; margin-bottom: 2px;">Senior Software Engineer</p>
      <p style="font-size: 9px; color: #666; margin-bottom: 4px;">Acme Corp | 2020 - Present</p>
      <ul style="font-size: 9px; padding-left: 16px; margin: 0;">
        <li>Led development of microservices</li>
        <li>Reduced deployment time by 60%</li>
      </ul>
    </div>
  `,
  classic: `
    <div style="font-family: Georgia, serif; padding: 20px; max-width: 400px; border: 1px solid #e5e7eb; border-radius: 8px;">
      <h3 style="font-size: 20px; font-weight: bold; text-align: center; margin-bottom: 4px; color: #000; text-transform: uppercase; letter-spacing: 2px;">John Doe</h3>
      <p style="font-size: 10px; text-align: center; color: #000; margin-bottom: 12px;">john@email.com | (555) 123-4567 | San Francisco</p>
      <h4 style="font-size: 11px; font-weight: bold; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 8px; padding-bottom: 4px; border-bottom: 2px solid #000;">Professional Experience</h4>
      <p style="font-size: 11px; font-weight: bold; margin-bottom: 2px; text-transform: uppercase;">Senior Software Engineer</p>
      <p style="font-size: 10px; font-style: italic; margin-bottom: 4px;">Acme Corporation | San Francisco, CA | 2020 - Present</p>
      <ul style="font-size: 10px; padding-left: 20px; margin: 0;">
        <li style="margin-bottom: 4px;">Led development of microservices architecture</li>
        <li style="margin-bottom: 4px;">Reduced deployment time by 60%</li>
      </ul>
    </div>
  `,
};

export function ExportDialog({
  open,
  onOpenChange,
  tailorId,
  candidateName,
}: ExportDialogProps) {
  const [selectedFormat, setSelectedFormat] = useState<ExportFormat>('pdf');
  const [selectedTemplate, setSelectedTemplate] = useState<ResumeTemplate>('modern');
  const [previewHtml, setPreviewHtml] = useState<string | null>(null);

  // Fetch available templates
  const { data: templatesData } = useQuery({
    queryKey: ['resume-templates'],
    queryFn: () => resumeTailorApi.getTemplates(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Fetch preview when template changes
  const previewQuery = useQuery({
    queryKey: ['resume-preview', tailorId, selectedTemplate],
    queryFn: () => resumeTailorApi.getPreview(tailorId, selectedTemplate),
    enabled: open && selectedFormat !== 'markdown',
    staleTime: 30 * 1000, // 30 seconds
  });

  useEffect(() => {
    if (previewQuery.data) {
      setPreviewHtml(previewQuery.data);
    }
  }, [previewQuery.data]);

  // Export mutation
  const exportMutation = useMutation({
    mutationFn: async () => {
      const filename = candidateName
        ? `${candidateName.replace(/\s+/g, '_')}_tailored_resume.${FORMAT_CONFIG[selectedFormat].extension}`
        : `tailored_resume.${FORMAT_CONFIG[selectedFormat].extension}`;
      
      await resumeTailorApi.downloadResume(tailorId, selectedFormat, selectedTemplate, filename);
    },
    onSuccess: () => {
      toast.success(`Resume exported as ${FORMAT_CONFIG[selectedFormat].label}`);
      onOpenChange(false);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to export resume');
    },
  });

  const templates = templatesData?.templates || [
    { id: 'modern' as ResumeTemplate, name: 'Modern', description: 'Clean, minimal design', is_default: true },
    { id: 'classic' as ResumeTemplate, name: 'Classic', description: 'Traditional, formal design', is_default: false },
  ];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh]">
        <DialogHeader>
          <DialogTitle>Export Tailored Resume</DialogTitle>
          <DialogDescription>
            Choose a template and format to export your tailored resume
          </DialogDescription>
        </DialogHeader>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 py-4">
          {/* Left side - Options */}
          <div className="space-y-6">
            {/* Template Selection */}
            <div className="space-y-3">
              <Label className="text-sm font-medium">Template</Label>
              <div className="grid grid-cols-1 gap-3">
                {templates.map((template) => (
                  <button
                    key={template.id}
                    onClick={() => setSelectedTemplate(template.id)}
                    className={`flex items-start gap-3 p-3 rounded-lg border-2 text-left transition-all ${
                      selectedTemplate === template.id
                        ? 'border-primary bg-primary/5'
                        : 'border-muted hover:border-muted-foreground/30'
                    }`}
                  >
                    <div className="flex-shrink-0 mt-0.5">
                      {selectedTemplate === template.id ? (
                        <div className="w-5 h-5 rounded-full bg-primary flex items-center justify-center">
                          <Check className="w-3 h-3 text-primary-foreground" />
                        </div>
                      ) : (
                        <div className="w-5 h-5 rounded-full border-2 border-muted-foreground/30" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{template.name}</span>
                        {template.is_default && (
                          <span className="text-xs bg-muted px-1.5 py-0.5 rounded">Default</span>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground mt-0.5">
                        {template.description}
                      </p>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Format Selection */}
            <div className="space-y-3">
              <Label className="text-sm font-medium">Format</Label>
              <Select
                value={selectedFormat}
                onValueChange={(value) => setSelectedFormat(value as ExportFormat)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(Object.keys(FORMAT_CONFIG) as ExportFormat[]).map((format) => {
                    const config = FORMAT_CONFIG[format];
                    const Icon = config.icon;
                    return (
                      <SelectItem key={format} value={format}>
                        <div className="flex items-center gap-2">
                          <Icon className="h-4 w-4" />
                          <span>{config.label}</span>
                        </div>
                      </SelectItem>
                    );
                  })}
                </SelectContent>
              </Select>
            </div>

            {/* Template Preview Thumbnails */}
            <div className="space-y-3">
              <Label className="text-sm font-medium">Preview</Label>
              <div className="border rounded-lg overflow-hidden bg-muted/30">
                <div 
                  className="p-2 text-center text-xs text-muted-foreground"
                  dangerouslySetInnerHTML={{ __html: TEMPLATE_PREVIEWS[selectedTemplate] }}
                />
              </div>
            </div>
          </div>

          {/* Right side - Live Preview */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label className="text-sm font-medium">Live Preview</Label>
              {previewQuery.isFetching && (
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  Loading...
                </div>
              )}
            </div>
            <ScrollArea className="h-[400px] border rounded-lg bg-white">
              {selectedFormat === 'markdown' ? (
                <div className="p-4 text-sm text-muted-foreground">
                  <p>Template preview is not available for Markdown format.</p>
                  <p className="mt-2">The raw markdown content will be exported.</p>
                </div>
              ) : previewQuery.isLoading ? (
                <div className="p-4 space-y-3">
                  <Skeleton className="h-8 w-48" />
                  <Skeleton className="h-4 w-64" />
                  <Skeleton className="h-4 w-full mt-6" />
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-4 w-5/6" />
                </div>
              ) : previewHtml ? (
                <iframe
                  srcDoc={previewHtml}
                  className="w-full h-full border-0"
                  title="Resume Preview"
                  sandbox="allow-same-origin"
                />
              ) : (
                <div className="p-4 flex items-center justify-center h-full text-muted-foreground">
                  <Eye className="h-8 w-8 mr-2 opacity-50" />
                  <span>Preview not available</span>
                </div>
              )}
            </ScrollArea>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={() => exportMutation.mutate()}
            disabled={exportMutation.isPending}
          >
            {exportMutation.isPending ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Exporting...
              </>
            ) : (
              <>
                <Download className="h-4 w-4 mr-2" />
                Export {FORMAT_CONFIG[selectedFormat].label}
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
