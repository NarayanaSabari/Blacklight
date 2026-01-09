/**
 * InvitationReviewPage
 * Dedicated page for reviewing submitted candidate invitations
 * Shows full submission data with approve/reject actions
 */

import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  ArrowLeft,
  User,
  Mail,
  Phone,
  MapPin,
  Calendar,
  Briefcase,
  GraduationCap,
  FileText,
  Github,
  Linkedin,
  Globe,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import { format } from 'date-fns';
import { toast } from 'sonner';
import { invitationApi } from '@/lib/api/invitationApi';
import { getErrorMessage } from '@/lib/api-client';

interface SubmissionData {
  phone?: string;
  location?: string;
  experience_years?: number;
  position?: string;
  linkedin_url?: string;
  github_url?: string;
  portfolio_url?: string;
  summary?: string;
  skills?: string[];
  work_experience?: string;
  education?: string;
  parsed_resume_data?: Record<string, unknown>;
  preferred_roles?: string[];
  preferred_locations?: string[];
}

export default function InvitationReviewPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const invitationId = id ? parseInt(id, 10) : 0;

  const [showApproveDialog, setShowApproveDialog] = useState(false);
  const [showRejectDialog, setShowRejectDialog] = useState(false);
  const [rejectionReason, setRejectionReason] = useState('');

  // Fetch invitation data
  const {
    data: invitation,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['invitation', invitationId],
    queryFn: () => invitationApi.getById(invitationId),
    enabled: !!invitationId,
  });

  // Approve mutation
  const approveMutation = useMutation({
    mutationFn: (id: number) => invitationApi.approve(id),
    onSuccess: async () => {
      await queryClient.refetchQueries({ queryKey: ['submitted-invitations'] });
      await queryClient.refetchQueries({ queryKey: ['invitation', invitationId] });
      toast.success('Candidate approved and profile created successfully!');
      setShowApproveDialog(false);
      navigate('/candidate-management?tab=onboarding');
    },
    onError: (error: unknown) => {
      toast.error(getErrorMessage(error));
    },
  });

  // Reject mutation
  const rejectMutation = useMutation({
    mutationFn: (data: { id: number; reason: string }) =>
      invitationApi.reject(data.id, { rejection_reason: data.reason }),
    onSuccess: async () => {
      await queryClient.refetchQueries({ queryKey: ['submitted-invitations'] });
      await queryClient.refetchQueries({ queryKey: ['invitation', invitationId] });
      toast.success('Invitation rejected');
      setShowRejectDialog(false);
      setRejectionReason('');
      navigate('/candidate-management?tab=onboarding');
    },
    onError: (error: unknown) => {
      toast.error(getErrorMessage(error));
    },
  });

  const handleApprove = () => {
    approveMutation.mutate(invitationId);
  };

  const handleReject = () => {
    if (!rejectionReason.trim()) {
      toast.error('Please provide a rejection reason');
      return;
    }
    rejectMutation.mutate({ id: invitationId, reason: rejectionReason.trim() });
  };

  if (!invitationId) {
    return (
      <div className="p-6">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>Invalid invitation ID</AlertDescription>
        </Alert>
      </div>
    );
  }

  if (isLoading) {
    return <ReviewPageSkeleton />;
  }

  if (error || !invitation) {
    return (
      <div className="p-6">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Failed to load invitation. {error?.message || 'Invitation not found.'}
          </AlertDescription>
        </Alert>
        <Button onClick={() => navigate('/candidate-management?tab=onboarding')} className="mt-4">
          Back to Onboarding
        </Button>
      </div>
    );
  }

  if (invitation.status !== 'pending_review') {
    return (
      <div className="p-6">
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            This invitation has already been reviewed (Status: {invitation.status}).
          </AlertDescription>
        </Alert>
        <Button onClick={() => navigate('/candidate-management?tab=onboarding')} className="mt-4">
          Back to Onboarding
        </Button>
      </div>
    );
  }

  const submissionData = (invitation.invitation_data || undefined) as SubmissionData | undefined;

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => navigate('/candidate-management?tab=onboarding')}
        >
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold">Review Candidate Submission</h1>
          <p className="text-sm text-muted-foreground">
            Review candidate details and approve or reject the application
          </p>
        </div>
        <Badge variant="outline" className="flex items-center gap-1">
          <FileText className="h-3 w-3" />
          Submitted
        </Badge>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main Content - 2 columns */}
        <div className="lg:col-span-2 space-y-6">
          {/* Basic Information */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <User className="h-5 w-5" />
                <CardTitle>Candidate Information</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <InfoItem
                  icon={User}
                  label="Name"
                  value={`${invitation.first_name} ${invitation.last_name}`}
                />
                <InfoItem icon={Mail} label="Email" value={invitation.email} />
                {submissionData?.phone && (
                  <InfoItem icon={Phone} label="Phone" value={submissionData.phone} />
                )}
                {submissionData?.location && (
                  <InfoItem icon={MapPin} label="Location" value={submissionData.location} />
                )}
                {submissionData?.experience_years !== undefined && (
                  <InfoItem
                    icon={Briefcase}
                    label="Years of Experience"
                    value={String(submissionData.experience_years)}
                  />
                )}
                {submissionData?.position && (
                  <InfoItem icon={Briefcase} label="Position" value={submissionData.position} />
                )}
              </div>

              {/* Links */}
              {(submissionData?.linkedin_url || submissionData?.github_url || submissionData?.portfolio_url) && (
                <div className="pt-4 border-t">
                  <Label className="text-sm font-medium mb-2 block">Professional Links</Label>
                  <div className="flex flex-wrap gap-2">
                    {submissionData.linkedin_url && (
                      <a
                        href={submissionData.linkedin_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-sm text-blue-600 hover:underline"
                      >
                        <Linkedin className="h-4 w-4" />
                        LinkedIn
                      </a>
                    )}
                    {submissionData.github_url && (
                      <a
                        href={submissionData.github_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-sm text-gray-600 hover:underline"
                      >
                        <Github className="h-4 w-4" />
                        GitHub
                      </a>
                    )}
                    {submissionData.portfolio_url && (
                      <a
                        href={submissionData.portfolio_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-sm text-purple-600 hover:underline"
                      >
                        <Globe className="h-4 w-4" />
                        Portfolio
                      </a>
                    )}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Professional Summary */}
          {submissionData?.summary && (
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <FileText className="h-5 w-5" />
                  <CardTitle>Professional Summary</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm whitespace-pre-wrap leading-relaxed">{submissionData.summary}</p>
              </CardContent>
            </Card>
          )}

          {/* Skills */}
          {submissionData?.skills && submissionData.skills.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Skills</CardTitle>
                <CardDescription>
                  {submissionData.skills.length} skill{submissionData.skills.length !== 1 ? 's' : ''} listed
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {submissionData.skills.map((skill: string, idx: number) => (
                    <Badge key={idx} variant="secondary">
                      {skill}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Preferred Roles */}
          {submissionData?.preferred_roles && submissionData.preferred_roles.length > 0 && (
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Briefcase className="h-5 w-5" />
                  <CardTitle>Preferred Roles</CardTitle>
                </div>
                <CardDescription>
                  {submissionData.preferred_roles.length} role{submissionData.preferred_roles.length !== 1 ? 's' : ''} specified
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {submissionData.preferred_roles.map((role: string, idx: number) => (
                    <Badge key={idx} variant="default" className="bg-purple-100 text-purple-800 hover:bg-purple-200">
                      {role}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Preferred Locations */}
          {submissionData?.preferred_locations && submissionData.preferred_locations.length > 0 && (
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <MapPin className="h-5 w-5" />
                  <CardTitle>Preferred Locations</CardTitle>
                </div>
                <CardDescription>
                  {submissionData.preferred_locations.length} location{submissionData.preferred_locations.length !== 1 ? 's' : ''} specified
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {submissionData.preferred_locations.map((loc: string, idx: number) => (
                    <Badge key={idx} variant="outline" className="border-blue-300 text-blue-800">
                      <MapPin className="h-3 w-3 mr-1" />
                      {loc}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Work Experience */}
          {submissionData?.work_experience && (
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Briefcase className="h-5 w-5" />
                  <CardTitle>Work Experience</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm whitespace-pre-wrap leading-relaxed max-h-96 overflow-y-auto">
                  {submissionData.work_experience}
                </p>
              </CardContent>
            </Card>
          )}

          {/* Education */}
          {submissionData?.education && (
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <GraduationCap className="h-5 w-5" />
                  <CardTitle>Education</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm whitespace-pre-wrap leading-relaxed">
                  {submissionData.education}
                </p>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Sidebar - 1 column */}
        <div className="space-y-6">
          {/* Timeline */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Calendar className="h-5 w-5" />
                <CardTitle>Timeline</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <TimelineItem
                label="Invited"
                date={format(new Date(invitation.invited_at), 'PPp')}
              />
              {invitation.submitted_at && (
                <TimelineItem
                  label="Submitted"
                  date={format(new Date(invitation.submitted_at), 'PPp')}
                />
              )}
              <TimelineItem
                label="Expires"
                date={format(new Date(invitation.expires_at), 'PPp')}
              />
            </CardContent>
          </Card>

          {/* Actions */}
          <Card>
            <CardHeader>
              <CardTitle>Review Actions</CardTitle>
              <CardDescription>Approve or reject this submission</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <Button
                onClick={() => setShowApproveDialog(true)}
                className="w-full"
                disabled={approveMutation.isPending || rejectMutation.isPending}
              >
                {approveMutation.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <CheckCircle2 className="mr-2 h-4 w-4" />
                )}
                Approve & Create Profile
              </Button>
              <Button
                onClick={() => setShowRejectDialog(true)}
                variant="destructive"
                className="w-full"
                disabled={approveMutation.isPending || rejectMutation.isPending}
              >
                {rejectMutation.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <XCircle className="mr-2 h-4 w-4" />
                )}
                Reject Submission
              </Button>
            </CardContent>
          </Card>

          {/* AI Parsing Info */}
          {submissionData?.parsed_resume_data && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">AI Resume Parsing</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-xs text-muted-foreground">
                  This submission includes AI-parsed resume data from the candidate's uploaded resume.
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* Approve Dialog */}
      <Dialog open={showApproveDialog} onOpenChange={setShowApproveDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Approve Candidate Submission</DialogTitle>
            <DialogDescription>
              This will create a candidate profile with the submitted information and change the status to approved.
              The candidate will receive an approval confirmation email.
            </DialogDescription>
          </DialogHeader>
          <Alert>
            <CheckCircle2 className="h-4 w-4" />
            <AlertDescription>
              <strong>Candidate:</strong> {invitation.first_name} {invitation.last_name} ({invitation.email})
            </AlertDescription>
          </Alert>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowApproveDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleApprove} disabled={approveMutation.isPending}>
              {approveMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Approve
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reject Dialog */}
      <Dialog open={showRejectDialog} onOpenChange={setShowRejectDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reject Candidate Submission</DialogTitle>
            <DialogDescription>
              This will mark the submission as rejected. The candidate will receive an email with your rejection reason.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="rejection-reason">
                Rejection Reason <span className="text-red-500">*</span>
              </Label>
              <Textarea
                id="rejection-reason"
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
                placeholder="Please explain why this submission is being rejected..."
                rows={4}
                className="resize-none mt-2"
              />
              {rejectionReason.trim() === '' && (
                <p className="text-xs text-red-500 mt-1">Rejection reason is required</p>
              )}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowRejectDialog(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleReject}
              disabled={!rejectionReason.trim() || rejectMutation.isPending}
            >
              {rejectMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Reject
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function InfoItem({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof User;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-start gap-3">
      <Icon className="h-4 w-4 text-muted-foreground mt-0.5" />
      <div className="flex-1 min-w-0">
        <Label className="text-xs text-muted-foreground">{label}</Label>
        <p className="text-sm font-medium truncate">{value}</p>
      </div>
    </div>
  );
}

function TimelineItem({ label, date }: { label: string; date: string }) {
  return (
    <div className="flex justify-between items-start text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium text-right">{date}</span>
    </div>
  );
}

function ReviewPageSkeleton() {
  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center gap-4">
        <Skeleton className="h-10 w-10" />
        <div className="flex-1">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-4 w-96 mt-2" />
        </div>
      </div>
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <Skeleton className="h-64 w-full" />
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-96 w-full" />
        </div>
        <div className="space-y-6">
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-32 w-full" />
        </div>
      </div>
    </div>
  );
}
