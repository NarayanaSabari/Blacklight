/**
 * Active Sessions Page
 * Detailed real-time monitoring of active scraper sessions with comprehensive metrics
 */

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
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
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { scraperMonitoringApi, type ScrapeSession, type SessionDetails } from '@/lib/dashboard-api';
import { usePMAdminAuth } from '@/hooks/usePMAdminAuth';
import { 
  Activity, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  RefreshCw,
  Loader2,
  FileText,
  FileCheck,
  FileX,
  Layers,
  Timer,
  StopCircle,
  RotateCcw,
  AlertTriangle,
  MapPin,
  Zap,
  Package,
  TrendingUp,
  Server,
  Cpu,
  ArrowRight
} from 'lucide-react';
import { formatDistanceToNow, differenceInSeconds } from 'date-fns';
import { toast } from 'sonner';

// Format duration nicely
const formatDuration = (seconds: number): string => {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  }
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  return `${hrs}h ${mins}m`;
};

// Live Timer component
function LiveTimer({ startedAt }: { startedAt: string }) {
  const [elapsed, setElapsed] = useState(0);
  
  useEffect(() => {
    const startTime = new Date(startedAt).getTime();
    const updateElapsed = () => {
      setElapsed(Math.floor((Date.now() - startTime) / 1000));
    };
    updateElapsed();
    const interval = setInterval(updateElapsed, 1000);
    return () => clearInterval(interval);
  }, [startedAt]);
  
  return (
    <span className="tabular-nums font-mono">{formatDuration(elapsed)}</span>
  );
}

// Detailed Session Card component
function DetailedSessionCard({ 
  session, 
  onTerminate, 
  isTerminating 
}: { 
  session: ScrapeSession; 
  onTerminate?: (sessionId: string) => void;
  isTerminating?: boolean;
}) {
  const [sessionDetails, setSessionDetails] = useState<SessionDetails | null>(null);
  
  // Fetch detailed session info
  const { data: details } = useQuery({
    queryKey: ['session-details', session.sessionId],
    queryFn: () => scraperMonitoringApi.getSessionDetails(session.sessionId),
    refetchInterval: 3000, // Refresh every 3 seconds for active sessions
  });
  
  useEffect(() => {
    if (details) setSessionDetails(details);
  }, [details]);
  
  const batchProgress = session.totalBatches > 0 
    ? Math.round((session.completedBatches / session.totalBatches) * 100) 
    : 0;
  
  const platformProgress = session.platformsTotal > 0
    ? Math.round((session.platformsCompleted / session.platformsTotal) * 100)
    : 0;
  
  const importRate = session.jobsFound > 0 
    ? Math.round((session.jobsImported / session.jobsFound) * 100) 
    : 0;

  const lastUpdated = session.updatedAt 
    ? formatDistanceToNow(new Date(session.updatedAt), { addSuffix: true })
    : null;
  
  // Check if session might be stale (no update in 2+ minutes)
  const isStale = session.updatedAt 
    ? differenceInSeconds(new Date(), new Date(session.updatedAt)) > 120
    : false;

  return (
    <Card className={`overflow-hidden ${isStale ? 'border-yellow-500 border-2' : ''}`}>
      {/* Header with status indicator */}
      <div className="bg-gradient-to-r from-blue-500 to-indigo-600 p-4 text-white">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-white/20 rounded-full">
              <Loader2 className="h-5 w-5 animate-spin" />
            </div>
            <div>
              <h3 className="font-semibold text-lg">{session.roleName}</h3>
              <div className="flex items-center gap-2 text-sm text-blue-100">
                {session.location && (
                  <span className="flex items-center gap-1">
                    <MapPin className="h-3 w-3" />
                    {session.location}
                  </span>
                )}
                <span>•</span>
                <span>{session.scraperKeyName}</span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {isStale && (
              <Tooltip>
                <TooltipTrigger>
                  <Badge variant="outline" className="bg-yellow-500 text-yellow-900 border-yellow-600">
                    <AlertTriangle className="h-3 w-3 mr-1" />
                    Possibly Stale
                  </Badge>
                </TooltipTrigger>
                <TooltipContent>
                  No updates received in over 2 minutes. Session may be stuck.
                </TooltipContent>
              </Tooltip>
            )}
            {onTerminate && (
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button 
                    variant="secondary" 
                    size="sm"
                    className="bg-white/20 hover:bg-white/30 text-white border-0"
                    disabled={isTerminating}
                  >
                    {isTerminating ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <>
                        <StopCircle className="h-4 w-4 mr-1" />
                        Terminate
                      </>
                    )}
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Terminate Session?</AlertDialogTitle>
                    <AlertDialogDescription>
                      This will stop the scraping session for <strong>{session.roleName}</strong> and 
                      return the role back to the queue.
                      <br /><br />
                      <span className="flex items-center gap-2 text-sm">
                        <RotateCcw className="h-4 w-4 text-blue-500" />
                        The role will be available for scraping again immediately.
                      </span>
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction
                      onClick={() => onTerminate(session.sessionId)}
                      className="bg-orange-600 hover:bg-orange-700"
                    >
                      Terminate & Requeue
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            )}
          </div>
        </div>
      </div>
      
      <CardContent className="p-4 space-y-4">
        {/* Live Stats Row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center p-3 rounded-lg bg-blue-50 border border-blue-200">
            <Timer className="h-5 w-5 mx-auto text-blue-600 mb-1 animate-pulse" />
            <p className="text-xs text-blue-600 font-medium">Elapsed Time</p>
            <p className="text-xl font-bold text-blue-700">
              <LiveTimer startedAt={session.startedAt} />
            </p>
          </div>
          
          <div className="text-center p-3 rounded-lg bg-muted/50 border">
            <FileText className="h-5 w-5 mx-auto text-gray-600 mb-1" />
            <p className="text-xs text-muted-foreground font-medium">Jobs Found</p>
            <p className="text-xl font-bold">{session.jobsFound}</p>
          </div>
          
          <div className="text-center p-3 rounded-lg bg-green-50 border border-green-200">
            <FileCheck className="h-5 w-5 mx-auto text-green-600 mb-1" />
            <p className="text-xs text-green-600 font-medium">Imported</p>
            <p className="text-xl font-bold text-green-700">{session.jobsImported}</p>
          </div>
          
          <div className="text-center p-3 rounded-lg bg-yellow-50 border border-yellow-200">
            <FileX className="h-5 w-5 mx-auto text-yellow-600 mb-1" />
            <p className="text-xs text-yellow-600 font-medium">Skipped</p>
            <p className="text-xl font-bold text-yellow-700">{session.jobsSkipped}</p>
          </div>
        </div>
        
        {/* Progress Indicators */}
        <div className="space-y-3">
          {/* Batch Progress */}
          {session.totalBatches > 0 && (
            <div className="p-3 rounded-lg bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-medium text-blue-700 flex items-center gap-2">
                  <Package className="h-4 w-4" />
                  Batch Progress
                </span>
                <span className="text-sm font-bold text-blue-800 tabular-nums">
                  {session.completedBatches} / {session.totalBatches} ({batchProgress}%)
                </span>
              </div>
              <Progress value={batchProgress} className="h-3" />
              {lastUpdated && (
                <p className="text-xs text-blue-500 mt-2">
                  Last activity: {lastUpdated}
                </p>
              )}
            </div>
          )}
          
          {/* Platform Progress */}
          <div className="p-3 rounded-lg bg-muted/30 border">
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm font-medium flex items-center gap-2">
                <Layers className="h-4 w-4" />
                Platform Progress
              </span>
              <span className="text-sm font-bold tabular-nums">
                {session.platformsCompleted} / {session.platformsTotal} 
                {session.platformsFailed > 0 && (
                  <span className="text-red-500 ml-1">({session.platformsFailed} failed)</span>
                )}
              </span>
            </div>
            <Progress value={platformProgress} className="h-2" />
          </div>
          
          {/* Import Success Rate */}
          {session.jobsFound > 0 && (
            <div className="p-3 rounded-lg bg-muted/30 border">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-medium flex items-center gap-2">
                  <TrendingUp className="h-4 w-4" />
                  Import Success Rate
                </span>
                <span className={`text-sm font-bold ${
                  importRate >= 80 ? 'text-green-600' : 
                  importRate >= 50 ? 'text-yellow-600' : 
                  'text-red-600'
                }`}>
                  {importRate}%
                </span>
              </div>
              <Progress value={importRate} className="h-2" />
            </div>
          )}
        </div>
        
        {/* Platform Status Details */}
        {sessionDetails && sessionDetails.platformStatuses.length > 0 && (
          <div>
            <Separator className="my-3" />
            <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
              <Server className="h-4 w-4" />
              Platform Details
            </h4>
            <div className="grid gap-2">
              {sessionDetails.platformStatuses.map((platform) => {
                const platformBatchProgress = platform.totalBatches > 0
                  ? Math.round((platform.completedBatches / platform.totalBatches) * 100)
                  : 0;
                
                return (
                  <div 
                    key={platform.id}
                    className={`p-3 rounded-lg border flex items-center justify-between ${
                      platform.status === 'completed' ? 'bg-green-50/50 border-green-200' :
                      platform.status === 'failed' ? 'bg-red-50/50 border-red-200' :
                      platform.status === 'in_progress' ? 'bg-blue-50/50 border-blue-200' :
                      'bg-muted/30'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className={`p-1.5 rounded-full ${
                        platform.status === 'completed' ? 'bg-green-100' :
                        platform.status === 'failed' ? 'bg-red-100' :
                        platform.status === 'in_progress' ? 'bg-blue-100' :
                        'bg-gray-100'
                      }`}>
                        {platform.status === 'completed' && <CheckCircle2 className="h-4 w-4 text-green-600" />}
                        {platform.status === 'failed' && <XCircle className="h-4 w-4 text-red-600" />}
                        {platform.status === 'in_progress' && <Loader2 className="h-4 w-4 text-blue-600 animate-spin" />}
                        {platform.status === 'pending' && <Clock className="h-4 w-4 text-gray-400" />}
                        {platform.status === 'skipped' && <AlertTriangle className="h-4 w-4 text-yellow-600" />}
                      </div>
                      <div>
                        <p className="font-medium text-sm capitalize">{platform.platformName}</p>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <span>Found: {platform.jobsFound}</span>
                          <span className="text-green-600">+{platform.jobsImported}</span>
                          <span className="text-yellow-600">~{platform.jobsSkipped}</span>
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-3">
                      {platform.status === 'in_progress' && platform.totalBatches > 0 && (
                        <div className="text-right">
                          <p className="text-xs text-blue-600 font-medium">
                            Batch {platform.completedBatches}/{platform.totalBatches}
                          </p>
                          <Progress value={platformBatchProgress} className="h-1.5 w-20" />
                        </div>
                      )}
                      {platform.durationSeconds && (
                        <Badge variant="outline" className="tabular-nums">
                          {formatDuration(platform.durationSeconds)}
                        </Badge>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
        
        {/* Actions */}
        <div className="flex items-center justify-between pt-2">
          <p className="text-xs text-muted-foreground">
            Session ID: <code className="text-xs">{session.sessionId.substring(0, 8)}...</code>
          </p>
          <Link to={`/sessions/${session.sessionId}`}>
            <Button variant="outline" size="sm" className="gap-2">
              <FileText className="h-4 w-4" />
              View Job Logs
              <ArrowRight className="h-3 w-3" />
            </Button>
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}

// Summary Stats Component
function SessionStats({ sessions }: { sessions: ScrapeSession[] }) {
  const totalJobs = sessions.reduce((sum, s) => sum + s.jobsFound, 0);
  const totalImported = sessions.reduce((sum, s) => sum + s.jobsImported, 0);
  const totalSkipped = sessions.reduce((sum, s) => sum + s.jobsSkipped, 0);
  const totalBatches = sessions.reduce((sum, s) => sum + s.totalBatches, 0);
  const completedBatches = sessions.reduce((sum, s) => sum + s.completedBatches, 0);
  
  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
      <Card className="p-4">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-full bg-blue-100">
            <Zap className="h-5 w-5 text-blue-600" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Active Sessions</p>
            <p className="text-2xl font-bold">{sessions.length}</p>
          </div>
        </div>
      </Card>
      
      <Card className="p-4">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-full bg-gray-100">
            <FileText className="h-5 w-5 text-gray-600" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Jobs Found</p>
            <p className="text-2xl font-bold">{totalJobs}</p>
          </div>
        </div>
      </Card>
      
      <Card className="p-4">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-full bg-green-100">
            <FileCheck className="h-5 w-5 text-green-600" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Imported</p>
            <p className="text-2xl font-bold text-green-600">{totalImported}</p>
          </div>
        </div>
      </Card>
      
      <Card className="p-4">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-full bg-yellow-100">
            <FileX className="h-5 w-5 text-yellow-600" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Skipped</p>
            <p className="text-2xl font-bold text-yellow-600">{totalSkipped}</p>
          </div>
        </div>
      </Card>
      
      <Card className="p-4">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-full bg-purple-100">
            <Package className="h-5 w-5 text-purple-600" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Batches</p>
            <p className="text-2xl font-bold">{completedBatches}/{totalBatches}</p>
          </div>
        </div>
      </Card>
    </div>
  );
}

export function ActiveSessionsPage() {
  const queryClient = useQueryClient();
  const { isAuthenticated, isLoading: authLoading } = usePMAdminAuth();
  const [terminatingSessionId, setTerminatingSessionId] = useState<string | null>(null);
  
  const { data: sessions, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['active-scraper-sessions'],
    queryFn: scraperMonitoringApi.getActiveSessions,
    refetchInterval: 5000, // Refresh every 5 seconds
    enabled: !authLoading && isAuthenticated,
  });

  const terminateMutation = useMutation({
    mutationFn: scraperMonitoringApi.terminateSession,
    onMutate: (sessionId) => {
      setTerminatingSessionId(sessionId);
    },
    onSuccess: (result) => {
      toast.success("Session Terminated", {
        description: result.message,
      });
      queryClient.invalidateQueries({ queryKey: ['active-scraper-sessions'] });
      queryClient.invalidateQueries({ queryKey: ['recent-scraper-sessions'] });
      queryClient.invalidateQueries({ queryKey: ['scraper-stats'] });
    },
    onError: (error: Error) => {
      toast.error("Failed to terminate session", {
        description: error.message || "An error occurred",
      });
    },
    onSettled: () => {
      setTerminatingSessionId(null);
    },
  });

  const handleTerminate = (sessionId: string) => {
    terminateMutation.mutate(sessionId);
  };

  return (
    <TooltipProvider>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Zap className="h-6 w-6 text-blue-600" />
              Active Sessions
            </h1>
            <p className="text-muted-foreground">
              Real-time monitoring of running scraper sessions
            </p>
          </div>
          <Button 
            variant="outline" 
            size="sm" 
            onClick={() => refetch()}
            disabled={isFetching}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isFetching ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>

        {isLoading ? (
          <div className="space-y-4">
            <div className="grid grid-cols-5 gap-4">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-24" />
              ))}
            </div>
            {[...Array(2)].map((_, i) => (
              <Skeleton key={i} className="h-64" />
            ))}
          </div>
        ) : error ? (
          <Card className="p-8 text-center">
            <XCircle className="h-12 w-12 mx-auto text-red-500 mb-4" />
            <p className="text-lg font-medium">Failed to load active sessions</p>
            <p className="text-sm text-muted-foreground mb-4">There was an error fetching the session data.</p>
            <Button onClick={() => refetch()}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Try Again
            </Button>
          </Card>
        ) : !sessions?.length ? (
          <Card className="p-12 text-center">
            <div className="max-w-md mx-auto">
              <div className="p-4 bg-muted rounded-full w-fit mx-auto mb-4">
                <Activity className="h-12 w-12 text-muted-foreground" />
              </div>
              <h3 className="text-xl font-semibold mb-2">No Active Sessions</h3>
              <p className="text-muted-foreground mb-6">
                There are currently no scraper sessions running. Active sessions will appear here 
                when scrapers start processing roles.
              </p>
              <div className="flex items-center justify-center gap-3 text-sm text-muted-foreground">
                <Cpu className="h-4 w-4" />
                <span>Sessions auto-refresh every 5 seconds</span>
              </div>
            </div>
          </Card>
        ) : (
          <>
            {/* Stats Summary */}
            <SessionStats sessions={sessions} />
            
            {/* Session Cards */}
            <div className="grid gap-6">
              {sessions.map((session) => (
                <DetailedSessionCard 
                  key={session.id} 
                  session={session} 
                  onTerminate={handleTerminate}
                  isTerminating={terminatingSessionId === session.sessionId}
                />
              ))}
            </div>
          </>
        )}
      </div>
    </TooltipProvider>
  );
}

export default ActiveSessionsPage;
