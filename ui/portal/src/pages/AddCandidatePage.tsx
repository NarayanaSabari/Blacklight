/**
 * Add Candidate Page
 * Dedicated page for adding candidates with resume upload or manual entry
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Upload, PenSquare, ArrowLeft, Mail, FileUp, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';
import { ResumeUpload } from '@/components/candidates/ResumeUpload';
import { ResumeViewer } from '@/components/candidates/ResumeViewer';
import { CandidateForm } from '@/components/candidates/CandidateForm';
import { invitationApi } from '@/lib/api/invitationApi';
import type { CandidateCreateInput, CandidateUpdateInput, UploadResumeResponse } from '@/types/candidate';
import type { InvitationCreateRequest, InvitationWithRelations } from '@/types/invitation';

export function AddCandidatePage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<string>('manual');
  const [manualSubTab, setManualSubTab] = useState<string>('upload');
  const [parsedData, setParsedData] = useState<UploadResumeResponse | null>(null);
  const [showForm, setShowForm] = useState(false);
  
  // Email invite form state
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteFirstName, setInviteFirstName] = useState('');
  const [inviteLastName, setInviteLastName] = useState('');
  const [inviteMessage, setInviteMessage] = useState('');
  const [duplicateError, setDuplicateError] = useState(false);

  const handleUploadSuccess = (result: UploadResumeResponse) => {
    setParsedData(result);
    
    // Check if this is async processing (new flow)
    if (result.status === 'processing' || result.message?.includes('Processing')) {
      // Show success toast for async processing
      toast.success('Resume uploaded successfully!', {
        description: 'AI parsing in progress. The candidate will appear in "Review Submissions" shortly.',
        duration: 6000,
      });
      
      // Navigate to candidate-management with pending-review tab
      setTimeout(() => {
        navigate('/candidate-management?tab=onboarding');
      }, 2000);
    } else {
      // Old sync flow - show form immediately
      setShowForm(true);
    }
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

  // Send invitation mutation
  const sendInviteMutation = useMutation<InvitationWithRelations, Error, InvitationCreateRequest>({
    mutationFn: (data) => invitationApi.create(data),
    onSuccess: () => {
      toast.success("Invitation sent successfully! The candidate will receive an email with onboarding instructions.");
      setInviteEmail("");
      setInviteFirstName("");
      setInviteLastName("");
      setInviteMessage("");
      setDuplicateError(false);
      navigate('/invitations');
    },
    onError: (error: any) => {
      // Handle 409 Conflict - invitation already exists
      if (error?.status === 409 || error?.message?.includes('already exists')) {
        setDuplicateError(true);
        toast.error(
          "An active invitation already exists for this email address.",
          {
            description: "Please check the invitations list or use the resend option if needed.",
            duration: 5000,
            action: {
              label: "View Invitations",
              onClick: () => navigate('/invitations')
            }
          }
        );
      } else {
        setDuplicateError(false);
        toast.error(error?.message || "Failed to send invitation");
      }
    }
  });

  const handleSendInvite = () => {
    if (!inviteEmail || !inviteFirstName || !inviteLastName) {
      toast.error("Please fill in all required fields");
      return;
    }

    sendInviteMutation.mutate({
      email: inviteEmail,
      first_name: inviteFirstName,
      last_name: inviteLastName,
      recruiter_notes: inviteMessage || undefined,
      expiry_hours: 168, // 7 days
    });
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
                <TabsTrigger value="manual" className="gap-2">
                  <PenSquare className="h-4 w-4" />
                  Manual Entry
                </TabsTrigger>
                <TabsTrigger value="invite" className="gap-2">
                  <Mail className="h-4 w-4" />
                  Email Invite
                </TabsTrigger>
              </TabsList>

              <TabsContent value="manual" className="space-y-4">
                <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 mb-4">
                  <h3 className="font-semibold text-purple-900 mb-2">Manual Entry</h3>
                  <p className="text-sm text-purple-700">
                    Upload a resume for AI parsing or manually enter candidate information.
                  </p>
                </div>
                
                {/* Sub-tabs for Manual Entry */}
                <Tabs value={manualSubTab} onValueChange={setManualSubTab} className="w-full">
                  <TabsList className="grid w-full grid-cols-2 mb-4">
                    <TabsTrigger value="upload" className="gap-2">
                      <FileUp className="h-4 w-4" />
                      Upload Resume
                    </TabsTrigger>
                    <TabsTrigger value="form" className="gap-2">
                      <PenSquare className="h-4 w-4" />
                      Type Details
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

                  <TabsContent value="form" className="space-y-4">
                    <CandidateForm
                      onSubmit={handleFormSubmit}
                      onCancel={handleCancel}
                    />
                  </TabsContent>
                </Tabs>
              </TabsContent>

              <TabsContent value="invite" className="space-y-4">
                <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-4">
                  <h3 className="font-semibold text-green-900 mb-2">Send Email Invitation</h3>
                  <p className="text-sm text-green-700 mb-2">
                    Send an email invitation to the candidate. They can fill out their information 
                    and upload their resume through a personalized link.
                  </p>
                  <p className="text-xs text-green-600 flex items-start gap-1">
                    <span className="font-semibold">Note:</span>
                    <span>Each email can only have one active invitation. If an invitation already exists, you can resend it from the Invitations page.</span>
                  </p>
                </div>

                <div className="space-y-4 max-w-2xl">
                  {duplicateError && (
                    <Alert variant="destructive">
                      <AlertCircle className="h-4 w-4" />
                      <AlertTitle>Duplicate Invitation Detected</AlertTitle>
                      <AlertDescription className="space-y-2">
                        <p>An active invitation already exists for <strong>{inviteEmail}</strong>.</p>
                        <p className="text-sm">
                          This email address already has a pending invitation. You can:
                        </p>
                        <ul className="list-disc list-inside text-sm space-y-1 mt-2">
                          <li>View existing invitations and resend if needed</li>
                          <li>Wait for the candidate to complete their onboarding</li>
                          <li>Check if the invitation has expired and needs to be resent</li>
                        </ul>
                        <div className="flex gap-2 mt-3">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => navigate('/invitations')}
                          >
                            View Invitations
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => setDuplicateError(false)}
                          >
                            Dismiss
                          </Button>
                        </div>
                      </AlertDescription>
                    </Alert>
                  )}

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="invite-first-name">First Name *</Label>
                      <Input
                        id="invite-first-name"
                        placeholder="John"
                        value={inviteFirstName}
                        onChange={(e) => setInviteFirstName(e.target.value)}
                        required
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="invite-last-name">Last Name *</Label>
                      <Input
                        id="invite-last-name"
                        placeholder="Doe"
                        value={inviteLastName}
                        onChange={(e) => setInviteLastName(e.target.value)}
                        required
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="invite-email">Email Address *</Label>
                    <Input
                      id="invite-email"
                      type="email"
                      placeholder="john.doe@example.com"
                      value={inviteEmail}
                      onChange={(e) => {
                        setInviteEmail(e.target.value);
                        setDuplicateError(false); // Clear error when email changes
                      }}
                      required
                    />
                    <p className="text-xs text-slate-500">
                      If an active invitation already exists for this email, you'll need to resend it instead.
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="invite-message">Personal Message (Optional)</Label>
                    <Textarea
                      id="invite-message"
                      placeholder="Add a personal message to the invitation email..."
                      rows={4}
                      value={inviteMessage}
                      onChange={(e) => setInviteMessage(e.target.value)}
                    />
                  </div>

                  <div className="flex gap-3 pt-4">
                    <Button
                      onClick={handleSendInvite}
                      disabled={!inviteEmail || !inviteFirstName || !inviteLastName || sendInviteMutation.isPending}
                      className="gap-2"
                    >
                      <Mail className="h-4 w-4" />
                      {sendInviteMutation.isPending ? 'Sending...' : 'Send Invitation'}
                    </Button>
                    <Button
                      variant="outline"
                      onClick={handleCancel}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
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
