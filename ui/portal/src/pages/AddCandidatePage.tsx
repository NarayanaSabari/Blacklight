/**
 * Add Candidate Page
 * Dedicated page for adding candidates with resume upload or manual entry
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Upload, PenSquare, ArrowLeft } from 'lucide-react';
import { ResumeUpload } from '@/components/candidates/ResumeUpload';
import { ResumeViewer } from '@/components/candidates/ResumeViewer';
import { CandidateForm } from '@/components/candidates/CandidateForm';
import type { CandidateCreateInput, CandidateUpdateInput, UploadResumeResponse } from '@/types/candidate';

export function AddCandidatePage() {
  const navigate = useNavigate();
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
      // Navigate to candidate detail page
      navigate(`/candidates/${parsedData.candidate_id}`);
    } else {
      // Create candidate manually
      try {
        const { candidateApi } = await import('@/lib/candidateApi');
        const newCandidate = await candidateApi.createCandidate(data as CandidateCreateInput);
        navigate(`/candidates/${newCandidate.id}`);
      } catch (error) {
        console.error('Failed to create candidate:', error);
      }
    }
  };

  const handleCancel = () => {
    navigate('/candidates');
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate('/candidates')}
          className="gap-2"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Candidates
        </Button>
      </div>

      <div>
        <h1 className="text-3xl font-bold text-slate-900">Add New Candidate</h1>
        <p className="text-slate-600 mt-1">
          Upload a resume for AI parsing or enter candidate details manually
        </p>
      </div>

      {/* Main Content */}
      <Card>
        <CardHeader>
          <CardTitle>
            {showForm ? 'Review & Edit Information' : 'Choose Input Method'}
          </CardTitle>
          <CardDescription>
            {showForm
              ? 'Review the parsed information and make any necessary edits'
              : 'Select how you want to add the candidate'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {!showForm ? (
            <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
              <TabsList className="grid w-full grid-cols-2 mb-6">
                <TabsTrigger value="upload" className="gap-2">
                  <Upload className="h-4 w-4" />
                  Upload Resume
                </TabsTrigger>
                <TabsTrigger value="manual" className="gap-2">
                  <PenSquare className="h-4 w-4" />
                  Manual Entry
                </TabsTrigger>
              </TabsList>

              <TabsContent value="upload" className="space-y-4">
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
                  <h3 className="font-semibold text-blue-900 mb-2">AI-Powered Resume Parsing</h3>
                  <p className="text-sm text-blue-700">
                    Upload a resume in PDF or DOCX format. Our AI will automatically extract candidate 
                    information including personal details, skills, experience, and education.
                  </p>
                </div>
                <ResumeUpload onUploadSuccess={handleUploadSuccess} />
              </TabsContent>

              <TabsContent value="manual" className="space-y-4">
                <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 mb-4">
                  <h3 className="font-semibold text-purple-900 mb-2">Manual Entry</h3>
                  <p className="text-sm text-purple-700">
                    Manually enter candidate information. You can always upload a resume later 
                    to enhance the candidate profile.
                  </p>
                </div>
                <CandidateForm
                  onSubmit={handleFormSubmit}
                  onCancel={handleCancel}
                />
              </TabsContent>
            </Tabs>
          ) : (
            <div className="space-y-4">
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <h3 className="font-semibold text-green-900 mb-2">✓ Resume Parsed Successfully</h3>
                <p className="text-sm text-green-700">
                  We've extracted the information below from the resume. Please review and edit 
                  as needed before saving.
                </p>
              </div>
              
              {/* Two-Column Layout: Form + Resume Viewer */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Left Column: Form */}
                <div className="lg:col-span-1">
                  <CandidateForm
                    parsedData={parsedData?.parsed_data}
                    onSubmit={handleFormSubmit}
                    onCancel={handleCancel}
                  />
                </div>

                {/* Right Column: Resume Viewer */}
                <div className="lg:col-span-1 lg:sticky lg:top-6 lg:self-start">
                  <ResumeViewer
                    resumeUrl={parsedData?.file_info?.file_url}
                    resumeFileName={parsedData?.file_info?.original_filename}
                    candidateName={parsedData?.parsed_data?.full_name as string}
                  />
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
