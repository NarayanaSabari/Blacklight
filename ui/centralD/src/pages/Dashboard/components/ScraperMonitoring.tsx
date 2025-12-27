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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { scraperMonitoringApi, type ScrapeSession, type SessionPlatformStatus, type ScraperStats } from "@/lib/dashboard-api";
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
  RotateCcw,
  Eye,
  AlertTriangle,
  MapPin,
  Globe,
  TrendingUp,
  BarChart3
} from "lucide-react";
import { formatDistanceToNow, format } from "date-fns";
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

function PlatformStatusBadge({ status }: { status: SessionPlatformStatus['status'] }) {
  const variants: Record<SessionPlatformStatus['status'], { variant: "default" | "secondary" | "destructive" | "outline"; label: string; className: string }> = {
    pending: { variant: "outline", label: "Pending", className: "text-gray-500" },
    in_progress: { variant: "default", label: "Running", className: "bg-blue-500" },
    completed: { variant: "secondary", label: "Completed", className: "bg-green-100 text-green-800" },
    failed: { variant: "destructive", label: "Failed", className: "" },
    skipped: { variant: "outline", label: "Skipped", className: "text-yellow-600 border-yellow-500" },
  };

  const { variant, label, className } = variants[status] || { variant: "outline" as const, label: status, className: "" };
  return <Badge variant={variant} className={className}>{label}</Badge>;
}

function SessionDetailsDialog({ session }: { session: ScrapeSession }) {
  const [open, setOpen] = useState(false);
  
  const { data: sessionDetails, isLoading, error } = useQuery({
    queryKey: ['session-details', session.sessionId],
    queryFn: () => scraperMonitoringApi.getSessionDetails(session.sessionId),
    enabled: open,
  });
  
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm" className="h-7 gap-1.5">
          <Eye className="h-3.5 w-3.5" />
          <span className="text-xs">Details</span>
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 flex-wrap">
            <span>Session Details</span>
            <SessionStatusBadge status={session.status} />
          </DialogTitle>
          <DialogDescription className="flex flex-col gap-1">
            <span className="text-sm font-medium text-foreground">{session.roleName}</span>
            <div className="flex items-center gap-2">
              {session.location && (
                <Badge variant="outline" className="text-xs gap-1 border-blue-300 text-blue-600 bg-blue-50">
                  <MapPin className="h-3 w-3" />
                  {session.location}
                </Badge>
              )}
              <span className="text-xs text-muted-foreground">• {session.scraperKeyName}</span>
            </div>
          </DialogDescription>
        </DialogHeader>
        
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : error ? (
          <div className="p-4 rounded bg-destructive/10 border border-destructive/20">
            <p className="text-sm text-destructive">Failed to load session details</p>
          </div>
        ) : sessionDetails ? (
          <div className="space-y-4">
            {/* Scrape Target Info */}
            <div className="p-3 rounded-lg bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-full bg-blue-100">
                  <Activity className="h-4 w-4 text-blue-600" />
                </div>
                <div className="flex-1">
                  <p className="text-xs text-blue-600 font-medium">Scrape Target</p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="font-semibold text-blue-900">{sessionDetails.roleName}</span>
                    <span className="text-blue-400">→</span>
                    {sessionDetails.location ? (
                      <Badge className="gap-1 bg-blue-600 text-white">
                        <MapPin className="h-3 w-3" />
                        {sessionDetails.location}
                      </Badge>
                    ) : (
                      <span className="text-sm text-muted-foreground italic">No location data</span>
                    )}
                  </div>
                </div>
              </div>
            </div>
            
            {/* Session Summary */}
            <div className="grid grid-cols-4 gap-3">
              <div className="p-3 rounded-lg bg-muted/50 text-center">
                <p className="text-xs text-muted-foreground">Jobs Found</p>
                <p className="text-lg font-semibold">{sessionDetails.jobsFound}</p>
              </div>
              <div className="p-3 rounded-lg bg-green-50 text-center">
                <p className="text-xs text-green-600">Imported</p>
                <p className="text-lg font-semibold text-green-700">{sessionDetails.jobsImported}</p>
              </div>
              <div className="p-3 rounded-lg bg-yellow-50 text-center">
                <p className="text-xs text-yellow-600">Skipped</p>
                <p className="text-lg font-semibold text-yellow-700">{sessionDetails.jobsSkipped}</p>
              </div>
              <div className="p-3 rounded-lg bg-muted/50 text-center">
                <p className="text-xs text-muted-foreground">Duration</p>
                <p className="text-lg font-semibold">
                  {sessionDetails.durationSeconds ? `${sessionDetails.durationSeconds}s` : '-'}
                </p>
              </div>
            </div>
            
            {/* Session-level error */}
            {sessionDetails.errorMessage && (
              <div className="p-3 rounded-lg bg-destructive/10 border border-destructive/20">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="h-4 w-4 text-destructive mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-destructive">Session Error</p>
                    <p className="text-sm text-destructive/80">{sessionDetails.errorMessage}</p>
                  </div>
                </div>
              </div>
            )}
            
            {/* Platform Statuses */}
            <div>
              <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
                <Layers className="h-4 w-4" />
                Platform Results ({sessionDetails.platformStatuses.length})
              </h4>
              <div className="space-y-2">
                {sessionDetails.platformStatuses.map((platform) => (
                  <div 
                    key={platform.id} 
                    className={`p-3 rounded-lg border ${
                      platform.status === 'failed' 
                        ? 'border-destructive/30 bg-destructive/5' 
                        : platform.status === 'completed'
                        ? 'border-green-200 bg-green-50/50'
                        : 'border-muted'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-sm">{platform.platformName}</span>
                        <PlatformStatusBadge status={platform.status} />
                      </div>
                      {platform.durationSeconds && (
                        <span className="text-xs text-muted-foreground">
                          {platform.durationSeconds}s
                        </span>
                      )}
                    </div>
                    
                    {/* Platform stats */}
                    <div className="flex gap-4 text-xs text-muted-foreground">
                      <span>Found: {platform.jobsFound}</span>
                      <span className="text-green-600">Imported: {platform.jobsImported}</span>
                      <span className="text-yellow-600">Skipped: {platform.jobsSkipped}</span>
                    </div>
                    
                    {/* Platform error */}
                    {platform.status === 'failed' && platform.errorMessage && (
                      <div className="mt-2 p-2 rounded bg-destructive/10">
                        <p className="text-xs text-destructive font-medium">Error:</p>
                        <p className="text-xs text-destructive/80 break-words">{platform.errorMessage}</p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
            
            {/* Timestamps */}
            <div className="pt-3 border-t text-xs text-muted-foreground">
              <div className="flex justify-between">
                <span>Started: {sessionDetails.startedAt ? format(new Date(sessionDetails.startedAt), 'PPpp') : '-'}</span>
                <span>Completed: {sessionDetails.completedAt ? format(new Date(sessionDetails.completedAt), 'PPpp') : '-'}</span>
              </div>
            </div>
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  );
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
            <div className="flex items-center gap-2 flex-wrap">
              <p className="font-medium">{session.roleName}</p>
              {session.location && (
                <Badge variant="outline" className="text-xs gap-1 border-blue-300 text-blue-600 bg-blue-50">
                  <MapPin className="h-3 w-3" />
                  {session.location}
                </Badge>
              )}
            </div>
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
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <div className="flex items-center gap-2">
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
          <SessionDetailsDialog session={session} />
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
    refetchInterval: 15000, // Refresh every 15 seconds for active sessions
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

function LocationAnalytics({ stats }: { stats: ScraperStats }) {
  const { locationAnalytics } = stats;
  const totalLocationSessions = locationAnalytics.sessionsWithLocation + locationAnalytics.sessionsWithoutLocation;
  const locationSessionPercentage = totalLocationSessions > 0 
    ? Math.round((locationAnalytics.sessionsWithLocation / totalLocationSessions) * 100)
    : 0;
  
  return (
    <div className="space-y-4">
      {/* Location Queue Overview */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="p-3 rounded-lg bg-blue-50 border border-blue-200">
          <div className="flex items-center gap-2">
            <Globe className="h-4 w-4 text-blue-600" />
            <span className="text-xs text-blue-600 font-medium">Total Queue</span>
          </div>
          <p className="text-2xl font-bold text-blue-700 mt-1">
            {locationAnalytics.queue.total}
          </p>
          <p className="text-xs text-blue-500">
            {locationAnalytics.queue.uniqueLocations} unique locations
          </p>
        </div>
        <div className="p-3 rounded-lg bg-yellow-50 border border-yellow-200">
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-yellow-600" />
            <span className="text-xs text-yellow-600 font-medium">Pending</span>
          </div>
          <p className="text-2xl font-bold text-yellow-700 mt-1">
            {locationAnalytics.queue.pending}
          </p>
        </div>
        <div className="p-3 rounded-lg bg-green-50 border border-green-200">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-green-600" />
            <span className="text-xs text-green-600 font-medium">Approved</span>
          </div>
          <p className="text-2xl font-bold text-green-700 mt-1">
            {locationAnalytics.queue.approved}
          </p>
        </div>
        <div className="p-3 rounded-lg bg-purple-50 border border-purple-200">
          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-purple-600" />
            <span className="text-xs text-purple-600 font-medium">Processing</span>
          </div>
          <p className="text-2xl font-bold text-purple-700 mt-1">
            {locationAnalytics.queue.processing}
          </p>
        </div>
      </div>

      {/* Session Distribution */}
      <div className="p-4 rounded-lg border bg-muted/30">
        <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
          <BarChart3 className="h-4 w-4" />
          Session Distribution (Last 24h)
        </h4>
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <div className="flex justify-between text-xs mb-1">
              <span className="text-muted-foreground">Location-based Scraping</span>
              <span className={locationSessionPercentage > 50 ? 'text-blue-600' : 'text-muted-foreground'}>
                {locationSessionPercentage}%
              </span>
            </div>
            <Progress value={locationSessionPercentage} className="h-2" />
          </div>
          <div className="text-right text-xs">
            <span className="text-blue-600 font-medium">{locationAnalytics.sessionsWithLocation}</span>
            <span className="text-muted-foreground"> / {totalLocationSessions} sessions</span>
          </div>
        </div>
      </div>

      {/* Top Locations by Jobs Imported */}
      {locationAnalytics.topLocations.length > 0 && (
        <div className="p-4 rounded-lg border">
          <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
            <TrendingUp className="h-4 w-4" />
            Top Locations by Jobs Imported (Last 24h)
          </h4>
          <div className="space-y-2">
            {locationAnalytics.topLocations.map((loc, idx) => {
              const maxJobs = locationAnalytics.topLocations[0]?.jobsImported || 1;
              const barWidth = (loc.jobsImported / maxJobs) * 100;
              const successRate = loc.jobsFound > 0 
                ? Math.round((loc.jobsImported / loc.jobsFound) * 100) 
                : 0;
              
              return (
                <div key={loc.location} className="relative">
                  <div 
                    className="absolute inset-y-0 left-0 bg-blue-100 rounded-lg transition-all"
                    style={{ width: `${barWidth}%` }}
                  />
                  <div className="relative flex items-center justify-between p-2 rounded-lg">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium text-muted-foreground w-5">#{idx + 1}</span>
                      <MapPin className="h-3.5 w-3.5 text-blue-600" />
                      <span className="text-sm font-medium truncate max-w-[200px]">{loc.location}</span>
                    </div>
                    <div className="flex items-center gap-4 text-xs">
                      <span className="text-muted-foreground">
                        {loc.sessionCount} session{loc.sessionCount !== 1 ? 's' : ''}
                      </span>
                      <span className="text-blue-600">
                        {loc.jobsFound} found
                      </span>
                      <span className="text-green-600 font-medium">
                        {loc.jobsImported} imported
                      </span>
                      <Badge 
                        variant={successRate >= 80 ? "secondary" : successRate >= 50 ? "outline" : "destructive"}
                        className={`text-xs ${successRate >= 80 ? 'bg-green-100 text-green-800' : ''}`}
                      >
                        {successRate}%
                      </Badge>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {locationAnalytics.topLocations.length === 0 && (
        <div className="text-center py-8 text-muted-foreground">
          <MapPin className="h-8 w-8 mx-auto mb-2 opacity-50" />
          <p className="text-sm">No location-based sessions in the last 24 hours</p>
          <p className="text-xs mt-1">Run scraper with --mode role-location to see location analytics</p>
        </div>
      )}
    </div>
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
  const { isAuthenticated, isLoading: authLoading } = usePMAdminAuth();
  
  const { data: stats } = useQuery({
    queryKey: ['scraper-stats-for-location'],
    queryFn: scraperMonitoringApi.getStats,
    refetchInterval: 30000,
    enabled: !authLoading && isAuthenticated,
  });

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
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="active">
              Active Sessions
            </TabsTrigger>
            <TabsTrigger value="recent">
              Recent Activity
            </TabsTrigger>
            <TabsTrigger value="locations" className="gap-1">
              <MapPin className="h-3.5 w-3.5" />
              Location Analytics
            </TabsTrigger>
          </TabsList>
          <TabsContent value="active" className="mt-4">
            <ActiveSessionsList />
          </TabsContent>
          <TabsContent value="recent" className="mt-4">
            <RecentSessionsList />
          </TabsContent>
          <TabsContent value="locations" className="mt-4">
            {stats ? (
              <LocationAnalytics stats={stats} />
            ) : (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
