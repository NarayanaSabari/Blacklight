/**
 * Edit Candidate Page
 * Dedicated page for editing candidate information
 */

import { useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { CandidateForm } from '@/components/candidates/CandidateForm';
import { ResumeViewer } from '@/components/candidates/ResumeViewer';
import { candidateApi } from '@/lib/candidateApi';
import { toast } from 'sonner';
import type { CandidateCreateInput, CandidateUpdateInput } from '@/types/candidate';

export function EditCandidatePage() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const candidateId = parseInt(id || '0', 10);

  // Fetch candidate data
  const { data: candidate, isLoading, error } = useQuery({
    queryKey: ['candidate', candidateId],
    queryFn: () => candidateApi.getCandidate(candidateId),
    enabled: !!candidateId,
  });

  useEffect(() => {
    if (error) {
      toast.error('Failed to load candidate');
      navigate('/candidates');
    }
  }, [error, navigate]);

  const handleFormSubmit = async (data: CandidateCreateInput | CandidateUpdateInput) => {
    try {
      await candidateApi.updateCandidate(candidateId, data as CandidateUpdateInput);
      toast.success('Candidate updated successfully');
      navigate(`/candidates/${candidateId}`);
    } catch (error) {
      console.error('Failed to update candidate:', error);
      toast.error('Failed to update candidate');
    }
  };

  const handleCancel = () => {
    navigate(`/candidates/${candidateId}`);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!candidate) {
    return null;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate(`/candidates/${candidateId}`)}
          className="gap-2"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Candidate
        </Button>
      </div>

      <div>
        <h1 className="text-3xl font-bold text-slate-900">Edit Candidate</h1>
        <p className="text-slate-600 mt-1">
          Update {candidate.full_name || `${candidate.first_name} ${candidate.last_name}`}'s information
        </p>
      </div>

      {/* Two-Column Layout: Form + Resume Viewer */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column: Form */}
        <div className="lg:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle>Candidate Information</CardTitle>
              <CardDescription>
                Update the candidate's details below. Check the resume on the right for reference.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <CandidateForm
                candidate={candidate}
                onSubmit={handleFormSubmit}
                onCancel={handleCancel}
              />
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Resume Viewer */}
        <div className="lg:col-span-1 lg:sticky lg:top-6 lg:self-start">
          <ResumeViewer
            resumeUrl={candidate.resume_file_url}
            resumeFileName={candidate.resume_file_url?.split('/').pop()}
            candidateName={candidate.full_name || `${candidate.first_name} ${candidate.last_name}`}
          />
        </div>
      </div>
    </div>
  );
}
