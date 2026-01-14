/**
 * Location Analytics Page
 * Comprehensive location-based scraping statistics and analytics
 */

import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Progress } from '@/components/ui/progress';
import { scraperMonitoringApi } from '@/lib/dashboard-api';
import { usePMAdminAuth } from '@/hooks/usePMAdminAuth';
import { 
  CheckCircle2, 
  XCircle, 
  Clock, 
  RefreshCw,
  MapPin,
  Globe,
  TrendingUp,
  BarChart3,
  Activity,
  Layers,
  FileCheck,
  Target
} from 'lucide-react';

export function LocationAnalyticsPage() {
  const { isAuthenticated, isLoading: authLoading } = usePMAdminAuth();
  
  const { data: stats, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['scraper-stats'],
    queryFn: scraperMonitoringApi.getStats,
    refetchInterval: 30000,
    enabled: !authLoading && isAuthenticated,
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-10 w-24" />
        </div>
        <div className="grid grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
        <Skeleton className="h-64" />
        <Skeleton className="h-96" />
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <MapPin className="h-6 w-6 text-blue-600" />
              Location Analytics
            </h1>
          </div>
        </div>
        <Card className="p-8 text-center">
          <XCircle className="h-12 w-12 mx-auto text-red-500 mb-4" />
          <p className="text-lg font-medium">Failed to load analytics</p>
          <Button onClick={() => refetch()} variant="outline" className="mt-4">
            <RefreshCw className="h-4 w-4 mr-2" />
            Try Again
          </Button>
        </Card>
      </div>
    );
  }

  const { locationAnalytics } = stats;
  const totalLocationSessions = locationAnalytics.sessionsWithLocation + locationAnalytics.sessionsWithoutLocation;
  const locationSessionPercentage = totalLocationSessions > 0 
    ? Math.round((locationAnalytics.sessionsWithLocation / totalLocationSessions) * 100)
    : 0;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <MapPin className="h-6 w-6 text-blue-600" />
            Location Analytics
          </h1>
          <p className="text-muted-foreground">
            Location-based scraping performance and queue statistics
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

      {/* Location Queue Overview */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="p-4 bg-gradient-to-br from-blue-50 to-indigo-50 border-blue-200">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-full bg-blue-100">
              <Globe className="h-6 w-6 text-blue-600" />
            </div>
            <div>
              <p className="text-xs text-blue-600 font-medium">Total Queue</p>
              <p className="text-3xl font-bold text-blue-700">{locationAnalytics.queue.total}</p>
              <p className="text-xs text-blue-500">{locationAnalytics.queue.uniqueLocations} unique locations</p>
            </div>
          </div>
        </Card>
        
        <Card className="p-4 bg-gradient-to-br from-yellow-50 to-amber-50 border-yellow-200">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-full bg-yellow-100">
              <Clock className="h-6 w-6 text-yellow-600" />
            </div>
            <div>
              <p className="text-xs text-yellow-600 font-medium">Pending Approval</p>
              <p className="text-3xl font-bold text-yellow-700">{locationAnalytics.queue.pending}</p>
              <p className="text-xs text-yellow-500">Waiting for review</p>
            </div>
          </div>
        </Card>
        
        <Card className="p-4 bg-gradient-to-br from-green-50 to-emerald-50 border-green-200">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-full bg-green-100">
              <CheckCircle2 className="h-6 w-6 text-green-600" />
            </div>
            <div>
              <p className="text-xs text-green-600 font-medium">Approved</p>
              <p className="text-3xl font-bold text-green-700">{locationAnalytics.queue.approved}</p>
              <p className="text-xs text-green-500">Ready to scrape</p>
            </div>
          </div>
        </Card>
        
        <Card className="p-4 bg-gradient-to-br from-purple-50 to-violet-50 border-purple-200">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-full bg-purple-100">
              <Activity className="h-6 w-6 text-purple-600" />
            </div>
            <div>
              <p className="text-xs text-purple-600 font-medium">Processing</p>
              <p className="text-3xl font-bold text-purple-700">{locationAnalytics.queue.processing}</p>
              <p className="text-xs text-purple-500">Currently scraping</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Session Distribution */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            Session Distribution (Last 24h)
          </CardTitle>
          <CardDescription>
            Breakdown of location-based vs non-location scraping sessions
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid md:grid-cols-2 gap-6">
            {/* Distribution Bar */}
            <div className="space-y-4">
              <div className="flex justify-between text-sm mb-2">
                <span className="flex items-center gap-2">
                  <MapPin className="h-4 w-4 text-blue-600" />
                  Location-based Scraping
                </span>
                <span className={`font-bold ${locationSessionPercentage > 50 ? 'text-blue-600' : 'text-muted-foreground'}`}>
                  {locationSessionPercentage}%
                </span>
              </div>
              <Progress value={locationSessionPercentage} className="h-4" />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>{locationAnalytics.sessionsWithLocation} with location</span>
                <span>{locationAnalytics.sessionsWithoutLocation} without location</span>
              </div>
            </div>
            
            {/* Stats Cards */}
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 rounded-lg bg-blue-50 border border-blue-200 text-center">
                <Target className="h-6 w-6 mx-auto text-blue-600 mb-2" />
                <p className="text-2xl font-bold text-blue-700">{locationAnalytics.sessionsWithLocation}</p>
                <p className="text-xs text-blue-600">Location Sessions</p>
              </div>
              <div className="p-4 rounded-lg bg-gray-50 border text-center">
                <Layers className="h-6 w-6 mx-auto text-gray-600 mb-2" />
                <p className="text-2xl font-bold">{locationAnalytics.sessionsWithoutLocation}</p>
                <p className="text-xs text-muted-foreground">Global Sessions</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Top Locations */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            Top Locations by Jobs Imported (Last 24h)
          </CardTitle>
          <CardDescription>
            Best performing locations based on job import success
          </CardDescription>
        </CardHeader>
        <CardContent>
          {locationAnalytics.topLocations.length === 0 ? (
            <div className="text-center py-12">
              <MapPin className="h-12 w-12 mx-auto text-muted-foreground/50 mb-4" />
              <p className="text-lg font-medium text-muted-foreground">No Location Data</p>
              <p className="text-sm text-muted-foreground mt-2">
                No location-based sessions in the last 24 hours.
              </p>
              <p className="text-sm text-muted-foreground mt-1">
                Run scraper with <code className="bg-muted px-1.5 py-0.5 rounded text-xs">--mode role-location</code> to see location analytics.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {locationAnalytics.topLocations.map((loc, idx) => {
                const maxJobs = locationAnalytics.topLocations[0]?.jobsImported || 1;
                const barWidth = (loc.jobsImported / maxJobs) * 100;
                const successRate = loc.jobsFound > 0 
                  ? Math.round((loc.jobsImported / loc.jobsFound) * 100) 
                  : 0;
                
                return (
                  <div key={loc.location} className="relative group">
                    {/* Background bar */}
                    <div 
                      className="absolute inset-y-0 left-0 bg-gradient-to-r from-blue-100 to-indigo-100 rounded-lg transition-all duration-300"
                      style={{ width: `${barWidth}%` }}
                    />
                    
                    {/* Content */}
                    <div className="relative flex items-center justify-between p-4 rounded-lg border bg-background/50 hover:bg-background/80 transition-colors">
                      <div className="flex items-center gap-4">
                        {/* Rank */}
                        <div className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold ${
                          idx === 0 ? 'bg-yellow-100 text-yellow-700' :
                          idx === 1 ? 'bg-gray-100 text-gray-600' :
                          idx === 2 ? 'bg-orange-100 text-orange-700' :
                          'bg-muted text-muted-foreground'
                        }`}>
                          #{idx + 1}
                        </div>
                        
                        {/* Location info */}
                        <div>
                          <div className="flex items-center gap-2">
                            <MapPin className="h-4 w-4 text-blue-600" />
                            <span className="font-medium">{loc.location}</span>
                          </div>
                          <p className="text-xs text-muted-foreground mt-0.5">
                            {loc.sessionCount} session{loc.sessionCount !== 1 ? 's' : ''} completed
                          </p>
                        </div>
                      </div>
                      
                      {/* Stats */}
                      <div className="flex items-center gap-6">
                        <div className="text-right">
                          <p className="text-sm text-muted-foreground">Found</p>
                          <p className="font-semibold">{loc.jobsFound}</p>
                        </div>
                        <div className="text-right">
                          <p className="text-sm text-green-600">Imported</p>
                          <p className="font-semibold text-green-700">{loc.jobsImported}</p>
                        </div>
                        <div className="w-20">
                          <Badge 
                            variant={successRate >= 80 ? "secondary" : successRate >= 50 ? "outline" : "destructive"}
                            className={`w-full justify-center ${successRate >= 80 ? 'bg-green-100 text-green-800' : ''}`}
                          >
                            <FileCheck className="h-3 w-3 mr-1" />
                            {successRate}%
                          </Badge>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Overall Stats Summary */}
      <div className="grid md:grid-cols-3 gap-4">
        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Total Jobs Found (24h)</p>
              <p className="text-3xl font-bold mt-1">{stats.jobsStats24h.totalFound.toLocaleString()}</p>
            </div>
            <div className="p-3 rounded-full bg-blue-100">
              <BarChart3 className="h-6 w-6 text-blue-600" />
            </div>
          </div>
        </Card>
        
        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-green-600">Total Jobs Imported (24h)</p>
              <p className="text-3xl font-bold mt-1 text-green-700">{stats.jobsStats24h.totalImported.toLocaleString()}</p>
            </div>
            <div className="p-3 rounded-full bg-green-100">
              <FileCheck className="h-6 w-6 text-green-600" />
            </div>
          </div>
        </Card>
        
        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Success Rate (24h)</p>
              <p className={`text-3xl font-bold mt-1 ${
                stats.jobsStats24h.successRate >= 80 ? 'text-green-700' :
                stats.jobsStats24h.successRate >= 50 ? 'text-yellow-700' :
                'text-red-700'
              }`}>
                {stats.jobsStats24h.successRate}%
              </p>
            </div>
            <div className={`p-3 rounded-full ${
              stats.jobsStats24h.successRate >= 80 ? 'bg-green-100' :
              stats.jobsStats24h.successRate >= 50 ? 'bg-yellow-100' :
              'bg-red-100'
            }`}>
              <TrendingUp className={`h-6 w-6 ${
                stats.jobsStats24h.successRate >= 80 ? 'text-green-600' :
                stats.jobsStats24h.successRate >= 50 ? 'text-yellow-600' :
                'text-red-600'
              }`} />
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}

export default LocationAnalyticsPage;
