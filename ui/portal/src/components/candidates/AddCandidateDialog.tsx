/**
 * Add/Edit Candidate Dialog
 * Modal dialog with tabs for resume upload or manual entry
 */

import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Upload, PenSquare } from 'lucide-react';
import { ResumeUpload } from './ResumeUpload';
import { CandidateForm } from './CandidateForm';
import type { Candidate, CandidateCreateInput, CandidateUpdateInput, UploadResumeResponse } from '@/types/candidate';

interface AddCandidateDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
  candidate?: Candidate; // If provided, dialog is in edit mode
}

export function AddCandidateDialog({
  open,
  onOpenChange,
  onSuccess,
  candidate,
}: AddCandidateDialogProps) {
  const [activeTab, setActiveTab] = useState<string>('upload');
  const [parsedData, setParsedData] = useState<UploadResumeResponse | null>(null);
  const [showForm, setShowForm] = useState(false);

  const handleUploadSuccess = (result: UploadResumeResponse) => {
    setParsedData(result);
    setShowForm(true);
  };

  const handleFormSubmit = async (data: CandidateCreateInput | CandidateUpdateInput) => {
    // If we have parsed data with candidate_id, the candidate was already created
    if (parsedData?.candidate_id) {
      // This path is for when a resume was uploaded and parsed, and a candidate was auto-created.
      // The form is then shown to review/edit. In this case, we are effectively updating
      // the existing candidate.
      if (candidate) { // Should not happen if parsedData?.candidate_id is true, but for type safety
        try {
          const { candidateApi } = await import('@/lib/candidateApi');
          await candidateApi.updateCandidate(candidate.id, data as CandidateUpdateInput);
          onSuccess();
          onOpenChange(false);
          resetState();
        } catch (error) {
          console.error('Failed to update candidate after parse:', error);
        }
      } else {
        // This case implies a candidate was created by resume upload, but we don't have the 'candidate' prop.
        // This might be an edge case or a logic flaw. For now, just close.
        onSuccess();
        onOpenChange(false);
        resetState();
      }
    } else {
      // This path is for manual creation or when parsed data doesn't lead to auto-creation.
      // We are creating a new candidate.
      try {
        const { candidateApi } = await import('@/lib/candidateApi');
        await candidateApi.createCandidate(data as CandidateCreateInput);
        onSuccess();
        onOpenChange(false);
        resetState();
      } catch (error) {
        console.error('Failed to create candidate:', error);
      }
    }
  };

  const handleCancel = () => {
    onOpenChange(false);
    resetState();
  };

  const resetState = () => {
    setActiveTab('upload');
    setParsedData(null);
    setShowForm(false);
  };

  // Edit mode: only show form
  if (candidate) {
    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Edit Candidate</DialogTitle>
            <DialogDescription>
              Update candidate information
            </DialogDescription>
          </DialogHeader>
          
          <CandidateForm
            candidate={candidate}
            onSubmit={async (data: CandidateUpdateInput) => {
              try {
                const { candidateApi } = await import('@/lib/candidateApi');
                await candidateApi.updateCandidate(candidate.id, data);
                onSuccess();
                onOpenChange(false);
              } catch (error) {
                console.error('Failed to update candidate:', error);
              }
            }}
            onCancel={handleCancel}
          />
        </DialogContent>
      </Dialog>
    );
  }

  // Create mode: show tabs or form based on state
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Add Candidate</DialogTitle>
          <DialogDescription>
            {showForm
              ? 'Review and edit the parsed information'
              : 'Upload a resume or enter details manually'}
          </DialogDescription>
        </DialogHeader>

        {!showForm ? (
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="upload" className="gap-2">
                <Upload className="h-4 w-4" />
                Upload Resume
              </TabsTrigger>
              <TabsTrigger value="manual" className="gap-2">
                <PenSquare className="h-4 w-4" />
                Manual Entry
              </TabsTrigger>
            </TabsList>

            <TabsContent value="upload" className="mt-6">
              <ResumeUpload onUploadSuccess={handleUploadSuccess} />
            </TabsContent>

            <TabsContent value="manual" className="mt-6">
              <CandidateForm
                onSubmit={handleFormSubmit as (data: CandidateCreateInput | CandidateUpdateInput) => void | Promise<void>}
                onCancel={handleCancel}
              />
            </TabsContent>
          </Tabs>
        ) : (
          <CandidateForm
            parsedData={parsedData?.parsed_data}
            onSubmit={handleFormSubmit as (data: CandidateCreateInput | CandidateUpdateInput) => void | Promise<void>}
            onCancel={handleCancel}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}
