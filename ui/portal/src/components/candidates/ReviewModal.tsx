/**
 * Review Modal Component
 * Modal for HR to review and edit AI-parsed candidate data before approval
 */

import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { CheckCircle2, XCircle, AlertCircle, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { candidateApi } from '@/lib/candidateApi';
import { getErrorMessage } from '@/lib/api-client';
import type { Candidate, CandidateUpdateInput } from '@/types/candidate';

interface ReviewModalProps {
  candidate: Candidate;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

export function ReviewModal({ candidate, open, onOpenChange, onSuccess }: ReviewModalProps) {
  const queryClient = useQueryClient();
  
  // Form state - initialize with candidate data
  const [firstName, setFirstName] = useState(candidate.first_name || '');
  const [lastName, setLastName] = useState(candidate.last_name || '');
  const [email, setEmail] = useState(candidate.email || '');
  const [phone, setPhone] = useState(candidate.phone || '');
  const [currentTitle, setCurrentTitle] = useState(candidate.current_title || '');
  const [location, setLocation] = useState(candidate.location || '');
  const [linkedinUrl, setLinkedinUrl] = useState(candidate.linkedin_url || '');
  const [skills, setSkills] = useState((candidate.skills || []).join(', '));
  const [experienceYears, setExperienceYears] = useState(candidate.total_experience_years?.toString() || '');
  const [summary, setSummary] = useState(candidate.professional_summary || '');

  // Review and update mutation
  const reviewMutation = useMutation({
    mutationFn: async (data: Partial<CandidateUpdateInput>) => {
      return candidateApi.reviewCandidate(candidate.id, data);
    },
    onSuccess: () => {
      toast.success('Changes saved successfully');
    },
    onError: (error: unknown) => {
      toast.error(getErrorMessage(error));
    },
  });

  // Approve mutation
  const approveMutation = useMutation({
    mutationFn: async () => {
      return candidateApi.approveCandidate(candidate.id);
    },
    onSuccess: async () => {
      toast.success('Candidate approved!', {
        description: 'Job matching workflow has been triggered.',
      });
      await queryClient.refetchQueries({ queryKey: ['candidates'] });
      await queryClient.refetchQueries({ queryKey: ['candidate-stats'] });
      onOpenChange(false);
      if (onSuccess) onSuccess();
    },
    onError: (error: unknown) => {
      toast.error(getErrorMessage(error));
    },
  });

  // Delete/Reject mutation
  const rejectMutation = useMutation({
    mutationFn: async () => {
      return candidateApi.deleteCandidate(candidate.id);
    },
    retry: false, // Disable retries to prevent 404 on already-deleted candidates
    onSuccess: async () => {
      // Close modal immediately before refetching to prevent re-renders
      onOpenChange(false);
      toast.success('Candidate rejected and removed');
      // Refetch in background after modal closes
      await queryClient.refetchQueries({ queryKey: ['candidates'] });
      await queryClient.refetchQueries({ queryKey: ['candidate-stats'] });
      await queryClient.refetchQueries({ queryKey: ['pending-review-candidates'] });
      if (onSuccess) onSuccess();
    },
    onError: (error: unknown) => {
      toast.error(getErrorMessage(error));
    },
  });

  const handleSaveAndApprove = async () => {
    // First save the edited data
    const updatedData: Partial<CandidateUpdateInput> = {
      first_name: firstName,
      last_name: lastName,
      email: email || undefined,
      phone: phone || undefined,
      current_title: currentTitle || undefined,
      location: location || undefined,
      linkedin_url: linkedinUrl || undefined,
      skills: skills ? skills.split(',').map(s => s.trim()).filter(Boolean) : undefined,
      total_experience_years: experienceYears ? parseInt(experienceYears) : undefined,
      professional_summary: summary || undefined,
    };

    try {
      await reviewMutation.mutateAsync(updatedData);
      // Then approve
      await approveMutation.mutateAsync();
    } catch {
      // Error handling done in mutations
    }
  };

  const isLoading = reviewMutation.isPending || approveMutation.isPending || rejectMutation.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            Review Candidate
            <Badge className="bg-blue-100 text-blue-800">Pending Review</Badge>
          </DialogTitle>
          <DialogDescription>
            Review and edit the AI-parsed information below. You can make corrections before approving.
          </DialogDescription>
        </DialogHeader>

        {candidate.resume_parsed_at && (
          <Alert className="bg-blue-50 border-blue-200">
            <AlertCircle className="h-4 w-4 text-blue-600" />
            <AlertDescription className="text-blue-800 text-sm">
              Resume parsed on {new Date(candidate.resume_parsed_at).toLocaleString()}
            </AlertDescription>
          </Alert>
        )}

        <div className="space-y-4">
          {/* Personal Information */}
          <div className="space-y-3">
            <h3 className="font-semibold text-sm text-slate-700">Personal Information</h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="firstName">First Name *</Label>
                <Input
                  id="firstName"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  placeholder="John"
                />
              </div>
              <div>
                <Label htmlFor="lastName">Last Name</Label>
                <Input
                  id="lastName"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  placeholder="Doe"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="john@example.com"
                />
              </div>
              <div>
                <Label htmlFor="phone">Phone</Label>
                <Input
                  id="phone"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="+1 234 567 8900"
                />
              </div>
            </div>
          </div>

          {/* Professional Information */}
          <div className="space-y-3">
            <h3 className="font-semibold text-sm text-slate-700">Professional Details</h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="currentTitle">Current Title</Label>
                <Input
                  id="currentTitle"
                  value={currentTitle}
                  onChange={(e) => setCurrentTitle(e.target.value)}
                  placeholder="Senior Software Engineer"
                />
              </div>
              <div>
                <Label htmlFor="experienceYears">Years of Experience</Label>
                <Input
                  id="experienceYears"
                  type="number"
                  value={experienceYears}
                  onChange={(e) => setExperienceYears(e.target.value)}
                  placeholder="5"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="location">Location</Label>
                <Input
                  id="location"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  placeholder="San Francisco, CA"
                />
              </div>
              <div>
                <Label htmlFor="linkedinUrl">LinkedIn URL</Label>
                <Input
                  id="linkedinUrl"
                  value={linkedinUrl}
                  onChange={(e) => setLinkedinUrl(e.target.value)}
                  placeholder="https://linkedin.com/in/..."
                />
              </div>
            </div>
          </div>

          {/* Skills */}
          <div className="space-y-2">
            <Label htmlFor="skills">Skills (comma-separated)</Label>
            <Textarea
              id="skills"
              value={skills}
              onChange={(e) => setSkills(e.target.value)}
              placeholder="Python, React, Node.js, AWS"
              rows={2}
            />
          </div>

          {/* Professional Summary */}
          <div className="space-y-2">
            <Label htmlFor="summary">Professional Summary</Label>
            <Textarea
              id="summary"
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              placeholder="Brief professional summary..."
              rows={3}
            />
          </div>
        </div>

        <DialogFooter className="gap-2">
          <Button
            variant="outline"
            onClick={() => rejectMutation.mutate()}
            disabled={isLoading}
            className="text-red-600 hover:text-red-700 hover:bg-red-50"
          >
            <XCircle className="h-4 w-4 mr-2" />
            Reject & Delete
          </Button>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isLoading}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSaveAndApprove}
            disabled={isLoading || !firstName}
            className="bg-green-600 hover:bg-green-700"
          >
            {isLoading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Processing...
              </>
            ) : (
              <>
                <CheckCircle2 className="h-4 w-4 mr-2" />
                Save & Approve
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
