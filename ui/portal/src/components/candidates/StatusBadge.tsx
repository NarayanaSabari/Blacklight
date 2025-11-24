/**
 * Status Badge Component
 * Displays candidate status with appropriate colors
 */

import { Badge } from '@/components/ui/badge';
import type { CandidateStatus } from '@/types/candidate';

interface StatusBadgeProps {
  status: CandidateStatus;
  className?: string;
}

const statusConfig: Record<CandidateStatus, { label: string; variant: string; className: string }> = {
  processing: {
    label: 'Processing',
    variant: 'secondary',
    className: 'bg-yellow-100 text-yellow-800 hover:bg-yellow-100 border-yellow-200',
  },
  pending_review: {
    label: 'Pending Review',
    variant: 'secondary',
    className: 'bg-blue-100 text-blue-800 hover:bg-blue-100 border-blue-200',
  },
  new: {
    label: 'New',
    variant: 'secondary',
    className: 'bg-slate-100 text-slate-800 hover:bg-slate-100 border-slate-200',
  },
  onboarded: {
    label: 'Onboarded',
    variant: 'secondary',
    className: 'bg-green-100 text-green-800 hover:bg-green-100 border-green-200',
  },
  ready_for_assignment: {
    label: 'Ready for Assignment',
    variant: 'secondary',
    className: 'bg-purple-100 text-purple-800 hover:bg-purple-100 border-purple-200',
  },
  screening: {
    label: 'Screening',
    variant: 'secondary',
    className: 'bg-blue-100 text-blue-700 hover:bg-blue-100 border-blue-200',
  },
  interviewed: {
    label: 'Interviewed',
    variant: 'secondary',
    className: 'bg-indigo-100 text-indigo-800 hover:bg-indigo-100 border-indigo-200',
  },
  offered: {
    label: 'Offered',
    variant: 'secondary',
    className: 'bg-green-100 text-green-700 hover:bg-green-100 border-green-200',
  },
  hired: {
    label: 'Hired',
    variant: 'secondary',
    className: 'bg-emerald-100 text-emerald-800 hover:bg-emerald-100 border-emerald-200',
  },
  rejected: {
    label: 'Rejected',
    variant: 'destructive',
    className: 'bg-red-100 text-red-800 hover:bg-red-100 border-red-200',
  },
  withdrawn: {
    label: 'Withdrawn',
    variant: 'secondary',
    className: 'bg-gray-100 text-gray-700 hover:bg-gray-100 border-gray-200',
  },
};

export function StatusBadge({ status, className = '' }: StatusBadgeProps) {
  const config = statusConfig[status] || statusConfig.new;

  return (
    <Badge variant={config.variant as any} className={`${config.className} ${className}`}>
      {config.label}
    </Badge>
  );
}
