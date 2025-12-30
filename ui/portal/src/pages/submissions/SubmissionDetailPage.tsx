/**
 * Submission Detail Page
 * View and manage a single submission with activity timeline
 */

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Textarea } from '@/components/ui/textarea';
import { Separator } from '@/components/ui/separator';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  ArrowLeft,
  Send,
  AlertCircle,
  Building2,
  User,
  Briefcase,
  Clock,
  DollarSign,
  Calendar,
  Flame,
  MapPin,
  Phone,
  Mail,
  ExternalLink,
  MessageSquare,
  Edit,
  CheckCircle2,
  XCircle,
  PauseCircle,
  Eye,
  TrendingUp,
  FileText,
  Plus,
  Loader2,
} from 'lucide-react';
import { submissionApi } from '@/lib/submissionApi';
import { format, formatDistanceToNow } from 'date-fns';
import { toast } from 'sonner';
import type {
  SubmissionStatus,
  ActivityType,
  SubmissionUpdateInput,
  PriorityLevel,
  RateType,
} from '@/types/submission';
import {
  STATUS_LABELS,
  STATUS_COLORS,
  PRIORITY_COLORS,
  PRIORITY_LEVELS,
  RATE_TYPES,
  getNextValidStatuses,
  isTerminalStatus,
} from '@/types/submission';

// Activity type icons and labels
const ACTIVITY_CONFIG: Record<
  ActivityType,
  { icon: React.ReactNode; label: string; color: string }
> = {
  CREATED: { icon: <Plus className="h-4 w-4" />, label: 'Created', color: 'text-blue-600' },
  STATUS_CHANGE: { icon: <TrendingUp className="h-4 w-4" />, label: 'Status Changed', color: 'text-purple-600' },
  NOTE: { icon: <MessageSquare className="h-4 w-4" />, label: 'Note', color: 'text-gray-600' },
  EMAIL_SENT: { icon: <Mail className="h-4 w-4" />, label: 'Email Sent', color: 'text-blue-600' },
  EMAIL_RECEIVED: { icon: <Mail className="h-4 w-4" />, label: 'Email Received', color: 'text-green-600' },
  CALL_LOGGED: { icon: <Phone className="h-4 w-4" />, label: 'Call Logged', color: 'text-amber-600' },
  INTERVIEW_SCHEDULED: { icon: <Calendar className="h-4 w-4" />, label: 'Interview Scheduled', color: 'text-purple-600' },
  INTERVIEW_COMPLETED: { icon: <CheckCircle2 className="h-4 w-4" />, label: 'Interview Completed', color: 'text-green-600' },
  INTERVIEW_CANCELLED: { icon: <XCircle className="h-4 w-4" />, label: 'Interview Cancelled', color: 'text-red-600' },
  RATE_UPDATED: { icon: <DollarSign className="h-4 w-4" />, label: 'Rate Updated', color: 'text-emerald-600' },
  VENDOR_UPDATED: { icon: <Building2 className="h-4 w-4" />, label: 'Vendor Updated', color: 'text-blue-600' },
  PRIORITY_CHANGED: { icon: <Flame className="h-4 w-4" />, label: 'Priority Changed', color: 'text-orange-600' },
  FOLLOW_UP_SET: { icon: <Clock className="h-4 w-4" />, label: 'Follow-up Set', color: 'text-yellow-600' },
  RESUME_SENT: { icon: <FileText className="h-4 w-4" />, label: 'Resume Sent', color: 'text-indigo-600' },
  CLIENT_FEEDBACK: { icon: <MessageSquare className="h-4 w-4" />, label: 'Client Feedback', color: 'text-teal-600' },
};

// Status icons
const STATUS_ICONS: Record<SubmissionStatus, React.ReactNode> = {
  SUBMITTED: <Send className="h-4 w-4" />,
  CLIENT_REVIEW: <Eye className="h-4 w-4" />,
  INTERVIEW_SCHEDULED: <Calendar className="h-4 w-4" />,
  INTERVIEWED: <CheckCircle2 className="h-4 w-4" />,
  OFFERED: <TrendingUp className="h-4 w-4" />,
  PLACED: <CheckCircle2 className="h-4 w-4" />,
  REJECTED: <XCircle className="h-4 w-4" />,
  WITHDRAWN: <XCircle className="h-4 w-4" />,
  ON_HOLD: <PauseCircle className="h-4 w-4" />,
};

export function SubmissionDetailPage() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const submissionId = parseInt(id || '0', 10);

  // Local state
  const [isStatusDialogOpen, setIsStatusDialogOpen] = useState(false);
  const [selectedStatus, setSelectedStatus] = useState<SubmissionStatus | null>(null);
  const [statusNote, setStatusNote] = useState('');
  const [isAddNoteDialogOpen, setIsAddNoteDialogOpen] = useState(false);
  const [newNote, setNewNote] = useState('');
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [editFormData, setEditFormData] = useState<Partial<SubmissionUpdateInput>>({});

  // Fetch submission with activities
  const {
    data: submission,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['submission', submissionId],
    queryFn: () => submissionApi.getSubmission(submissionId, true),
    enabled: submissionId > 0,
    staleTime: 0,
  });

  // Status update mutation
  const statusMutation = useMutation({
    mutationFn: (data: { status: SubmissionStatus; note?: string }) =>
      submissionApi.updateStatus(submissionId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['submission', submissionId] });
      queryClient.invalidateQueries({ queryKey: ['submissions'] });
      toast.success('Status updated successfully');
      setIsStatusDialogOpen(false);
      setSelectedStatus(null);
      setStatusNote('');
    },
    onError: (error: Error) => {
      toast.error(`Failed to update status: ${error.message}`);
    },
  });

  // Add note mutation
  const addNoteMutation = useMutation({
    mutationFn: (content: string) =>
      submissionApi.addActivity(submissionId, { content, activity_type: 'NOTE' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['submission', submissionId] });
      toast.success('Note added successfully');
      setIsAddNoteDialogOpen(false);
      setNewNote('');
    },
    onError: (error: Error) => {
      toast.error(`Failed to add note: ${error.message}`);
    },
  });

  // Update submission mutation
  const updateMutation = useMutation({
    mutationFn: (data: SubmissionUpdateInput) =>
      submissionApi.updateSubmission(submissionId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['submission', submissionId] });
      queryClient.invalidateQueries({ queryKey: ['submissions'] });
      toast.success('Submission updated successfully');
      setIsEditDialogOpen(false);
    },
    onError: (error: Error) => {
      toast.error(`Failed to update submission: ${error.message}`);
    },
  });

  const handleStatusUpdate = () => {
    if (!selectedStatus) return;
    statusMutation.mutate({ status: selectedStatus, note: statusNote || undefined });
  };

  const handleAddNote = () => {
    if (!newNote.trim()) return;
    addNoteMutation.mutate(newNote.trim());
  };

  const handleOpenEditDialog = () => {
    if (submission) {
      setEditFormData({
        vendor_company: submission.vendor_company || '',
        vendor_contact_name: submission.vendor_contact_name || '',
        vendor_contact_email: submission.vendor_contact_email || '',
        vendor_contact_phone: submission.vendor_contact_phone || '',
        client_company: submission.client_company || '',
        bill_rate: submission.bill_rate,
        pay_rate: submission.pay_rate,
        rate_type: submission.rate_type || 'HOURLY',
        currency: submission.currency || 'USD',
        submission_notes: submission.submission_notes || '',
        priority: submission.priority || 'MEDIUM',
        is_hot: submission.is_hot || false,
        follow_up_date: submission.follow_up_date?.split('T')[0] || '',
      });
      setIsEditDialogOpen(true);
    }
  };

  const handleSaveEdit = () => {
    // Build the update payload, only including changed fields
    const updateData: SubmissionUpdateInput = {};
    
    if (editFormData.vendor_company !== undefined) updateData.vendor_company = editFormData.vendor_company || undefined;
    if (editFormData.vendor_contact_name !== undefined) updateData.vendor_contact_name = editFormData.vendor_contact_name || undefined;
    if (editFormData.vendor_contact_email !== undefined) updateData.vendor_contact_email = editFormData.vendor_contact_email || undefined;
    if (editFormData.vendor_contact_phone !== undefined) updateData.vendor_contact_phone = editFormData.vendor_contact_phone || undefined;
    if (editFormData.client_company !== undefined) updateData.client_company = editFormData.client_company || undefined;
    if (editFormData.bill_rate !== undefined) updateData.bill_rate = editFormData.bill_rate;
    if (editFormData.pay_rate !== undefined) updateData.pay_rate = editFormData.pay_rate;
    if (editFormData.rate_type) updateData.rate_type = editFormData.rate_type;
    if (editFormData.currency) updateData.currency = editFormData.currency;
    if (editFormData.submission_notes !== undefined) updateData.submission_notes = editFormData.submission_notes || undefined;
    if (editFormData.priority) updateData.priority = editFormData.priority;
    if (editFormData.is_hot !== undefined) updateData.is_hot = editFormData.is_hot;
    if (editFormData.follow_up_date) updateData.follow_up_date = editFormData.follow_up_date;
    
    updateMutation.mutate(updateData);
  };

  const updateEditField = <K extends keyof SubmissionUpdateInput>(
    field: K,
    value: SubmissionUpdateInput[K]
  ) => {
    setEditFormData((prev) => ({ ...prev, [field]: value }));
  };

  const formatRate = (rate?: number, type?: string) => {
    if (!rate) return '-';
    const typeLabel = type?.toLowerCase() === 'hourly' ? 'hr' : type?.toLowerCase() || 'hr';
    return `$${rate.toFixed(2)}/${typeLabel}`;
  };

  const getMarginColor = (marginPct?: number) => {
    if (!marginPct) return 'text-muted-foreground';
    if (marginPct >= 30) return 'text-green-600';
    if (marginPct >= 20) return 'text-blue-600';
    if (marginPct >= 10) return 'text-yellow-600';
    return 'text-red-600';
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <Skeleton className="h-64 w-full" />
            <Skeleton className="h-96 w-full" />
          </div>
          <div className="space-y-6">
            <Skeleton className="h-48 w-full" />
            <Skeleton className="h-48 w-full" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !submission) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" onClick={() => navigate('/submissions')}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Submissions
        </Button>
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            {error ? 'Failed to load submission. Please try again.' : 'Submission not found.'}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  const nextStatuses = getNextValidStatuses(submission.status);
  const isTerminal = isTerminalStatus(submission.status);

  return (
    <TooltipProvider>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="sm" onClick={() => navigate('/submissions')}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">
                Submission #{submission.id}
              </h1>
              <p className="text-muted-foreground">
                {submission.candidate?.first_name} {submission.candidate?.last_name} →{' '}
                {submission.job?.title}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {submission.is_hot && (
              <Badge className="bg-orange-100 text-orange-800">
                <Flame className="h-3 w-3 mr-1" />
                Hot
              </Badge>
            )}
            <Badge className={STATUS_COLORS[submission.status]}>
              {STATUS_ICONS[submission.status]}
              <span className="ml-1">{STATUS_LABELS[submission.status]}</span>
            </Badge>
          </div>
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Main Info */}
          <div className="lg:col-span-2 space-y-6">
            {/* Candidate & Job Info */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Candidate Card */}
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base flex items-center gap-2">
                    <User className="h-4 w-4" />
                    Candidate
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div>
                    <p className="font-semibold text-lg">
                      {submission.candidate?.first_name} {submission.candidate?.last_name}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {submission.candidate?.current_title || 'No title'}
                    </p>
                  </div>
                  {submission.candidate?.email && (
                    <div className="flex items-center gap-2 text-sm">
                      <Mail className="h-4 w-4 text-muted-foreground" />
                      <a
                        href={`mailto:${submission.candidate.email}`}
                        className="text-primary hover:underline"
                      >
                        {submission.candidate.email}
                      </a>
                    </div>
                  )}
                  {submission.candidate?.phone && (
                    <div className="flex items-center gap-2 text-sm">
                      <Phone className="h-4 w-4 text-muted-foreground" />
                      <span>{submission.candidate.phone}</span>
                    </div>
                  )}
                  {submission.candidate?.location && (
                    <div className="flex items-center gap-2 text-sm">
                      <MapPin className="h-4 w-4 text-muted-foreground" />
                      <span>{submission.candidate.location}</span>
                    </div>
                  )}
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full"
                    onClick={() => navigate(`/candidates/${submission.candidate_id}`)}
                  >
                    View Full Profile
                  </Button>
                </CardContent>
              </Card>

              {/* Job Card */}
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base flex items-center gap-2">
                    <Briefcase className="h-4 w-4" />
                    Job Posting
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div>
                    <p className="font-semibold text-lg">{submission.job?.title}</p>
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Building2 className="h-4 w-4" />
                      <span>{submission.job?.company}</span>
                    </div>
                  </div>
                  {submission.job?.location && (
                    <div className="flex items-center gap-2 text-sm">
                      <MapPin className="h-4 w-4 text-muted-foreground" />
                      <span>{submission.job.location}</span>
                      {submission.job.is_remote && (
                        <Badge variant="secondary" className="text-xs">
                          Remote
                        </Badge>
                      )}
                    </div>
                  )}
                  {submission.job?.job_type && (
                    <div className="flex items-center gap-2 text-sm">
                      <Clock className="h-4 w-4 text-muted-foreground" />
                      <span>{submission.job.job_type}</span>
                    </div>
                  )}
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      className="flex-1"
                      onClick={() => navigate(`/jobs/${submission.job_posting_id}`)}
                    >
                      View Details
                    </Button>
                    {submission.job?.job_url && (
                      <Button
                        variant="outline"
                        size="sm"
                        className="flex-1"
                        onClick={() => window.open(submission.job?.job_url, '_blank')}
                      >
                        <ExternalLink className="h-4 w-4 mr-2" />
                        Original
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Rates & Vendor Info */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <DollarSign className="h-4 w-4" />
                  Rates & Vendor Information
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <p className="text-sm text-muted-foreground">Bill Rate</p>
                    <p className="font-semibold text-lg">
                      {formatRate(submission.bill_rate, submission.rate_type)}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Pay Rate</p>
                    <p className="font-semibold text-lg">
                      {formatRate(submission.pay_rate, submission.rate_type)}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Margin</p>
                    <p className={`font-semibold text-lg ${getMarginColor(submission.margin_percentage)}`}>
                      {submission.margin ? `$${submission.margin.toFixed(2)}` : '-'}
                      {submission.margin_percentage && (
                        <span className="text-sm ml-1">
                          ({submission.margin_percentage.toFixed(1)}%)
                        </span>
                      )}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Currency</p>
                    <p className="font-semibold text-lg">{submission.currency || 'USD'}</p>
                  </div>
                </div>

                <Separator className="my-4" />

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-muted-foreground">Vendor Company</p>
                    <p className="font-medium">{submission.vendor_company || '-'}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Client Company</p>
                    <p className="font-medium">{submission.client_company || '-'}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Vendor Contact</p>
                    <p className="font-medium">{submission.vendor_contact_name || '-'}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Vendor Email</p>
                    {submission.vendor_contact_email ? (
                      <a
                        href={`mailto:${submission.vendor_contact_email}`}
                        className="font-medium text-primary hover:underline"
                      >
                        {submission.vendor_contact_email}
                      </a>
                    ) : (
                      <p className="font-medium">-</p>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Activity Timeline */}
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base flex items-center gap-2">
                    <Clock className="h-4 w-4" />
                    Activity Timeline
                  </CardTitle>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setIsAddNoteDialogOpen(true)}
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    Add Note
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {submission.activities && submission.activities.length > 0 ? (
                  <div className="relative">
                    <div className="absolute left-4 top-0 bottom-0 w-px bg-border" />
                    <div className="space-y-6">
                      {submission.activities.map((activity) => {
                        const config = ACTIVITY_CONFIG[activity.activity_type] || ACTIVITY_CONFIG.NOTE;
                        return (
                          <div key={activity.id} className="relative pl-10">
                            <div
                              className={`absolute left-2 w-5 h-5 rounded-full bg-background border-2 flex items-center justify-center ${config.color}`}
                            >
                              {config.icon}
                            </div>
                            <div className="bg-muted/50 rounded-lg p-3">
                              <div className="flex items-center justify-between mb-1">
                                <span className={`text-sm font-medium ${config.color}`}>
                                  {config.label}
                                </span>
                                <Tooltip>
                                  <TooltipTrigger>
                                    <span className="text-xs text-muted-foreground">
                                      {formatDistanceToNow(new Date(activity.created_at), {
                                        addSuffix: true,
                                      })}
                                    </span>
                                  </TooltipTrigger>
                                  <TooltipContent>
                                    {format(new Date(activity.created_at), 'PPpp')}
                                  </TooltipContent>
                                </Tooltip>
                              </div>
                              {activity.content && (
                                <p className="text-sm text-muted-foreground">{activity.content}</p>
                              )}
                              {activity.old_value && activity.new_value && (
                                <p className="text-sm text-muted-foreground">
                                  Changed from{' '}
                                  <span className="font-medium">{activity.old_value}</span> to{' '}
                                  <span className="font-medium">{activity.new_value}</span>
                                </p>
                              )}
                              {activity.created_by && (
                                <p className="text-xs text-muted-foreground mt-1">
                                  by {activity.created_by.first_name || activity.created_by.email}
                                </p>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    <MessageSquare className="h-8 w-8 mx-auto mb-2" />
                    <p>No activity yet</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Right Column - Actions & Quick Info */}
          <div className="space-y-6">
            {/* Quick Actions */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Quick Actions</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {!isTerminal && nextStatuses.length > 0 && (
                  <Button
                    className="w-full"
                    onClick={() => {
                      setSelectedStatus(nextStatuses[0]);
                      setIsStatusDialogOpen(true);
                    }}
                  >
                    <TrendingUp className="h-4 w-4 mr-2" />
                    Update Status
                  </Button>
                )}
                <Button
                  variant="outline"
                  className="w-full"
                  onClick={() => setIsAddNoteDialogOpen(true)}
                >
                  <MessageSquare className="h-4 w-4 mr-2" />
                  Add Note
                </Button>
                <Button
                  variant="outline"
                  className="w-full"
                  onClick={handleOpenEditDialog}
                >
                  <Edit className="h-4 w-4 mr-2" />
                  Edit Submission
                </Button>
              </CardContent>
            </Card>

            {/* Status Info */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Submission Details</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <p className="text-sm text-muted-foreground">Status</p>
                  <Badge className={`${STATUS_COLORS[submission.status]} mt-1`}>
                    {STATUS_ICONS[submission.status]}
                    <span className="ml-1">{STATUS_LABELS[submission.status]}</span>
                  </Badge>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Priority</p>
                  <div className="flex items-center gap-2 mt-1">
                    {submission.is_hot && <Flame className="h-4 w-4 text-orange-500" />}
                    <Badge
                      variant="outline"
                      className={PRIORITY_COLORS[submission.priority || 'MEDIUM']}
                    >
                      {submission.priority || 'MEDIUM'}
                    </Badge>
                  </div>
                </div>
                <Separator />
                <div>
                  <p className="text-sm text-muted-foreground">Submitted</p>
                  <p className="font-medium">
                    {format(new Date(submission.submitted_at), 'PPp')}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {submission.days_since_submitted} days ago
                  </p>
                </div>
                {submission.status_changed_at && (
                  <div>
                    <p className="text-sm text-muted-foreground">Last Status Change</p>
                    <p className="font-medium">
                      {format(new Date(submission.status_changed_at), 'PPp')}
                    </p>
                  </div>
                )}
                {submission.follow_up_date && (
                  <div>
                    <p className="text-sm text-muted-foreground">Follow-up Date</p>
                    <p className="font-medium">
                      {format(new Date(submission.follow_up_date), 'PPp')}
                    </p>
                  </div>
                )}
                {submission.submitted_by && (
                  <div>
                    <p className="text-sm text-muted-foreground">Submitted By</p>
                    <p className="font-medium">
                      {submission.submitted_by.first_name || submission.submitted_by.email}
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Interview Info (if applicable) */}
            {submission.interview_scheduled_at && (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base flex items-center gap-2">
                    <Calendar className="h-4 w-4" />
                    Interview
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div>
                    <p className="text-sm text-muted-foreground">Scheduled</p>
                    <p className="font-medium">
                      {format(new Date(submission.interview_scheduled_at), 'PPp')}
                    </p>
                  </div>
                  {submission.interview_type && (
                    <div>
                      <p className="text-sm text-muted-foreground">Type</p>
                      <p className="font-medium">{submission.interview_type}</p>
                    </div>
                  )}
                  {submission.interview_location && (
                    <div>
                      <p className="text-sm text-muted-foreground">Location</p>
                      <p className="font-medium">{submission.interview_location}</p>
                    </div>
                  )}
                  {submission.interview_notes && (
                    <div>
                      <p className="text-sm text-muted-foreground">Notes</p>
                      <p className="text-sm">{submission.interview_notes}</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Notes */}
            {submission.submission_notes && (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base flex items-center gap-2">
                    <FileText className="h-4 w-4" />
                    Submission Notes
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                    {submission.submission_notes}
                  </p>
                </CardContent>
              </Card>
            )}
          </div>
        </div>

        {/* Status Update Dialog */}
        <Dialog open={isStatusDialogOpen} onOpenChange={setIsStatusDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Update Status</DialogTitle>
              <DialogDescription>
                Change the submission status and optionally add a note.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div>
                <label className="text-sm font-medium">New Status</label>
                <Select
                  value={selectedStatus || ''}
                  onValueChange={(v) => setSelectedStatus(v as SubmissionStatus)}
                >
                  <SelectTrigger className="mt-1">
                    <SelectValue placeholder="Select status" />
                  </SelectTrigger>
                  <SelectContent>
                    {nextStatuses.map((status) => (
                      <SelectItem key={status} value={status}>
                        <div className="flex items-center gap-2">
                          {STATUS_ICONS[status]}
                          {STATUS_LABELS[status]}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-sm font-medium">Note (optional)</label>
                <Textarea
                  value={statusNote}
                  onChange={(e) => setStatusNote(e.target.value)}
                  placeholder="Add a note about this status change..."
                  className="mt-1"
                  rows={3}
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsStatusDialogOpen(false)}>
                Cancel
              </Button>
              <Button
                onClick={handleStatusUpdate}
                disabled={!selectedStatus || statusMutation.isPending}
              >
                {statusMutation.isPending && (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                )}
                Update Status
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Add Note Dialog */}
        <Dialog open={isAddNoteDialogOpen} onOpenChange={setIsAddNoteDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add Note</DialogTitle>
              <DialogDescription>
                Add a note or comment to this submission's activity log.
              </DialogDescription>
            </DialogHeader>
            <div className="py-4">
              <Textarea
                value={newNote}
                onChange={(e) => setNewNote(e.target.value)}
                placeholder="Type your note here..."
                rows={4}
              />
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsAddNoteDialogOpen(false)}>
                Cancel
              </Button>
              <Button
                onClick={handleAddNote}
                disabled={!newNote.trim() || addNoteMutation.isPending}
              >
                {addNoteMutation.isPending && (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                )}
                Add Note
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Edit Submission Dialog */}
        <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Edit className="h-5 w-5" />
                Edit Submission
              </DialogTitle>
              <DialogDescription>
                Update submission details, rates, and vendor information.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-6 py-4">
              {/* Rates Section */}
              <div className="space-y-4">
                <h4 className="text-sm font-semibold flex items-center gap-2">
                  <DollarSign className="h-4 w-4" />
                  Rate Information
                </h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="edit_bill_rate">Bill Rate</Label>
                    <Input
                      id="edit_bill_rate"
                      type="number"
                      placeholder="0.00"
                      value={editFormData.bill_rate || ''}
                      onChange={(e) =>
                        updateEditField('bill_rate', parseFloat(e.target.value) || undefined)
                      }
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="edit_pay_rate">Pay Rate</Label>
                    <Input
                      id="edit_pay_rate"
                      type="number"
                      placeholder="0.00"
                      value={editFormData.pay_rate || ''}
                      onChange={(e) =>
                        updateEditField('pay_rate', parseFloat(e.target.value) || undefined)
                      }
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="edit_rate_type">Rate Type</Label>
                    <Select
                      value={editFormData.rate_type || 'HOURLY'}
                      onValueChange={(v) => updateEditField('rate_type', v as RateType)}
                    >
                      <SelectTrigger id="edit_rate_type">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {RATE_TYPES.map((type) => (
                          <SelectItem key={type} value={type}>
                            {type}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Margin</Label>
                    <div className="h-9 px-3 py-2 border rounded-md bg-muted/50 text-sm">
                      {editFormData.bill_rate && editFormData.pay_rate ? (
                        <span
                          className={
                            ((editFormData.bill_rate - editFormData.pay_rate) / editFormData.bill_rate) * 100 >= 20
                              ? 'text-green-600'
                              : ((editFormData.bill_rate - editFormData.pay_rate) / editFormData.bill_rate) * 100 >= 10
                                ? 'text-yellow-600'
                                : 'text-red-600'
                          }
                        >
                          ${(editFormData.bill_rate - editFormData.pay_rate).toFixed(2)} (
                          {(((editFormData.bill_rate - editFormData.pay_rate) / editFormData.bill_rate) * 100).toFixed(1)}%)
                        </span>
                      ) : (
                        <span className="text-muted-foreground">-</span>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* Vendor Section */}
              <div className="space-y-4">
                <h4 className="text-sm font-semibold flex items-center gap-2">
                  <Building2 className="h-4 w-4" />
                  Vendor Information
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="edit_vendor_company">Vendor Company</Label>
                    <Input
                      id="edit_vendor_company"
                      placeholder="Enter vendor company"
                      value={editFormData.vendor_company || ''}
                      onChange={(e) => updateEditField('vendor_company', e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="edit_client_company">Client Company</Label>
                    <Input
                      id="edit_client_company"
                      placeholder="Enter client company"
                      value={editFormData.client_company || ''}
                      onChange={(e) => updateEditField('client_company', e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="edit_vendor_contact_name">Contact Name</Label>
                    <Input
                      id="edit_vendor_contact_name"
                      placeholder="Enter contact name"
                      value={editFormData.vendor_contact_name || ''}
                      onChange={(e) => updateEditField('vendor_contact_name', e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="edit_vendor_contact_email">Contact Email</Label>
                    <Input
                      id="edit_vendor_contact_email"
                      type="email"
                      placeholder="contact@vendor.com"
                      value={editFormData.vendor_contact_email || ''}
                      onChange={(e) => updateEditField('vendor_contact_email', e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="edit_vendor_contact_phone">Contact Phone</Label>
                    <Input
                      id="edit_vendor_contact_phone"
                      type="tel"
                      placeholder="(555) 555-5555"
                      value={editFormData.vendor_contact_phone || ''}
                      onChange={(e) => updateEditField('vendor_contact_phone', e.target.value)}
                    />
                  </div>
                </div>
              </div>

              {/* Priority & Notes Section */}
              <div className="space-y-4">
                <h4 className="text-sm font-semibold">Priority & Follow-up</h4>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="edit_priority">Priority</Label>
                    <Select
                      value={editFormData.priority || 'MEDIUM'}
                      onValueChange={(v) => updateEditField('priority', v as PriorityLevel)}
                    >
                      <SelectTrigger id="edit_priority">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {PRIORITY_LEVELS.map((priority) => (
                          <SelectItem key={priority} value={priority}>
                            {priority}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="edit_is_hot" className="flex items-center gap-2">
                      <Flame className="h-4 w-4 text-orange-500" />
                      Mark as Hot
                    </Label>
                    <div className="flex items-center space-x-2 h-9">
                      <Switch
                        id="edit_is_hot"
                        checked={editFormData.is_hot || false}
                        onCheckedChange={(checked) => updateEditField('is_hot', checked)}
                      />
                      <Label htmlFor="edit_is_hot" className="text-sm text-muted-foreground">
                        {editFormData.is_hot ? 'Yes' : 'No'}
                      </Label>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="edit_follow_up_date">Follow-up Date</Label>
                    <Input
                      id="edit_follow_up_date"
                      type="date"
                      value={editFormData.follow_up_date || ''}
                      onChange={(e) => updateEditField('follow_up_date', e.target.value)}
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="edit_submission_notes">Notes</Label>
                  <Textarea
                    id="edit_submission_notes"
                    placeholder="Update submission notes..."
                    value={editFormData.submission_notes || ''}
                    onChange={(e) => updateEditField('submission_notes', e.target.value)}
                    rows={3}
                  />
                </div>
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setIsEditDialogOpen(false)}>
                Cancel
              </Button>
              <Button
                onClick={handleSaveEdit}
                disabled={updateMutation.isPending}
              >
                {updateMutation.isPending && (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                )}
                Save Changes
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </TooltipProvider>
  );
}
