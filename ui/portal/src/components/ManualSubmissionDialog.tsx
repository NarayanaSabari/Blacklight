/**
 * Manual Submission Dialog
 * Submit a candidate to an external job (not in the portal)
 * Used when recruiters find jobs on LinkedIn, Dice, company sites, etc.
 */

import { useState, useMemo } from 'react';
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
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Send,
  Loader2,
  DollarSign,
  Building2,
  User,
  Briefcase,
  Flame,
  ExternalLink,
  MapPin,
  Check,
  ChevronsUpDown,
} from 'lucide-react';
import { submissionApi } from '@/lib/submissionApi';
import { apiRequest } from '@/lib/api-client';
import { toast } from 'sonner';
import type { ExternalSubmissionCreateInput, PriorityLevel, RateType } from '@/types/submission';
import { PRIORITY_LEVELS, RATE_TYPES } from '@/types/submission';
import { cn } from '@/lib/utils';

interface Candidate {
  id: number;
  first_name: string;
  last_name: string;
  email?: string;
  current_title?: string;
}

interface ManualSubmissionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

export function ManualSubmissionDialog({
  open,
  onOpenChange,
  onSuccess,
}: ManualSubmissionDialogProps) {
  const queryClient = useQueryClient();

  // Candidate selection state
  const [candidateOpen, setCandidateOpen] = useState(false);
  const [selectedCandidateId, setSelectedCandidateId] = useState<number | null>(null);
  const [candidateSearch, setCandidateSearch] = useState('');

  // Form state
  const [formData, setFormData] = useState<Partial<ExternalSubmissionCreateInput>>({
    priority: 'MEDIUM',
    rate_type: 'HOURLY',
    currency: 'USD',
    is_hot: false,
  });

  // Fetch recruiter's assigned candidates
  const { data: candidatesData, isLoading: candidatesLoading } = useQuery({
    queryKey: ['my-own-candidates'],
    queryFn: async () => {
      return apiRequest.get<{ candidates: Candidate[]; total: number }>(
        '/api/candidates/assignments/my-candidates'
      );
    },
    enabled: open,
  });

  const allCandidates = candidatesData?.candidates || [];

  // Filter candidates based on search
  const filteredCandidates = useMemo(() => {
    if (!candidateSearch.trim()) return allCandidates;
    const search = candidateSearch.toLowerCase();
    return allCandidates.filter(
      (c) =>
        `${c.first_name} ${c.last_name}`.toLowerCase().includes(search) ||
        c.email?.toLowerCase().includes(search) ||
        c.current_title?.toLowerCase().includes(search)
    );
  }, [allCandidates, candidateSearch]);

  const selectedCandidate = allCandidates.find((c) => c.id === selectedCandidateId);

  // Create submission mutation
  const createMutation = useMutation({
    mutationFn: (data: ExternalSubmissionCreateInput) =>
      submissionApi.createExternalSubmission(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['submissions'] });
      queryClient.invalidateQueries({ queryKey: ['submission-stats'] });
      const candidateName = selectedCandidate
        ? `${selectedCandidate.first_name} ${selectedCandidate.last_name}`
        : 'Candidate';
      toast.success(
        `Successfully created submission for ${candidateName} to ${formData.external_job_title}`
      );
      onOpenChange(false);
      onSuccess?.();
      resetForm();
    },
    onError: (error: Error) => {
      toast.error(`Failed to create submission: ${error.message}`);
    },
  });

  const resetForm = () => {
    setSelectedCandidateId(null);
    setCandidateSearch('');
    setFormData({
      priority: 'MEDIUM',
      rate_type: 'HOURLY',
      currency: 'USD',
      is_hot: false,
    });
  };

  const handleSubmit = () => {
    if (!selectedCandidateId) {
      toast.error('Please select a candidate');
      return;
    }
    if (!formData.external_job_title?.trim()) {
      toast.error('Please enter a job title');
      return;
    }
    if (!formData.external_job_company?.trim()) {
      toast.error('Please enter a company name');
      return;
    }

    createMutation.mutate({
      candidate_id: selectedCandidateId,
      external_job_title: formData.external_job_title.trim(),
      external_job_company: formData.external_job_company.trim(),
      external_job_location: formData.external_job_location?.trim() || undefined,
      external_job_url: formData.external_job_url?.trim() || undefined,
      external_job_description: formData.external_job_description?.trim() || undefined,
      vendor_company: formData.vendor_company?.trim() || undefined,
      vendor_contact_name: formData.vendor_contact_name?.trim() || undefined,
      vendor_contact_email: formData.vendor_contact_email?.trim() || undefined,
      vendor_contact_phone: formData.vendor_contact_phone?.trim() || undefined,
      client_company: formData.client_company?.trim() || undefined,
      bill_rate: formData.bill_rate || undefined,
      pay_rate: formData.pay_rate || undefined,
      rate_type: formData.rate_type as RateType,
      currency: formData.currency || 'USD',
      submission_notes: formData.submission_notes?.trim() || undefined,
      priority: formData.priority as PriorityLevel,
      is_hot: formData.is_hot || false,
    });
  };

  const updateField = <K extends keyof ExternalSubmissionCreateInput>(
    field: K,
    value: ExternalSubmissionCreateInput[K]
  ) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  // Calculate margin
  const margin =
    formData.bill_rate && formData.pay_rate ? formData.bill_rate - formData.pay_rate : undefined;
  const marginPct =
    margin && formData.bill_rate ? (margin / formData.bill_rate) * 100 : undefined;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Send className="h-5 w-5" />
            Add Manual Submission
          </DialogTitle>
          <DialogDescription>
            Track a submission to an external job (LinkedIn, Dice, company website, etc.)
          </DialogDescription>
        </DialogHeader>

        <ScrollArea className="max-h-[60vh] pr-4">
          <div className="space-y-6 py-4">
            {/* Candidate Selection */}
            <div className="space-y-4">
              <h4 className="text-sm font-semibold flex items-center gap-2">
                <User className="h-4 w-4" />
                Select Candidate <span className="text-destructive">*</span>
              </h4>
              <Popover open={candidateOpen} onOpenChange={setCandidateOpen}>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    role="combobox"
                    aria-expanded={candidateOpen}
                    className="w-full justify-between"
                  >
                    {selectedCandidate ? (
                      <span>
                        {selectedCandidate.first_name} {selectedCandidate.last_name}
                        {selectedCandidate.current_title && (
                          <span className="text-muted-foreground ml-2">
                            - {selectedCandidate.current_title}
                          </span>
                        )}
                      </span>
                    ) : (
                      <span className="text-muted-foreground">Search and select a candidate...</span>
                    )}
                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-[500px] p-0" align="start">
                  <Command shouldFilter={false}>
                    <CommandInput
                      placeholder="Search by name, email, or title..."
                      value={candidateSearch}
                      onValueChange={setCandidateSearch}
                    />
                    <CommandList>
                      {candidatesLoading ? (
                        <div className="py-6 text-center text-sm">
                          <Loader2 className="h-4 w-4 animate-spin mx-auto mb-2" />
                          Loading candidates...
                        </div>
                      ) : filteredCandidates.length === 0 ? (
                        <CommandEmpty>
                          {allCandidates.length === 0
                            ? 'No candidates assigned to you'
                            : 'No candidates found'}
                        </CommandEmpty>
                      ) : (
                        <CommandGroup>
                          {filteredCandidates.slice(0, 50).map((candidate) => (
                            <CommandItem
                              key={candidate.id}
                              value={candidate.id.toString()}
                              onSelect={() => {
                                setSelectedCandidateId(candidate.id);
                                setCandidateOpen(false);
                              }}
                            >
                              <Check
                                className={cn(
                                  'mr-2 h-4 w-4',
                                  selectedCandidateId === candidate.id
                                    ? 'opacity-100'
                                    : 'opacity-0'
                                )}
                              />
                              <div className="flex flex-col">
                                <span>
                                  {candidate.first_name} {candidate.last_name}
                                </span>
                                <span className="text-xs text-muted-foreground">
                                  {candidate.current_title || candidate.email || 'No title'}
                                </span>
                              </div>
                            </CommandItem>
                          ))}
                        </CommandGroup>
                      )}
                    </CommandList>
                  </Command>
                </PopoverContent>
              </Popover>
            </div>

            {/* External Job Information */}
            <div className="space-y-4">
              <h4 className="text-sm font-semibold flex items-center gap-2">
                <Briefcase className="h-4 w-4" />
                Job Information <span className="text-destructive">*</span>
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="external_job_title">
                    Job Title <span className="text-destructive">*</span>
                  </Label>
                  <Input
                    id="external_job_title"
                    placeholder="e.g. Senior Software Engineer"
                    value={formData.external_job_title || ''}
                    onChange={(e) => updateField('external_job_title', e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="external_job_company">
                    Company <span className="text-destructive">*</span>
                  </Label>
                  <Input
                    id="external_job_company"
                    placeholder="e.g. Google, Microsoft"
                    value={formData.external_job_company || ''}
                    onChange={(e) => updateField('external_job_company', e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="external_job_location" className="flex items-center gap-1">
                    <MapPin className="h-3 w-3" />
                    Location
                  </Label>
                  <Input
                    id="external_job_location"
                    placeholder="e.g. San Francisco, CA or Remote"
                    value={formData.external_job_location || ''}
                    onChange={(e) => updateField('external_job_location', e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="external_job_url" className="flex items-center gap-1">
                    <ExternalLink className="h-3 w-3" />
                    Job URL
                  </Label>
                  <Input
                    id="external_job_url"
                    type="url"
                    placeholder="https://linkedin.com/jobs/..."
                    value={formData.external_job_url || ''}
                    onChange={(e) => updateField('external_job_url', e.target.value)}
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="external_job_description">Job Description / Notes</Label>
                <Textarea
                  id="external_job_description"
                  placeholder="Brief description of the job requirements..."
                  value={formData.external_job_description || ''}
                  onChange={(e) => updateField('external_job_description', e.target.value)}
                  rows={2}
                />
              </div>
            </div>

            {/* Rates Section */}
            <div className="space-y-4">
              <h4 className="text-sm font-semibold flex items-center gap-2">
                <DollarSign className="h-4 w-4" />
                Rate Information
              </h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="bill_rate">Bill Rate</Label>
                  <Input
                    id="bill_rate"
                    type="number"
                    placeholder="0.00"
                    value={formData.bill_rate || ''}
                    onChange={(e) =>
                      updateField('bill_rate', parseFloat(e.target.value) || undefined)
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="pay_rate">Pay Rate</Label>
                  <Input
                    id="pay_rate"
                    type="number"
                    placeholder="0.00"
                    value={formData.pay_rate || ''}
                    onChange={(e) =>
                      updateField('pay_rate', parseFloat(e.target.value) || undefined)
                    }
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
                  <Label htmlFor="vendor_company">Vendor Company</Label>
                  <Input
                    id="vendor_company"
                    placeholder="Enter vendor company"
                    value={formData.vendor_company || ''}
                    onChange={(e) => updateField('vendor_company', e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="client_company">Client Company</Label>
                  <Input
                    id="client_company"
                    placeholder="Enter client company"
                    value={formData.client_company || ''}
                    onChange={(e) => updateField('client_company', e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="vendor_contact_name">Contact Name</Label>
                  <Input
                    id="vendor_contact_name"
                    placeholder="Enter contact name"
                    value={formData.vendor_contact_name || ''}
                    onChange={(e) => updateField('vendor_contact_name', e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="vendor_contact_email">Contact Email</Label>
                  <Input
                    id="vendor_contact_email"
                    type="email"
                    placeholder="contact@vendor.com"
                    value={formData.vendor_contact_email || ''}
                    onChange={(e) => updateField('vendor_contact_email', e.target.value)}
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
                <Label htmlFor="submission_notes">Submission Notes</Label>
                <Textarea
                  id="submission_notes"
                  placeholder="Add any notes about this submission..."
                  value={formData.submission_notes || ''}
                  onChange={(e) => updateField('submission_notes', e.target.value)}
                  rows={3}
                />
              </div>
            </div>
          </div>
        </ScrollArea>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={
              createMutation.isPending ||
              !selectedCandidateId ||
              !formData.external_job_title?.trim() ||
              !formData.external_job_company?.trim()
            }
          >
            {createMutation.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            <Send className="h-4 w-4 mr-2" />
            Add Submission
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
