/**
 * Jobs Preview Component
 * Shows recent job imports by platform
 */

import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ScrollArea } from "@/components/ui/scroll-area";
import { jobImportsApi, type JobImportBatch } from "@/lib/dashboard-api";
import { usePMAdminAuth } from "@/hooks/usePMAdminAuth";
import { 
  Briefcase, 
  CheckCircle2, 
  Clock, 
  AlertCircle 
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";

function PlatformBadge({ platform }: { platform: string }) {
  const colors: Record<string, string> = {
    indeed: "bg-blue-100 text-blue-700 border-blue-200",
    dice: "bg-purple-100 text-purple-700 border-purple-200",
    linkedin: "bg-sky-100 text-sky-700 border-sky-200",
    techfetch: "bg-green-100 text-green-700 border-green-200",
    glassdoor: "bg-emerald-100 text-emerald-700 border-emerald-200",
    monster: "bg-orange-100 text-orange-700 border-orange-200",
  };

  return (
    <Badge variant="outline" className={colors[platform] || ""}>
      {platform}
    </Badge>
  );
}

function BatchItem({ batch }: { batch: JobImportBatch }) {
  const timeAgo = formatDistanceToNow(new Date(batch.startedAt), { addSuffix: true });
  const isCompleted = batch.importStatus === 'COMPLETED';
  const isFailed = batch.importStatus === 'FAILED';

  return (
    <div className="flex items-center justify-between p-3 rounded-lg border bg-card hover:bg-accent/50 transition-colors">
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-full ${
          isCompleted ? 'bg-green-100 text-green-600' :
          isFailed ? 'bg-red-100 text-red-600' :
          'bg-blue-100 text-blue-600'
        }`}>
          {isCompleted ? (
            <CheckCircle2 className="h-4 w-4" />
          ) : isFailed ? (
            <AlertCircle className="h-4 w-4" />
          ) : (
            <Clock className="h-4 w-4" />
          )}
        </div>
        <div>
          <div className="flex items-center gap-2">
            <PlatformBadge platform={batch.platform} />
            <span className="text-xs text-muted-foreground">{timeAgo}</span>
          </div>
          <p className="text-sm mt-1">
            <span className="font-medium">{batch.newJobs}</span> new
            {batch.updatedJobs > 0 && (
              <span className="text-muted-foreground"> • {batch.updatedJobs} updated</span>
            )}
            {batch.failedJobs > 0 && (
              <span className="text-destructive"> • {batch.failedJobs} failed</span>
            )}
          </p>
        </div>
      </div>
      <div className="text-right">
        <p className="text-lg font-bold">{batch.totalJobs}</p>
        <p className="text-xs text-muted-foreground">total jobs</p>
      </div>
    </div>
  );
}

export function JobsPreview() {
  const { isAuthenticated, isLoading: authLoading } = usePMAdminAuth();
  const { data: stats, isLoading, error } = useQuery({
    queryKey: ['job-import-stats'],
    queryFn: jobImportsApi.getStatistics,
    refetchInterval: 60000, // Refresh every minute
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
          <div className="space-y-3">
            {[...Array(4)].map((_, i) => (
              <Skeleton key={i} className="h-16 w-full" />
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
            <p className="text-sm text-destructive">Failed to load job imports</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Briefcase className="h-5 w-5" />
          Jobs Overview
        </CardTitle>
        <CardDescription>
          {stats?.totalJobs.toLocaleString() || 0} total jobs across {stats?.totalBatches || 0} imports
        </CardDescription>
      </CardHeader>
      <CardContent>
        {/* Platform breakdown */}
        <div className="grid grid-cols-3 gap-2 mb-4">
          {Object.entries(stats?.jobsByPlatform || {}).map(([platform, count]) => (
            <div 
              key={platform} 
              className="flex flex-col items-center p-2 rounded-lg bg-muted/50"
            >
              <PlatformBadge platform={platform} />
              <span className="text-lg font-bold mt-1">{count.toLocaleString()}</span>
            </div>
          ))}
        </div>

        {/* Recent imports */}
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-muted-foreground">Recent Imports</h4>
          <ScrollArea className="h-[200px]">
            <div className="space-y-2 pr-4">
              {stats?.recentImports.length === 0 ? (
                <div className="text-center py-4">
                  <p className="text-sm text-muted-foreground">No recent imports</p>
                </div>
              ) : (
                stats?.recentImports.map((batch) => (
                  <BatchItem key={batch.batchId} batch={batch} />
                ))
              )}
            </div>
          </ScrollArea>
        </div>
      </CardContent>
    </Card>
  );
}
