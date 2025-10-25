/**
 * Hook for updating PM Admin profile
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';

interface UpdateProfileData {
  first_name: string;
  last_name: string;
  email: string;
  phone?: string;
}

export function useUpdatePMAdminProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: UpdateProfileData) => {
      const response = await apiClient.put('/api/pm-admin/profile', data);
      return response.data;
    },
    onSuccess: () => {
      // Invalidate current admin query to refetch updated data
      queryClient.invalidateQueries({ queryKey: ['pm-admin', 'current'] });
      toast.success('Profile updated successfully');
    },
    onError: () => {
      toast.error('Failed to update profile');
    },
  });
}
