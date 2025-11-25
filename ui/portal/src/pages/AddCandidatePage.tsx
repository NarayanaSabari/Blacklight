/**
 * Add Candidate Page
 * Simplified page for adding candidates with resume upload, manual entry, or email invitation
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Upload, PenSquare, ArrowLeft, FileUp, Mail, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';
import { ResumeUpload } from '@/components/candidates/ResumeUpload';
import { CandidateForm } from '@/components/candidates/CandidateForm';
import { invitationApi } from '@/lib/api/invitationApi';
import type { CandidateCreateInput, CandidateUpdateInput, UploadResumeResponse } from '@/types/candidate';
import type { InvitationCreateRequest, InvitationWithRelations } from '@/types/invitation';

type AddMethod = 'choice' | 'upload' | 'manual' | 'invite';

export function AddCandidatePage() {
  const navigate = useNavigate();
  const [addMethod, setAddMethod] = useState<AddMethod>('choice');
  const [parsedData, setParsedData] = useState<UploadResumeResponse | null>(null);

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
      // Old sync flow - candidate already created with parsed data
      toast.success('Resume parsed successfully!');
      if (result.candidate_id) {
        navigate(`/candidates/${result.candidate_id}`);
      }
    }
  };

  const handleFormSubmit = async (data: CandidateCreateInput | CandidateUpdateInput) => {
    try {
      const { candidateApi } = await import('@/lib/candidateApi');
      const newCandidate = await candidateApi.createCandidate(data as CandidateCreateInput);
      toast.success('Candidate created successfully!');
      navigate(`/candidates/${newCandidate.id}`);
    } catch (error) {
      console.error('Failed to create candidate:', error);
      toast.error('Failed to create candidate');
    }
  };

  const handleCancel = () => {
    if (addMethod === 'choice') {
      navigate('/candidates');
    } else {
      setAddMethod('choice');
      setParsedData(null);
      // Reset invite form
      setInviteEmail('');
      setInviteFirstName('');
      setInviteLastName('');
      setInviteMessage('');
      setDuplicateError(false);
    }
  };

  // Send invitation mutation
  const sendInviteMutation = useMutation<InvitationWithRelations, Error, InvitationCreateRequest>({
    mutationFn: (data) => invitationApi.create(data),
    onSuccess: () => {
      toast.success('Invitation sent successfully! The candidate will receive an email with onboarding instructions.');
      setInviteEmail('');
      setInviteFirstName('');
      setInviteLastName('');
      setInviteMessage('');
      setDuplicateError(false);
      navigate('/invitations');
    },
    onError: (error: any) => {
      if (error?.status === 409 || error?.message?.includes('already exists')) {
        setDuplicateError(true);
        toast.error('An active invitation already exists for this email address.', {
          description: 'Please check the invitations list or use the resend option if needed.',
        });
      } else {
        toast.error(`Failed to send invitation: ${error.message || 'Unknown error'}`);
      }
    },
  });

  const handleSendInvite = () => {
    if (!inviteEmail || !inviteFirstName) {
      toast.error('Email and first name are required');
      return;
    }

    sendInviteMutation.mutate({
      email: inviteEmail.trim(),
      first_name: inviteFirstName.trim(),
      last_name: inviteLastName.trim(),
      recruiter_notes: inviteMessage.trim() || undefined,
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-primary/10 via-secondary/10 to-accent/10 rounded-lg border-2 border-black p-6 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
        <Button
          variant="ghost"
          size="sm"
          onClick={handleCancel}
          className="mb-3 -ml-2"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          {addMethod === 'choice' ? 'Back to Candidates' : 'Back to Options'}
        </Button>

        <div className="flex items-center gap-3">
          <div className="flex-shrink-0 w-16 h-16 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-2xl font-bold border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]">
            +
          </div>
          <div>
            <h1 className="text-3xl sm:text-4xl font-bold text-slate-900 mb-1">
              Add New Candidate
            </h1>
            <p className="text-lg text-slate-600">
              {addMethod === 'choice' && 'Choose how you want to add a candidate'}
              {addMethod === 'upload' && 'Upload and parse resume with AI'}
              {addMethod === 'manual' && 'Manually enter candidate details'}
              {addMethod === 'invite' && 'Send email invitation to candidate'}
            </p>
          </div>
        </div>
      </div>

      {/* Content */}
      {addMethod === 'choice' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Email Invitation Option */}
          <Card
            className="border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] transition-all cursor-pointer group md:col-span-2"
            onClick={() => setAddMethod('invite')}
          >
            <CardHeader className="bg-gradient-to-br from-purple-50 to-pink-50">
              <div className="flex items-center justify-center mb-4">
                <div className="w-20 h-20 rounded-full bg-purple-500 text-white flex items-center justify-center border-2 border-black shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] group-hover:scale-110 transition-transform">
                  <Mail className="h-10 w-10" />
                </div>
              </div>
              <CardTitle className="text-center text-xl">Email Invitation</CardTitle>
              <CardDescription className="text-center">
                Send an email invitation for the candidate to complete their profile themselves
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div className="flex items-center gap-2 text-sm text-slate-600">
                  <div className="w-2 h-2 rounded-full bg-purple-500" />
                  <span>Self-service onboarding</span>
                </div>
                <div className="flex items-center gap-2 text-sm text-slate-600">
                  <div className="w-2 h-2 rounded-full bg-purple-500" />
                  <span>Automated email workflow</span>
                </div>
                <div className="flex items-center gap-2 text-sm text-slate-600">
                  <div className="w-2 h-2 rounded-full bg-purple-500" />
                  <span>Candidate fills own details</span>
                </div>
              </div>
              <Button
                className="w-full mt-6 border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:shadow-[3px_3px_0px_0px_rgba(0,0,0,1)]"
                onClick={(e) => {
                  e.stopPropagation();
                  setAddMethod('invite');
                }}
              >
                <Mail className="h-4 w-4 mr-2" />
                Send Invitation
              </Button>
            </CardContent>
          </Card>

          {/* Resume Upload Option */}
          <Card
            className="border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] transition-all cursor-pointer group"
            onClick={() => setAddMethod('upload')}
          >
            <CardHeader className="bg-gradient-to-br from-blue-50 to-indigo-50">
              <div className="flex items-center justify-center mb-4">
                <div className="w-20 h-20 rounded-full bg-blue-500 text-white flex items-center justify-center border-2 border-black shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] group-hover:scale-110 transition-transform">
                  <Upload className="h-10 w-10" />
                </div>
              </div>
              <CardTitle className="text-center text-xl">Resume Upload</CardTitle>
              <CardDescription className="text-center">
                Upload a PDF or DOCX resume and let AI extract candidate information automatically
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-6">
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-sm text-slate-600">
                  <div className="w-2 h-2 rounded-full bg-blue-500" />
                  <span>Automatic information extraction</span>
                </div>
                <div className="flex items-center gap-2 text-sm text-slate-600">
                  <div className="w-2 h-2 rounded-full bg-blue-500" />
                  <span>Skills, experience, and education parsed</span>
                </div>
                <div className="flex items-center gap-2 text-sm text-slate-600">
                  <div className="w-2 h-2 rounded-full bg-blue-500" />
                  <span>Fast and accurate</span>
                </div>
              </div>
              <Button
                className="w-full mt-6 border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:shadow-[3px_3px_0px_0px_rgba(0,0,0,1)]"
                onClick={(e) => {
                  e.stopPropagation();
                  setAddMethod('upload');
                }}
              >
                <FileUp className="h-4 w-4 mr-2" />
                Upload Resume
              </Button>
            </CardContent>
          </Card>

          {/* Manual Entry Option */}
          <Card
            className="border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] transition-all cursor-pointer group"
            onClick={() => setAddMethod('manual')}
          >
            <CardHeader className="bg-gradient-to-br from-green-50 to-emerald-50">
              <div className="flex items-center justify-center mb-4">
                <div className="w-20 h-20 rounded-full bg-green-500 text-white flex items-center justify-center border-2 border-black shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] group-hover:scale-110 transition-transform">
                  <PenSquare className="h-10 w-10" />
                </div>
              </div>
              <CardTitle className="text-center text-xl">Manual Entry</CardTitle>
              <CardDescription className="text-center">
                Manually fill in candidate information using a detailed form
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-6">
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-sm text-slate-600">
                  <div className="w-2 h-2 rounded-full bg-green-500" />
                  <span>Complete control over data entry</span>
                </div>
                <div className="flex items-center gap-2 text-sm text-slate-600">
                  <div className="w-2 h-2 rounded-full bg-green-500" />
                  <span>Perfect for referrals and interviews</span>
                </div>
                <div className="flex items-center gap-2 text-sm text-slate-600">
                  <div className="w-2 h-2 rounded-full bg-green-500" />
                  <span>Detailed and customizable</span>
                </div>
              </div>
              <Button
                className="w-full mt-6 border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:shadow-[3px_3px_0px_0px_rgba(0,0,0,1)]"
                onClick={(e) => {
                  e.stopPropagation();
                  setAddMethod('manual');
                }}
              >
                <PenSquare className="h-4 w-4 mr-2" />
                Type Details
              </Button>
            </CardContent>
          </Card>
        </div>
      ) : addMethod === 'upload' ? (
        <Card className="border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] max-w-3xl">
          <CardHeader className="bg-gradient-to-br from-blue-50 to-indigo-50">
            <CardTitle className="flex items-center gap-2">
              <Upload className="h-5 w-5 text-blue-600" />
              Upload Resume
            </CardTitle>
            <CardDescription>
              Upload a resume in PDF or DOCX format. Our AI will automatically extract candidate information.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResumeUpload onUploadSuccess={handleUploadSuccess} />
          </CardContent>
        </Card>
      ) : addMethod === 'manual' ? (
        <Card className="border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
          <CardHeader className="bg-gradient-to-br from-green-50 to-emerald-50">
            <CardTitle className="flex items-center gap-2">
              <PenSquare className="h-5 w-5 text-green-600" />
              Manual Entry
            </CardTitle>
            <CardDescription>
              Fill in the candidate information manually
            </CardDescription>
          </CardHeader>
          <CardContent>
            <CandidateForm
              parsedData={parsedData?.parsed_data}
              onSubmit={handleFormSubmit}
              onCancel={handleCancel}
            />
          </CardContent>
        </Card>
      ) : (
        <Card className="border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] max-w-2xl">
          <CardHeader className="bg-gradient-to-br from-purple-50 to-pink-50">
            <CardTitle className="flex items-center gap-2">
              <Mail className="h-5 w-5 text-purple-600" />
              Send Email Invitation
            </CardTitle>
            <CardDescription>
              The candidate will receive an email invitation to complete their profile
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              {duplicateError && (
                <Alert variant="destructive" className="border-2 border-red-500">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    An active invitation already exists for this email. Please check the invitations list.
                  </AlertDescription>
                </Alert>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="invite-first-name">First Name *</Label>
                  <Input
                    id="invite-first-name"
                    value={inviteFirstName}
                    onChange={(e) => setInviteFirstName(e.target.value)}
                    placeholder="John"
                    className="border-2 border-black"
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="invite-last-name">Last Name</Label>
                  <Input
                    id="invite-last-name"
                    value={inviteLastName}
                    onChange={(e) => setInviteLastName(e.target.value)}
                    placeholder="Doe"
                    className="border-2 border-black"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="invite-email">Email Address *</Label>
                <Input
                  id="invite-email"
                  type="email"
                  value={inviteEmail}
                  onChange={(e) => {
                    setInviteEmail(e.target.value);
                    setDuplicateError(false);
                  }}
                  placeholder="john.doe@example.com"
                  className="border-2 border-black"
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="invite-message">Custom Message (Optional)</Label>
                <Textarea
                  id="invite-message"
                  value={inviteMessage}
                  onChange={(e) => setInviteMessage(e.target.value)}
                  placeholder="Add a personal message to the invitation email..."
                  rows={4}
                  className="border-2 border-black"
                />
              </div>

              <div className="flex gap-3 justify-end pt-4 border-t-2 border-slate-200">
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleCancel}
                  className="border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]"
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleSendInvite}
                  disabled={sendInviteMutation.isPending || !inviteEmail || !inviteFirstName}
                  className="border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] bg-purple-600 hover:bg-purple-700"
                >
                  {sendInviteMutation.isPending ? 'Sending...' : 'Send Invitation'}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
