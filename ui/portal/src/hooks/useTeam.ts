/**
 * React Query Hooks for Team Management
 * Custom hooks for team hierarchy, member management, and candidate access
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { teamApi } from '@/lib/teamApi';
import { apiRequest } from '@/lib/api-client';
import { toast } from 'sonner';
import type {
  TeamMemberWithCounts,
  AssignManagerRequest,
  CandidateInfo,
} from '@/types';

// =============================================================================
// QUERY KEYS
// =============================================================================

export const teamKeys = {
  all: ['team'] as const,
  hierarchy: () => [...teamKeys.all, 'hierarchy'] as const,
  managers: (roleFilter?: string) => [...teamKeys.all, 'managers', roleFilter] as const,
  availableManagers: (excludeUserId?: number, forUserId?: number) => 
    [...teamKeys.all, 'available-managers', excludeUserId, forUserId] as const,
  myTeamMembers: () => [...teamKeys.all, 'my-team-members'] as const,
  teamMembers: (contextId: number | null) => 
    [...teamKeys.all, 'team-members', contextId] as const,
  memberCandidates: (memberId: number) => 
    [...teamKeys.all, 'member-candidates', memberId] as const,
  myCandidates: () => [...teamKeys.all, 'my-candidates'] as const,
};

// =============================================================================
// QUERY HOOKS
// =============================================================================

/**
 * Hook: Get complete team hierarchy for the tenant
 */
export function useTeamHierarchy() {
  return useQuery({
    queryKey: teamKeys.hierarchy(),
    queryFn: teamApi.getTeamHierarchy,
    staleTime: 30000, // 30 seconds
  });
}

/**
 * Hook: Get list of all managers with team counts
 */
export function useManagersList(roleFilter?: string) {
  return useQuery({
    queryKey: teamKeys.managers(roleFilter),
    queryFn: () => teamApi.getManagersList(roleFilter),
    staleTime: 30000,
  });
}

/**
 * Hook: Get available managers for assignment
 */
export function useAvailableManagers(excludeUserId?: number, forUserId?: number) {
  return useQuery({
    queryKey: teamKeys.availableManagers(excludeUserId, forUserId),
    queryFn: () => teamApi.getAvailableManagers(excludeUserId, forUserId),
    staleTime: 30000,
  });
}

/**
 * Hook: Get current user's direct team members with counts
 * Used for the TeamJobsPage initial view
 */
export function useMyTeamMembers() {
  return useQuery({
    queryKey: teamKeys.myTeamMembers(),
    queryFn: async () => {
      return apiRequest.get<{ team_members: TeamMemberWithCounts[]; total: number }>(
        '/api/team/my-team-members'
      );
    },
    staleTime: 30000,
  });
}

/**
 * Hook: Get team members for a specific context (drill-down navigation)
 * When contextId is null, returns current user's team members
 */
export function useTeamMembers(contextId: number | null, enabled: boolean = true) {
  return useQuery({
    queryKey: teamKeys.teamMembers(contextId),
    queryFn: async () => {
      const url = contextId 
        ? `/api/team/${contextId}/team-members`
        : '/api/team/my-team-members';
      return apiRequest.get<{ team_members: TeamMemberWithCounts[]; total: number }>(url);
    },
    enabled,
    staleTime: 30000,
  });
}

/**
 * Hook: Get candidates assigned to a specific team member
 */
export function useTeamMemberCandidates(memberId: number | null, enabled: boolean = true) {
  return useQuery({
    queryKey: memberId ? teamKeys.memberCandidates(memberId) : ['disabled'],
    queryFn: async () => {
      if (!memberId) return null;
      return apiRequest.get<{ candidates: CandidateInfo[]; total: number }>(
        `/api/team/members/${memberId}/candidates`
      );
    },
    enabled: enabled && !!memberId,
    staleTime: 30000,
  });
}

/**
 * Hook: Get current user's own assigned candidates
 * Used for RECRUITER view or managers with no team
 */
export function useMyCandidates(enabled: boolean = true) {
  return useQuery({
    queryKey: teamKeys.myCandidates(),
    queryFn: async () => {
      return apiRequest.get<{ candidates: CandidateInfo[]; total: number }>(
        '/api/candidates/assignments/my-candidates'
      );
    },
    enabled,
    staleTime: 30000,
  });
}

// =============================================================================
// MUTATION HOOKS
// =============================================================================

/**
 * Hook: Assign manager to a user
 */
export function useAssignManager() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: AssignManagerRequest) => teamApi.assignManager(data),
    onSuccess: (response) => {
      // Invalidate all team-related queries
      queryClient.invalidateQueries({ queryKey: teamKeys.all });
      toast.success('Manager assigned successfully', {
        description: response.message,
      });
    },
    onError: (error: Error) => {
      toast.error('Failed to assign manager', {
        description: error.message,
      });
    },
  });
}

/**
 * Hook: Remove manager assignment from a user
 */
export function useRemoveManager() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (userId: number) => teamApi.removeManager({ user_id: userId }),
    onSuccess: (response) => {
      // Invalidate all team-related queries
      queryClient.invalidateQueries({ queryKey: teamKeys.all });
      toast.success('Manager removed successfully', {
        description: response.message,
      });
    },
    onError: (error: Error) => {
      toast.error('Failed to remove manager', {
        description: error.message,
      });
    },
  });
}

// =============================================================================
// UTILITY HOOKS
// =============================================================================

/**
 * Hook: Combined team context for TeamJobsPage
 * Handles both manager/admin and recruiter views
 */
export function useTeamContext(options: {
  isRecruiter: boolean;
  hasTeamView: boolean;
  contextId: number | null;
  selectedMemberId: number | null;
}) {
  const { isRecruiter, hasTeamView, contextId, selectedMemberId } = options;

  // Get team members (for managers/admins)
  const teamMembersQuery = useTeamMembers(contextId, hasTeamView);
  
  // Check if user has team members
  const hasNoTeamMembers = hasTeamView && 
    teamMembersQuery.data && 
    teamMembersQuery.data.team_members.length === 0;

  // Get recruiter's own candidates
  const ownCandidatesQuery = useMyCandidates(isRecruiter || hasNoTeamMembers);

  // Get selected team member's candidates
  const teamMemberCandidatesQuery = useTeamMemberCandidates(
    selectedMemberId,
    hasTeamView && !!selectedMemberId
  );

  // Determine which candidates to show
  const getCandidates = (): CandidateInfo[] => {
    if (isRecruiter || hasNoTeamMembers) {
      return ownCandidatesQuery.data?.candidates || [];
    }
    if (selectedMemberId) {
      return teamMemberCandidatesQuery.data?.candidates || [];
    }
    return [];
  };

  return {
    // Team members data
    teamMembers: teamMembersQuery.data?.team_members || [],
    isLoadingTeam: teamMembersQuery.isLoading,
    teamError: teamMembersQuery.error,

    // Candidates data
    candidates: getCandidates(),
    isLoadingCandidates: isRecruiter || hasNoTeamMembers 
      ? ownCandidatesQuery.isLoading 
      : teamMemberCandidatesQuery.isLoading,
    candidatesError: isRecruiter || hasNoTeamMembers 
      ? ownCandidatesQuery.error 
      : teamMemberCandidatesQuery.error,

    // State flags
    hasNoTeamMembers,

    // Refetch functions
    refetchTeamMembers: teamMembersQuery.refetch,
    refetchCandidates: isRecruiter || hasNoTeamMembers 
      ? ownCandidatesQuery.refetch 
      : teamMemberCandidatesQuery.refetch,
  };
}
