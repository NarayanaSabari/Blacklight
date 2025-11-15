/**
 * InvitationDetails Component
 * Detailed view of a single invitation with actions
 */

import { useState } from 'react';
import { format } from 'date-fns';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import {
  Mail,
  Calendar,
  User,
  FileText,
  CheckCircle2,
  XCircle,
  Send,
  Ban,
  Clock,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import {
  useInvitation,
  useInvitationAuditLogs,
  useResendInvitation,
  useCancelInvitation,
  useApproveInvitation,
  useRejectInvitation,
} from '@/hooks/useInvitations';
import type { InvitationStatus } from '@/types';

interface InvitationDetailsProps {
  invitationId: number;
  onClose?: () => void;
}

const STATUS_CONFIG: Record<
  InvitationStatus,
  { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline'; icon: typeof Mail }
> = {
  sent: { label: 'Sent', variant: 'default', icon: Mail },
  opened: { label: 'Opened', variant: 'secondary', icon: Mail }, // Added
  in_progress: { label: 'In Progress', variant: 'secondary', icon: Clock }, // Added
  submitted: { label: 'Submitted', variant: 'default', icon: FileText }, // Added
  pending_review: { label: 'Pending Review', variant: 'secondary', icon: Clock },
  approved: { label: 'Approved', variant: 'outline', icon: CheckCircle2 },
  rejected: { label: 'Rejected', variant: 'destructive', icon: XCircle },
  cancelled: { label: 'Cancelled', variant: 'outline', icon: Ban },
  expired: { label: 'Expired', variant: 'destructive', icon: AlertCircle },
};

export function InvitationDetails({ invitationId, onClose }: InvitationDetailsProps) {
  const { data: invitation, isLoading } = useInvitation(invitationId);
  const { data: auditLogs } = useInvitationAuditLogs(invitationId);
  const resendMutation = useResendInvitation();
  const cancelMutation = useCancelInvitation();
  const approveMutation = useApproveInvitation();
  const rejectMutation = useRejectInvitation();

  const [showApproveDialog, setShowApproveDialog] = useState(false);
  const [showRejectDialog, setShowRejectDialog] = useState(false);
  const [showCancelDialog, setShowCancelDialog] = useState(false);
  const [reviewNotes, setReviewNotes] = useState('');
  const [rejectionReason, setRejectionReason] = useState('');

  if (isLoading) {
    return <InvitationDetailsSkeleton />;
  }

  if (!invitation) {
    return (
      <Card>
        <CardContent className="py-8 text-center">
          <AlertCircle className="mx-auto h-12 w-12 text-muted-foreground" />
          <p className="mt-4 text-lg font-medium">Invitation not found</p>
        </CardContent>
      </Card>
    );
  }

  const config = STATUS_CONFIG[invitation.status];
  const StatusIcon = config.icon;
  const isExpired = new Date(invitation.expires_at) < new Date();
  const canResend = ['sent', 'expired', 'cancelled'].includes(invitation.status);
  const canCancel = ['sent', 'pending_review', 'submitted'].includes(invitation.status);
  const canReview = invitation.status === 'pending_review' || invitation.status === 'submitted';

  const handleApprove = async () => {
    await approveMutation.mutateAsync({
      id: invitationId,
      data: reviewNotes ? { notes: reviewNotes } : undefined,
    });
    setShowApproveDialog(false);
    setReviewNotes('');
  };

  const handleReject = async () => {
    await rejectMutation.mutateAsync({
      id: invitationId,
      data: { rejection_reason: rejectionReason, notes: reviewNotes },
    });
    setShowRejectDialog(false);
    setRejectionReason('');
    setReviewNotes('');
  };

  const handleCancel = async () => {
    await cancelMutation.mutateAsync(invitationId);
    setShowCancelDialog(false);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <StatusIcon className="h-5 w-5" />
                Invitation Details
              </CardTitle>
              <CardDescription>
                ID: {invitation.id} • Token: {invitation.token.substring(0, 12)}...
              </CardDescription>
            </div>
            <Badge variant={config.variant} className="flex items-center gap-1">
              <StatusIcon className="h-3 w-3" />
              {config.label}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid gap-6 md:grid-cols-2">
            {/* Candidate Info */}
            <div className="space-y-4">
              <div>
                <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                  <User className="h-4 w-4" />
                  Candidate Information
                </div>
                <Separator className="my-2" />
                <div className="space-y-2">
                  <InfoItem
                    label="Name"
                    value={
                      invitation.first_name || invitation.last_name
                        ? `${invitation.first_name || ''} ${invitation.last_name || ''}`.trim()
                        : 'Not provided'
                    }
                  />
                  <InfoItem label="Email" value={invitation.email} />
                  {invitation.invitation_data?.phone && (
                    <InfoItem label="Phone" value={invitation.invitation_data.phone} />
                  )}
                  {invitation.invitation_data?.location && (
                    <InfoItem label="Location" value={invitation.invitation_data.location} />
                  )}
                </div>
              </div>

              {/* Submitted Data */}
              {invitation.invitation_data && invitation.status === 'submitted' && (
                <div>
                  <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                    <FileText className="h-4 w-4" />
                    Submitted Information
                  </div>
                  <Separator className="my-2" />
                  <div className="space-y-3">
                    {invitation.invitation_data.summary && (
                      <div>
                        <Label className="text-xs text-muted-foreground">Professional Summary</Label>
                        <p className="text-sm whitespace-pre-wrap">{invitation.invitation_data.summary}</p>
                      </div>
                    )}
                    {invitation.invitation_data.skills && invitation.invitation_data.skills.length > 0 && (
                      <div>
                        <Label className="text-xs text-muted-foreground">Skills</Label>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {invitation.invitation_data.skills.slice(0, 10).map((skill: string, idx: number) => (
                            <Badge key={idx} variant="secondary" className="text-xs">
                              {skill}
                            </Badge>
                          ))}
                          {invitation.invitation_data.skills.length > 10 && (
                            <Badge variant="outline" className="text-xs">
                              +{invitation.invitation_data.skills.length - 10} more
                            </Badge>
                          )}
                        </div>
                      </div>
                    )}
                    {invitation.invitation_data.experience_years !== null && invitation.invitation_data.experience_years !== undefined && (
                      <InfoItem 
                        label="Years of Experience" 
                        value={String(invitation.invitation_data.experience_years)} 
                      />
                    )}
                    {invitation.invitation_data.position && (
                      <InfoItem label="Position Applied" value={invitation.invitation_data.position} />
                    )}
                  </div>
                </div>
              )}

              {/* Timeline */}
              <div>
                <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                  <Calendar className="h-4 w-4" />
                  Timeline
                </div>
                <Separator className="my-2" />
                <div className="space-y-2">
                  <InfoItem
                    label="Invited At"
                    value={format(new Date(invitation.invited_at), 'PPpp')}
                  />
                  <InfoItem
                    label="Expires At"
                    value={format(new Date(invitation.expires_at), 'PPpp')}
                    className={isExpired ? 'text-destructive' : ''}
                  />
                  {invitation.submitted_at && (
                    <InfoItem
                      label="Submitted At"
                      value={format(new Date(invitation.submitted_at), 'PPpp')}
                    />
                  )}
                  {invitation.reviewed_at && (
                    <InfoItem
                      label="Reviewed At"
                      value={format(new Date(invitation.reviewed_at), 'PPpp')}
                    />
                  )}
                </div>
              </div>
            </div>

            {/* Work Experience & Education */}
            {invitation.invitation_data && invitation.status === 'submitted' && (
              <div className="space-y-4">
                {invitation.invitation_data.work_experience && (
                  <div>
                    <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                      <FileText className="h-4 w-4" />
                      Work Experience
                    </div>
                    <Separator className="my-2" />
                    <p className="text-sm whitespace-pre-wrap max-h-48 overflow-y-auto">
                      {invitation.invitation_data.work_experience}
                    </p>
                  </div>
                )}
                {invitation.invitation_data.education && (
                  <div>
                    <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                      <FileText className="h-4 w-4" />
                      Education
                    </div>
                    <Separator className="my-2" />
                    <p className="text-sm whitespace-pre-wrap">{invitation.invitation_data.education}</p>
                  </div>
                )}
              </div>
            )}

            {/* Actors & Notes */}
            <div className="space-y-4">
              <div>
                <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                  <User className="h-4 w-4" />
                  People Involved
                </div>
                <Separator className="my-2" />
                <div className="space-y-2">
                  <InfoItem
                    label="Invited By"
                    value={
                      invitation.invited_by?.first_name ||
                      invitation.invited_by?.email ||
                      'Unknown'
                    }
                  />
                  {invitation.reviewed_by && (
                    <InfoItem
                      label="Reviewed By"
                      value={
                        invitation.reviewed_by.first_name ||
                        invitation.reviewed_by.email ||
                        'Unknown'
                      }
                    />
                  )}
                </div>
              </div>

              {/* Notes */}
              {(invitation.review_notes || invitation.rejection_reason || invitation.invitation_data) && (
                <div>
                  <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                    <FileText className="h-4 w-4" />
                    Notes
                  </div>
                  <Separator className="my-2" />
                  <div className="space-y-2">
                    {invitation.invitation_data && (
                      <div>
                        <Label className="text-xs text-muted-foreground">Initial Notes</Label>
                        <p className="text-sm">
                          {typeof invitation.invitation_data === 'object' && invitation.invitation_data !== null
                            ? (invitation.invitation_data as { notes?: string }).notes || 'N/A'
                            : 'N/A'}
                        </p>
                      </div>
                    )}
                    {invitation.review_notes && (
                      <div>
                        <Label className="text-xs text-muted-foreground">Review Notes</Label>
                        <p className="text-sm">{invitation.review_notes}</p>
                      </div>
                    )}
                    {invitation.rejection_reason && (
                      <div>
                        <Label className="text-xs text-muted-foreground text-destructive">
                          Rejection Reason
                        </Label>
                        <p className="text-sm text-destructive">{invitation.rejection_reason}</p>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Actions */}
          <div className="mt-6 flex flex-wrap gap-2">
            {canReview && (
              <>
                <Button onClick={() => setShowApproveDialog(true)} variant="default">
                  <CheckCircle2 className="mr-2 h-4 w-4" />
                  Approve
                </Button>
                <Button onClick={() => setShowRejectDialog(true)} variant="destructive">
                  <XCircle className="mr-2 h-4 w-4" />
                  Reject
                </Button>
              </>
            )}
            {canResend && (
              <Button
                onClick={() => {
                  if (resendMutation.isPending) return; // Prevent double-click
                  resendMutation.mutate(invitationId);
                }}
                disabled={resendMutation.isPending}
                variant="outline"
              >
                {resendMutation.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Send className="mr-2 h-4 w-4" />
                )}
                Resend
              </Button>
            )}
            {canCancel && (
              <Button
                onClick={() => setShowCancelDialog(true)}
                variant="outline"
                className="text-destructive"
              >
                <Ban className="mr-2 h-4 w-4" />
                Cancel
              </Button>
            )}
            {onClose && (
              <Button onClick={onClose} variant="ghost">
                Close
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Audit Logs */}
      {auditLogs && auditLogs.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Activity Log</CardTitle>
            <CardDescription>History of actions performed on this invitation</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {auditLogs.map((log) => (
                <div key={log.id} className="flex gap-3 text-sm">
                  <div className="text-muted-foreground">
                    {format(new Date(log.performed_at), 'MMM dd, HH:mm')}
                  </div>
                  <div className="flex-1">
                    <span className="font-medium">{log.action}</span>
                    {log.extra_data && (
                      <span className="text-muted-foreground">
                        {' '}
                        • {JSON.stringify(log.extra_data)}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Approve Dialog */}
      <AlertDialog open={showApproveDialog} onOpenChange={setShowApproveDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Approve Invitation</AlertDialogTitle>
            <AlertDialogDescription>
              This will approve the candidate's onboarding submission and create their profile.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="space-y-2">
            <Label>Review Notes (Optional)</Label>
            <Textarea
              value={reviewNotes}
              onChange={(e) => setReviewNotes(e.target.value)}
              placeholder="Add any notes about this approval..."
              rows={3}
            />
          </div>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleApprove} disabled={approveMutation.isPending}>
              {approveMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Approve
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Reject Dialog */}
      <AlertDialog open={showRejectDialog} onOpenChange={setShowRejectDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Reject Invitation</AlertDialogTitle>
            <AlertDialogDescription>
              This will reject the candidate's submission. Please provide a reason.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Rejection Reason *</Label>
              <Textarea
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
                placeholder="Please explain why this submission is being rejected..."
                rows={3}
              />
            </div>
            <div>
              <Label>Additional Notes (Optional)</Label>
              <Textarea
                value={reviewNotes}
                onChange={(e) => setReviewNotes(e.target.value)}
                placeholder="Any additional notes..."
                rows={2}
              />
            </div>
          </div>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleReject}
              disabled={!rejectionReason || rejectMutation.isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {rejectMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Reject
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Cancel Dialog */}
      <AlertDialog open={showCancelDialog} onOpenChange={setShowCancelDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Cancel Invitation</AlertDialogTitle>
            <AlertDialogDescription>
              This will cancel the invitation. The candidate will no longer be able to use this
              invitation link.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Go Back</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleCancel}
              disabled={cancelMutation.isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {cancelMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Cancel Invitation
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

function InfoItem({
  label,
  value,
  className,
}: {
  label: string;
  value: string;
  className?: string;
}) {
  return (
    <div>
      <Label className="text-xs text-muted-foreground">{label}</Label>
      <p className={`text-sm ${className || ''}`}>{value}</p>
    </div>
  );
}

function InvitationDetailsSkeleton() {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-4 w-96" />
        </CardHeader>
        <CardContent>
          <div className="grid gap-6 md:grid-cols-2">
            <div className="space-y-4">
              <Skeleton className="h-32 w-full" />
              <Skeleton className="h-32 w-full" />
            </div>
            <div className="space-y-4">
              <Skeleton className="h-32 w-full" />
              <Skeleton className="h-32 w-full" />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
