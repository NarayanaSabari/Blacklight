/**
 * Polished Resume Editor Component
 * A simple markdown editor for editing the polished resume
 */

import { useState, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Save, X, Eye, Edit2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface PolishedResumeEditorProps {
  initialContent: string;
  onSave: (markdown: string) => void;
  onCancel: () => void;
  isSaving?: boolean;
}

export function PolishedResumeEditor({
  initialContent,
  onSave,
  onCancel,
  isSaving = false,
}: PolishedResumeEditorProps) {
  const [content, setContent] = useState(initialContent);
  const [activeTab, setActiveTab] = useState<string>('edit');

  const handleSave = useCallback(() => {
    onSave(content);
  }, [content, onSave]);

  const hasChanges = content !== initialContent;

  return (
    <div className="space-y-4">
      {/* Editor Header */}
      <div className="flex items-center justify-between">
        <div className="text-sm text-muted-foreground">
          {hasChanges ? (
            <span className="text-amber-600 dark:text-amber-400">Unsaved changes</span>
          ) : (
            <span>No changes</span>
          )}
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={onCancel}
            disabled={isSaving}
          >
            <X className="h-4 w-4 mr-2" />
            Cancel
          </Button>
          <Button
            size="sm"
            onClick={handleSave}
            disabled={!hasChanges || isSaving}
          >
            {isSaving ? (
              <>
                <span className="h-4 w-4 mr-2 animate-spin">...</span>
                Saving...
              </>
            ) : (
              <>
                <Save className="h-4 w-4 mr-2" />
                Save Changes
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Tabs for Edit/Preview */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="edit" className="gap-2">
            <Edit2 className="h-4 w-4" />
            Edit
          </TabsTrigger>
          <TabsTrigger value="preview" className="gap-2">
            <Eye className="h-4 w-4" />
            Preview
          </TabsTrigger>
        </TabsList>

        <TabsContent value="edit" className="mt-4">
          <Textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            className="min-h-[500px] font-mono text-sm resize-none"
            placeholder="Enter markdown content..."
          />
          <p className="text-xs text-muted-foreground mt-2">
            Supports Markdown formatting. Use # for headings, ** for bold, - for bullet points, etc.
          </p>
        </TabsContent>

        <TabsContent value="preview" className="mt-4">
          <div className="prose prose-sm dark:prose-invert max-w-none border rounded-lg p-6 bg-white dark:bg-gray-900 min-h-[500px] max-h-[600px] overflow-y-auto">
            {content ? (
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {content}
              </ReactMarkdown>
            ) : (
              <p className="text-muted-foreground italic">No content to preview</p>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
