/**
 * Candidate Assignment Dialog Component
 * Allows HR/Managers to assign candidates to team members
 */

import { useState, useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { candidateAssignmentApi } from '@/lib/candidateAssignmentApi';
import { apiRequest } from '@/lib/api-client';
import type { PortalUserFull, AssignCandidateRequest } from '@/types';
import { toast } from 'sonner';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Switch } from '@/components/ui/switch';
import { UserPlus, AlertCircle, Users } from 'lucide-react';

interface CandidateAssignmentDialogProps {
  candidateId: number;
  candidateName: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
  isReassignment?: boolean;
}

interface AssignmentFormData {
  assignedToUserId: number | null;
  reason: string;
  isBroadcast: boolean;
}

export function CandidateAssignmentDialog({
  candidateId,
  candidateName,
  open,
  onOpenChange,
  onSuccess,
  isReassignment = false,
}: CandidateAssignmentDialogProps) {
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState<AssignmentFormData>({
    assignedToUserId: null,
    reason: '',
    isBroadcast: false,
  });

  // Fetch available users (managers and recruiters)
  const { data: usersData, isLoading: isLoadingUsers } = useQuery({
    queryKey: ['portal-users', 'assignable'],
    queryFn: async () => {
      return apiRequest.get<{ items: PortalUserFull[] }>('/api/portal/users');
    },
    enabled: open,
  });

  // Filter users to show only MANAGER and RECRUITER roles
  const assignableUsers = usersData?.items?.filter((user) => {
    const roleNames = user.roles?.map((r) => r.name) || [];
    return roleNames.includes('TEAM_LEAD') || roleNames.includes('RECRUITER');
  }) || [];

  // Assignment mutation (single user)
  const assignMutation = useMutation({
    mutationFn: async (data: AssignCandidateRequest) => {
      if (isReassignment) {
        // Use reassign endpoint for reassignment
        return candidateAssignmentApi.reassignCandidate({
          candidate_id: data.candidate_id,
          new_assigned_to_user_id: data.assigned_to_user_id,
          assignment_reason: data.assignment_reason,
        });
      } else {
        // Use assign endpoint for initial assignment
        return candidateAssignmentApi.assignCandidate(data);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['candidates'] });
      queryClient.invalidateQueries({ queryKey: ['candidate', candidateId] });
      queryClient.invalidateQueries({ queryKey: ['candidate-assignments'] });
      queryClient.invalidateQueries({ queryKey: ['my-assigned-candidates'] });
      queryClient.invalidateQueries({ queryKey: ['ready-to-assign'] });
      queryClient.invalidateQueries({ queryKey: ['onboarding-stats'] });
      
      toast.success('Candidate assigned successfully');
      
      if (onSuccess) {
        onSuccess();
      }
      
      // Reset form and close dialog
      setFormData({ assignedToUserId: null, reason: '', isBroadcast: false });
      onOpenChange(false);
    },
  });

  // Broadcast assignment mutation (all users)
  const broadcastMutation = useMutation({
    mutationFn: async () => {
      return candidateAssignmentApi.broadcastAssignCandidate(
        candidateId,
        formData.reason || undefined
      );
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['candidates'] });
      queryClient.invalidateQueries({ queryKey: ['candidate', candidateId] });
      queryClient.invalidateQueries({ queryKey: ['candidate-assignments'] });
      queryClient.invalidateQueries({ queryKey: ['my-assigned-candidates'] });
      queryClient.invalidateQueries({ queryKey: ['ready-to-assign'] });
      queryClient.invalidateQueries({ queryKey: ['onboarding-stats'] });
      
      toast.success(`Candidate is now visible to all team members (${data.current_team_count} current users + future hires)`);
      
      if (onSuccess) {
        onSuccess();
      }
      
      // Reset form and close dialog
      setFormData({ assignedToUserId: null, reason: '', isBroadcast: false });
      onOpenChange(false);
    },
  });

  const isPending = assignMutation.isPending || broadcastMutation.isPending;
  const isError = assignMutation.isError || broadcastMutation.isError;
  const error = assignMutation.error || broadcastMutation.error;

  // Reset form when dialog closes
  useEffect(() => {
    if (!open) {
      setFormData({ assignedToUserId: null, reason: '', isBroadcast: false });
      assignMutation.reset();
      broadcastMutation.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (formData.isBroadcast) {
      // Broadcast to all team members
      broadcastMutation.mutate();
    } else {
      // Single user assignment
      if (!formData.assignedToUserId) {
        return;
      }

      assignMutation.mutate({
        candidate_id: candidateId,
        assigned_to_user_id: formData.assignedToUserId,
        assignment_reason: formData.reason || undefined,
      });
    }
  };

  const getUserRoleLabel = (user: PortalUserFull): string => {
    const roleNames = user.roles?.map((r) => r.name) || [];
    if (roleNames.includes('TEAM_LEAD')) return 'Team Lead';
    if (roleNames.includes('RECRUITER')) return 'Recruiter';
    return 'User';
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {formData.isBroadcast ? (
              <Users className="h-5 w-5" />
            ) : (
              <UserPlus className="h-5 w-5" />
            )}
            {isReassignment ? 'Reassign Candidate' : 'Assign Candidate'}
          </DialogTitle>
          <DialogDescription>
            {isReassignment 
              ? `Reassign ${candidateName} to a different team member.`
              : `Assign ${candidateName} to a team member for recruitment processing.`
            }
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit}>
          <div className="space-y-4 py-4">
            {/* Broadcast Toggle (only for new assignments, not reassignments) */}
            {!isReassignment && (
              <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg border">
                <div className="space-y-0.5">
                  <Label htmlFor="broadcast" className="text-base font-medium">
                    Visible to All Team Members
                  </Label>
                  <p className="text-sm text-muted-foreground">
                    Make this candidate visible to all current ({assignableUsers.length}) and future team members
                  </p>
                </div>
                <Switch
                  id="broadcast"
                  checked={formData.isBroadcast}
                  onCheckedChange={(checked) =>
                    setFormData({ ...formData, isBroadcast: checked, assignedToUserId: null })
                  }
                  disabled={isPending}
                />
              </div>
            )}

            {/* Assignment Target Selection (hidden when broadcast is on) */}
            {!formData.isBroadcast && (
              <div className="space-y-2">
                <Label htmlFor="assignedTo">
                  Assign To <span className="text-red-500">*</span>
                </Label>
                <Select
                  value={formData.assignedToUserId?.toString() || ''}
                  onValueChange={(value) =>
                    setFormData({ ...formData, assignedToUserId: parseInt(value) })
                  }
                  disabled={isLoadingUsers || isPending}
                >
                  <SelectTrigger id="assignedTo">
                    <SelectValue placeholder="Select a team member..." />
                  </SelectTrigger>
                  <SelectContent>
                    {isLoadingUsers ? (
                      <SelectItem value="loading" disabled>
                        Loading users...
                      </SelectItem>
                    ) : assignableUsers.length === 0 ? (
                      <SelectItem value="none" disabled>
                        No assignable users found
                      </SelectItem>
                    ) : (
                      assignableUsers.map((user) => (
                        <SelectItem key={user.id} value={user.id.toString()}>
                          {user.full_name} ({getUserRoleLabel(user)}) - {user.email}
                        </SelectItem>
                      ))
                    )}
                  </SelectContent>
                </Select>
                <p className="text-sm text-muted-foreground">
                  Select a Manager or Recruiter to assign this candidate to
                </p>
              </div>
            )}

            {/* Optional Reason */}
            <div className="space-y-2">
              <Label htmlFor="reason">Assignment Reason (Optional)</Label>
              <Textarea
                id="reason"
                placeholder={formData.isBroadcast 
                  ? "Why are you sharing this candidate with the whole team?"
                  : "Why are you assigning this candidate to this team member?"
                }
                value={formData.reason}
                onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
                disabled={isPending}
                rows={3}
              />
            </div>

            {/* Error Message */}
            {isError && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  {error instanceof Error
                    ? error.message
                    : 'Failed to assign candidate. Please try again.'}
                </AlertDescription>
              </Alert>
            )}
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isPending}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={(!formData.isBroadcast && !formData.assignedToUserId) || isPending}
            >
              {isPending 
                ? (formData.isBroadcast ? 'Assigning to All...' : (isReassignment ? 'Reassigning...' : 'Assigning...'))
                : (formData.isBroadcast ? `Assign to All (${assignableUsers.length})` : (isReassignment ? 'Reassign Candidate' : 'Assign Candidate'))
              }
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
