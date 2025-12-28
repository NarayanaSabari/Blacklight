/**
 * InvitationDetailsPage
 * Detailed view page for a single invitation
 */

import { useParams, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { InvitationDetails } from '@/components/invitations/InvitationDetails';
import { ArrowLeft } from 'lucide-react';

export default function InvitationDetailsPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const invitationId = id ? parseInt(id, 10) : 0;

  if (!invitationId) {
    return (
      <div className="p-6">
        <div className="text-center">
          <h2 className="text-lg font-semibold">Invalid invitation ID</h2>
          <Button onClick={() => navigate('/invitations')} className="mt-4">
            Back to Invitations
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => navigate('/email-invitations')}
        >
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold">Invitation Details</h1>
          <p className="text-sm text-muted-foreground">
            View and manage this invitation
          </p>
        </div>
      </div>

      <InvitationDetails
        invitationId={invitationId}
        onClose={() => navigate('/invitations')}
      />
    </div>
  );
}
