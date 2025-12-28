/**
 * Unified Candidate Management Page - Tab Navigation Layout
 * HR-focused workflow with horizontal tabs and quick stats
 * All tabs share the same consistent layout pattern
 */

import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  UserPlus,
  ClipboardList,
  Mail,
  Users,
  CheckCircle,
  Clock,
} from 'lucide-react';
import { invitationApi } from '@/lib/api/invitationApi';
import { onboardingApi } from '@/lib/onboardingApi';
import { AllCandidatesTab } from './tabs/AllCandidatesTab';
import { ReviewSubmissionsTab } from './tabs/ReviewSubmissionsTab';
import { ReadyToAssignTab } from './tabs/ReadyToAssignTab';
import { EmailInvitationsTab } from './tabs/EmailInvitationsTab';

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

  const handleSectionChange = (value: string) => {
    setActiveSection(value as SectionType);
    setSearchParams({ tab: value });
  };

  // Calculate stats
  const needsReviewCount = submittedInvitations?.total || 0;
  const readyToAssignCount = statsData?.approved || 0;
  const pendingInvites = statsData?.pending_onboarding || 0;

  return (
    <div className="space-y-6">
      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card 
          className={`cursor-pointer hover:shadow-md transition-all ${activeSection === 'all-candidates' ? 'ring-2 ring-primary' : ''}`} 
          onClick={() => handleSectionChange('all-candidates')}
        >
          <CardContent className="pt-4 pb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-blue-100">
                <Users className="h-5 w-5 text-blue-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{statsData?.total || 0}</p>
                <p className="text-xs text-muted-foreground">All Candidates</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card 
          className={`cursor-pointer hover:shadow-md transition-all ${activeSection === 'review-submissions' ? 'ring-2 ring-primary' : ''}`}
          onClick={() => handleSectionChange('review-submissions')}
        >
          <CardContent className="pt-4 pb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-orange-100">
                <ClipboardList className="h-5 w-5 text-orange-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{needsReviewCount}</p>
                <p className="text-xs text-muted-foreground">Needs Review</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card 
          className={`cursor-pointer hover:shadow-md transition-all ${activeSection === 'ready-to-assign' ? 'ring-2 ring-primary' : ''}`}
          onClick={() => handleSectionChange('ready-to-assign')}
        >
          <CardContent className="pt-4 pb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-green-100">
                <CheckCircle className="h-5 w-5 text-green-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{readyToAssignCount}</p>
                <p className="text-xs text-muted-foreground">Ready to Assign</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card 
          className={`cursor-pointer hover:shadow-md transition-all ${activeSection === 'email-invitations' ? 'ring-2 ring-primary' : ''}`}
          onClick={() => handleSectionChange('email-invitations')}
        >
          <CardContent className="pt-4 pb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-purple-100">
                <Clock className="h-5 w-5 text-purple-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{pendingInvites}</p>
                <p className="text-xs text-muted-foreground">Pending Invites</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tab Navigation */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <Tabs value={activeSection} onValueChange={handleSectionChange} className="w-full md:w-auto">
          <TabsList className="grid w-full md:w-auto grid-cols-4 h-auto p-1">
            <TabsTrigger value="all-candidates" className="flex items-center gap-2 px-4 py-2">
              <Users className="h-4 w-4" />
              <span className="hidden sm:inline">All Candidates</span>
              <span className="sm:hidden">All</span>
            </TabsTrigger>
            <TabsTrigger value="review-submissions" className="flex items-center gap-2 px-4 py-2">
              <ClipboardList className="h-4 w-4" />
              <span className="hidden sm:inline">Review</span>
              <span className="sm:hidden">Review</span>
              {needsReviewCount > 0 && (
                <Badge variant="destructive" className="ml-1 h-5 px-1.5 text-xs">
                  {needsReviewCount}
                </Badge>
              )}
            </TabsTrigger>
            <TabsTrigger value="ready-to-assign" className="flex items-center gap-2 px-4 py-2">
              <UserPlus className="h-4 w-4" />
              <span className="hidden sm:inline">Assign</span>
              <span className="sm:hidden">Assign</span>
              {readyToAssignCount > 0 && (
                <Badge variant="secondary" className="ml-1 h-5 px-1.5 text-xs bg-green-100 text-green-700">
                  {readyToAssignCount}
                </Badge>
              )}
            </TabsTrigger>
            <TabsTrigger value="email-invitations" className="flex items-center gap-2 px-4 py-2">
              <Mail className="h-4 w-4" />
              <span className="hidden sm:inline">Invitations</span>
              <span className="sm:hidden">Invite</span>
            </TabsTrigger>
          </TabsList>
        </Tabs>

        <Button onClick={() => navigate('/candidates/new')} className="gap-2">
          <UserPlus className="h-4 w-4" />
          Add Candidate
        </Button>
      </div>

      {/* Content Area - All tabs use same layout pattern */}
      <Card>
        <CardContent className="p-6">
          {activeSection === 'all-candidates' && <AllCandidatesTab />}
          {activeSection === 'review-submissions' && <ReviewSubmissionsTab />}
          {activeSection === 'ready-to-assign' && <ReadyToAssignTab />}
          {activeSection === 'email-invitations' && <EmailInvitationsTab />}
        </CardContent>
      </Card>
    </div>
  );
}
