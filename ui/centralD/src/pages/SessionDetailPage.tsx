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
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Copy,
  FileText
} from 'lucide-react';
import { format } from 'date-fns';

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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';

import { 
  sessionJobLogsApi,
  type SessionJobLog
} from '@/lib/dashboard-api';

export function SessionDetailPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  
  const [statusFilter, setStatusFilter] = useState<'all' | 'imported' | 'skipped' | 'error'>('all');
  const [skipReasonFilter, setSkipReasonFilter] = useState<string>('');
  const [page, setPage] = useState(1);
  const [selectedJobLog, setSelectedJobLog] = useState<SessionJobLog | null>(null);
  const [showDetailDialog, setShowDetailDialog] = useState(false);
  
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
  
  // Fetch job log detail
  const { data: jobLogDetail, isLoading: detailLoading } = useQuery({
    queryKey: ['job-log-detail', sessionId, selectedJobLog?.id],
    queryFn: () => sessionJobLogsApi.getJobLogDetail(sessionId!, selectedJobLog!.id),
    enabled: !!sessionId && !!selectedJobLog?.id && showDetailDialog,
  });

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'imported':
        return <CheckCircle2 className="h-4 w-4 text-green-600" />;
      case 'skipped':
        return <XCircle className="h-4 w-4 text-amber-600" />;
      case 'error':
        return <AlertCircle className="h-4 w-4 text-red-600" />;
      default:
        return <Clock className="h-4 w-4 text-gray-400" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'imported':
        return <Badge className="bg-green-100 text-green-800 border-green-200">Imported</Badge>;
      case 'skipped':
        return <Badge className="bg-amber-100 text-amber-800 border-amber-200">Skipped</Badge>;
      case 'error':
        return <Badge className="bg-red-100 text-red-800 border-red-200">Error</Badge>;
      default:
        return <Badge variant="outline">Pending</Badge>;
    }
  };

  const getSkipReasonLabel = (reason: string) => {
    switch (reason) {
      case 'duplicate_platform_id':
        return 'Same Platform + ID';
      case 'duplicate_title_company_location':
        return 'Same Title + Company + Location';
      case 'duplicate_title_company_description':
        return 'Same Title + Company + Description';
      case 'missing_required':
        return 'Missing Required Fields';
      default:
        return reason;
    }
  };

  const handleViewDetails = (jobLog: SessionJobLog) => {
    setSelectedJobLog(jobLog);
    setShowDetailDialog(true);
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
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
            <p className="text-muted-foreground">Session not found</p>
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
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back
        </Button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold">Session Details</h1>
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
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Jobs</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{summary.total}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Received from scraper
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Imported</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-green-600">{summary.imported}</div>
            <Progress value={importRate} className="mt-2 h-2" />
            <p className="text-xs text-muted-foreground mt-1">
              {importRate}% success rate
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Skipped</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-amber-600">{summary.skipped}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Duplicates or missing data
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Errors</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-red-600">{summary.error}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Failed to process
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Skip Reasons Breakdown */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Skip Reasons Breakdown</CardTitle>
          <CardDescription>Why jobs were not imported</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {skipReasonsChart.map((item) => (
              <div key={item.reason} className="flex items-center gap-4">
                <div className="w-48 text-sm">{item.reason}</div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <div 
                      className="h-6 bg-amber-100 rounded"
                      style={{ 
                        width: `${summary.skipped > 0 ? (item.count / summary.skipped) * 100 : 0}%`,
                        minWidth: item.count > 0 ? '24px' : '0'
                      }}
                    />
                    <span className="text-sm font-medium">{item.count}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Platform Breakdown */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Platform Breakdown</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Platform</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Found</TableHead>
                <TableHead className="text-right">Imported</TableHead>
                <TableHead className="text-right">Skipped</TableHead>
                <TableHead>Completed</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {platformBreakdown.map((platform) => (
                <TableRow key={platform.platformName}>
                  <TableCell className="font-medium capitalize">{platform.platformName}</TableCell>
                  <TableCell>
                    <Badge variant={platform.status === 'completed' ? 'default' : 'secondary'}>
                      {platform.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">{platform.jobsFound}</TableCell>
                  <TableCell className="text-right text-green-600">{platform.jobsImported}</TableCell>
                  <TableCell className="text-right text-amber-600">{platform.jobsSkipped}</TableCell>
                  <TableCell>
                    {platform.completedAt 
                      ? format(new Date(platform.completedAt), 'MMM d, HH:mm')
                      : '-'
                    }
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Job Logs Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-lg">Job Logs</CardTitle>
              <CardDescription>All jobs received in this session</CardDescription>
            </div>
            <div className="flex gap-2">
              <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v as typeof statusFilter); setPage(1); }}>
                <SelectTrigger className="w-32">
                  <Filter className="h-4 w-4 mr-2" />
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All</SelectItem>
                  <SelectItem value="imported">Imported</SelectItem>
                  <SelectItem value="skipped">Skipped</SelectItem>
                  <SelectItem value="error">Error</SelectItem>
                </SelectContent>
              </Select>
              
              {statusFilter === 'skipped' && (
                <Select value={skipReasonFilter} onValueChange={(v) => { setSkipReasonFilter(v); setPage(1); }}>
                  <SelectTrigger className="w-48">
                    <SelectValue placeholder="Skip Reason" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">All Reasons</SelectItem>
                    <SelectItem value="duplicate_platform_id">Platform + ID</SelectItem>
                    <SelectItem value="duplicate_title_company_location">Title + Company + Location</SelectItem>
                    <SelectItem value="duplicate_title_company_description">Title + Company + Description</SelectItem>
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
              {[1, 2, 3, 4, 5].map(i => <Skeleton key={i} className="h-16" />)}
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-12">#</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Title</TableHead>
                    <TableHead>Company</TableHead>
                    <TableHead>Location</TableHead>
                    <TableHead>Platform</TableHead>
                    <TableHead>Reason</TableHead>
                    <TableHead className="w-24">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {jobLogsData?.jobs.map((job) => (
                    <TableRow key={job.id}>
                      <TableCell className="text-muted-foreground">{job.jobIndex + 1}</TableCell>
                      <TableCell>{getStatusBadge(job.status)}</TableCell>
                      <TableCell className="max-w-48 truncate" title={job.title || ''}>
                        {job.title || <span className="text-muted-foreground italic">No title</span>}
                      </TableCell>
                      <TableCell className="max-w-32 truncate" title={job.company || ''}>
                        {job.company || '-'}
                      </TableCell>
                      <TableCell className="max-w-32 truncate" title={job.location || ''}>
                        {job.location || '-'}
                      </TableCell>
                      <TableCell className="capitalize">{job.platformName}</TableCell>
                      <TableCell>
                        {job.skipReason && (
                          <Badge variant="outline" className="text-xs">
                            {getSkipReasonLabel(job.skipReason)}
                          </Badge>
                        )}
                        {job.status === 'imported' && job.importedJobId && (
                          <Badge variant="outline" className="text-xs text-green-600">
                            ID: {job.importedJobId}
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        <Button 
                          variant="ghost" 
                          size="sm"
                          onClick={() => handleViewDetails(job)}
                        >
                          View
                          <ChevronRight className="h-4 w-4 ml-1" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              
              {/* Pagination */}
              {jobLogsData && jobLogsData.pagination.pages > 1 && (
                <div className="flex items-center justify-between mt-4">
                  <p className="text-sm text-muted-foreground">
                    Page {jobLogsData.pagination.page} of {jobLogsData.pagination.pages}
                    {' '}({jobLogsData.pagination.total} total jobs)
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

      {/* Job Detail Dialog */}
      <Dialog open={showDetailDialog} onOpenChange={setShowDetailDialog}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {selectedJobLog && getStatusIcon(selectedJobLog.status)}
              Job Details
            </DialogTitle>
            <DialogDescription>
              {selectedJobLog?.title || 'Untitled'} at {selectedJobLog?.company || 'Unknown Company'}
            </DialogDescription>
          </DialogHeader>
          
          <ScrollArea className="flex-1 pr-4">
            {detailLoading ? (
              <div className="space-y-4 py-4">
                <Skeleton className="h-32" />
                <Skeleton className="h-64" />
              </div>
            ) : jobLogDetail ? (
              <Tabs defaultValue="incoming" className="py-4">
                <TabsList className="mb-4">
                  <TabsTrigger value="incoming">Incoming Job</TabsTrigger>
                  {jobLogDetail.duplicateJob && <TabsTrigger value="duplicate">Existing Duplicate</TabsTrigger>}
                  {jobLogDetail.comparison && <TabsTrigger value="comparison">Comparison</TabsTrigger>}
                  {jobLogDetail.importedJob && <TabsTrigger value="imported">Imported Job</TabsTrigger>}
                </TabsList>
                
                <TabsContent value="incoming" className="space-y-4">
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base">Raw Job Data from Scraper</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-2 gap-4 mb-4">
                        <div>
                          <p className="text-sm text-muted-foreground">Title</p>
                          <p className="font-medium">{jobLogDetail.rawJobData.title as string || '-'}</p>
                        </div>
                        <div>
                          <p className="text-sm text-muted-foreground">Company</p>
                          <p className="font-medium">{jobLogDetail.rawJobData.company as string || '-'}</p>
                        </div>
                        <div>
                          <p className="text-sm text-muted-foreground">Location</p>
                          <p className="font-medium">{jobLogDetail.rawJobData.location as string || '-'}</p>
                        </div>
                        <div>
                          <p className="text-sm text-muted-foreground">Platform</p>
                          <p className="font-medium capitalize">{jobLogDetail.rawJobData.platform as string || selectedJobLog?.platformName}</p>
                        </div>
                        <div>
                          <p className="text-sm text-muted-foreground">External ID</p>
                          <div className="flex items-center gap-2">
                            <p className="font-mono text-sm truncate max-w-48">
                              {(jobLogDetail.rawJobData.jobId || jobLogDetail.rawJobData.job_id || jobLogDetail.rawJobData.external_job_id) as string || '-'}
                            </p>
                            <Button 
                              variant="ghost" 
                              size="sm" 
                              className="h-6 w-6 p-0"
                              onClick={() => copyToClipboard((jobLogDetail.rawJobData.jobId || jobLogDetail.rawJobData.job_id) as string || '')}
                            >
                              <Copy className="h-3 w-3" />
                            </Button>
                          </div>
                        </div>
                        <div>
                          <p className="text-sm text-muted-foreground">Job URL</p>
                          {(jobLogDetail.rawJobData.jobUrl || jobLogDetail.rawJobData.job_url) ? (
                            <a 
                              href={(jobLogDetail.rawJobData.jobUrl || jobLogDetail.rawJobData.job_url) as string}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-blue-600 hover:underline flex items-center gap-1 text-sm"
                            >
                              Open <ExternalLink className="h-3 w-3" />
                            </a>
                          ) : '-'}
                        </div>
                      </div>
                      
                      <Separator className="my-4" />
                      
                      <div>
                        <p className="text-sm text-muted-foreground mb-2">Description</p>
                        <div className="bg-muted p-3 rounded-lg text-sm whitespace-pre-wrap max-h-48 overflow-auto">
                          {jobLogDetail.rawJobData.description as string || 'No description provided'}
                        </div>
                      </div>
                      
                      {Array.isArray(jobLogDetail.rawJobData.skills) && (jobLogDetail.rawJobData.skills as string[]).length > 0 && (
                        <>
                          <Separator className="my-4" />
                          <div>
                            <p className="text-sm text-muted-foreground mb-2">Skills</p>
                            <div className="flex flex-wrap gap-1">
                              {(jobLogDetail.rawJobData.skills as string[]).map((skill, i) => (
                                <Badge key={i} variant="outline">{String(skill)}</Badge>
                              ))}
                            </div>
                          </div>
                        </>
                      )}
                    </CardContent>
                  </Card>
                  
                  {/* Full raw JSON */}
                  <Collapsible>
                    <CollapsibleTrigger asChild>
                      <Button variant="outline" className="w-full">
                        <FileText className="h-4 w-4 mr-2" />
                        View Full Raw JSON
                        <ChevronDown className="h-4 w-4 ml-2" />
                      </Button>
                    </CollapsibleTrigger>
                    <CollapsibleContent className="mt-2">
                      <pre className="bg-muted p-4 rounded-lg text-xs overflow-auto max-h-96">
                        {JSON.stringify(jobLogDetail.rawJobData, null, 2)}
                      </pre>
                    </CollapsibleContent>
                  </Collapsible>
                </TabsContent>
                
                {jobLogDetail.duplicateJob && (
                  <TabsContent value="duplicate" className="space-y-4">
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-base flex items-center gap-2">
                          <XCircle className="h-5 w-5 text-amber-600" />
                          Existing Job (Caused Skip)
                        </CardTitle>
                        <CardDescription>
                          This job already exists in the database
                        </CardDescription>
                      </CardHeader>
                      <CardContent>
                        <div className="grid grid-cols-2 gap-4 mb-4">
                          <div>
                            <p className="text-sm text-muted-foreground">ID</p>
                            <p className="font-mono">{jobLogDetail.duplicateJob.id}</p>
                          </div>
                          <div>
                            <p className="text-sm text-muted-foreground">Platform</p>
                            <p className="font-medium capitalize">{jobLogDetail.duplicateJob.platform}</p>
                          </div>
                          <div>
                            <p className="text-sm text-muted-foreground">Title</p>
                            <p className="font-medium">{jobLogDetail.duplicateJob.title}</p>
                          </div>
                          <div>
                            <p className="text-sm text-muted-foreground">Company</p>
                            <p className="font-medium">{jobLogDetail.duplicateJob.company}</p>
                          </div>
                          <div>
                            <p className="text-sm text-muted-foreground">Location</p>
                            <p className="font-medium">{jobLogDetail.duplicateJob.location}</p>
                          </div>
                          <div>
                            <p className="text-sm text-muted-foreground">Created At</p>
                            <p className="font-medium">
                              {jobLogDetail.duplicateJob.createdAt 
                                ? format(new Date(jobLogDetail.duplicateJob.createdAt), 'PPpp')
                                : '-'
                              }
                            </p>
                          </div>
                        </div>
                        
                        <Separator className="my-4" />
                        
                        <div>
                          <p className="text-sm text-muted-foreground mb-2">Description</p>
                          <div className="bg-muted p-3 rounded-lg text-sm whitespace-pre-wrap max-h-48 overflow-auto">
                            {jobLogDetail.duplicateJob.description || 'No description'}
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </TabsContent>
                )}
                
                {jobLogDetail.comparison && (
                  <TabsContent value="comparison" className="space-y-4">
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-base">Side-by-Side Comparison</CardTitle>
                        <CardDescription>
                          Compare incoming job with existing duplicate
                        </CardDescription>
                      </CardHeader>
                      <CardContent>
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead>Field</TableHead>
                              <TableHead>Incoming</TableHead>
                              <TableHead>Existing</TableHead>
                              <TableHead className="w-20">Match</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {Object.entries(jobLogDetail.comparison).map(([field, data]) => (
                              <TableRow key={field}>
                                <TableCell className="font-medium capitalize">
                                  {field.replace(/([A-Z])/g, ' $1').trim()}
                                </TableCell>
                                <TableCell className="max-w-48 truncate" title={data.incoming}>
                                  {data.incoming || <span className="text-muted-foreground italic">empty</span>}
                                </TableCell>
                                <TableCell className="max-w-48 truncate" title={data.existing}>
                                  {data.existing || <span className="text-muted-foreground italic">empty</span>}
                                </TableCell>
                                <TableCell>
                                  {data.match ? (
                                    <CheckCircle2 className="h-5 w-5 text-green-600" />
                                  ) : (
                                    <XCircle className="h-5 w-5 text-red-600" />
                                  )}
                                </TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </CardContent>
                    </Card>
                  </TabsContent>
                )}
                
                {jobLogDetail.importedJob && (
                  <TabsContent value="imported" className="space-y-4">
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-base flex items-center gap-2">
                          <CheckCircle2 className="h-5 w-5 text-green-600" />
                          Successfully Imported Job
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <p className="text-sm text-muted-foreground">Job ID</p>
                            <p className="font-mono text-lg">{jobLogDetail.importedJob.id}</p>
                          </div>
                          <div>
                            <p className="text-sm text-muted-foreground">Title</p>
                            <p className="font-medium">{jobLogDetail.importedJob.title}</p>
                          </div>
                          <div>
                            <p className="text-sm text-muted-foreground">Company</p>
                            <p className="font-medium">{jobLogDetail.importedJob.company}</p>
                          </div>
                          <div>
                            <p className="text-sm text-muted-foreground">Location</p>
                            <p className="font-medium">{jobLogDetail.importedJob.location}</p>
                          </div>
                          <div>
                            <p className="text-sm text-muted-foreground">Platform</p>
                            <p className="font-medium capitalize">{jobLogDetail.importedJob.platform}</p>
                          </div>
                          <div>
                            <p className="text-sm text-muted-foreground">Created At</p>
                            <p className="font-medium">
                              {jobLogDetail.importedJob.createdAt 
                                ? format(new Date(jobLogDetail.importedJob.createdAt), 'PPpp')
                                : '-'
                              }
                            </p>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </TabsContent>
                )}
              </Tabs>
            ) : null}
          </ScrollArea>
        </DialogContent>
      </Dialog>
    </div>
  );
}
