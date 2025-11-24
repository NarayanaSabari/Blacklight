/**
 * Status Timeline Component
 * Visual timeline showing candidate onboarding progress
 */

import { CheckCircle2, Circle, Clock, Loader2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { CandidateStatus } from '@/types/candidate';

interface StatusTimelineProps {
  currentStatus: CandidateStatus;
  timestamps?: {
    created_at?: string;
    resume_uploaded_at?: string;
    resume_parsed_at?: string;
    approved_at?: string;
  };
  className?: string;
}

export function StatusTimeline({ currentStatus, timestamps, className = '' }: StatusTimelineProps) {
  // Define the onboarding workflow steps
  const getStepIcon = (status: 'complete' | 'current' | 'pending') => {
    switch (status) {
      case 'complete':
        return <CheckCircle2 className="h-5 w-5 text-green-600" />;
      case 'current':
        return <Loader2 className="h-5 w-5 text-blue-600 animate-spin" />;
      case 'pending':
        return <Circle className="h-5 w-5 text-slate-300" />;
    }
  };

  const getStepStatus = (stepStatuses: CandidateStatus[]): 'complete' | 'current' | 'pending' => {
    if (stepStatuses.includes(currentStatus)) {
      return 'current';
    }
    
    // Check if current status comes after this step
    const allStatuses: CandidateStatus[] = ['processing', 'pending_review', 'onboarded', 'ready_for_assignment'];
    const currentIndex = allStatuses.indexOf(currentStatus);
    const stepMaxIndex = Math.max(...stepStatuses.map(s => allStatuses.indexOf(s)));
    
    if (currentIndex > stepMaxIndex) {
      return 'complete';
    }
    
    return 'pending';
  };

  const steps = [
    {
      id: 'upload',
      label: 'Resume Uploaded',
      statuses: ['processing'],
      icon: getStepStatus(['processing'])
    },
    {
      id: 'parsing',
      label: 'AI Parsing',
      statuses: ['processing'],
      icon: getStepStatus(['processing'])
    },
    {
      id: 'review',
      label: 'HR Review',
      statuses: ['pending_review'],
      icon: getStepStatus(['pending_review'])
    },
    {
      id: 'approved',
      label: 'Approved',
      statuses: ['onboarded'],
      icon: getStepStatus(['onboarded'])
    },
    {
      id: 'ready',
      label: 'Ready for Assignment',
      statuses: ['ready_for_assignment'],
      icon: getStepStatus(['ready_for_assignment'])
    }
  ];

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <Clock className="h-4 w-4" />
          Onboarding Progress
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {steps.map((step, index) => {
            const status = step.icon;
            const isLast = index === steps.length - 1;
            
            return (
              <div key={step.id} className="relative">
                <div className="flex items-start gap-3">
                  {/* Icon */}
                  <div className="flex-shrink-0 relative z-10">
                    {getStepIcon(status)}
                  </div>
                  
                  {/* Content */}
                  <div className="flex-1 min-w-0 pt-0.5">
                    <p
                      className={`text-sm font-medium ${
                        status === 'complete'
                          ? 'text-green-900'
                          : status === 'current'
                          ? 'text-blue-900'
                          : 'text-slate-400'
                      }`}
                    >
                      {step.label}
                    </p>
                    {status === 'current' && (
                      <p className="text-xs text-slate-600 mt-0.5">In progress...</p>
                    )}
                    {status === 'complete' && timestamps?.[step.id as keyof typeof timestamps] && (
                      <p className="text-xs text-slate-500 mt-0.5">
                        {new Date(timestamps[step.id as keyof typeof timestamps]!).toLocaleString()}
                      </p>
                    )}
                  </div>
                </div>
                
                {/* Connector Line */}
                {!isLast && (
                  <div
                    className={`absolute left-2.5 top-6 w-0.5 h-8 -ml-px ${
                      status === 'complete' ? 'bg-green-300' : 'bg-slate-200'
                    }`}
                  />
                )}
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
