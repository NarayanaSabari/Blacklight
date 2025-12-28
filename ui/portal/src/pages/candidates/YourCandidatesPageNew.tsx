/**
 * Your Candidates Page - Hierarchical Team View
 * Drill-down interface to view team members and their assigned candidates
 */

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import {
  ArrowLeft,
  Users,
  ChevronRight,
  Search,
  Mail,
  Phone,
  Eye,
  UserCog,
} from 'lucide-react';
import { apiRequest } from '@/lib/api-client';
import type { CandidateInfo } from '@/types';

interface TeamMember {
  id: number;
  full_name: string;
  email: string;
  role_name: string;
  candidate_count: number;
  team_member_count: number;
  has_team_members: boolean;
}

const ONBOARDING_STATUS_COLORS: Record<string, string> = {
  PENDING_ASSIGNMENT: 'bg-gray-100 text-gray-800',
  ASSIGNED: 'bg-blue-100 text-blue-800',
  PENDING_ONBOARDING: 'bg-yellow-100 text-yellow-800',
  ONBOARDED: 'bg-purple-100 text-purple-800',
  APPROVED: 'bg-green-100 text-green-800',
  REJECTED: 'bg-red-100 text-red-800',
};

export function YourCandidatesPageNew() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedMemberId, setSelectedMemberId] = useState<number | null>(null);
  const [navigationStack, setNavigationStack] = useState<TeamMember[]>([]);
  
  // Current context - either logged in user or drilled-down member
  const currentContextId = navigationStack.length > 0 
    ? navigationStack[navigationStack.length - 1].id 
    : null;

  // Get team members for current context
  const {
    data: teamMembersData,
    isLoading: isLoadingTeam,
  } = useQuery({
    queryKey: ['team-members', currentContextId],
    queryFn: async () => {
      // If we have drilled down, get that member's team
      // Otherwise get current user's team
      const url = currentContextId 
        ? `/api/team/${currentContextId}/team-members`
        : '/api/team/my-team-members';
      
      return apiRequest.get<{ team_members: TeamMember[]; total: number }>(url);
    },
  });

  // Check if user has no team members (e.g., recruiter role)
  const hasNoTeamMembers = teamMembersData && teamMembersData.team_members.length === 0;

  // Get current user's own candidates (for recruiters with no team)
  const {
    data: ownCandidatesData,
    isLoading: isLoadingOwnCandidates,
  } = useQuery({
    queryKey: ['my-own-candidates'],
    queryFn: async () => {
      return apiRequest.get<{ candidates: CandidateInfo[]; total: number }>(
        '/api/candidates/assignments/my-candidates'
      );
    },
    enabled: hasNoTeamMembers, // Only fetch if user has no team members
  });

  // Get selected team member's candidates
  const {
    data: candidatesData,
    isLoading: isLoadingCandidates,
  } = useQuery({
    queryKey: ['team-member-candidates', selectedMemberId],
    queryFn: async () => {
      if (!selectedMemberId) return null;
      return apiRequest.get<{ candidates: CandidateInfo[]; total: number }>(
        `/api/team/members/${selectedMemberId}/candidates`
      );
    },
    enabled: !!selectedMemberId,
  });

  const currentTeamMembers = teamMembersData?.team_members || [];
  const currentCandidates = hasNoTeamMembers 
    ? (ownCandidatesData?.candidates || []) 
    : (candidatesData?.candidates || []);
  const currentMember = navigationStack[navigationStack.length - 1];

  // Filter team members by search
  const filteredTeamMembers = currentTeamMembers.filter((member) =>
    member.full_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    member.email.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Handle clicking a team member card
  const handleTeamMemberClick = async (member: TeamMember) => {
    if (member.has_team_members) {
      // Drill down - this member has team members, show them
      setNavigationStack([...navigationStack, member]);
      setSelectedMemberId(null);
      // Fetch this member's team (will be handled by refetching with new context)
    } else {
      // Show this member's candidates
      setSelectedMemberId(member.id);
    }
  };

  // Handle back navigation
  const handleBack = () => {
    const newStack = [...navigationStack];
    newStack.pop();
    setNavigationStack(newStack);
    setSelectedMemberId(null);
  };

  // Handle viewing candidate details
  const handleViewCandidate = (candidateId: number) => {
    navigate(`/candidates/${candidateId}`);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Your Candidates</h1>
          <p className="text-slate-600 mt-1">
            {hasNoTeamMembers 
              ? 'View and manage your assigned candidates' 
              : 'View team members and their assigned candidates'}
          </p>
        </div>
      </div>

      {/* If user has no team members, show only their candidates */}
      {hasNoTeamMembers ? (
        <Card>
          <div className="p-6 border-b">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-slate-900">Your Assigned Candidates</h3>
                <p className="text-sm text-slate-600 mt-1">
                  {currentCandidates.length} candidates assigned to you
                </p>
              </div>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                <Input
                  placeholder="Search candidates..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9 w-64"
                />
              </div>
            </div>
          </div>
          
          <div className="p-6 grid grid-cols-1 lg:grid-cols-2 gap-4">
            {isLoadingOwnCandidates ? (
              <>
                {[1, 2, 3, 4].map((i) => (
                  <Skeleton key={i} className="h-40 w-full" />
                ))}
              </>
            ) : currentCandidates.length === 0 ? (
              <div className="col-span-2 flex flex-col items-center justify-center py-16 text-center">
                <div className="p-4 rounded-full bg-slate-100 mb-4">
                  <UserCog className="h-12 w-12 text-slate-400" />
                </div>
                <h3 className="text-lg font-semibold text-slate-900 mb-2">No candidates assigned</h3>
                <p className="text-slate-600 max-w-sm">
                  You don't have any candidates assigned to you yet
                </p>
              </div>
            ) : (
              currentCandidates.map((candidate) => (
                <Card
                  key={candidate.id}
                  className="hover:shadow-lg transition-all hover:border-primary/50 group cursor-pointer"
                  onClick={() => handleViewCandidate(candidate.id)}
                >
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-start justify-between mb-3">
                          <div>
                            <h4 className="font-semibold text-slate-900 text-lg group-hover:text-primary transition-colors">
                              {candidate.first_name} {candidate.last_name}
                            </h4>
                            <div className="flex items-center gap-2 mt-1">
                              <Badge
                                className={ONBOARDING_STATUS_COLORS[candidate.onboarding_status || 'PENDING_ASSIGNMENT']}
                              >
                                {(candidate.onboarding_status || 'PENDING_ASSIGNMENT').replace(/_/g, ' ')}
                              </Badge>
                            </div>
                          </div>
                        </div>

                        <div className="space-y-2 text-sm text-slate-600">
                          <div className="flex items-center gap-2">
                            <Mail className="h-4 w-4" />
                            <span>{candidate.email}</span>
                          </div>
                          {candidate.phone && (
                            <div className="flex items-center gap-2">
                              <Phone className="h-4 w-4" />
                              <span>{candidate.phone}</span>
                            </div>
                          )}
                        </div>
                      </div>

                      <Button
                        variant="outline"
                        size="sm"
                        onClick={(e) => { e.stopPropagation(); handleViewCandidate(candidate.id); }}
                        className="gap-2"
                      >
                        <Eye className="h-4 w-4" />
                        View
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </div>
        </Card>
      ) : (
        <>
          {/* Breadcrumb Navigation */}
          {navigationStack.length > 0 && (
            <div className="flex items-center gap-2 text-sm bg-slate-50 rounded-lg px-4 py-2">
              <button
                onClick={() => {
                  setNavigationStack([]);
                  setSelectedMemberId(null);
                }}
                className="hover:text-primary font-medium"
              >
                Home
              </button>
              {navigationStack.map((member, index) => (
                <div key={member.id} className="flex items-center gap-2">
                  <ChevronRight className="h-4 w-4 text-slate-400" />
                  <button
                    onClick={() => {
                      setNavigationStack(navigationStack.slice(0, index + 1));
                      setSelectedMemberId(null);
                    }}
                    className="hover:text-primary font-medium"
                  >
                    {member.full_name}
                  </button>
                </div>
              ))}
            </div>
          )}

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Column 1: Team Members */}
        <Card className="h-[calc(100vh-14rem)] flex flex-col">
          <div className="p-6 border-b space-y-4 flex-shrink-0">
            {/* Back Button & Current Context */}
            {currentMember ? (
              <div className="flex items-center justify-between">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleBack}
                  className="gap-2"
                >
                  <ArrowLeft className="h-4 w-4" />
                  Back
                </Button>
                <div className="flex items-center gap-3 p-2 px-4 bg-primary/10 rounded-lg">
                  <div className="h-8 w-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-semibold text-sm">
                    {currentMember.full_name.charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <div className="font-semibold text-slate-900 text-sm">
                      {currentMember.full_name}
                    </div>
                    <div className="text-xs text-slate-600">
                      {currentMember.role_name} • {currentMember.candidate_count} candidates
                    </div>
                  </div>
                </div>
              </div>
            ) : null}

            <div className="space-y-3">
              <h3 className="font-semibold text-slate-900">
                {currentMember ? `${currentMember.full_name}'s Team` : 'My Team'}
              </h3>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
                <Input
                  placeholder="Search team members..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
          </div>

          {/* Team Members List */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {isLoadingTeam ? (
              <>
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-20 w-full" />
                ))}
              </>
            ) : filteredTeamMembers.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center py-12">
                <div className="p-4 rounded-full bg-slate-100 mb-4">
                  <Users className="h-10 w-10 text-slate-400" />
                </div>
                <p className="text-slate-600 font-medium">No team members found</p>
                <p className="text-sm text-slate-500 mt-1">
                  {searchQuery ? 'Try a different search term' : 'You have no direct reports'}
                </p>
              </div>
            ) : (
              filteredTeamMembers.map((member) => (
                <button
                  key={member.id}
                  onClick={() => handleTeamMemberClick(member)}
                  className={`w-full text-left p-4 rounded-lg border transition-all hover:shadow-md ${
                    selectedMemberId === member.id
                      ? 'border-primary bg-primary/5 shadow-md'
                      : 'border-slate-200 bg-white hover:border-primary/50'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      <div className="h-10 w-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-semibold flex-shrink-0">
                        {member.full_name.charAt(0).toUpperCase()}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="font-semibold text-slate-900 truncate">
                          {member.full_name}
                        </div>
                        <div className="text-sm text-slate-600 truncate">
                          {member.email}
                        </div>
                        <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                          <Badge variant="secondary" className="text-xs">
                            {member.role_name}
                          </Badge>
                          <span className="text-xs text-slate-500">
                            {member.candidate_count} candidates
                          </span>
                          {member.has_team_members && (
                            <span className="text-xs text-primary font-medium">
                              {member.team_member_count} team members →
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    <ChevronRight className={`h-5 w-5 flex-shrink-0 ${selectedMemberId === member.id ? 'text-primary' : 'text-slate-400'}`} />
                  </div>
                </button>
              ))
            )}
          </div>
        </Card>

        {/* Column 2: Candidates */}
        <Card className="h-[calc(100vh-14rem)] flex flex-col">
          <div className="p-6 border-b flex-shrink-0">
            <h3 className="font-semibold text-slate-900">
              {selectedMemberId ? 'Assigned Candidates' : 'Select a Team Member'}
            </h3>
            {selectedMemberId && (
              <p className="text-sm text-slate-600 mt-1">
                {currentCandidates.length} candidates assigned
              </p>
            )}
          </div>

          {/* Candidates List */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {!selectedMemberId ? (
              <div className="flex flex-col items-center justify-center h-full text-center py-12">
                <div className="p-4 rounded-full bg-slate-100 mb-4">
                  <UserCog className="h-10 w-10 text-slate-400" />
                </div>
                <p className="text-slate-600 font-medium">
                  Select a team member
                </p>
                <p className="text-sm text-slate-500 mt-1">
                  Click on any team member card to view their candidates
                </p>
              </div>
            ) : isLoadingCandidates ? (
              <>
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-28 w-full" />
                ))}
              </>
            ) : currentCandidates.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center py-12">
                <div className="p-4 rounded-full bg-slate-100 mb-4">
                  <Users className="h-10 w-10 text-slate-400" />
                </div>
                <p className="text-slate-600 font-medium">No candidates assigned</p>
                <p className="text-sm text-slate-500 mt-1">
                  This team member has no candidates yet
                </p>
              </div>
            ) : (
              currentCandidates.map((candidate) => (
                <Card 
                  key={candidate.id} 
                  className="hover:shadow-lg transition-all hover:border-primary/50 cursor-pointer group"
                  onClick={() => handleViewCandidate(candidate.id)}
                >
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between mb-2">
                          <div>
                            <h4 className="font-semibold text-slate-900 group-hover:text-primary transition-colors">
                              {candidate.first_name} {candidate.last_name}
                            </h4>
                            <div className="flex items-center gap-2 mt-1">
                              <Badge
                                className={ONBOARDING_STATUS_COLORS[candidate.onboarding_status || 'PENDING_ASSIGNMENT']}
                              >
                                {(candidate.onboarding_status || 'PENDING_ASSIGNMENT').replace(/_/g, ' ')}
                              </Badge>
                            </div>
                          </div>
                        </div>

                        <div className="space-y-1 text-sm text-slate-600">
                          <div className="flex items-center gap-2">
                            <Mail className="h-4 w-4" />
                            <span className="truncate">{candidate.email}</span>
                          </div>
                          {candidate.phone && (
                            <div className="flex items-center gap-2">
                              <Phone className="h-4 w-4" />
                              <span>{candidate.phone}</span>
                            </div>
                          )}
                        </div>
                      </div>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={(e) => { e.stopPropagation(); handleViewCandidate(candidate.id); }}
                        className="gap-2"
                      >
                        <Eye className="h-4 w-4" />
                        View
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </div>
        </Card>
      </div>
      </>
      )}
    </div>
  );
}
