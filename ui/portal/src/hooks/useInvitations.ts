/**
 * React Query Hooks for Invitation Management
 * Custom hooks for HR invitation operations
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { invitationApi } from '@/lib/api/invitationApi';
import { getErrorMessage } from '@/lib/api-client';
import { toast } from 'sonner';
import type {
  InvitationCreateRequest,
  InvitationUpdateRequest,
  InvitationListParams,
  BulkInvitationRequest,
} from '@/types';
import { AxiosError } from 'axios';

// Query keys for cache management
export const invitationKeys = {
  all: ['invitations'] as const,
  lists: () => [...invitationKeys.all, 'list'] as const,
  list: (params?: InvitationListParams) => [...invitationKeys.lists(), params] as const,
  details: () => [...invitationKeys.all, 'detail'] as const,
  detail: (id: number) => [...invitationKeys.details(), id] as const,
  stats: () => [...invitationKeys.all, 'stats'] as const,
  auditLogs: (id: number) => [...invitationKeys.all, 'audit', id] as const,
};

/**
 * Hook: List invitations with filters
 */
export function useInvitations(params?: InvitationListParams) {
  return useQuery({
    queryKey: invitationKeys.list(params),
    queryFn: () => invitationApi.list(params),
    staleTime: 30000, // 30 seconds
  });
}

/**
 * Hook: Get invitation statistics
 */
export function useInvitationStats() {
  return useQuery({
    queryKey: invitationKeys.stats(),
    queryFn: () => invitationApi.stats(),
    staleTime: 60000, // 1 minute
    select: (data) => ({
      total: data.total,
      sent: data.total, // Assuming 'total' from backend represents 'total sent'
      pending_review: data.by_status.in_progress || 0,
      approved: data.by_status.approved || 0,
      rejected: data.by_status.rejected || 0,
    }),
  });
}

/**
 * Hook: Get single invitation details
 */
export function useInvitation(id: number) {
  return useQuery({
    queryKey: invitationKeys.detail(id),
    queryFn: () => invitationApi.getById(id),
    enabled: !!id,
  });
}

/**
 * Hook: Get invitation audit logs
 */
export function useInvitationAuditLogs(id: number) {
  return useQuery({
    queryKey: invitationKeys.auditLogs(id),
    queryFn: () => invitationApi.getAuditLogs(id),
    enabled: !!id,
  });
}

/**
 * Hook: Create invitation
 */
export function useCreateInvitation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: InvitationCreateRequest) => invitationApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: invitationKeys.lists() });
      queryClient.invalidateQueries({ queryKey: invitationKeys.stats() });
      toast.success('Invitation sent successfully');
    },
    onError: (error: unknown) => {
      const axiosError = error as AxiosError;
      if (axiosError?.response?.status === 409) {
        toast.error('Duplicate Invitation', {
          description: 'An active invitation for this email address already exists.',
        });
      } else {
        toast.error('Failed to send invitation', {
          description: getErrorMessage(error),
        });
      }
    },
  });
}

/**
 * Hook: Update invitation
 */
export function useUpdateInvitation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: InvitationUpdateRequest }) =>
      invitationApi.update(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: invitationKeys.detail(variables.id) });
      queryClient.invalidateQueries({ queryKey: invitationKeys.lists() });
      toast.success('Invitation updated successfully');
    },
    onError: (error: unknown) => {
      toast.error(getErrorMessage(error));
    },
  });
}

/**
 * Hook: Resend invitation
 */
export function useResendInvitation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) => invitationApi.resend(id),
    onSuccess: (data, id) => {
      queryClient.invalidateQueries({ queryKey: invitationKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: invitationKeys.lists() });
      queryClient.invalidateQueries({ queryKey: invitationKeys.auditLogs(id) });
      toast.success(data.message || 'Invitation resent successfully');
    },
    onError: (error: unknown) => {
      toast.error(getErrorMessage(error));
    },
  });
}

/**
 * Hook: Cancel invitation
 */
export function useCancelInvitation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) => invitationApi.cancel(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: invitationKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: invitationKeys.lists() });
      queryClient.invalidateQueries({ queryKey: invitationKeys.stats() });
      queryClient.invalidateQueries({ queryKey: invitationKeys.auditLogs(id) });
      toast.success('Invitation cancelled successfully');
    },
    onError: (error: unknown) => {
      toast.error(getErrorMessage(error));
    },
  });
}

/**
 * Hook: Approve invitation
 */
export function useApproveInvitation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data?: { notes?: string; edited_data?: Record<string, any> } }) =>
      invitationApi.approve(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: invitationKeys.detail(variables.id) });
      queryClient.invalidateQueries({ queryKey: invitationKeys.lists() });
      queryClient.invalidateQueries({ queryKey: invitationKeys.stats() });
      queryClient.invalidateQueries({ queryKey: invitationKeys.auditLogs(variables.id) });
      toast.success('Invitation approved successfully');
    },
    onError: (error: unknown) => {
      toast.error(getErrorMessage(error));
    },
  });
}

/**
 * Hook: Reject invitation
 */
export function useRejectInvitation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: { rejection_reason: string; notes?: string } }) =>
      invitationApi.reject(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: invitationKeys.detail(variables.id) });
      queryClient.invalidateQueries({ queryKey: invitationKeys.lists() });
      queryClient.invalidateQueries({ queryKey: invitationKeys.stats() });
      queryClient.invalidateQueries({ queryKey: invitationKeys.auditLogs(variables.id) });
      toast.success('Invitation rejected');
    },
    onError: (error: unknown) => {
      toast.error(getErrorMessage(error));
    },
  });
}

/**
 * Hook: Bulk create invitations
 */
export function useBulkCreateInvitations() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: BulkInvitationRequest) => invitationApi.bulkCreate(data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: invitationKeys.lists() });
      queryClient.invalidateQueries({ queryKey: invitationKeys.stats() });
      
      if (data.failed > 0) {
        toast.warning(
          `${data.created} invitations sent, ${data.failed} failed`,
          {
            description: 'Check the details for failed invitations',
          }
        );
      } else {
        toast.success(`${data.created} invitations sent successfully`);
      }
    },
    onError: (error: unknown) => {
      toast.error(getErrorMessage(error));
    },
  });
}
