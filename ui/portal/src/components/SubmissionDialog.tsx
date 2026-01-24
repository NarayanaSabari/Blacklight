/**
 * Submission Dialog
 * Quick submit modal for submitting candidates to jobs
 */

import { useState } from 'react';
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
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
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Send,
  Loader2,
  DollarSign,
  Building2,
  User,
  Briefcase,
  AlertCircle,
  Flame,
} from 'lucide-react';
import { submissionApi } from '@/lib/submissionApi';
import { toast } from 'sonner';
import type { SubmissionCreateInput, PriorityLevel, RateType } from '@/types/submission';
import { PRIORITY_LEVELS, RATE_TYPES } from '@/types/submission';

interface SubmissionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  candidateId: number;
  candidateName: string;
  jobPostingId: number;
  jobTitle: string;
  company: string;
  onSuccess?: () => void;
}

export function SubmissionDialog({
  open,
  onOpenChange,
  candidateId,
  candidateName,
  jobPostingId,
  jobTitle,
  company,
  onSuccess,
}: SubmissionDialogProps) {
  const queryClient = useQueryClient();

  // Form state
  const [formData, setFormData] = useState<Partial<SubmissionCreateInput>>({
    candidate_id: candidateId,
    job_posting_id: jobPostingId,
    priority: 'MEDIUM',
    rate_type: 'HOURLY',
    currency: 'USD',
    is_hot: false,
  });

  // Check for existing submission
  const { data: duplicateCheck, isLoading: checkingDuplicate } = useQuery({
    queryKey: ['submission-check-duplicate', candidateId, jobPostingId],
    queryFn: () => submissionApi.checkDuplicate(candidateId, jobPostingId),
    enabled: open && candidateId > 0 && jobPostingId > 0,
  });

  // Create submission mutation
  const createMutation = useMutation({
    mutationFn: (data: SubmissionCreateInput) => submissionApi.createSubmission(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['submissions'] });
      queryClient.invalidateQueries({ queryKey: ['submission-stats'] });
      toast.success(`Successfully submitted ${candidateName} to ${jobTitle}`);
      onOpenChange(false);
      onSuccess?.();
      resetForm();
    },
    onError: (error: Error) => {
      toast.error(`Failed to create submission: ${error.message}`);
    },
  });

  const resetForm = () => {
    setFormData({
      candidate_id: candidateId,
      job_posting_id: jobPostingId,
      priority: 'MEDIUM',
      rate_type: 'HOURLY',
      currency: 'USD',
      is_hot: false,
    });
  };

  const handleSubmit = () => {
    const requiredFields = {
      vendor_company: 'Vendor Company',
      vendor_contact_name: 'Vendor Contact Name',
      vendor_contact_email: 'Vendor Contact Email',
      vendor_contact_phone: 'Vendor Contact Phone',
      client_company: 'Client Company',
      bill_rate: 'Bill Rate',
      pay_rate: 'Pay Rate',
      submission_notes: 'Submission Notes',
    };

    const missingFields: string[] = [];
    for (const [field, label] of Object.entries(requiredFields)) {
      const value = formData[field as keyof typeof formData];
      if (!value || (typeof value === 'string' && value.trim() === '')) {
        missingFields.push(label);
      }
    }

    if (missingFields.length > 0) {
      toast.error(`Please fill in all required fields: ${missingFields.join(', ')}`);
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (formData.vendor_contact_email && !emailRegex.test(formData.vendor_contact_email)) {
      toast.error('Please enter a valid email address');
      return;
    }

    createMutation.mutate({
      candidate_id: candidateId,
      job_posting_id: jobPostingId,
      vendor_company: formData.vendor_company!,
      vendor_contact_name: formData.vendor_contact_name!,
      vendor_contact_email: formData.vendor_contact_email!,
      vendor_contact_phone: formData.vendor_contact_phone!,
      client_company: formData.client_company!,
      bill_rate: formData.bill_rate!,
      pay_rate: formData.pay_rate!,
      rate_type: formData.rate_type as RateType,
      currency: formData.currency || 'USD',
      submission_notes: formData.submission_notes!,
      priority: formData.priority as PriorityLevel,
      is_hot: formData.is_hot || false,
    });
  };

  const updateField = <K extends keyof SubmissionCreateInput>(
    field: K,
    value: SubmissionCreateInput[K]
  ) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  // Calculate margin
  const margin =
    formData.bill_rate && formData.pay_rate
      ? formData.bill_rate - formData.pay_rate
      : undefined;
  const marginPct =
    margin && formData.bill_rate ? (margin / formData.bill_rate) * 100 : undefined;

  const isDuplicate = duplicateCheck?.exists;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Send className="h-5 w-5" />
            Submit Candidate to Job
          </DialogTitle>
          <DialogDescription>
            Create a submission to track this candidate's application.
          </DialogDescription>
        </DialogHeader>

        {/* Summary */}
        <div className="grid grid-cols-2 gap-4 p-4 bg-muted/50 rounded-lg">
          <div className="flex items-center gap-2">
            <User className="h-4 w-4 text-muted-foreground" />
            <div>
              <p className="text-xs text-muted-foreground">Candidate</p>
              <p className="font-medium">{candidateName}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Briefcase className="h-4 w-4 text-muted-foreground" />
            <div>
              <p className="text-xs text-muted-foreground">Job</p>
              <p className="font-medium">{jobTitle}</p>
              <p className="text-xs text-muted-foreground">{company}</p>
            </div>
          </div>
        </div>

        {/* Duplicate Warning */}
        {isDuplicate && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              This candidate has already been submitted to this job. You cannot create a
              duplicate submission.
            </AlertDescription>
          </Alert>
        )}

        {!isDuplicate && (
          <div className="space-y-6 py-4">
            {/* Rates Section */}
            <div className="space-y-4">
              <h4 className="text-sm font-semibold flex items-center gap-2">
                <DollarSign className="h-4 w-4" />
                Rate Information
              </h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="bill_rate">
                    Bill Rate <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    id="bill_rate"
                    type="number"
                    placeholder="0.00"
                    value={formData.bill_rate || ''}
                    onChange={(e) =>
                      updateField('bill_rate', parseFloat(e.target.value) || 0)
                    }
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="pay_rate">
                    Pay Rate <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    id="pay_rate"
                    type="number"
                    placeholder="0.00"
                    value={formData.pay_rate || ''}
                    onChange={(e) =>
                      updateField('pay_rate', parseFloat(e.target.value) || 0)
                    }
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="rate_type">Rate Type</Label>
                  <Select
                    value={formData.rate_type || 'HOURLY'}
                    onValueChange={(v) => updateField('rate_type', v as RateType)}
                  >
                    <SelectTrigger id="rate_type">
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
                    {margin ? (
                      <span
                        className={
                          marginPct && marginPct >= 20
                            ? 'text-green-600'
                            : marginPct && marginPct >= 10
                              ? 'text-yellow-600'
                              : 'text-red-600'
                        }
                      >
                        ${margin.toFixed(2)} ({marginPct?.toFixed(1)}%)
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
                  <Label htmlFor="vendor_company">
                    Vendor Company <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    id="vendor_company"
                    placeholder="Enter vendor company"
                    value={formData.vendor_company || ''}
                    onChange={(e) => updateField('vendor_company', e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="client_company">
                    Client Company <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    id="client_company"
                    placeholder="Enter client company"
                    value={formData.client_company || ''}
                    onChange={(e) => updateField('client_company', e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="vendor_contact_name">
                    Contact Name <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    id="vendor_contact_name"
                    placeholder="Enter contact name"
                    value={formData.vendor_contact_name || ''}
                    onChange={(e) => updateField('vendor_contact_name', e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="vendor_contact_email">
                    Contact Email <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    id="vendor_contact_email"
                    type="email"
                    placeholder="contact@vendor.com"
                    value={formData.vendor_contact_email || ''}
                    onChange={(e) => updateField('vendor_contact_email', e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="vendor_contact_phone">
                    Contact Phone <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    id="vendor_contact_phone"
                    type="tel"
                    placeholder="Enter contact phone"
                    value={formData.vendor_contact_phone || ''}
                    onChange={(e) => updateField('vendor_contact_phone', e.target.value)}
                    required
                  />
                </div>
              </div>
            </div>

            {/* Priority & Notes Section */}
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="priority">Priority</Label>
                  <Select
                    value={formData.priority || 'MEDIUM'}
                    onValueChange={(v) => updateField('priority', v as PriorityLevel)}
                  >
                    <SelectTrigger id="priority">
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
                  <Label htmlFor="is_hot" className="flex items-center gap-2">
                    <Flame className="h-4 w-4 text-orange-500" />
                    Mark as Hot
                  </Label>
                  <div className="flex items-center space-x-2 h-9">
                    <Switch
                      id="is_hot"
                      checked={formData.is_hot || false}
                      onCheckedChange={(checked) => updateField('is_hot', checked)}
                    />
                    <Label htmlFor="is_hot" className="text-sm text-muted-foreground">
                      {formData.is_hot ? 'Yes' : 'No'}
                    </Label>
                  </div>
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="submission_notes">
                  Notes <span className="text-red-500">*</span>
                </Label>
                <Textarea
                  id="submission_notes"
                  placeholder="Add any notes about this submission..."
                  value={formData.submission_notes || ''}
                  onChange={(e) => updateField('submission_notes', e.target.value)}
                  rows={3}
                  required
                />
              </div>
            </div>
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={isDuplicate || createMutation.isPending || checkingDuplicate}
          >
            {createMutation.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            <Send className="h-4 w-4 mr-2" />
            Submit Candidate
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
