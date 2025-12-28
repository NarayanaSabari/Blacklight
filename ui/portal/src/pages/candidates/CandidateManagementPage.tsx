/**
 * Unified Candidate Management Page - Sidebar Navigation Layout
 * HR-focused workflow with persistent sidebar and action dashboard
 */

import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  UserPlus,
  ClipboardList,
  Mail,
  Users,
} from 'lucide-react';
import { invitationApi } from '@/lib/api/invitationApi';
import { onboardingApi } from '@/lib/onboardingApi';
import { CandidatesPage } from './CandidatesPage';
import { OnboardCandidatesPage } from './OnboardCandidatesPage';
import InvitationsPage from '../invitations/InvitationsPage';
import { cn } from '@/lib/utils';

type SectionType = 'all-candidates' | 'review-submissions' | 'ready-to-assign' | 'email-invitations';

export function CandidateManagementPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const tab = searchParams.get('tab') || 'all-candidates';
  const [activeSection, setActiveSection] = useState<SectionType>(tab as SectionType);

  // Fetch real-time stats
  const { data: submittedInvitations } = useQuery({
    queryKey: ['submitted-invitations-count'],
    queryFn: () => invitationApi.getSubmittedInvitations({ page: 1, per_page: 1 }),
    refetchInterval: 30000,
  });

  const { data: statsData } = useQuery({
    queryKey: ['onboarding-stats'],
    queryFn: () => onboardingApi.getOnboardingStats(),
    refetchInterval: 30000,
  });

  // Sync URL with active section
  useEffect(() => {
    if (tab !== activeSection) {
      setActiveSection(tab as SectionType);
    }
  }, [tab, activeSection]);

  const handleSectionChange = (value: SectionType) => {
    setActiveSection(value);
    setSearchParams({ tab: value });
  };

  // Calculate stats
  const needsReviewCount = submittedInvitations?.total || 0;
  const readyToAssignCount = statsData?.approved || 0;

  // Sidebar navigation items
  const navItems = [
    {
      id: 'all-candidates' as SectionType,
      label: 'All Candidates',
      icon: Users,
      description: 'View all candidates',
    },
    {
      id: 'review-submissions' as SectionType,
      label: 'Review Submissions',
      icon: ClipboardList,
      badge: needsReviewCount,
      badgeVariant: 'destructive' as const,
      description: 'Review and approve candidates',
    },
    {
      id: 'ready-to-assign' as SectionType,
      label: 'Ready to Assign',
      icon: UserPlus,
      badge: readyToAssignCount,
      description: 'Assign candidates to recruiters',
    },
    {
      id: 'email-invitations' as SectionType,
      label: 'Email Invitations',
      icon: Mail,
      description: 'Track and manage invites',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Action Bar */}
      <div className="flex justify-end">
        <Button
          onClick={() => navigate('/candidates/new')}
          className="gap-2 border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:shadow-[3px_3px_0px_0px_rgba(0,0,0,1)]"
        >
          <UserPlus className="h-4 w-4" />
          Add Candidate
        </Button>
      </div>

      {/* Sidebar Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-6">
        {/* Left Sidebar - Navigation */}
        <aside className="space-y-2">
          <Card className="border-2 border-black shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] sticky top-6">
            <CardHeader className="bg-slate-50 pb-4">
              <CardTitle className="text-lg font-bold">Navigation</CardTitle>
              <CardDescription className="text-sm">Select workflow section</CardDescription>
            </CardHeader>
            <CardContent className="p-2">
              <nav className="space-y-1">
                {navItems.map((item) => {
                  const Icon = item.icon;
                  const isActive = activeSection === item.id;

                  return (
                    <button
                      key={item.id}
                      onClick={() => handleSectionChange(item.id)}
                      className={cn(
                        'w-full flex items-center gap-3 p-3 rounded border-2 transition-all text-left',
                        isActive
                          ? 'bg-primary text-primary-foreground border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]'
                          : 'bg-white border-slate-200 hover:border-black hover:shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]'
                      )}
                    >
                      <Icon className={cn('h-5 w-5 flex-shrink-0', isActive ? 'text-primary-foreground' : 'text-slate-600')} />
                      <div className="flex-1 min-w-0">
                        <div className={cn('font-semibold text-sm', isActive ? 'text-primary-foreground' : 'text-slate-900')}>
                          {item.label}
                        </div>
                        <div className={cn('text-xs truncate', isActive ? 'text-primary-foreground/80' : 'text-slate-500')}>
                          {item.description}
                        </div>
                      </div>
                      {item.badge !== undefined && item.badge > 0 && (
                        <Badge
                          variant={item.badgeVariant || 'secondary'}
                          className="border-2 border-black shadow-[1px_1px_0px_0px_rgba(0,0,0,1)] font-bold"
                        >
                          {item.badge}
                        </Badge>
                      )}
                    </button>
                  );
                })}
              </nav>
            </CardContent>
          </Card>
        </aside>

        {/* Main Dashboard Area */}
        <main className="space-y-6">
          {/* Dynamic Content Area */}
          <div>
            {activeSection === 'all-candidates' && <CandidatesPage />}
            {activeSection === 'review-submissions' && <OnboardCandidatesPage defaultTab="review-submissions" hideTabNavigation={true} />}
            {activeSection === 'ready-to-assign' && <OnboardCandidatesPage defaultTab="ready-to-assign" hideTabNavigation={true} />}
            {activeSection === 'email-invitations' && <InvitationsPage />}
          </div>
        </main>
      </div>
    </div>
  );
}
