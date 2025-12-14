/**
 * Scraper Monitoring Component
 * Shows active scraper sessions and recent activity with detailed stats
 */

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
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
} from "@/components/ui/alert-dialog";
import { scraperMonitoringApi, type ScrapeSession } from "@/lib/dashboard-api";
import { usePMAdminAuth } from "@/hooks/usePMAdminAuth";
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
  RotateCcw
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { toast } from "sonner";

function SessionStatusBadge({ status }: { status: ScrapeSession['status'] }) {
  const variants: Record<ScrapeSession['status'], { variant: "default" | "secondary" | "destructive" | "outline"; label: string; className: string }> = {
    in_progress: { variant: "default", label: "Running", className: "bg-blue-500" },
    completed: { variant: "secondary", label: "Completed", className: "bg-green-100 text-green-800" },
    failed: { variant: "destructive", label: "Failed", className: "" },
    terminated: { variant: "outline", label: "Terminated", className: "border-orange-500 text-orange-600" },
  };

  const { variant, label, className } = variants[status] || { variant: "outline" as const, label: status, className: "" };
  return <Badge variant={variant} className={className}>{label}</Badge>;
}

function SessionCard({ session, onTerminate, isTerminating }: { 
  session: ScrapeSession; 
  onTerminate?: (sessionId: string) => void;
  isTerminating?: boolean;
}) {
  const timeAgo = formatDistanceToNow(new Date(session.startedAt), { addSuffix: true });
  const successRate = session.jobsFound > 0 
    ? Math.round((session.jobsImported / session.jobsFound) * 100) 
    : 0;
  
  return (
    <div className="p-4 rounded-lg border bg-card hover:bg-accent/30 transition-colors">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-full ${
            session.status === 'in_progress' ? 'bg-blue-100 text-blue-600' :
            session.status === 'completed' ? 'bg-green-100 text-green-600' :
            session.status === 'terminated' ? 'bg-orange-100 text-orange-600' :
            'bg-red-100 text-red-600'
          }`}>
            {session.status === 'in_progress' ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : session.status === 'completed' ? (
              <CheckCircle2 className="h-4 w-4" />
            ) : session.status === 'terminated' ? (
              <StopCircle className="h-4 w-4" />
            ) : (
              <XCircle className="h-4 w-4" />
            )}
          </div>
          <div>
            <p className="font-medium">{session.roleName}</p>
            <p className="text-xs text-muted-foreground">
              {session.scraperKeyName} • {timeAgo}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <SessionStatusBadge status={session.status} />
          {/* Terminate button for in_progress sessions */}
          {session.status === 'in_progress' && onTerminate && (
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button 
                  variant="outline" 
                  size="sm" 
                  className="text-orange-600 border-orange-300 hover:bg-orange-50"
                  disabled={isTerminating}
                >
                  {isTerminating ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    <StopCircle className="h-3 w-3" />
                  )}
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Terminate Session?</AlertDialogTitle>
                  <AlertDialogDescription>
                    This will stop the scraping session for <strong>{session.roleName}</strong> and 
                    return the role back to the queue so it can be picked up by another scraper.
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

      {/* Stats Grid */}
      <div className="grid grid-cols-4 gap-3 mb-3">
        <div className="flex items-center gap-2 p-2 rounded bg-muted/50">
          <FileText className="h-4 w-4 text-blue-500" />
          <div>
            <p className="text-xs text-muted-foreground">Found</p>
            <p className="font-semibold text-sm">{session.jobsFound}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 p-2 rounded bg-muted/50">
          <FileCheck className="h-4 w-4 text-green-500" />
          <div>
            <p className="text-xs text-muted-foreground">Imported</p>
            <p className="font-semibold text-sm text-green-600">{session.jobsImported}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 p-2 rounded bg-muted/50">
          <FileX className="h-4 w-4 text-yellow-500" />
          <div>
            <p className="text-xs text-muted-foreground">Skipped</p>
            <p className="font-semibold text-sm text-yellow-600">{session.jobsSkipped}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 p-2 rounded bg-muted/50">
          <Timer className="h-4 w-4 text-purple-500" />
          <div>
            <p className="text-xs text-muted-foreground">Duration</p>
            <p className="font-semibold text-sm">
              {session.durationSeconds ? `${session.durationSeconds}s` : '-'}
            </p>
          </div>
        </div>
      </div>

      {/* Progress bar for import success rate */}
      {session.jobsFound > 0 && (
        <div className="mb-3">
          <div className="flex justify-between text-xs mb-1">
            <span className="text-muted-foreground">Import Success Rate</span>
            <span className={successRate >= 80 ? 'text-green-600' : successRate >= 50 ? 'text-yellow-600' : 'text-red-600'}>
              {successRate}%
            </span>
          </div>
          <Progress value={successRate} className="h-2" />
        </div>
      )}

      {/* Platforms Progress */}
      {session.platformsTotal > 0 && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Layers className="h-3 w-3" />
          <span>
            Platforms: {session.platformsCompleted}/{session.platformsTotal} completed
            {session.platformsFailed > 0 && (
              <span className="text-destructive ml-1">
                ({session.platformsFailed} failed)
              </span>
            )}
          </span>
        </div>
      )}

      {/* Error message */}
      {session.errorMessage && (
        <div className="mt-2 p-2 rounded bg-destructive/10 border border-destructive/20">
          <p className="text-xs text-destructive">{session.errorMessage}</p>
        </div>
      )}
    </div>
  );
}

function ActiveSessionsList() {
  const queryClient = useQueryClient();
  const { isAuthenticated, isLoading: authLoading } = usePMAdminAuth();
  const [terminatingSessionId, setTerminatingSessionId] = useState<string | null>(null);
  
  const { data: sessions, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['active-scraper-sessions'],
    queryFn: scraperMonitoringApi.getActiveSessions,
    refetchInterval: 5000, // Refresh every 5 seconds for active sessions
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
      // Refetch sessions to update the list
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

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="flex items-center gap-3 p-3 rounded-lg border">
            <Skeleton className="h-10 w-10 rounded-full" />
            <div className="flex-1">
              <Skeleton className="h-4 w-32 mb-2" />
              <Skeleton className="h-3 w-24" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-sm text-destructive">Failed to load active sessions</p>
        <Button variant="ghost" size="sm" onClick={() => refetch()} className="mt-2">
          <RefreshCw className="h-4 w-4 mr-2" />
          Retry
        </Button>
      </div>
    );
  }

  if (!sessions?.length) {
    return (
      <div className="text-center py-8">
        <Activity className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
        <p className="text-sm text-muted-foreground">No active scraper sessions</p>
        <p className="text-xs text-muted-foreground mt-1">
          Scrapers will appear here when running
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-muted-foreground">
          {sessions.length} active session{sessions.length !== 1 ? 's' : ''}
        </span>
        <Button 
          variant="ghost" 
          size="sm" 
          onClick={() => refetch()}
          disabled={isFetching}
        >
          <RefreshCw className={`h-3 w-3 mr-1 ${isFetching ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>
      {sessions.map((session) => (
        <SessionCard 
          key={session.id} 
          session={session} 
          onTerminate={handleTerminate}
          isTerminating={terminatingSessionId === session.sessionId}
        />
      ))}
    </div>
  );
}

function RecentSessionsList() {
  const { isAuthenticated, isLoading: authLoading } = usePMAdminAuth();
  const { data: sessions, isLoading, error } = useQuery({
    queryKey: ['recent-scraper-sessions'],
    queryFn: () => scraperMonitoringApi.getRecentSessions(20),
    refetchInterval: 30000, // Refresh every 30 seconds
    enabled: !authLoading && isAuthenticated,
  });

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="flex items-center gap-3 p-3 rounded-lg border">
            <Skeleton className="h-10 w-10 rounded-full" />
            <div className="flex-1">
              <Skeleton className="h-4 w-32 mb-2" />
              <Skeleton className="h-3 w-24" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-sm text-destructive">Failed to load recent sessions</p>
      </div>
    );
  }

  if (!sessions?.length) {
    return (
      <div className="text-center py-8">
        <Clock className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
        <p className="text-sm text-muted-foreground">No recent sessions</p>
      </div>
    );
  }

  return (
    <ScrollArea className="h-[350px]">
      <div className="space-y-3 pr-4">
        {sessions.map((session) => (
          <SessionCard key={session.id} session={session} />
        ))}
      </div>
    </ScrollArea>
  );
}

function StatsSummary() {
  const { isAuthenticated, isLoading: authLoading } = usePMAdminAuth();
  const { data: stats, isLoading } = useQuery({
    queryKey: ['scraper-stats'],
    queryFn: scraperMonitoringApi.getStats,
    refetchInterval: 30000, // Refresh every 30 seconds
    enabled: !authLoading && isAuthenticated,
  });

  if (isLoading || !stats) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        {[...Array(4)].map((_, i) => (
          <Skeleton key={i} className="h-20 w-full rounded-lg" />
        ))}
      </div>
    );
  }

  const jobSuccessRate = stats.jobsStats24h.successRate;

  return (
    <div className="mb-6">
      {/* Job Stats Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <div className="p-3 rounded-lg bg-blue-50 border border-blue-200">
          <div className="flex items-center gap-2">
            <FileText className="h-4 w-4 text-blue-600" />
            <span className="text-xs text-blue-600 font-medium">Jobs Found</span>
          </div>
          <p className="text-2xl font-bold text-blue-700 mt-1">
            {stats.jobsStats24h.totalFound.toLocaleString()}
          </p>
        </div>
        <div className="p-3 rounded-lg bg-green-50 border border-green-200">
          <div className="flex items-center gap-2">
            <FileCheck className="h-4 w-4 text-green-600" />
            <span className="text-xs text-green-600 font-medium">Imported</span>
          </div>
          <p className="text-2xl font-bold text-green-700 mt-1">
            {stats.jobsStats24h.totalImported.toLocaleString()}
          </p>
        </div>
        <div className="p-3 rounded-lg bg-yellow-50 border border-yellow-200">
          <div className="flex items-center gap-2">
            <FileX className="h-4 w-4 text-yellow-600" />
            <span className="text-xs text-yellow-600 font-medium">Skipped</span>
          </div>
          <p className="text-2xl font-bold text-yellow-700 mt-1">
            {stats.jobsStats24h.totalSkipped.toLocaleString()}
          </p>
        </div>
        <div className={`p-3 rounded-lg border ${
          jobSuccessRate >= 80 ? 'bg-green-50 border-green-200' : 
          jobSuccessRate >= 50 ? 'bg-yellow-50 border-yellow-200' : 
          'bg-red-50 border-red-200'
        }`}>
          <div className="flex items-center gap-2">
            <Activity className={`h-4 w-4 ${
              jobSuccessRate >= 80 ? 'text-green-600' : 
              jobSuccessRate >= 50 ? 'text-yellow-600' : 
              'text-red-600'
            }`} />
            <span className={`text-xs font-medium ${
              jobSuccessRate >= 80 ? 'text-green-600' : 
              jobSuccessRate >= 50 ? 'text-yellow-600' : 
              'text-red-600'
            }`}>Success Rate</span>
          </div>
          <p className={`text-2xl font-bold mt-1 ${
            jobSuccessRate >= 80 ? 'text-green-700' : 
            jobSuccessRate >= 50 ? 'text-yellow-700' : 
            'text-red-700'
          }`}>
            {jobSuccessRate}%
          </p>
        </div>
      </div>

      {/* Session Stats */}
      <div className="flex flex-wrap gap-2 text-xs">
        <Badge variant="outline" className="gap-1">
          <Activity className="h-3 w-3" />
          {stats.sessions24h.total} sessions today
        </Badge>
        <Badge variant="secondary" className="gap-1 bg-green-100 text-green-800">
          <CheckCircle2 className="h-3 w-3" />
          {stats.sessions24h.completed} completed
        </Badge>
        {stats.sessions24h.failed > 0 && (
          <Badge variant="destructive" className="gap-1">
            <XCircle className="h-3 w-3" />
            {stats.sessions24h.failed} failed
          </Badge>
        )}
        {stats.sessions24h.inProgress > 0 && (
          <Badge variant="default" className="gap-1">
            <Loader2 className="h-3 w-3 animate-spin" />
            {stats.sessions24h.inProgress} running
          </Badge>
        )}
        <Badge variant="outline" className="gap-1">
          <Timer className="h-3 w-3" />
          Avg: {stats.avgDurationSeconds}s
        </Badge>
      </div>
    </div>
  );
}

export function ScraperMonitoring() {
  const [activeTab, setActiveTab] = useState("active");

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Activity className="h-5 w-5" />
          Scraper Monitoring
        </CardTitle>
        <CardDescription>
          Real-time scraper session tracking and job import statistics (Last 24 hours)
        </CardDescription>
      </CardHeader>
      <CardContent>
        {/* Stats Summary */}
        <StatsSummary />

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="active">
              Active Sessions
            </TabsTrigger>
            <TabsTrigger value="recent">
              Recent Activity
            </TabsTrigger>
          </TabsList>
          <TabsContent value="active" className="mt-4">
            <ActiveSessionsList />
          </TabsContent>
          <TabsContent value="recent" className="mt-4">
            <RecentSessionsList />
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
