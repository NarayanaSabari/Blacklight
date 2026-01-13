/**
 * ExportMenu Component
 * Dropdown menu for exporting tailored resume in different formats
 */

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  Download,
  FileText,
  FileType,
  Loader2,
  ChevronDown,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

import { resumeTailorApi } from '@/lib/resumeTailorApi';
import type { ExportFormat } from '@/types/tailoredResume';

interface ExportMenuProps {
  tailorId: string;  // UUID string from tailor_id
  candidateName?: string;
  disabled?: boolean;
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

export function ExportMenu({ tailorId, candidateName, disabled }: ExportMenuProps) {
  const [exportingFormat, setExportingFormat] = useState<ExportFormat | null>(null);

  const exportMutation = useMutation({
    mutationFn: async (format: ExportFormat) => {
      setExportingFormat(format);
      const filename = candidateName
        ? `${candidateName.replace(/\s+/g, '_')}_tailored_resume.${FORMAT_CONFIG[format].extension}`
        : `tailored_resume.${FORMAT_CONFIG[format].extension}`;
      
      await resumeTailorApi.downloadResume(tailorId, format, 'modern', filename);
    },
    onSuccess: (_, format) => {
      toast.success(`Resume exported as ${FORMAT_CONFIG[format].label}`);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to export resume');
    },
    onSettled: () => {
      setExportingFormat(null);
    },
  });

  const isExporting = exportMutation.isPending;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" disabled={disabled || isExporting}>
          {isExporting ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Exporting...
            </>
          ) : (
            <>
              <Download className="h-4 w-4 mr-2" />
              Export
              <ChevronDown className="h-4 w-4 ml-1" />
            </>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        <DropdownMenuLabel>Export Format</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {(Object.keys(FORMAT_CONFIG) as ExportFormat[]).map((format) => {
          const config = FORMAT_CONFIG[format];
          const Icon = config.icon;
          const isCurrentlyExporting = exportingFormat === format;

          return (
            <DropdownMenuItem
              key={format}
              onClick={() => exportMutation.mutate(format)}
              disabled={isExporting}
              className="cursor-pointer"
            >
              {isCurrentlyExporting ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Icon className="h-4 w-4 mr-2" />
              )}
              {config.label}
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
