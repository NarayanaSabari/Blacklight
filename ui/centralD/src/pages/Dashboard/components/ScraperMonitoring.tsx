/**
 * Scraper Monitoring Component
 * Shows active scraper sessions and recent activity
 */

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { scraperMonitoringApi, type ScrapeSession } from "@/lib/dashboard-api";
import { usePMAdminAuth } from "@/hooks/usePMAdminAuth";
import { 
  Activity, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  RefreshCw,
  Loader2
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";

function SessionStatusBadge({ status }: { status: ScrapeSession['status'] }) {
  const variants: Record<ScrapeSession['status'], { variant: "default" | "secondary" | "destructive" | "outline"; label: string }> = {
    in_progress: { variant: "default", label: "Running" },
    completed: { variant: "secondary", label: "Completed" },
    failed: { variant: "destructive", label: "Failed" },
  };

  const { variant, label } = variants[status];
  return <Badge variant={variant}>{label}</Badge>;
}

function SessionCard({ session }: { session: ScrapeSession }) {
  const timeAgo = formatDistanceToNow(new Date(session.startedAt), { addSuffix: true });
  
  return (
    <div className="flex items-center justify-between p-3 rounded-lg border bg-card hover:bg-accent/50 transition-colors">
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-full ${
          session.status === 'in_progress' ? 'bg-blue-100 text-blue-600' :
          session.status === 'completed' ? 'bg-green-100 text-green-600' :
          'bg-red-100 text-red-600'
        }`}>
          {session.status === 'in_progress' ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : session.status === 'completed' ? (
            <CheckCircle2 className="h-4 w-4" />
          ) : (
            <XCircle className="h-4 w-4" />
          )}
        </div>
        <div>
          <p className="font-medium text-sm">{session.roleName}</p>
          <p className="text-xs text-muted-foreground">
            {session.scraperKeyName}
          </p>
        </div>
      </div>
      <div className="text-right">
        <div className="flex items-center gap-2">
          <SessionStatusBadge status={session.status} />
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          {session.status === 'in_progress' ? (
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              Started {timeAgo}
            </span>
          ) : (
            <>
              {session.jobsImported} jobs • {session.durationSeconds}s
            </>
          )}
        </p>
        {session.errorMessage && (
          <p className="text-xs text-destructive mt-1 max-w-[200px] truncate">
            {session.errorMessage}
          </p>
        )}
      </div>
    </div>
  );
}

function ActiveSessionsList() {
  const { isAuthenticated, isLoading: authLoading } = usePMAdminAuth();
  const { data: sessions, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['active-scraper-sessions'],
    queryFn: scraperMonitoringApi.getActiveSessions,
    refetchInterval: 5000, // Refresh every 5 seconds for active sessions
    enabled: !authLoading && isAuthenticated,
  });

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
        <SessionCard key={session.id} session={session} />
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
          Real-time scraper session tracking and observability
        </CardDescription>
      </CardHeader>
      <CardContent>
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
