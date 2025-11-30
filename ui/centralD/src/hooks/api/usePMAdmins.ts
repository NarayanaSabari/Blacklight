/**
 * React Query hooks for PM Admin users
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import type { PMAdmin, PMAdminCreateRequest, PMAdminUpdateRequest } from '@/types';
import { toast } from 'sonner';

// Fetch all PM admins
export function usePMAdmins() {
  return useQuery({
    queryKey: ['pm-admins'],
    queryFn: async () => {
      const response = await apiClient.get<{ items: PMAdmin[]; total: number; page: number; per_page: number }>('/api/pm-admin/admins');
      return response.data.items;
    },
  });
}

// Create PM admin
export function useCreatePMAdmin() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: PMAdminCreateRequest) => {
      const response = await apiClient.post<PMAdmin>(
        '/api/pm-admin/admins',
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pm-admins'] });
      toast.success('Admin created successfully');
    },
    onError: (error: unknown) => {
      const message = (error as any).response?.data?.message || 'Failed to create admin';
      toast.error(message);
    },
  });
}

// Update PM admin
export function useUpdatePMAdmin(adminId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: PMAdminUpdateRequest) => {
      const response = await apiClient.patch<PMAdmin>(
        `/api/pm-admin/admins/${adminId}`,
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pm-admins'] });
      toast.success('Admin updated successfully');
    },
    onError: (error: unknown) => {
      const message = (error as any).response?.data?.message || 'Failed to update admin';
      toast.error(message);
    },
  });
}

// Delete PM admin
export function useDeletePMAdmin(adminId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const response = await apiClient.delete<{ message: string }>(
        `/api/pm-admin/admins/${adminId}`
      );
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['pm-admins'] });
      toast.success(data.message || 'Admin deleted successfully');
    },
    onError: (error: unknown) => {
      const message = (error as any).response?.data?.message || 'Failed to delete admin';
      toast.error(message);
    },
  });
}
