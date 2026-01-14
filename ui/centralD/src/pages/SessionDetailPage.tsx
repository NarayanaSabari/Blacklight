/**
 * Session Detail Page
 * 
 * Detailed view of a scrape session showing:
 * - Session info and summary stats
 * - All jobs received with their import status
 * - Duplicate job comparisons for skipped jobs
 */

import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { 
  ArrowLeft, 
  CheckCircle2, 
  XCircle, 
  AlertCircle, 
  Clock,
  Filter,
  ChevronRight,
  ExternalLink,
  Copy,
  FileText,
  Check,
  X,
  Info,
  Briefcase,
  Building2,
  MapPin,
  Globe,
  Hash,
  Link2,
  Calendar,
  ArrowRightLeft
} from 'lucide-react';
import { format } from 'date-fns';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
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
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

import { 
  sessionJobLogsApi,
  type SessionJobLog
} from '@/lib/dashboard-api';

// Field display component for consistent formatting
function FieldDisplay({ 
  label, 
  value, 
  icon: Icon,
  copyable = false,
  isUrl = false,
  className = ""
}: { 
  label: string; 
  value: string | null | undefined;
  icon?: React.ComponentType<{ className?: string }>;
  copyable?: boolean;
  isUrl?: boolean;
  className?: string;
}) {
  const displayValue = value || '-';
  
  const handleCopy = () => {
    if (value) {
      navigator.clipboard.writeText(value);
      toast.success('Copied to clipboard');
    }
  };
  
  return (
    <div className={className}>
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1">
        {Icon && <Icon className="h-3 w-3" />}
        <span>{label}</span>
      </div>
      <div className="flex items-center gap-2">
        {isUrl && value ? (
          <a 
            href={value}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:underline flex items-center gap-1 text-sm font-medium"
          >
            Open Link <ExternalLink className="h-3 w-3" />
          </a>
        ) : (
          <p className="font-medium text-sm break-words">{displayValue}</p>
        )}
        {copyable && value && (
          <Button 
            variant="ghost" 
            size="sm" 
            className="h-5 w-5 p-0 text-muted-foreground hover:text-foreground"
            onClick={handleCopy}
          >
            <Copy className="h-3 w-3" />
          </Button>
        )}
      </div>
    </div>
  );
}

// Comparison row for side-by-side view
function ComparisonRow({ 
  label, 
  incoming, 
  existing, 
  match 
}: { 
  label: string; 
  incoming: string | null | undefined;
  existing: string | null | undefined;
  match: boolean;
}) {
  return (
    <div className="grid grid-cols-[140px_1fr_1fr_40px] gap-3 py-3 border-b last:border-0">
      <div className="font-medium text-sm text-muted-foreground">{label}</div>
      <div className="text-sm bg-blue-50 dark:bg-blue-950 p-2 rounded border border-blue-200 dark:border-blue-800">
        {incoming || <span className="text-muted-foreground italic">empty</span>}
      </div>
      <div className="text-sm bg-amber-50 dark:bg-amber-950 p-2 rounded border border-amber-200 dark:border-amber-800">
        {existing || <span className="text-muted-foreground italic">empty</span>}
      </div>
      <div className="flex items-center justify-center">
        {match ? (
          <div className="h-6 w-6 rounded-full bg-green-100 dark:bg-green-900 flex items-center justify-center">
            <Check className="h-4 w-4 text-green-600" />
          </div>
        ) : (
          <div className="h-6 w-6 rounded-full bg-red-100 dark:bg-red-900 flex items-center justify-center">
            <X className="h-4 w-4 text-red-600" />
          </div>
        )}
      </div>
    </div>
  );
}

export function SessionDetailPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  
  const [statusFilter, setStatusFilter] = useState<'all' | 'imported' | 'skipped' | 'error'>('all');
  const [skipReasonFilter, setSkipReasonFilter] = useState<string>('');
  const [page, setPage] = useState(1);
  const [selectedJobLog, setSelectedJobLog] = useState<SessionJobLog | null>(null);
  const [showDetailSheet, setShowDetailSheet] = useState(false);
  
  // Fetch session summary
  const { data: summaryData, isLoading: summaryLoading } = useQuery({
    queryKey: ['session-summary', sessionId],
    queryFn: () => sessionJobLogsApi.getSessionSummary(sessionId!),
    enabled: !!sessionId,
  });
  
  // Fetch job logs
  const { data: jobLogsData, isLoading: jobLogsLoading } = useQuery({
    queryKey: ['session-job-logs', sessionId, statusFilter, skipReasonFilter, page],
    queryFn: () => sessionJobLogsApi.getSessionJobLogs(sessionId!, {
      status: statusFilter,
      skipReason: skipReasonFilter || undefined,
      page,
      perPage: 50,
      includeDuplicate: true,
    }),
    enabled: !!sessionId,
  });
  
  // Fetch job log detail when selected
  const { data: jobLogDetail, isLoading: detailLoading } = useQuery({
    queryKey: ['job-log-detail', sessionId, selectedJobLog?.id],
    queryFn: () => sessionJobLogsApi.getJobLogDetail(sessionId!, selectedJobLog!.id),
    enabled: !!sessionId && !!selectedJobLog?.id && showDetailSheet,
  });

  const getStatusIcon = (status: string, size = 4) => {
    const sizeClass = `h-${size} w-${size}`;
    switch (status) {
      case 'imported':
        return <CheckCircle2 className={`${sizeClass} text-green-600`} />;
      case 'skipped':
        return <XCircle className={`${sizeClass} text-amber-600`} />;
      case 'error':
        return <AlertCircle className={`${sizeClass} text-red-600`} />;
      default:
        return <Clock className={`${sizeClass} text-gray-400`} />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'imported':
        return <Badge className="bg-green-100 text-green-800 border-green-200 dark:bg-green-900 dark:text-green-200">Imported</Badge>;
      case 'skipped':
        return <Badge className="bg-amber-100 text-amber-800 border-amber-200 dark:bg-amber-900 dark:text-amber-200">Skipped</Badge>;
      case 'error':
        return <Badge className="bg-red-100 text-red-800 border-red-200 dark:bg-red-900 dark:text-red-200">Error</Badge>;
      default:
        return <Badge variant="outline">Pending</Badge>;
    }
  };

  const getSkipReasonLabel = (reason: string) => {
    switch (reason) {
      case 'duplicate_platform_id':
        return 'Same Platform + External ID';
      case 'duplicate_title_company_location':
        return 'Same Title + Company + Location';
      case 'duplicate_title_company_description':
        return 'Same Title + Company + Description';
      case 'missing_required':
        return 'Missing Required Fields';
      default:
        return reason || 'Unknown';
    }
  };

  const getSkipReasonDescription = (reason: string) => {
    switch (reason) {
      case 'duplicate_platform_id':
        return 'A job with the same external ID already exists in the database from the same platform.';
      case 'duplicate_title_company_location':
        return 'A job with matching title, company, and location already exists.';
      case 'duplicate_title_company_description':
        return 'A job with matching title, company, and description already exists.';
      case 'missing_required':
        return 'The job data was missing required fields (title, company, or description).';
      default:
        return 'This job was skipped for an unspecified reason.';
    }
  };

  const handleViewDetails = (jobLog: SessionJobLog) => {
    setSelectedJobLog(jobLog);
    setShowDetailSheet(true);
  };

  if (summaryLoading) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid grid-cols-4 gap-4">
          {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-32" />)}
        </div>
        <Skeleton className="h-96" />
      </div>
    );
  }

  if (!summaryData) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="py-12 text-center">
            <AlertCircle className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-muted-foreground">Session not found or no job logs available yet.</p>
            <p className="text-sm text-muted-foreground mt-2">
              Job logs are created during the import process. If this is a new session, logs may not be available.
            </p>
            <Button variant="outline" className="mt-4" onClick={() => navigate(-1)}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              Go Back
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const { sessionInfo, summary, platformBreakdown, skipReasonsChart } = summaryData;
  const importRate = summary.total > 0 ? Math.round((summary.imported / summary.total) * 100) : 0;

  return (
    <TooltipProvider>
      <div className="space-y-6 p-6">
        {/* Header */}
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
          <div className="flex-1">
            <h1 className="text-2xl font-bold">Session Job Logs</h1>
            <p className="text-muted-foreground">
              {sessionInfo.roleName}
              {sessionInfo.location && ` • ${sessionInfo.location}`}
            </p>
          </div>
          <Badge variant={sessionInfo.status === 'completed' ? 'default' : 'secondary'}>
            {sessionInfo.status}
          </Badge>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Total Jobs Received</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{summary.total}</div>
              <p className="text-xs text-muted-foreground mt-1">
                From all platforms
              </p>
            </CardContent>
          </Card>
          
          <Card className="border-green-200 dark:border-green-800">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-green-600">Imported</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-green-600">{summary.imported}</div>
              <Progress value={importRate} className="mt-2 h-2" />
              <p className="text-xs text-muted-foreground mt-1">
                {importRate}% of total
              </p>
            </CardContent>
          </Card>
          
          <Card className="border-amber-200 dark:border-amber-800">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-amber-600">Skipped (Duplicates)</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-amber-600">{summary.skipped}</div>
              <p className="text-xs text-muted-foreground mt-1">
                Already in database
              </p>
            </CardContent>
          </Card>
          
          <Card className="border-red-200 dark:border-red-800">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-red-600">Errors</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-red-600">{summary.error}</div>
              <p className="text-xs text-muted-foreground mt-1">
                Failed to process
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Skip Reasons & Platform Breakdown in columns */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Skip Reasons Breakdown */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Why Jobs Were Skipped</CardTitle>
              <CardDescription>Breakdown by duplicate detection method</CardDescription>
            </CardHeader>
            <CardContent>
              {skipReasonsChart.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-4">No skipped jobs in this session</p>
              ) : (
                <div className="space-y-3">
                  {skipReasonsChart.map((item) => (
                    <div key={item.reason} className="space-y-1">
                      <div className="flex items-center justify-between text-sm">
                        <span>{item.reason}</span>
                        <span className="font-medium">{item.count}</span>
                      </div>
                      <div className="h-2 bg-muted rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-amber-500 rounded-full transition-all"
                          style={{ 
                            width: `${summary.skipped > 0 ? (item.count / summary.skipped) * 100 : 0}%`,
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Platform Breakdown */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Platform Breakdown</CardTitle>
              <CardDescription>Jobs per scraping platform</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Platform</TableHead>
                    <TableHead className="text-right">Found</TableHead>
                    <TableHead className="text-right">Imported</TableHead>
                    <TableHead className="text-right">Skipped</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {platformBreakdown.map((platform) => (
                    <TableRow key={platform.platformName}>
                      <TableCell className="font-medium capitalize">{platform.platformName}</TableCell>
                      <TableCell className="text-right">{platform.jobsFound}</TableCell>
                      <TableCell className="text-right text-green-600">{platform.jobsImported}</TableCell>
                      <TableCell className="text-right text-amber-600">{platform.jobsSkipped}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </div>

        {/* Job Logs Table */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between flex-wrap gap-4">
              <div>
                <CardTitle className="text-lg">Individual Job Logs</CardTitle>
                <CardDescription>Click on any job to see full details and compare with duplicates</CardDescription>
              </div>
              <div className="flex gap-2">
                <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v as typeof statusFilter); setPage(1); }}>
                  <SelectTrigger className="w-36">
                    <Filter className="h-4 w-4 mr-2" />
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Status</SelectItem>
                    <SelectItem value="imported">Imported Only</SelectItem>
                    <SelectItem value="skipped">Skipped Only</SelectItem>
                    <SelectItem value="error">Errors Only</SelectItem>
                  </SelectContent>
                </Select>
                
                {statusFilter === 'skipped' && (
                  <Select value={skipReasonFilter} onValueChange={(v) => { setSkipReasonFilter(v); setPage(1); }}>
                    <SelectTrigger className="w-56">
                      <SelectValue placeholder="All Skip Reasons" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">All Reasons</SelectItem>
                      <SelectItem value="duplicate_platform_id">Same Platform + ID</SelectItem>
                      <SelectItem value="duplicate_title_company_location">Same Title/Company/Location</SelectItem>
                      <SelectItem value="duplicate_title_company_description">Same Title/Company/Description</SelectItem>
                      <SelectItem value="missing_required">Missing Required</SelectItem>
                    </SelectContent>
                  </Select>
                )}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {jobLogsLoading ? (
              <div className="space-y-2">
                {[1, 2, 3, 4, 5].map(i => <Skeleton key={i} className="h-14" />)}
              </div>
            ) : !jobLogsData?.jobs.length ? (
              <div className="text-center py-12">
                <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground">No job logs found for this filter.</p>
              </div>
            ) : (
              <>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-14">#</TableHead>
                      <TableHead className="w-24">Status</TableHead>
                      <TableHead>Job Title</TableHead>
                      <TableHead>Company</TableHead>
                      <TableHead>Location</TableHead>
                      <TableHead>Platform</TableHead>
                      <TableHead>Skip Reason</TableHead>
                      <TableHead className="w-20"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {jobLogsData.jobs.map((job) => (
                      <TableRow 
                        key={job.id} 
                        className="cursor-pointer hover:bg-muted/50"
                        onClick={() => handleViewDetails(job)}
                      >
                        <TableCell className="text-muted-foreground font-mono text-sm">
                          {job.jobIndex + 1}
                        </TableCell>
                        <TableCell>{getStatusBadge(job.status)}</TableCell>
                        <TableCell className="max-w-48">
                          <div className="truncate font-medium" title={job.title || ''}>
                            {job.title || <span className="text-muted-foreground italic">No title</span>}
                          </div>
                        </TableCell>
                        <TableCell className="max-w-32">
                          <div className="truncate" title={job.company || ''}>
                            {job.company || '-'}
                          </div>
                        </TableCell>
                        <TableCell className="max-w-32">
                          <div className="truncate" title={job.location || ''}>
                            {job.location || '-'}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline" className="capitalize">
                            {job.platformName}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          {job.skipReason ? (
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Badge variant="secondary" className="text-xs cursor-help">
                                  {getSkipReasonLabel(job.skipReason).split(' ').slice(0, 2).join(' ')}...
                                </Badge>
                              </TooltipTrigger>
                              <TooltipContent>
                                <p className="font-medium">{getSkipReasonLabel(job.skipReason)}</p>
                                <p className="text-xs text-muted-foreground mt-1 max-w-64">
                                  {getSkipReasonDescription(job.skipReason)}
                                </p>
                              </TooltipContent>
                            </Tooltip>
                          ) : job.status === 'error' ? (
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Badge variant="destructive" className="text-xs cursor-help">
                                  Error
                                </Badge>
                              </TooltipTrigger>
                              <TooltipContent className="max-w-80">
                                <p className="font-medium text-red-600">Import Error</p>
                                <p className="text-xs text-muted-foreground mt-1 break-words">
                                  {job.errorMessage || 'Unknown error occurred during import'}
                                </p>
                              </TooltipContent>
                            </Tooltip>
                          ) : job.status === 'imported' ? (
                            <span className="text-xs text-green-600">New job added</span>
                          ) : null}
                        </TableCell>
                        <TableCell>
                          <Button variant="ghost" size="sm" className="h-8">
                            Details
                            <ChevronRight className="h-4 w-4 ml-1" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
                
                {/* Pagination */}
                {jobLogsData.pagination.pages > 1 && (
                  <div className="flex items-center justify-between mt-4 pt-4 border-t">
                    <p className="text-sm text-muted-foreground">
                      Page {jobLogsData.pagination.page} of {jobLogsData.pagination.pages}
                      {' '}• {jobLogsData.pagination.total} total jobs
                    </p>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={!jobLogsData.pagination.hasPrev}
                        onClick={() => setPage(p => p - 1)}
                      >
                        Previous
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={!jobLogsData.pagination.hasNext}
                        onClick={() => setPage(p => p + 1)}
                      >
                        Next
                      </Button>
                    </div>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>

        {/* Job Detail Sheet (Side Panel) */}
        <Sheet open={showDetailSheet} onOpenChange={setShowDetailSheet}>
          <SheetContent className="w-full sm:max-w-2xl overflow-y-auto">
            <SheetHeader className="mb-6">
              <div className="flex items-center gap-3">
                {selectedJobLog && (
                  <div className={`p-2 rounded-full ${
                    selectedJobLog.status === 'imported' ? 'bg-green-100 dark:bg-green-900' :
                    selectedJobLog.status === 'skipped' ? 'bg-amber-100 dark:bg-amber-900' :
                    'bg-red-100 dark:bg-red-900'
                  }`}>
                    {getStatusIcon(selectedJobLog.status, 5)}
                  </div>
                )}
                <div>
                  <SheetTitle className="text-xl">
                    {selectedJobLog?.status === 'imported' ? 'Job Imported Successfully' :
                     selectedJobLog?.status === 'skipped' ? 'Job Skipped (Duplicate)' :
                     'Job Import Error'}
                  </SheetTitle>
                  <SheetDescription className="mt-1">
                    Job #{(selectedJobLog?.jobIndex ?? 0) + 1} from {selectedJobLog?.platformName}
                  </SheetDescription>
                </div>
              </div>
            </SheetHeader>
            
            {detailLoading ? (
              <div className="space-y-4">
                <Skeleton className="h-32" />
                <Skeleton className="h-64" />
              </div>
            ) : jobLogDetail ? (
              <div className="space-y-6">
                {/* Status Banner */}
                {selectedJobLog?.status === 'skipped' && selectedJobLog.skipReason && (
                  <div className="bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded-lg p-4">
                    <div className="flex items-start gap-3">
                      <Info className="h-5 w-5 text-amber-600 mt-0.5 flex-shrink-0" />
                      <div>
                        <p className="font-medium text-amber-800 dark:text-amber-200">
                          {getSkipReasonLabel(selectedJobLog.skipReason)}
                        </p>
                        <p className="text-sm text-amber-700 dark:text-amber-300 mt-1">
                          {getSkipReasonDescription(selectedJobLog.skipReason)}
                        </p>
                        {selectedJobLog.skipReasonDetail && (
                          <p className="text-xs text-amber-600 dark:text-amber-400 mt-2 font-mono">
                            Detail: {selectedJobLog.skipReasonDetail}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {selectedJobLog?.status === 'imported' && jobLogDetail.importedJob && (
                  <div className="bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded-lg p-4">
                    <div className="flex items-start gap-3">
                      <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                      <div>
                        <p className="font-medium text-green-800 dark:text-green-200">
                          Successfully imported as Job #{jobLogDetail.importedJob.id}
                        </p>
                        <p className="text-sm text-green-700 dark:text-green-300 mt-1">
                          This job was new and has been added to the database.
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Error Banner */}
                {selectedJobLog?.status === 'error' && (
                  <div className="bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg p-4">
                    <div className="flex items-start gap-3">
                      <AlertCircle className="h-5 w-5 text-red-600 mt-0.5 flex-shrink-0" />
                      <div className="flex-1">
                        <p className="font-medium text-red-800 dark:text-red-200">
                          Import Failed
                        </p>
                        <p className="text-sm text-red-700 dark:text-red-300 mt-1">
                          This job could not be imported due to an error.
                        </p>
                        {selectedJobLog.errorMessage && (
                          <div className="mt-2 p-2 bg-red-100 dark:bg-red-900 rounded text-xs font-mono text-red-800 dark:text-red-200 max-h-32 overflow-auto whitespace-pre-wrap break-words">
                            {selectedJobLog.errorMessage}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                <Tabs defaultValue={jobLogDetail.duplicateJob ? "comparison" : "incoming"} className="space-y-4">
                  <TabsList className="grid w-full" style={{ gridTemplateColumns: `repeat(${jobLogDetail.duplicateJob ? 3 : 2}, 1fr)` }}>
                    <TabsTrigger value="incoming">
                      <FileText className="h-4 w-4 mr-2" />
                      Incoming Data
                    </TabsTrigger>
                    {jobLogDetail.duplicateJob && (
                      <TabsTrigger value="comparison">
                        <ArrowRightLeft className="h-4 w-4 mr-2" />
                        Comparison
                      </TabsTrigger>
                    )}
                    <TabsTrigger value="raw">
                      <Hash className="h-4 w-4 mr-2" />
                      Raw JSON
                    </TabsTrigger>
                  </TabsList>
                  
                  {/* Incoming Data Tab */}
                  <TabsContent value="incoming" className="space-y-4">
                    <Card>
                      <CardHeader className="pb-3">
                        <CardTitle className="text-base flex items-center gap-2">
                          <Globe className="h-4 w-4" />
                          Job Data from Scraper
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                          <FieldDisplay 
                            label="Job Title" 
                            value={jobLogDetail.rawJobData.title as string}
                            icon={Briefcase}
                          />
                          <FieldDisplay 
                            label="Company" 
                            value={jobLogDetail.rawJobData.company as string}
                            icon={Building2}
                          />
                          <FieldDisplay 
                            label="Location" 
                            value={jobLogDetail.rawJobData.location as string}
                            icon={MapPin}
                          />
                          <FieldDisplay 
                            label="Platform" 
                            value={(jobLogDetail.rawJobData.platform as string) || selectedJobLog?.platformName}
                            icon={Globe}
                          />
                          <FieldDisplay 
                            label="External Job ID" 
                            value={(jobLogDetail.rawJobData.jobId || jobLogDetail.rawJobData.job_id || jobLogDetail.rawJobData.external_job_id) as string}
                            icon={Hash}
                            copyable
                          />
                          <FieldDisplay 
                            label="Job URL" 
                            value={(jobLogDetail.rawJobData.jobUrl || jobLogDetail.rawJobData.job_url) as string}
                            icon={Link2}
                            isUrl
                          />
                          {typeof jobLogDetail.rawJobData.posted_date === 'string' && jobLogDetail.rawJobData.posted_date && (
                            <FieldDisplay 
                              label="Posted Date" 
                              value={jobLogDetail.rawJobData.posted_date}
                              icon={Calendar}
                            />
                          )}
                          {typeof jobLogDetail.rawJobData.salary === 'string' && jobLogDetail.rawJobData.salary && (
                            <FieldDisplay 
                              label="Salary" 
                              value={jobLogDetail.rawJobData.salary}
                            />
                          )}
                        </div>
                        
                        <Separator />
                        
                        <div>
                          <p className="text-xs text-muted-foreground mb-2 flex items-center gap-1">
                            <FileText className="h-3 w-3" />
                            Description
                          </p>
                          <div className="bg-muted p-3 rounded-lg text-sm whitespace-pre-wrap max-h-64 overflow-auto">
                            {jobLogDetail.rawJobData.description as string || 'No description provided'}
                          </div>
                        </div>
                        
                        {Array.isArray(jobLogDetail.rawJobData.skills) && (jobLogDetail.rawJobData.skills as string[]).length > 0 && (
                          <>
                            <Separator />
                            <div>
                              <p className="text-xs text-muted-foreground mb-2">Skills</p>
                              <div className="flex flex-wrap gap-1">
                                {(jobLogDetail.rawJobData.skills as string[]).map((skill, i) => (
                                  <Badge key={i} variant="secondary">{String(skill)}</Badge>
                                ))}
                              </div>
                            </div>
                          </>
                        )}
                      </CardContent>
                    </Card>
                  </TabsContent>
                  
                  {/* Comparison Tab */}
                  {jobLogDetail.duplicateJob && jobLogDetail.comparison && (
                    <TabsContent value="comparison" className="space-y-4">
                      <Card>
                        <CardHeader className="pb-3">
                          <CardTitle className="text-base">Side-by-Side Comparison</CardTitle>
                          <CardDescription>
                            Compare the incoming job with the existing duplicate in the database
                          </CardDescription>
                        </CardHeader>
                        <CardContent>
                          {/* Legend */}
                          <div className="flex gap-4 mb-4 text-xs">
                            <div className="flex items-center gap-2">
                              <div className="w-3 h-3 bg-blue-100 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded"></div>
                              <span>Incoming (New)</span>
                            </div>
                            <div className="flex items-center gap-2">
                              <div className="w-3 h-3 bg-amber-100 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded"></div>
                              <span>Existing (Database)</span>
                            </div>
                          </div>
                          
                          {/* Header */}
                          <div className="grid grid-cols-[140px_1fr_1fr_40px] gap-3 py-2 border-b text-xs font-medium text-muted-foreground">
                            <div>Field</div>
                            <div>Incoming</div>
                            <div>Existing</div>
                            <div className="text-center">Match</div>
                          </div>
                          
                          {/* Comparison Rows */}
                          <ComparisonRow 
                            label="Title"
                            incoming={jobLogDetail.comparison.title?.incoming}
                            existing={jobLogDetail.comparison.title?.existing}
                            match={jobLogDetail.comparison.title?.match ?? false}
                          />
                          <ComparisonRow 
                            label="Company"
                            incoming={jobLogDetail.comparison.company?.incoming}
                            existing={jobLogDetail.comparison.company?.existing}
                            match={jobLogDetail.comparison.company?.match ?? false}
                          />
                          <ComparisonRow 
                            label="Location"
                            incoming={jobLogDetail.comparison.location?.incoming}
                            existing={jobLogDetail.comparison.location?.existing}
                            match={jobLogDetail.comparison.location?.match ?? false}
                          />
                          <ComparisonRow 
                            label="Platform"
                            incoming={jobLogDetail.comparison.platform?.incoming}
                            existing={jobLogDetail.comparison.platform?.existing}
                            match={jobLogDetail.comparison.platform?.match ?? false}
                          />
                          <ComparisonRow 
                            label="External ID"
                            incoming={jobLogDetail.comparison.externalId?.incoming}
                            existing={jobLogDetail.comparison.externalId?.existing}
                            match={jobLogDetail.comparison.externalId?.match ?? false}
                          />
                          
                          {/* Description Preview */}
                          {jobLogDetail.comparison.descriptionPreview && (
                            <div className="mt-4 space-y-2">
                              <p className="text-xs font-medium text-muted-foreground">Description Preview (first 200 chars)</p>
                              <div className="grid grid-cols-2 gap-3">
                                <div className="text-xs bg-blue-50 dark:bg-blue-950 p-3 rounded border border-blue-200 dark:border-blue-800 max-h-32 overflow-auto">
                                  {jobLogDetail.comparison.descriptionPreview.incoming || <span className="text-muted-foreground italic">empty</span>}
                                </div>
                                <div className="text-xs bg-amber-50 dark:bg-amber-950 p-3 rounded border border-amber-200 dark:border-amber-800 max-h-32 overflow-auto">
                                  {jobLogDetail.comparison.descriptionPreview.existing || <span className="text-muted-foreground italic">empty</span>}
                                </div>
                              </div>
                            </div>
                          )}
                        </CardContent>
                      </Card>
                      
                      {/* Existing Job Details */}
                      <Card>
                        <CardHeader className="pb-3">
                          <CardTitle className="text-base flex items-center gap-2">
                            <XCircle className="h-4 w-4 text-amber-600" />
                            Existing Job in Database
                          </CardTitle>
                          <CardDescription>
                            Job ID: {jobLogDetail.duplicateJob.id} • Created: {jobLogDetail.duplicateJob.createdAt ? format(new Date(jobLogDetail.duplicateJob.createdAt), 'PPp') : 'Unknown'}
                          </CardDescription>
                        </CardHeader>
                        <CardContent>
                          <div className="grid grid-cols-2 gap-4">
                            <FieldDisplay label="Title" value={jobLogDetail.duplicateJob.title} icon={Briefcase} />
                            <FieldDisplay label="Company" value={jobLogDetail.duplicateJob.company} icon={Building2} />
                            <FieldDisplay label="Location" value={jobLogDetail.duplicateJob.location} icon={MapPin} />
                            <FieldDisplay label="Platform" value={jobLogDetail.duplicateJob.platform} icon={Globe} />
                            <FieldDisplay label="External ID" value={jobLogDetail.duplicateJob.externalJobId} icon={Hash} copyable />
                            <FieldDisplay label="Job URL" value={jobLogDetail.duplicateJob.jobUrl} icon={Link2} isUrl />
                          </div>
                        </CardContent>
                      </Card>
                    </TabsContent>
                  )}
                  
                  {/* Raw JSON Tab */}
                  <TabsContent value="raw">
                    <Card>
                      <CardHeader className="pb-3">
                        <CardTitle className="text-base">Raw JSON Data</CardTitle>
                        <CardDescription>Complete data as received from the scraper</CardDescription>
                      </CardHeader>
                      <CardContent>
                        <ScrollArea className="h-96">
                          <pre className="text-xs bg-muted p-4 rounded-lg overflow-auto">
                            {JSON.stringify(jobLogDetail.rawJobData, null, 2)}
                          </pre>
                        </ScrollArea>
                      </CardContent>
                    </Card>
                  </TabsContent>
                </Tabs>
              </div>
            ) : (
              <div className="text-center py-12">
                <AlertCircle className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground">Could not load job details</p>
              </div>
            )}
          </SheetContent>
        </Sheet>
      </div>
    </TooltipProvider>
  );
}
