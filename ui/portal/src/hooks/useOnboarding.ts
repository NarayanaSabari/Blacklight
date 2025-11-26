/**
 * React Query Hooks for Candidate Onboarding
 * Custom hooks for public onboarding flow
 */

import { useMutation, useQuery } from '@tanstack/react-query';
import { onboardingApi } from '@/lib/api/invitationApi';
import { toast } from 'sonner';
import type { OnboardingSubmissionRequest } from '@/types';

// Query keys for cache management
export const onboardingKeys = {
  all: ['onboarding'] as const,
  verify: (token: string) => [...onboardingKeys.all, 'verify', token] as const,
};

/**
 * Hook: Verify invitation token
 */
export function useVerifyInvitation(token: string) {
  return useQuery({
    queryKey: onboardingKeys.verify(token),
    queryFn: () => onboardingApi.verify(token),
    enabled: !!token,
    retry: false, // Don't retry if token is invalid
    staleTime: Infinity, // Token validity doesn't change
  });
}

/**
 * Hook: Submit onboarding data
 */
export function useSubmitOnboarding() {
  return useMutation({
    mutationFn: ({ token, data }: { token: string; data: OnboardingSubmissionRequest }) =>
      onboardingApi.submit(token, data),
    onSuccess: () => {
      toast.success('Application submitted successfully!', {
        description: 'We will review your application and get back to you soon.',
      });
    },
    onError: (error: Error) => {
      toast.error('Failed to submit application', {
        description: error.message,
      });
    },
  });
}

/**
 * Hook: Upload document during onboarding
 */
export function useUploadOnboardingDocument() {
  return useMutation({
    mutationFn: ({
      token,
      file,
      documentType,
    }: {
      token: string;
      file: File;
      documentType: string;
    }) => onboardingApi.uploadDocument(token, file, documentType),
    onSuccess: (data) => {
      const fileName = data.document?.file_name ?? 'Document';
      toast.success('Document uploaded successfully', {
        description: `${fileName} uploaded`,
      });
    },
    onError: (error: Error) => {
      toast.error('Failed to upload document', {
        description: error.message,
      });
    },
  });
}

/**
 * Hook: Upload multiple documents
 * Handles batch uploads with progress tracking
 */
export function useUploadOnboardingDocuments() {
  const uploadMutation = useUploadOnboardingDocument();

  const uploadMultiple = async (
    token: string,
    files: Array<{ file: File; documentType: string }>
  ) => {
    const results = [];
    
    for (const { file, documentType } of files) {
      try {
        const result = await uploadMutation.mutateAsync({ token, file, documentType });
        results.push({ success: true, result, file });
      } catch (error) {
        results.push({ success: false, error, file });
      }
    }

    const successCount = results.filter((r) => r.success).length;
    const failCount = results.filter((r) => !r.success).length;

    if (failCount === 0) {
      toast.success(`All ${successCount} documents uploaded successfully`);
    } else if (successCount > 0) {
      toast.warning(`${successCount} uploaded, ${failCount} failed`);
    } else {
      toast.error('All document uploads failed');
    }

    return results;
  };

  return {
    uploadMultiple,
    isUploading: uploadMutation.isPending,
  };
}
