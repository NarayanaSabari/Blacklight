/**
 * Invitations Page
 * Main page for listing and managing candidate invitations
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { InvitationList } from '@/components/invitations/InvitationList';
import { InvitationForm } from '@/components/invitations/InvitationForm';
import { useInvitationStats } from '@/hooks/useInvitations';
import { Card, CardContent } from '@/components/ui/card';
import { Mail, Clock, CheckCircle2, XCircle } from 'lucide-react';

export default function InvitationsPage() {
  const navigate = useNavigate();
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const { data: stats } = useInvitationStats();

  const handleViewDetails = (id: number) => {
    navigate(`/invitations/${id}`);
  };

  return (
    <div className="space-y-6 p-6">
      {/* Stats Cards */}
      {stats && (
        <div className="grid gap-4 md:grid-cols-4">
          <StatsCard
            title="Total Sent"
            value={stats.by_status.invited}
            icon={Mail}
            iconColor="text-blue-600"
          />
          <StatsCard
            title="Pending Review"
            value={stats.by_status.submitted}
            icon={Clock}
            iconColor="text-yellow-600"
          />
          <StatsCard
            title="Approved"
            value={stats.by_status.approved}
            icon={CheckCircle2}
            iconColor="text-green-600"
          />
          <StatsCard
            title="Rejected"
            value={stats.by_status.rejected}
            icon={XCircle}
            iconColor="text-red-600"
          />
        </div>
      )}

      {/* Invitation List */}
      <InvitationList
        onViewDetails={handleViewDetails}
        onCreateNew={() => setShowCreateDialog(true)}
      />

      {/* Create Dialog */}
      <InvitationForm
        open={showCreateDialog}
        onOpenChange={setShowCreateDialog}
        onSuccess={() => {
          setShowCreateDialog(false);
        }}
      />
    </div>
  );
}

function StatsCard({
  title,
  value,
  icon: Icon,
  iconColor,
}: {
  title: string;
  value: number;
  icon: typeof Mail;
  iconColor: string;
}) {
  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground">{title}</p>
            <p className="text-2xl font-bold">{value}</p>
          </div>
          <div className={`rounded-full bg-muted p-3 ${iconColor}`}>
            <Icon className="h-5 w-5" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
