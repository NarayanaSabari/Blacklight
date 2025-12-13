/**
 * Jobs Preview Component
 * Shows detailed job import statistics with platform breakdown
 */

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { 
  Collapsible, 
  CollapsibleContent, 
  CollapsibleTrigger 
} from "@/components/ui/collapsible";
import { jobImportsApi, type JobImportBatch, type PlatformStatus } from "@/lib/dashboard-api";
import { usePMAdminAuth } from "@/hooks/usePMAdminAuth";
import { 
  Briefcase, 
  CheckCircle2, 
  Clock, 
  AlertCircle,
  ChevronDown,
  ChevronRight,
  TrendingUp,
  Activity,
  Timer,
  BarChart3,
  XCircle,
  Loader2,
  AlertTriangle
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";

// Platform badge colors
const platformColors: Record<string, string> = {
  indeed: "bg-blue-100 text-blue-700 border-blue-200",
  dice: "bg-purple-100 text-purple-700 border-purple-200",
  linkedin: "bg-sky-100 text-sky-700 border-sky-200",
  techfetch: "bg-green-100 text-green-700 border-green-200",
  glassdoor: "bg-emerald-100 text-emerald-700 border-emerald-200",
  monster: "bg-orange-100 text-orange-700 border-orange-200",
};

// Status configurations
const statusConfig = {
  completed: { icon: CheckCircle2, color: "text-green-600", bg: "bg-green-100" },
  failed: { icon: XCircle, color: "text-red-600", bg: "bg-red-100" },
  in_progress: { icon: Loader2, color: "text-blue-600", bg: "bg-blue-100" },
  pending: { icon: Clock, color: "text-gray-600", bg: "bg-gray-100" },
  timeout: { icon: AlertTriangle, color: "text-amber-600", bg: "bg-amber-100" },
  skipped: { icon: AlertCircle, color: "text-gray-500", bg: "bg-gray-100" },
};

function PlatformBadge({ platform }: { platform: string }) {
  return (
    <Badge variant="outline" className={platformColors[platform.toLowerCase()] || "bg-gray-100 text-gray-700"}>
      {platform}
    </Badge>
  );
}

function StatusIcon({ status }: { status: string }) {
  const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.pending;
  const Icon = config.icon;
  return (
    <div className={`p-1.5 rounded-full ${config.bg}`}>
      <Icon className={`h-3.5 w-3.5 ${config.color} ${status === 'in_progress' ? 'animate-spin' : ''}`} />
    </div>
  );
}

function PlatformStatusRow({ platform }: { platform: PlatformStatus }) {
  const hasFailed = platform.status === 'failed';
  
  return (
    <div className={`flex items-center justify-between py-2 px-3 rounded-md ${hasFailed ? 'bg-red-50' : 'bg-muted/30'}`}>
      <div className="flex items-center gap-2">
        <StatusIcon status={platform.status} />
        <div>
          <div className="flex items-center gap-2">
            <span className="font-medium text-sm">{platform.platformName}</span>
            <Badge variant="secondary" className="text-xs">
              {platform.statusLabel}
            </Badge>
          </div>
          {hasFailed && platform.errorMessage && (
            <p className="text-xs text-red-600 mt-0.5 max-w-[300px] truncate">
              {platform.errorMessage}
            </p>
          )}
        </div>
      </div>
      <div className="flex items-center gap-4 text-sm">
        <div className="text-right">
          <span className="font-semibold text-green-600">{platform.jobsImported}</span>
          <span className="text-muted-foreground"> imported</span>
        </div>
        {platform.jobsSkipped > 0 && (
          <div className="text-right">
            <span className="text-amber-600">{platform.jobsSkipped}</span>
            <span className="text-muted-foreground"> skipped</span>
          </div>
        )}
        {platform.durationFormatted && (
          <span className="text-xs text-muted-foreground w-14 text-right">
            {platform.durationFormatted}
          </span>
        )}
      </div>
    </div>
  );
}

function SessionItem({ batch }: { batch: JobImportBatch }) {
  const [isOpen, setIsOpen] = useState(false);
  const timeAgo = batch.startedAt ? formatDistanceToNow(new Date(batch.startedAt), { addSuffix: true }) : '';
  const isFailed = batch.importStatus === 'failed';
  
  const hasPlatforms = batch.platforms && batch.platforms.length > 0;
  const failedPlatforms = batch.platforms?.filter(p => p.status === 'failed') || [];
  
  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <div className={`rounded-lg border ${isFailed ? 'border-red-200 bg-red-50/50' : 'bg-card'}`}>
        <CollapsibleTrigger className="w-full">
          <div className="flex items-center justify-between p-3 hover:bg-accent/50 transition-colors rounded-t-lg">
            <div className="flex items-center gap-3">
              <StatusIcon status={batch.importStatus} />
              <div className="text-left">
                <div className="flex items-center gap-2">
                  <span className="font-medium">{batch.roleName || 'Unknown Role'}</span>
                  <span className="text-xs text-muted-foreground">{timeAgo}</span>
                </div>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-xs text-muted-foreground">
                    by {batch.scraperName || 'unknown'}
                  </span>
                  {batch.platformsTotal > 0 && (
                    <span className="text-xs">
                      <span className={batch.platformsFailed > 0 ? 'text-red-600' : 'text-green-600'}>
                        {batch.platformsCompleted}/{batch.platformsTotal}
                      </span>
                      <span className="text-muted-foreground"> platforms</span>
                    </span>
                  )}
                  {batch.durationFormatted && (
                    <span className="text-xs text-muted-foreground flex items-center gap-1">
                      <Timer className="h-3 w-3" />
                      {batch.durationFormatted}
                    </span>
                  )}
                </div>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              <div className="text-right">
                <div className="flex items-center gap-2">
                  <span className="text-lg font-bold text-green-600">{batch.newJobs}</span>
                  <span className="text-sm text-muted-foreground">new</span>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  {batch.skippedJobs > 0 && (
                    <span className="text-amber-600">{batch.skippedJobs} skipped</span>
                  )}
                  {batch.failedJobs > 0 && (
                    <span className="text-red-600">{batch.failedJobs} failed</span>
                  )}
                </div>
              </div>
              {hasPlatforms && (
                <div className="text-muted-foreground">
                  {isOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                </div>
              )}
            </div>
          </div>
        </CollapsibleTrigger>
        
        {hasPlatforms && (
          <CollapsibleContent>
            <div className="border-t px-3 py-2 space-y-1">
              {/* Show failed platforms first */}
              {failedPlatforms.length > 0 && (
                <div className="mb-2">
                  <p className="text-xs font-medium text-red-600 mb-1">
                    Failed Platforms ({failedPlatforms.length})
                  </p>
                  {failedPlatforms.map((platform) => (
                    <PlatformStatusRow key={platform.platformName} platform={platform} />
                  ))}
                </div>
              )}
              
              {/* Then show successful platforms */}
              {batch.platforms
                .filter(p => p.status !== 'failed')
                .map((platform) => (
                  <PlatformStatusRow key={platform.platformName} platform={platform} />
                ))}
            </div>
          </CollapsibleContent>
        )}
        
        {/* Error message at session level */}
        {(batch.errorMessage || batch.sessionNotes) && (
          <div className="border-t px-3 py-2 text-xs text-muted-foreground bg-muted/30">
            {batch.errorMessage && (
              <p className="text-red-600">{batch.errorMessage}</p>
            )}
            {batch.sessionNotes && (
              <p>{batch.sessionNotes}</p>
            )}
          </div>
        )}
      </div>
    </Collapsible>
  );
}

function StatCard({ 
  title, 
  value, 
  subtitle, 
  icon: Icon, 
  className = ""
}: { 
  title: string; 
  value: string | number; 
  subtitle?: string; 
  icon: React.ElementType;
  className?: string;
}) {
  return (
    <div className={`p-4 rounded-lg border bg-card ${className}`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-muted-foreground">{title}</p>
          <p className="text-2xl font-bold mt-1">{value}</p>
          {subtitle && (
            <p className="text-xs text-muted-foreground mt-0.5">{subtitle}</p>
          )}
        </div>
        <div className="p-2 rounded-full bg-muted">
          <Icon className="h-5 w-5 text-muted-foreground" />
        </div>
      </div>
    </div>
  );
}

function PlatformHealthCard({ platform, health }: { platform: string; health: { totalAttempts: number; successful: number; failed: number; successRate: number; jobsImported: number; avgDurationSeconds: number } }) {
  return (
    <div className="p-3 rounded-lg border bg-card">
      <div className="flex items-center justify-between mb-2">
        <PlatformBadge platform={platform} />
        <span className={`text-sm font-medium ${health.successRate >= 90 ? 'text-green-600' : health.successRate >= 70 ? 'text-amber-600' : 'text-red-600'}`}>
          {health.successRate}%
        </span>
      </div>
      <Progress value={health.successRate} className="h-1.5 mb-2" />
      <div className="grid grid-cols-3 gap-2 text-xs">
        <div>
          <span className="text-muted-foreground">Attempts</span>
          <p className="font-medium">{health.totalAttempts}</p>
        </div>
        <div>
          <span className="text-muted-foreground">Jobs</span>
          <p className="font-medium text-green-600">{health.jobsImported.toLocaleString()}</p>
        </div>
        <div>
          <span className="text-muted-foreground">Avg Time</span>
          <p className="font-medium">{Math.round(health.avgDurationSeconds)}s</p>
        </div>
      </div>
    </div>
  );
}

export function JobsPreview() {
  const { isAuthenticated, isLoading: authLoading } = usePMAdminAuth();
  const { data: stats, isLoading, error } = useQuery({
    queryKey: ['job-import-stats'],
    queryFn: jobImportsApi.getStatistics,
    refetchInterval: 30000, // Refresh every 30 seconds
    enabled: !authLoading && isAuthenticated,
  });

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-32" />
          <Skeleton className="h-4 w-48" />
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-4 gap-4 mb-4">
            {[...Array(4)].map((_, i) => (
              <Skeleton key={i} className="h-24 w-full" />
            ))}
          </div>
          <div className="space-y-3">
            {[...Array(4)].map((_, i) => (
              <Skeleton key={i} className="h-20 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="py-8">
          <div className="text-center">
            <AlertCircle className="h-8 w-8 text-destructive mx-auto mb-2" />
            <p className="text-sm text-destructive">Failed to load job imports</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const summary = stats?.summary;
  const platformHealth = stats?.platformHealth || {};

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Briefcase className="h-5 w-5" />
          Jobs Overview
        </CardTitle>
        <CardDescription>
          {stats?.totalJobs?.toLocaleString() || 0} total jobs across {stats?.totalBatches || 0} import sessions
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="overview" className="space-y-4">
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="recent">Recent Imports</TabsTrigger>
            <TabsTrigger value="platforms">Platform Health</TabsTrigger>
          </TabsList>
          
          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-4">
            {/* Summary Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard
                title="Total Jobs"
                value={stats?.totalJobs?.toLocaleString() || 0}
                subtitle={`${summary?.totalJobsImported?.toLocaleString() || 0} from scraper`}
                icon={Briefcase}
              />
              <StatCard
                title="Success Rate"
                value={`${summary?.successRate || 0}%`}
                subtitle={`${summary?.successfulSessions || 0} of ${summary?.totalSessions || 0} sessions`}
                icon={TrendingUp}
              />
              <StatCard
                title="Avg per Session"
                value={Math.round(summary?.avgJobsPerSession || 0)}
                subtitle="jobs imported"
                icon={BarChart3}
              />
              <StatCard
                title="Avg Duration"
                value={`${Math.round(summary?.avgDurationSeconds || 0)}s`}
                subtitle="per session"
                icon={Timer}
              />
            </div>
            
            {/* Session Status Breakdown */}
            <div className="grid grid-cols-4 gap-2">
              <div className="flex items-center gap-2 p-2 rounded-lg bg-green-50 border border-green-200">
                <CheckCircle2 className="h-4 w-4 text-green-600" />
                <div>
                  <p className="text-lg font-bold text-green-700">{summary?.successfulSessions || 0}</p>
                  <p className="text-xs text-green-600">Completed</p>
                </div>
              </div>
              <div className="flex items-center gap-2 p-2 rounded-lg bg-blue-50 border border-blue-200">
                <Loader2 className="h-4 w-4 text-blue-600" />
                <div>
                  <p className="text-lg font-bold text-blue-700">{summary?.inProgressSessions || 0}</p>
                  <p className="text-xs text-blue-600">In Progress</p>
                </div>
              </div>
              <div className="flex items-center gap-2 p-2 rounded-lg bg-red-50 border border-red-200">
                <XCircle className="h-4 w-4 text-red-600" />
                <div>
                  <p className="text-lg font-bold text-red-700">{summary?.failedSessions || 0}</p>
                  <p className="text-xs text-red-600">Failed</p>
                </div>
              </div>
              <div className="flex items-center gap-2 p-2 rounded-lg bg-amber-50 border border-amber-200">
                <AlertTriangle className="h-4 w-4 text-amber-600" />
                <div>
                  <p className="text-lg font-bold text-amber-700">{summary?.timeoutSessions || 0}</p>
                  <p className="text-xs text-amber-600">Timeout</p>
                </div>
              </div>
            </div>
            
            {/* Platform breakdown */}
            <div>
              <h4 className="text-sm font-medium text-muted-foreground mb-2">Jobs by Platform</h4>
              <div className="grid grid-cols-3 md:grid-cols-6 gap-2">
                {Object.entries(stats?.jobsByPlatform || {}).map(([platform, count]) => (
                  <div 
                    key={platform} 
                    className="flex flex-col items-center p-3 rounded-lg bg-muted/50 border"
                  >
                    <PlatformBadge platform={platform} />
                    <span className="text-lg font-bold mt-2">{count.toLocaleString()}</span>
                  </div>
                ))}
              </div>
            </div>
          </TabsContent>
          
          {/* Recent Imports Tab */}
          <TabsContent value="recent">
            <ScrollArea className="h-[500px]">
              <div className="space-y-2 pr-4">
                {stats?.recentImports.length === 0 ? (
                  <div className="text-center py-8">
                    <Clock className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
                    <p className="text-sm text-muted-foreground">No recent imports</p>
                  </div>
                ) : (
                  stats?.recentImports.map((batch) => (
                    <SessionItem key={batch.batchId} batch={batch} />
                  ))
                )}
              </div>
            </ScrollArea>
          </TabsContent>
          
          {/* Platform Health Tab */}
          <TabsContent value="platforms">
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {Object.entries(platformHealth).length === 0 ? (
                <div className="col-span-full text-center py-8">
                  <Activity className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
                  <p className="text-sm text-muted-foreground">No platform data yet</p>
                </div>
              ) : (
                Object.entries(platformHealth).map(([platform, health]) => (
                  <PlatformHealthCard key={platform} platform={platform} health={health} />
                ))
              )}
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
