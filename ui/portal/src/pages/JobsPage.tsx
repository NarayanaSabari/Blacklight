/**
 * Jobs Page
 * View candidates and their matched jobs
 * Left sidebar: Assigned candidates
 * Right panel: Job matches for selected candidate with pagination
 */

import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { 
  Briefcase, 
  Search, 
  User,
  Target,
  TrendingUp,
  AlertCircle,
  ChevronRight,
  ChevronLeft,
  ChevronsLeft,
  ChevronsRight,
} from 'lucide-react';
import { candidateApi } from '@/lib/candidateApi';
import { jobMatchApi } from '@/lib/jobMatchApi';
import { MatchCard } from '@/components/matches/MatchCard';

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

export function JobsPage() {
  const navigate = useNavigate();
  const [selectedCandidateId, setSelectedCandidateId] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);

  // Reset page when candidate changes
  useEffect(() => {
    setCurrentPage(1);
  }, [selectedCandidateId]);

  // Fetch all candidates
  const { data: candidatesData, isLoading: loadingCandidates } = useQuery({
    queryKey: ['candidates', { page: 1, per_page: 100 }],
    queryFn: () => candidateApi.listCandidates({ page: 1, per_page: 100 }),
    staleTime: 0,
  });

  const candidates = candidatesData?.candidates || [];
  
  // Filter candidates by search
  const filteredCandidates = candidates.filter((candidate) => {
    const searchLower = searchQuery.toLowerCase();
    const fullName = `${candidate.first_name} ${candidate.last_name}`.toLowerCase();
    const email = candidate.email?.toLowerCase() || '';
    return fullName.includes(searchLower) || email.includes(searchLower);
  });

  // Fetch matches for selected candidate with pagination
  const { 
    data: matchesData, 
    isLoading: loadingMatches,
    error: matchesError 
  } = useQuery({
    queryKey: ['jobMatches', selectedCandidateId, currentPage, pageSize],
    queryFn: async () => {
      if (!selectedCandidateId) return null;
      return jobMatchApi.getCandidateMatches(selectedCandidateId, { 
        page: currentPage,
        per_page: pageSize,
        sort_by: 'match_score',
        sort_order: 'desc'
      });
    },
    enabled: !!selectedCandidateId,
    staleTime: 0,
  });

  const matches = matchesData?.matches || [];
  const totalMatches = matchesData?.total_matches || 0;
  const totalPages = matchesData?.total_pages || 0;
  const selectedCandidate = candidates.find((c) => c.id === selectedCandidateId);

  const handleCandidateSelect = (candidateId: number) => {
    setSelectedCandidateId(candidateId);
  };

  const handleViewAllMatches = () => {
    if (selectedCandidateId) {
      navigate(`/candidates/${selectedCandidateId}/matches`);
    }
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  const handlePageSizeChange = (size: string) => {
    setPageSize(parseInt(size));
    setCurrentPage(1);
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Job Matches</h1>
          <p className="text-slate-600 mt-1">View AI-powered job recommendations for candidates</p>
        </div>
      </div>

      {/* Main Layout: Split View */}
      <div className="grid grid-cols-12 gap-6">
        {/* Left Sidebar: Candidates List */}
        <div className="col-span-4">
          <Card className="h-[calc(100vh-220px)]">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2">
                <User className="h-5 w-5" />
                Candidates ({filteredCandidates.length})
              </CardTitle>
              <div className="relative mt-2">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search candidates..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9"
                />
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <ScrollArea className="h-[calc(100vh-340px)]">
                {loadingCandidates ? (
                  <div className="space-y-2 p-4">
                    {[1, 2, 3, 4, 5].map((i) => (
                      <Skeleton key={i} className="h-20 w-full" />
                    ))}
                  </div>
                ) : filteredCandidates.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-12 text-center px-4">
                    <User className="h-12 w-12 text-muted-foreground mb-3" />
                    <p className="text-sm text-muted-foreground">
                      {searchQuery ? 'No candidates found' : 'No candidates available'}
                    </p>
                  </div>
                ) : (
                  <div className="space-y-1 p-2">
                    {filteredCandidates.map((candidate) => (
                      <button
                        key={candidate.id}
                        onClick={() => handleCandidateSelect(candidate.id)}
                        className={`w-full text-left p-3 rounded-lg transition-colors ${
                          selectedCandidateId === candidate.id
                            ? 'bg-primary text-primary-foreground'
                            : 'hover:bg-muted'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex-1 min-w-0">
                            <p className="font-medium truncate">
                              {candidate.first_name} {candidate.last_name}
                            </p>
                          </div>
                          <ChevronRight className={`h-4 w-4 ml-2 flex-shrink-0 ${
                            selectedCandidateId === candidate.id
                              ? 'text-primary-foreground'
                              : 'text-muted-foreground'
                          }`} />
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </ScrollArea>
            </CardContent>
          </Card>
        </div>

        {/* Right Panel: Job Matches */}
        <div className="col-span-8">
          {!selectedCandidateId ? (
            <Card className="h-[calc(100vh-220px)]">
              <CardContent className="flex flex-col items-center justify-center h-full text-center">
                <Target className="h-16 w-16 text-muted-foreground mb-4" />
                <h3 className="text-xl font-semibold mb-2">Select a Candidate</h3>
                <p className="text-muted-foreground max-w-md">
                  Choose a candidate from the list to view their AI-powered job matches and recommendations
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {/* Selected Candidate Header */}
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-xl flex items-center gap-2">
                        <Briefcase className="h-5 w-5" />
                        Job Matches for {selectedCandidate?.first_name} {selectedCandidate?.last_name}
                      </CardTitle>
                      <p className="text-sm text-muted-foreground mt-1">
                        {(selectedCandidate as any)?.current_position || 'No position'} • {selectedCandidate?.email}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant="secondary" className="text-base px-3 py-1">
                        <Target className="h-4 w-4 mr-1" />
                        {totalMatches} Matches
                      </Badge>
                    </div>
                  </div>
                </CardHeader>
              </Card>

              {/* Pagination Controls - Top */}
              {totalMatches > 0 && (
                <Card>
                  <CardContent className="py-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <span>Show</span>
                        <Select value={pageSize.toString()} onValueChange={handlePageSizeChange}>
                          <SelectTrigger className="w-[80px] h-8">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {PAGE_SIZE_OPTIONS.map((size) => (
                              <SelectItem key={size} value={size.toString()}>
                                {size}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <span>per page</span>
                        <span className="mx-2">•</span>
                        <span>
                          Showing {((currentPage - 1) * pageSize) + 1} - {Math.min(currentPage * pageSize, totalMatches)} of {totalMatches}
                        </span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="outline"
                          size="icon"
                          className="h-8 w-8"
                          onClick={() => handlePageChange(1)}
                          disabled={currentPage === 1}
                        >
                          <ChevronsLeft className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="outline"
                          size="icon"
                          className="h-8 w-8"
                          onClick={() => handlePageChange(currentPage - 1)}
                          disabled={currentPage === 1}
                        >
                          <ChevronLeft className="h-4 w-4" />
                        </Button>
                        <span className="px-3 text-sm font-medium">
                          Page {currentPage} of {totalPages}
                        </span>
                        <Button
                          variant="outline"
                          size="icon"
                          className="h-8 w-8"
                          onClick={() => handlePageChange(currentPage + 1)}
                          disabled={currentPage >= totalPages}
                        >
                          <ChevronRight className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="outline"
                          size="icon"
                          className="h-8 w-8"
                          onClick={() => handlePageChange(totalPages)}
                          disabled={currentPage >= totalPages}
                        >
                          <ChevronsRight className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Matches List */}
              <ScrollArea className="h-[calc(100vh-360px)]">
                {loadingMatches ? (
                  <div className="space-y-4">
                    {[1, 2, 3].map((i) => (
                      <Skeleton key={i} className="h-64 w-full" />
                    ))}
                  </div>
                ) : matchesError ? (
                  <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                      Failed to load job matches. Please try again.
                    </AlertDescription>
                  </Alert>
                ) : matches.length === 0 ? (
                  <Card>
                    <CardContent className="flex flex-col items-center justify-center py-12 text-center">
                      <TrendingUp className="h-12 w-12 text-muted-foreground mb-4" />
                      <h3 className="text-lg font-semibold mb-2">No Job Matches Yet</h3>
                      <p className="text-muted-foreground mb-4 max-w-md">
                        Generate AI-powered job matches for this candidate to see recommendations
                      </p>
                      <Button onClick={handleViewAllMatches}>
                        Go to Matches Page
                      </Button>
                    </CardContent>
                  </Card>
                ) : (
                  <div className="space-y-4 pr-2">
                    {matches.map((match) => (
                      <MatchCard
                        key={match.id}
                        match={match}
                        candidateId={selectedCandidateId}
                        onViewDetails={(jobId) => {
                          navigate(`/candidates/${selectedCandidateId}/matches/jobs/${jobId}`, {
                            state: { match }
                          });
                        }}
                        showActions={true}
                      />
                    ))}
                  </div>
                )}
              </ScrollArea>

              {/* Pagination Controls - Bottom */}
              {totalMatches > 0 && totalPages > 1 && (
                <Card>
                  <CardContent className="py-3">
                    <div className="flex items-center justify-center gap-1">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handlePageChange(1)}
                        disabled={currentPage === 1}
                      >
                        <ChevronsLeft className="h-4 w-4 mr-1" />
                        First
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handlePageChange(currentPage - 1)}
                        disabled={currentPage === 1}
                      >
                        <ChevronLeft className="h-4 w-4 mr-1" />
                        Previous
                      </Button>
                      <div className="flex items-center gap-1 mx-2">
                        {/* Page number buttons */}
                        {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                          let pageNum: number;
                          if (totalPages <= 5) {
                            pageNum = i + 1;
                          } else if (currentPage <= 3) {
                            pageNum = i + 1;
                          } else if (currentPage >= totalPages - 2) {
                            pageNum = totalPages - 4 + i;
                          } else {
                            pageNum = currentPage - 2 + i;
                          }
                          return (
                            <Button
                              key={pageNum}
                              variant={currentPage === pageNum ? "default" : "outline"}
                              size="sm"
                              className="w-9"
                              onClick={() => handlePageChange(pageNum)}
                            >
                              {pageNum}
                            </Button>
                          );
                        })}
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handlePageChange(currentPage + 1)}
                        disabled={currentPage >= totalPages}
                      >
                        Next
                        <ChevronRight className="h-4 w-4 ml-1" />
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handlePageChange(totalPages)}
                        disabled={currentPage >= totalPages}
                      >
                        Last
                        <ChevronsRight className="h-4 w-4 ml-1" />
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
