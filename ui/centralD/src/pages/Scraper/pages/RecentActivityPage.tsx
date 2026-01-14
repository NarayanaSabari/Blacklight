/**
 * Recent Activity Page
 * Shows completed and failed scraper sessions with detailed metrics
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Progress } from '@/components/ui/progress';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { scraperMonitoringApi, type ScrapeSession } from '@/lib/dashboard-api';
import { usePMAdminAuth } from '@/hooks/usePMAdminAuth';
import { 
  CheckCircle2, 
  XCircle, 
  Clock, 
  RefreshCw,
  FileText,
  FileCheck,
  FileX,
  Layers,
  Timer,
  StopCircle,
  AlertTriangle,
  MapPin,
  Search,
  Filter,
  Eye,
  ArrowRight,
  TrendingUp,
  TrendingDown,
  History
} from 'lucide-react';
import { formatDistanceToNow, format } from 'date-fns';

// Session status badge
function SessionStatusBadge({ status }: { status: ScrapeSession['status'] }) {
  const variants: Record<ScrapeSession['status'], { 
    variant: "default" | "secondary" | "destructive" | "outline"; 
    label: string; 
    className: string;
    icon: React.ReactNode;
  }> = {
    in_progress: { 
      variant: "default", 
      label: "Running", 
      className: "bg-blue-500",
      icon: <Clock className="h-3 w-3 animate-pulse" />
    },
    completed: { 
      variant: "secondary", 
      label: "Completed", 
      className: "bg-green-100 text-green-800",
      icon: <CheckCircle2 className="h-3 w-3" />
    },
    failed: { 
      variant: "destructive", 
      label: "Failed", 
      className: "",
      icon: <XCircle className="h-3 w-3" />
    },
    terminated: { 
      variant: "outline", 
      label: "Terminated", 
      className: "border-orange-500 text-orange-600",
      icon: <StopCircle className="h-3 w-3" />
    },
  };

  const { variant, label, className, icon } = variants[status] || { 
    variant: "outline" as const, 
    label: status, 
    className: "",
    icon: null 
  };
  
  return (
    <Badge variant={variant} className={`gap-1 ${className}`}>
      {icon}
      {label}
    </Badge>
  );
}

// Session Details Dialog
function SessionDetailsDialog({ session }: { session: ScrapeSession }) {
  const { data: sessionDetails, isLoading } = useQuery({
    queryKey: ['session-details', session.sessionId],
    queryFn: () => scraperMonitoringApi.getSessionDetails(session.sessionId),
  });
  
  const successRate = session.jobsFound > 0 
    ? Math.round((session.jobsImported / session.jobsFound) * 100) 
    : 0;

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm" className="h-8 gap-1">
          <Eye className="h-3.5 w-3.5" />
          Details
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 flex-wrap">
            <span>{session.roleName}</span>
            <SessionStatusBadge status={session.status} />
          </DialogTitle>
          <DialogDescription className="flex items-center gap-2">
            {session.location && (
              <span className="flex items-center gap-1">
                <MapPin className="h-3 w-3" />
                {session.location}
              </span>
            )}
            <span>•</span>
            <span>{session.scraperKeyName}</span>
            <span>•</span>
            <span>{format(new Date(session.startedAt), 'PPpp')}</span>
          </DialogDescription>
        </DialogHeader>
        
        {isLoading ? (
          <div className="space-y-4">
            <Skeleton className="h-24" />
            <Skeleton className="h-48" />
          </div>
        ) : (
          <div className="space-y-6 mt-4">
            {/* Summary Stats */}
            <div className="grid grid-cols-4 gap-4">
              <div className="text-center p-4 rounded-lg bg-muted/50 border">
                <FileText className="h-5 w-5 mx-auto text-gray-500 mb-2" />
                <p className="text-2xl font-bold">{session.jobsFound}</p>
                <p className="text-xs text-muted-foreground">Jobs Found</p>
              </div>
              <div className="text-center p-4 rounded-lg bg-green-50 border border-green-200">
                <FileCheck className="h-5 w-5 mx-auto text-green-600 mb-2" />
                <p className="text-2xl font-bold text-green-700">{session.jobsImported}</p>
                <p className="text-xs text-green-600">Imported</p>
              </div>
              <div className="text-center p-4 rounded-lg bg-yellow-50 border border-yellow-200">
                <FileX className="h-5 w-5 mx-auto text-yellow-600 mb-2" />
                <p className="text-2xl font-bold text-yellow-700">{session.jobsSkipped}</p>
                <p className="text-xs text-yellow-600">Skipped</p>
              </div>
              <div className="text-center p-4 rounded-lg bg-muted/50 border">
                <Timer className="h-5 w-5 mx-auto text-purple-500 mb-2" />
                <p className="text-2xl font-bold">
                  {session.durationSeconds ? `${session.durationSeconds}s` : '-'}
                </p>
                <p className="text-xs text-muted-foreground">Duration</p>
              </div>
            </div>
            
            {/* Success Rate */}
            <div className="p-4 rounded-lg border">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-medium flex items-center gap-2">
                  {successRate >= 50 ? (
                    <TrendingUp className="h-4 w-4 text-green-500" />
                  ) : (
                    <TrendingDown className="h-4 w-4 text-red-500" />
                  )}
                  Import Success Rate
                </span>
                <span className={`text-sm font-bold ${
                  successRate >= 80 ? 'text-green-600' : 
                  successRate >= 50 ? 'text-yellow-600' : 
                  'text-red-600'
                }`}>
                  {successRate}%
                </span>
              </div>
              <Progress value={successRate} className="h-2" />
            </div>
            
            {/* Error Message */}
            {session.errorMessage && (
              <div className="p-4 rounded-lg bg-red-50 border border-red-200">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="font-medium text-red-800">Session Error</p>
                    <p className="text-sm text-red-700 mt-1">{session.errorMessage}</p>
                  </div>
                </div>
              </div>
            )}
            
            {/* Platform Breakdown */}
            {sessionDetails && sessionDetails.platformStatuses.length > 0 && (
              <div>
                <h4 className="font-medium mb-3 flex items-center gap-2">
                  <Layers className="h-4 w-4" />
                  Platform Results ({sessionDetails.platformStatuses.length})
                </h4>
                <div className="space-y-2">
                  {sessionDetails.platformStatuses.map((platform) => (
                    <div 
                      key={platform.id}
                      className={`p-3 rounded-lg border flex items-center justify-between ${
                        platform.status === 'completed' ? 'bg-green-50/50 border-green-200' :
                        platform.status === 'failed' ? 'bg-red-50/50 border-red-200' :
                        'bg-muted/30'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div className={`p-1.5 rounded-full ${
                          platform.status === 'completed' ? 'bg-green-100' :
                          platform.status === 'failed' ? 'bg-red-100' :
                          platform.status === 'skipped' ? 'bg-yellow-100' :
                          'bg-gray-100'
                        }`}>
                          {platform.status === 'completed' && <CheckCircle2 className="h-4 w-4 text-green-600" />}
                          {platform.status === 'failed' && <XCircle className="h-4 w-4 text-red-600" />}
                          {platform.status === 'skipped' && <AlertTriangle className="h-4 w-4 text-yellow-600" />}
                          {(platform.status === 'pending' || platform.status === 'in_progress') && <Clock className="h-4 w-4 text-gray-500" />}
                        </div>
                        <div>
                          <p className="font-medium text-sm capitalize">{platform.platformName}</p>
                          <div className="flex items-center gap-3 text-xs text-muted-foreground">
                            <span>Found: {platform.jobsFound}</span>
                            <span className="text-green-600">Imported: {platform.jobsImported}</span>
                            <span className="text-yellow-600">Skipped: {platform.jobsSkipped}</span>
                          </div>
                        </div>
                      </div>
                      {platform.durationSeconds && (
                        <Badge variant="outline" className="tabular-nums">
                          {platform.durationSeconds}s
                        </Badge>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            {/* Actions */}
            <div className="flex justify-end pt-4 border-t">
              <Link to={`/sessions/${session.sessionId}`}>
                <Button className="gap-2">
                  <FileText className="h-4 w-4" />
                  View Job Logs
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

export function RecentActivityPage() {
  const { isAuthenticated, isLoading: authLoading } = usePMAdminAuth();
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  
  const { data: sessions, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['recent-scraper-sessions'],
    queryFn: () => scraperMonitoringApi.getRecentSessions(50),
    refetchInterval: 30000, // Refresh every 30 seconds
    enabled: !authLoading && isAuthenticated,
  });

  // Filter sessions
  const filteredSessions = sessions?.filter(session => {
    const matchesStatus = statusFilter === 'all' || session.status === statusFilter;
    const matchesSearch = !searchQuery || 
      session.roleName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      session.scraperKeyName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (session.location?.toLowerCase().includes(searchQuery.toLowerCase()) ?? false);
    return matchesStatus && matchesSearch;
  }) || [];

  // Calculate stats
  const stats = sessions ? {
    total: sessions.length,
    completed: sessions.filter(s => s.status === 'completed').length,
    failed: sessions.filter(s => s.status === 'failed').length,
    terminated: sessions.filter(s => s.status === 'terminated').length,
    totalJobs: sessions.reduce((sum, s) => sum + s.jobsFound, 0),
    totalImported: sessions.reduce((sum, s) => sum + s.jobsImported, 0),
  } : null;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <History className="h-6 w-6 text-gray-600" />
            Recent Activity
          </h1>
          <p className="text-muted-foreground">
            Browse completed and failed scraper sessions
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

      {/* Stats Summary */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
          <Card className="p-4">
            <p className="text-xs text-muted-foreground">Total Sessions</p>
            <p className="text-2xl font-bold">{stats.total}</p>
          </Card>
          <Card className="p-4">
            <p className="text-xs text-green-600">Completed</p>
            <p className="text-2xl font-bold text-green-700">{stats.completed}</p>
          </Card>
          <Card className="p-4">
            <p className="text-xs text-red-600">Failed</p>
            <p className="text-2xl font-bold text-red-700">{stats.failed}</p>
          </Card>
          <Card className="p-4">
            <p className="text-xs text-orange-600">Terminated</p>
            <p className="text-2xl font-bold text-orange-700">{stats.terminated}</p>
          </Card>
          <Card className="p-4">
            <p className="text-xs text-muted-foreground">Jobs Found</p>
            <p className="text-2xl font-bold">{stats.totalJobs.toLocaleString()}</p>
          </Card>
          <Card className="p-4">
            <p className="text-xs text-green-600">Jobs Imported</p>
            <p className="text-2xl font-bold text-green-700">{stats.totalImported.toLocaleString()}</p>
          </Card>
        </div>
      )}

      {/* Filters */}
      <Card>
        <CardHeader className="pb-4">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <CardTitle className="text-lg">Session History</CardTitle>
            <div className="flex items-center gap-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search by role, scraper, location..."
                  className="pl-9 w-64"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-40">
                  <Filter className="h-4 w-4 mr-2" />
                  <SelectValue placeholder="All statuses" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Statuses</SelectItem>
                  <SelectItem value="completed">Completed</SelectItem>
                  <SelectItem value="failed">Failed</SelectItem>
                  <SelectItem value="terminated">Terminated</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">
              {[...Array(10)].map((_, i) => (
                <Skeleton key={i} className="h-14" />
              ))}
            </div>
          ) : error ? (
            <div className="text-center py-12">
              <XCircle className="h-12 w-12 mx-auto text-red-500 mb-4" />
              <p className="text-lg font-medium">Failed to load sessions</p>
              <Button variant="outline" onClick={() => refetch()} className="mt-4">
                Try Again
              </Button>
            </div>
          ) : filteredSessions.length === 0 ? (
            <div className="text-center py-12">
              <History className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-lg font-medium">No sessions found</p>
              <p className="text-sm text-muted-foreground">
                {searchQuery || statusFilter !== 'all' 
                  ? 'Try adjusting your filters' 
                  : 'No recent scraper sessions available'}
              </p>
            </div>
          ) : (
            <ScrollArea className="h-[500px]">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Status</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Location</TableHead>
                    <TableHead>Scraper</TableHead>
                    <TableHead className="text-right">Jobs</TableHead>
                    <TableHead className="text-right">Imported</TableHead>
                    <TableHead className="text-right">Duration</TableHead>
                    <TableHead>Started</TableHead>
                    <TableHead></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredSessions.map((session) => (
                    <TableRow key={session.id}>
                      <TableCell>
                        <SessionStatusBadge status={session.status} />
                      </TableCell>
                      <TableCell className="font-medium max-w-48 truncate">
                        {session.roleName}
                      </TableCell>
                      <TableCell>
                        {session.location ? (
                          <span className="flex items-center gap-1 text-sm">
                            <MapPin className="h-3 w-3" />
                            {session.location}
                          </span>
                        ) : (
                          <span className="text-muted-foreground">-</span>
                        )}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {session.scraperKeyName}
                      </TableCell>
                      <TableCell className="text-right">{session.jobsFound}</TableCell>
                      <TableCell className="text-right text-green-600">
                        {session.jobsImported}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {session.durationSeconds ? `${session.durationSeconds}s` : '-'}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {formatDistanceToNow(new Date(session.startedAt), { addSuffix: true })}
                      </TableCell>
                      <TableCell>
                        <SessionDetailsDialog session={session} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </ScrollArea>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default RecentActivityPage;
