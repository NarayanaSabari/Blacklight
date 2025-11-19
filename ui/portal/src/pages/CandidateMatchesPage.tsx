/**
 * Candidate Matches Page
 * 
 * Displays AI-powered job matches for a specific candidate with:
 * - Match cards with score breakdown
 * - Filtering by grade and score range
 * - Sorting options
 * - Pagination
 * - Match statistics
 * - Generate/refresh matches actions
 */

import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  RefreshCw,
  Sparkles,
  TrendingUp,
  Award,
  Loader2,
  AlertCircle,
  Target,
} from 'lucide-react';
import { toast } from 'sonner';

import { jobMatchApi } from '@/lib/jobMatchApi';
import { candidateApi } from '@/lib/candidateApi';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { MatchCard } from '@/components/matches/MatchCard';
import { MatchFilters } from '@/components/matches/MatchFilters';
import { Empty, EmptyHeader, EmptyMedia, EmptyTitle, EmptyDescription } from '@/components/ui/empty';
import type { JobMatchFilters } from '@/types';

export function CandidateMatchesPage() {
  const { candidateId } = useParams<{ candidateId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [filters, setFilters] = useState<JobMatchFilters>({
    page: 1,
    per_page: 20,
    sort_by: 'match_score',
    sort_order: 'desc',
  });

  const candidateIdNum = parseInt(candidateId || '0', 10);

  // Fetch candidate details
  const { data: candidate, isLoading: loadingCandidate } = useQuery({
    queryKey: ['candidate', candidateIdNum],
    queryFn: () => candidateApi.getCandidate(candidateIdNum),
    enabled: !!candidateIdNum,
  });

  // Fetch matches
  const {
    data: matchesData,
    isLoading: loadingMatches,
    error: matchesError,
  } = useQuery({
    queryKey: ['candidateMatches', candidateIdNum, filters],
    queryFn: () => jobMatchApi.getCandidateMatches(candidateIdNum, filters),
    enabled: !!candidateIdNum,
    staleTime: 0,
  });

  // Fetch match statistics
  const { data: stats } = useQuery({
    queryKey: ['matchStats', candidateIdNum],
    queryFn: () => jobMatchApi.getMatchStats(candidateIdNum),
    enabled: !!candidateIdNum,
  });

  // Generate matches mutation
  const generateMutation = useMutation({
    mutationFn: () =>
      jobMatchApi.generateMatches(candidateIdNum, { min_score: 50, limit: 50 }),
    onSuccess: async (data) => {
      toast.success(`Generated ${data.matches_generated} matches`);
      await queryClient.refetchQueries({ queryKey: ['candidateMatches', candidateIdNum] });
      await queryClient.refetchQueries({ queryKey: ['matchStats', candidateIdNum] });
    },
    onError: (error: Error) => {
      toast.error(error?.message || 'Failed to generate matches');
    },
  });

  // Refresh matches mutation
  const refreshMutation = useMutation({
    mutationFn: () =>
      jobMatchApi.refreshCandidateMatches(candidateIdNum, { min_score: 50, limit: 50 }),
    onSuccess: async (data) => {
      toast.success(`Refreshed matches: ${data.matches_generated} new matches`);
      await queryClient.refetchQueries({ queryKey: ['candidateMatches', candidateIdNum] });
      await queryClient.refetchQueries({ queryKey: ['matchStats', candidateIdNum] });
    },
    onError: (error: Error) => {
      toast.error(error?.message || 'Failed to refresh matches');
    },
  });

  const handlePageChange = (newPage: number) => {
    setFilters((prev) => ({ ...prev, page: newPage }));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleResetFilters = () => {
    setFilters({
      page: 1,
      per_page: 20,
      sort_by: 'match_score',
      sort_order: 'desc',
    });
  };

  if (loadingCandidate) {
    return (
      <div className="container mx-auto py-8">
        <Skeleton className="h-8 w-64 mb-6" />
        <Skeleton className="h-96" />
      </div>
    );
  }

  if (!candidate) {
    return (
      <div className="container mx-auto py-8">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>Candidate not found</AlertDescription>
        </Alert>
      </div>
    );
  }

  const matches = matchesData?.matches || [];
  const totalMatches = matchesData?.total_matches || 0;
  const totalPages = matchesData?.pages || 0;

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigate(`/candidates/${candidateId}`)}
          >
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold">
              Job Matches
            </h1>
            <p className="text-muted-foreground">
              {candidate.first_name} {candidate.last_name} • {candidate.current_title}
            </p>
          </div>
        </div>

        <div className="flex gap-2">
          {totalMatches > 0 && (
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button
                  variant="outline"
                  disabled={refreshMutation.isPending}
                >
                  {refreshMutation.isPending ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Refreshing...
                    </>
                  ) : (
                    <>
                      <RefreshCw className="h-4 w-4 mr-2" />
                      Refresh Matches
                    </>
                  )}
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Refresh Matches?</AlertDialogTitle>
                  <AlertDialogDescription>
                    This will regenerate all job matches for this candidate based on the latest job postings.
                    Existing matches will be replaced.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction onClick={() => refreshMutation.mutate()}>
                    Refresh
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          )}

          {totalMatches === 0 && (
            <Button
              onClick={() => generateMutation.mutate()}
              disabled={generateMutation.isPending}
            >
              {generateMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4 mr-2" />
                  Generate Matches
                </>
              )}
            </Button>
          )}
        </div>
      </div>

      {/* Statistics Cards */}
      {stats && totalMatches > 0 && (
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total Matches
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2">
                <Target className="h-5 w-5 text-primary" />
                <span className="text-3xl font-bold">{stats.total}</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Average Score
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5 text-primary" />
                <span className="text-3xl font-bold">{stats.avg_score.toFixed(0)}%</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Grade Distribution
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2">
                <Award className="h-5 w-5 text-primary" />
                <div className="flex gap-1.5 flex-wrap">
                  {Object.entries(stats.by_grade)
                    .sort(([a], [b]) => {
                      const order = ['A+', 'A', 'B', 'C', 'D', 'F'];
                      return order.indexOf(a) - order.indexOf(b);
                    })
                    .map(([grade, count]) => (
                      <span key={grade} className="text-sm font-medium">
                        {grade}:{count}
                      </span>
                    ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filters */}
      {totalMatches > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Filters</CardTitle>
            <CardDescription>
              Showing {matches.length} of {totalMatches} matches
            </CardDescription>
          </CardHeader>
          <CardContent>
            <MatchFilters
              filters={filters}
              onFiltersChange={setFilters}
              onReset={handleResetFilters}
            />
          </CardContent>
        </Card>
      )}

      {/* Matches List */}
      {loadingMatches ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-64" />
          ))}
        </div>
      ) : matchesError ? (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Failed to load matches. Please try again.
          </AlertDescription>
        </Alert>
      ) : matches.length === 0 ? (
        <Card>
          <CardContent className="py-16">
            <Empty>
              <EmptyHeader>
                <EmptyMedia>
                  <Target className="h-12 w-12 text-muted-foreground" />
                </EmptyMedia>
                <EmptyTitle>No Matches Found</EmptyTitle>
                <EmptyDescription>
                  {totalMatches === 0
                    ? 'Generate matches to see AI-powered job recommendations'
                    : 'Try adjusting your filters to see more results'}
                </EmptyDescription>
              </EmptyHeader>
              {totalMatches === 0 && (
                <Button
                  className="mt-4"
                  onClick={() => generateMutation.mutate()}
                  disabled={generateMutation.isPending}
                >
                  {generateMutation.isPending ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Generating...
                    </>
                  ) : (
                    <>
                      <Sparkles className="h-4 w-4 mr-2" />
                      Generate Matches
                    </>
                  )}
                </Button>
              )}
            </Empty>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid gap-4">
            {matches.map((match) => (
              <MatchCard
                key={match.id}
                match={match}
                candidateId={candidateIdNum}
                onViewDetails={(jobId) => {
                  navigate(`/candidates/${candidateIdNum}/matches/jobs/${jobId}`, {
                    state: { match }
                  });
                }}
                showActions={true}
              />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                Page {filters.page} of {totalPages}
              </p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={() => handlePageChange((filters.page || 1) - 1)}
                  disabled={filters.page === 1}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  onClick={() => handlePageChange((filters.page || 1) + 1)}
                  disabled={filters.page === totalPages}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
