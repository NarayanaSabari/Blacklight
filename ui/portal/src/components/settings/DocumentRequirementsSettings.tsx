/**
 * Document Requirements Settings Component
 * Allows tenant admins to configure which documents are required during self-onboarding
 */

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  fetchDocumentRequirements, 
  updateDocumentRequirements,
  type DocumentRequirement 
} from '@/lib/api/settings';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
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
import { 
  Plus, 
  Pencil, 
  Trash2, 
  GripVertical, 
  FileText, 
  Loader2,
  Save,
  Info,
  AlertCircle
} from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';

// Predefined document type options
const DOCUMENT_TYPE_OPTIONS = [
  { value: 'id_proof', label: 'ID Proof' },
  { value: 'work_authorization', label: 'Work Authorization' },
  { value: 'educational_certificates', label: 'Educational Certificates' },
  { value: 'employment_verification', label: 'Employment Verification' },
  { value: 'professional_certifications', label: 'Professional Certifications' },
  { value: 'background_check', label: 'Background Check' },
  { value: 'tax_documents', label: 'Tax Documents' },
  { value: 'references', label: 'References' },
  { value: 'portfolio', label: 'Portfolio' },
  { value: 'other', label: 'Other' },
];

// Common file type options
const FILE_TYPE_OPTIONS = [
  { value: 'application/pdf', label: 'PDF' },
  { value: 'image/jpeg', label: 'JPEG' },
  { value: 'image/png', label: 'PNG' },
  { value: 'application/msword', label: 'DOC' },
  { value: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', label: 'DOCX' },
];

// Default empty document for the form
const DEFAULT_DOCUMENT: Omit<DocumentRequirement, 'id'> = {
  document_type: 'other',
  label: '',
  description: '',
  is_required: true,
  display_order: 0,
  allowed_file_types: ['application/pdf', 'image/jpeg', 'image/png'],
  max_file_size_mb: 10,
};

function generateId(): string {
  return `doc_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

interface DocumentFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  document?: DocumentRequirement;
  onSave: (document: DocumentRequirement) => void;
  existingTypes: string[];
}

function DocumentFormDialog({ 
  open, 
  onOpenChange, 
  document, 
  onSave,
  existingTypes 
}: DocumentFormDialogProps) {
  const isEditing = !!document;
  const [formData, setFormData] = useState<Omit<DocumentRequirement, 'id'>>({
    ...DEFAULT_DOCUMENT,
    ...(document || {}),
  });
  const [selectedFileTypes, setSelectedFileTypes] = useState<string[]>(
    document?.allowed_file_types || DEFAULT_DOCUMENT.allowed_file_types
  );

  useEffect(() => {
    if (document) {
      setFormData(document);
      setSelectedFileTypes(document.allowed_file_types);
    } else {
      setFormData(DEFAULT_DOCUMENT);
      setSelectedFileTypes(DEFAULT_DOCUMENT.allowed_file_types);
    }
  }, [document, open]);

  const handleSave = () => {
    if (!formData.label.trim()) {
      toast.error('Document label is required');
      return;
    }

    if (selectedFileTypes.length === 0) {
      toast.error('At least one file type must be selected');
      return;
    }

    const newDocument: DocumentRequirement = {
      id: document?.id || generateId(),
      ...formData,
      allowed_file_types: selectedFileTypes,
    };

    onSave(newDocument);
    onOpenChange(false);
  };

  const toggleFileType = (fileType: string) => {
    setSelectedFileTypes(prev => 
      prev.includes(fileType) 
        ? prev.filter(t => t !== fileType)
        : [...prev, fileType]
    );
  };

  // Filter out already used document types (unless editing that type)
  const availableTypes = DOCUMENT_TYPE_OPTIONS.filter(
    opt => !existingTypes.includes(opt.value) || document?.document_type === opt.value
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>
            {isEditing ? 'Edit Document Requirement' : 'Add Document Requirement'}
          </DialogTitle>
          <DialogDescription>
            Configure the document requirements for candidate self-onboarding
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Document Type */}
          <div className="space-y-2">
            <Label htmlFor="document_type">Document Type</Label>
            <Select 
              value={formData.document_type} 
              onValueChange={(value) => setFormData(prev => ({ ...prev, document_type: value }))}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select document type" />
              </SelectTrigger>
              <SelectContent>
                {availableTypes.map(option => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Label */}
          <div className="space-y-2">
            <Label htmlFor="label">Display Label *</Label>
            <Input
              id="label"
              placeholder="e.g., Government-issued ID"
              value={formData.label}
              onChange={(e) => setFormData(prev => ({ ...prev, label: e.target.value }))}
            />
            <p className="text-xs text-muted-foreground">
              This is the label candidates will see during onboarding
            </p>
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description">Help Text</Label>
            <Textarea
              id="description"
              placeholder="e.g., Please upload a clear copy of your passport, driver's license, or state ID"
              value={formData.description || ''}
              onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
              rows={2}
            />
          </div>

          {/* Is Required */}
          <div className="flex items-center space-x-2">
            <Checkbox
              id="is_required"
              checked={formData.is_required}
              onCheckedChange={(checked) => 
                setFormData(prev => ({ ...prev, is_required: checked === true }))
              }
            />
            <Label htmlFor="is_required" className="font-normal">
              This document is mandatory
            </Label>
          </div>

          {/* Allowed File Types */}
          <div className="space-y-2">
            <Label>Allowed File Types</Label>
            <div className="flex flex-wrap gap-2">
              {FILE_TYPE_OPTIONS.map(option => (
                <Badge
                  key={option.value}
                  variant={selectedFileTypes.includes(option.value) ? 'default' : 'outline'}
                  className="cursor-pointer"
                  onClick={() => toggleFileType(option.value)}
                >
                  {option.label}
                </Badge>
              ))}
            </div>
          </div>

          {/* Max File Size */}
          <div className="space-y-2">
            <Label htmlFor="max_file_size">Max File Size (MB)</Label>
            <Input
              id="max_file_size"
              type="number"
              min={1}
              max={50}
              value={formData.max_file_size_mb}
              onChange={(e) => setFormData(prev => ({ 
                ...prev, 
                max_file_size_mb: Math.min(50, Math.max(1, parseInt(e.target.value) || 10))
              }))}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSave}>
            {isEditing ? 'Save Changes' : 'Add Document'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function DocumentRequirementsSettings() {
  const queryClient = useQueryClient();
  const [documents, setDocuments] = useState<DocumentRequirement[]>([]);
  const [hasChanges, setHasChanges] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingDocument, setEditingDocument] = useState<DocumentRequirement | undefined>();

  // Fetch current document requirements
  const { data, isLoading, error } = useQuery({
    queryKey: ['document-requirements'],
    queryFn: fetchDocumentRequirements,
    staleTime: 0,
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: updateDocumentRequirements,
    onSuccess: () => {
      toast.success('Document requirements saved successfully');
      setHasChanges(false);
      queryClient.invalidateQueries({ queryKey: ['document-requirements'] });
    },
    onError: (error: Error) => {
      toast.error(`Failed to save: ${error.message}`);
    },
  });

  // Sync local state with fetched data
  useEffect(() => {
    if (data?.requirements) {
      setDocuments(data.requirements);
      setHasChanges(false);
    }
  }, [data]);

  const handleAddDocument = () => {
    setEditingDocument(undefined);
    setDialogOpen(true);
  };

  const handleEditDocument = (doc: DocumentRequirement) => {
    setEditingDocument(doc);
    setDialogOpen(true);
  };

  const handleSaveDocument = (doc: DocumentRequirement) => {
    setDocuments(prev => {
      const existingIndex = prev.findIndex(d => d.id === doc.id);
      if (existingIndex >= 0) {
        // Update existing
        const updated = [...prev];
        updated[existingIndex] = doc;
        return updated;
      } else {
        // Add new with display_order at end
        return [...prev, { ...doc, display_order: prev.length }];
      }
    });
    setHasChanges(true);
  };

  const handleDeleteDocument = (docId: string) => {
    setDocuments(prev => prev.filter(d => d.id !== docId));
    setHasChanges(true);
  };

  const handleMoveUp = (index: number) => {
    if (index === 0) return;
    setDocuments(prev => {
      const updated = [...prev];
      [updated[index - 1], updated[index]] = [updated[index], updated[index - 1]];
      // Update display_order values
      return updated.map((d, i) => ({ ...d, display_order: i }));
    });
    setHasChanges(true);
  };

  const handleMoveDown = (index: number) => {
    if (index === documents.length - 1) return;
    setDocuments(prev => {
      const updated = [...prev];
      [updated[index], updated[index + 1]] = [updated[index + 1], updated[index]];
      // Update display_order values
      return updated.map((d, i) => ({ ...d, display_order: i }));
    });
    setHasChanges(true);
  };

  const handleSave = () => {
    updateMutation.mutate({ requirements: documents });
  };

  const handleReset = () => {
    if (data?.requirements) {
      setDocuments(data.requirements);
      setHasChanges(false);
    }
  };

  // Get file type labels from MIME types
  const getFileTypeLabels = (mimeTypes: string[]) => {
    return mimeTypes
      .map(mime => FILE_TYPE_OPTIONS.find(opt => opt.value === mime)?.label || mime.split('/')[1]?.toUpperCase())
      .join(', ');
  };

  // Get existing document types for validation
  const existingTypes = documents.map(d => d.document_type);

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="py-12">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Failed to load document requirements. Please try again.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div>
            <CardTitle>Document Requirements</CardTitle>
            <CardDescription>
              Configure which documents candidates must upload during self-onboarding
            </CardDescription>
          </div>
          <Button onClick={handleAddDocument} size="sm">
            <Plus className="h-4 w-4 mr-2" />
            Add Document
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Info Alert */}
        <Alert>
          <Info className="h-4 w-4" />
          <AlertDescription>
            <strong>Resume</strong> is always required and handled separately with AI parsing. 
            Configure additional documents that candidates should provide during onboarding.
          </AlertDescription>
        </Alert>

        {/* Documents List */}
        {documents.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center border rounded-lg border-dashed">
            <FileText className="h-12 w-12 text-slate-400 mb-4" />
            <h3 className="text-lg font-semibold text-slate-900 mb-2">No Additional Documents</h3>
            <p className="text-slate-600 max-w-sm mb-4">
              Only the resume will be required during candidate onboarding. 
              Add document requirements if you need additional files.
            </p>
            <Button variant="outline" onClick={handleAddDocument}>
              <Plus className="h-4 w-4 mr-2" />
              Add First Document
            </Button>
          </div>
        ) : (
          <div className="space-y-2">
            {documents.map((doc, index) => (
              <div 
                key={doc.id}
                className="flex items-center gap-3 p-4 border rounded-lg bg-slate-50 hover:bg-slate-100 transition-colors"
              >
                {/* Drag Handle / Reorder */}
                <div className="flex flex-col gap-1">
                  <Button 
                    variant="ghost" 
                    size="icon" 
                    className="h-6 w-6"
                    onClick={() => handleMoveUp(index)}
                    disabled={index === 0}
                  >
                    <GripVertical className="h-4 w-4 rotate-90" />
                  </Button>
                  <Button 
                    variant="ghost" 
                    size="icon" 
                    className="h-6 w-6"
                    onClick={() => handleMoveDown(index)}
                    disabled={index === documents.length - 1}
                  >
                    <GripVertical className="h-4 w-4 rotate-90" />
                  </Button>
                </div>

                {/* Document Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <FileText className="h-4 w-4 text-slate-500" />
                    <span className="font-medium text-slate-900">{doc.label}</span>
                    {doc.is_required ? (
                      <Badge variant="destructive" className="text-xs">Required</Badge>
                    ) : (
                      <Badge variant="secondary" className="text-xs">Optional</Badge>
                    )}
                  </div>
                  {doc.description && (
                    <p className="text-sm text-slate-600 truncate">{doc.description}</p>
                  )}
                  <div className="flex items-center gap-4 mt-1 text-xs text-slate-500">
                    <span>Type: {DOCUMENT_TYPE_OPTIONS.find(o => o.value === doc.document_type)?.label || doc.document_type}</span>
                    <span>Files: {getFileTypeLabels(doc.allowed_file_types)}</span>
                    <span>Max: {doc.max_file_size_mb}MB</span>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-1">
                  <Button 
                    variant="ghost" 
                    size="icon"
                    onClick={() => handleEditDocument(doc)}
                  >
                    <Pencil className="h-4 w-4" />
                  </Button>
                  <Button 
                    variant="ghost" 
                    size="icon"
                    onClick={() => handleDeleteDocument(doc.id)}
                    className="text-destructive hover:text-destructive"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Save/Reset Actions */}
        {hasChanges && (
          <div className="flex items-center justify-end gap-2 pt-4 border-t">
            <Button variant="outline" onClick={handleReset}>
              Reset Changes
            </Button>
            <Button onClick={handleSave} disabled={updateMutation.isPending}>
              {updateMutation.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              <Save className="h-4 w-4 mr-2" />
              Save Changes
            </Button>
          </div>
        )}

        {/* Document Form Dialog */}
        <DocumentFormDialog
          open={dialogOpen}
          onOpenChange={setDialogOpen}
          document={editingDocument}
          onSave={handleSaveDocument}
          existingTypes={existingTypes}
        />
      </CardContent>
    </Card>
  );
}
