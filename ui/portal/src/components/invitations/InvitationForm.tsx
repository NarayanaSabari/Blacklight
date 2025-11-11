/**
 * InvitationForm Component
 * Form for creating/editing candidate invitations
 */

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Loader2 } from 'lucide-react';
import { useCreateInvitation, useUpdateInvitation } from '@/hooks/useInvitations';
import type { CandidateInvitation } from '@/types';

const invitationFormSchema = z.object({
  email: z.string().email('Invalid email address'),
  first_name: z.string().min(1, 'First name is required'),
  last_name: z.string().optional(),
  position: z.string().optional(),
  recruiter_notes: z.string().optional(),
  expires_in_days: z.number().min(1).max(90),
});

type InvitationFormValues = z.infer<typeof invitationFormSchema>;

interface InvitationFormProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  invitation?: CandidateInvitation;
  onSuccess?: () => void;
}

export function InvitationForm({
  open,
  onOpenChange,
  invitation,
  onSuccess,
}: InvitationFormProps) {
  const isEdit = !!invitation;
  const createMutation = useCreateInvitation();
  const updateMutation = useUpdateInvitation();

  const form = useForm<InvitationFormValues>({
    resolver: zodResolver(invitationFormSchema),
    defaultValues: {
      email: invitation?.email || '',
      first_name: invitation?.first_name || '',
      last_name: invitation?.last_name || '',
      position: invitation?.position || '',
      recruiter_notes: invitation?.recruiter_notes || '',
      expires_in_days: 7,
    },
  });

  const onSubmit = async (values: InvitationFormValues) => {
    try {
      const { expires_in_days, ...invitationData } = values;
      const data = {
        ...invitationData,
        expiry_hours: expires_in_days * 24, // Convert days to hours
      };

      if (isEdit) {
        // Note: The backend doesn't support updating all these fields post-creation.
        // This is a simplified example. A real implementation would be more specific.
        await updateMutation.mutateAsync({
          id: invitation.id,
          data: {
            first_name: data.first_name,
            last_name: data.last_name,
            position: data.position,
            recruiter_notes: data.recruiter_notes,
          },
        });
      } else {
        await createMutation.mutateAsync(data);
      }

      form.reset();
      onOpenChange(false);
      onSuccess?.();
    } catch {
      // Error is handled by the mutation's onError callback
    }
  };

  const isPending = createMutation.isPending || updateMutation.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>
            {isEdit ? 'Edit Invitation' : 'Send Candidate Invitation'}
          </DialogTitle>
          <DialogDescription>
            {isEdit
              ? 'Update invitation details'
              : 'Send an invitation to a candidate to complete their onboarding'}
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="email"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Email *</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="candidate@example.com"
                      type="email"
                      {...field}
                      disabled={isPending || isEdit}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="grid gap-4 sm:grid-cols-2">
              <FormField
                control={form.control}
                name="first_name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>First Name *</FormLabel>
                    <FormControl>
                      <Input placeholder="John" {...field} disabled={isPending} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="last_name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Last Name</FormLabel>
                    <FormControl>
                      <Input placeholder="Doe" {...field} disabled={isPending} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="position"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Position</FormLabel>
                  <FormControl>
                    <Input placeholder="e.g., Senior Software Engineer" {...field} disabled={isPending} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {!isEdit && (
              <FormField
                control={form.control}
                name="expires_in_days"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Expires In (Days)</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        min={1}
                        max={90}
                        {...field}
                        onChange={(e) => field.onChange(parseInt(e.target.value))}
                        disabled={isPending}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            )}

            <FormField
              control={form.control}
              name="recruiter_notes"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Recruiter Notes</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="Internal notes for the hiring team..."
                      rows={3}
                      {...field}
                      disabled={isPending}
                    />
                  </FormControl>
                  <FormDescription>
                    These notes are for internal use and not visible to the candidate.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={isPending}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isPending}>
                {isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {isEdit ? 'Update' : 'Send Invitation'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
