/**
 * Unified Candidate Management Page
 * HR-focused workflow: Add candidates, manage onboarding, and track invitations
 */

import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { 
  UserPlus, 
  ClipboardList, 
  Mail, 
  Upload, 
  FileText, 
  Users,
  CheckCircle2,
  Inbox
} from 'lucide-react';
import { invitationApi } from '@/lib/api/invitationApi';
import { onboardingApi } from '@/lib/onboardingApi';
import { Skeleton } from '@/components/ui/skeleton';
import { CandidatesPage } from './CandidatesPage';
import { OnboardCandidatesPage } from './OnboardCandidatesPage';
import InvitationsPage from './invitations/InvitationsPage';

export function CandidateManagementPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const tab = searchParams.get('tab') || 'onboarding';
  const [activeTab, setActiveTab] = useState<string>(tab);

  // Fetch real-time stats
  const { data: submittedInvitations, isLoading: loadingInvitations } = useQuery({
    queryKey: ['submitted-invitations-count'],
    queryFn: () => invitationApi.getSubmittedInvitations({ page: 1, per_page: 1 }),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  const { data: statsData, isLoading: loadingStats } = useQuery({
    queryKey: ['onboarding-stats'],
    queryFn: () => onboardingApi.getOnboardingStats(),
    refetchInterval: 30000,
  });

  // Sync URL with active tab
  useEffect(() => {
    if (tab !== activeTab) {
      setActiveTab(tab);
    }
  }, [tab, activeTab]);

  const handleTabChange = (value: string) => {
    setActiveTab(value);
    setSearchParams({ tab: value });
  };

  // Calculate stats
  const needsReviewCount = submittedInvitations?.total || 0;
  const readyToAssignCount = statsData?.pending_assignment || 0;
  const activePipelineCount = (
    (statsData?.assigned || 0) +
    (statsData?.pending_onboarding || 0) +
    (statsData?.onboarded || 0)
  );

  const isLoadingStats = loadingInvitations || loadingStats;

  return (
    <div className="space-y-6">
      {/* Page Header with Quick Actions */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">HR Candidate Management</h1>
          <p className="text-slate-600 mt-1">
            Manage recruitment workflow and candidate pipeline
          </p>
        </div>
        
        {/* Quick Action Buttons */}
        <div className="flex gap-3">
          <Button 
            variant="outline" 
            onClick={() => navigate('/candidates/new')}
            className="gap-2"
          >
            <Upload className="h-4 w-4" />
            Upload Resume
          </Button>
          <Button 
            onClick={() => navigate('/candidates/new')}
            className="gap-2"
          >
            <UserPlus className="h-4 w-4" />
            Add Candidate
          </Button>
        </div>
      </div>

      {/* Simplified Action-Oriented Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card 
          className="border-l-4 border-l-amber-500 cursor-pointer hover:shadow-md transition-shadow"
          onClick={() => handleTabChange('onboarding')}
        >
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardDescription className="flex items-center gap-2 text-sm font-medium">
                <Inbox className="h-5 w-5 text-amber-500" />
                Needs Review
              </CardDescription>
              <div className="text-xs text-amber-600 font-medium bg-amber-50 px-2 py-1 rounded">
                Action Required
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {isLoadingStats ? (
              <Skeleton className="h-10 w-16" />
            ) : (
              <CardTitle className="text-4xl text-amber-600">{needsReviewCount}</CardTitle>
            )}
            <p className="text-sm text-slate-600 mt-2">
              Candidate submissions awaiting approval
            </p>
          </CardContent>
        </Card>

        <Card 
          className="border-l-4 border-l-blue-500 cursor-pointer hover:shadow-md transition-shadow"
          onClick={() => handleTabChange('onboarding')}
        >
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardDescription className="flex items-center gap-2 text-sm font-medium">
                <CheckCircle2 className="h-5 w-5 text-blue-500" />
                Ready to Assign
              </CardDescription>
              <div className="text-xs text-blue-600 font-medium bg-blue-50 px-2 py-1 rounded">
                Next Step
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {isLoadingStats ? (
              <Skeleton className="h-10 w-16" />
            ) : (
              <CardTitle className="text-4xl text-blue-600">{readyToAssignCount}</CardTitle>
            )}
            <p className="text-sm text-slate-600 mt-2">
              Approved candidates awaiting assignment
            </p>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-green-500">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardDescription className="flex items-center gap-2 text-sm font-medium">
                <Users className="h-5 w-5 text-green-500" />
                Active Pipeline
              </CardDescription>
              <div className="text-xs text-green-600 font-medium bg-green-50 px-2 py-1 rounded">
                In Progress
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {isLoadingStats ? (
              <Skeleton className="h-10 w-16" />
            ) : (
              <CardTitle className="text-4xl text-green-600">{activePipelineCount}</CardTitle>
            )}
            <p className="text-sm text-slate-600 mt-2">
              Candidates currently being onboarded
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Workflow Tabs */}
      <Tabs value={activeTab} onValueChange={handleTabChange} className="w-full">
        <TabsList className="grid w-full grid-cols-3 mb-6 h-auto p-1">
          <TabsTrigger 
            value="onboarding" 
            className="gap-2 py-3 data-[state=active]:bg-blue-500 data-[state=active]:text-white"
          >
            <ClipboardList className="h-4 w-4" />
            <div className="text-left">
              <div className="font-semibold text-sm">Review Submissions</div>
              {!isLoadingStats && needsReviewCount > 0 && (
                <div className="text-xs opacity-80">({needsReviewCount} pending)</div>
              )}
            </div>
          </TabsTrigger>
          
          <TabsTrigger 
            value="invitations" 
            className="gap-2 py-3 data-[state=active]:bg-purple-500 data-[state=active]:text-white"
          >
            <Mail className="h-4 w-4" />
            <div className="text-left">
              <div className="font-semibold text-sm">Email Invitations</div>
              <div className="text-xs opacity-80">Track & manage invites</div>
            </div>
          </TabsTrigger>

          <TabsTrigger 
            value="candidates" 
            className="gap-2 py-3 data-[state=active]:bg-green-500 data-[state=active]:text-white"
          >
            <FileText className="h-4 w-4" />
            <div className="text-left">
              <div className="font-semibold text-sm">All Candidates</div>
              <div className="text-xs opacity-80">Complete database</div>
            </div>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="onboarding" className="space-y-4 mt-0">
          <OnboardCandidatesPage />
        </TabsContent>

        <TabsContent value="invitations" className="space-y-4 mt-0">
          <InvitationsPage />
        </TabsContent>

        <TabsContent value="candidates" className="space-y-4 mt-0">
          <CandidatesPage />
        </TabsContent>
      </Tabs>
    </div>
  );
}
