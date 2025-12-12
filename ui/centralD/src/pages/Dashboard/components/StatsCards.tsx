/**
 * Stats Cards Component
 * Displays key metrics at the top of the dashboard
 */

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useQuery } from "@tanstack/react-query";
import { dashboardApi, type DashboardStats } from "@/lib/dashboard-api";
import { usePMAdminAuth } from "@/hooks/usePMAdminAuth";
import { 
  ListTodo, 
  Wifi, 
  Tags, 
  Briefcase, 
  Key,
  type LucideIcon 
} from "lucide-react";

interface StatCard {
  title: string;
  value: number;
  icon: LucideIcon;
  description: string;
  trend?: string;
  trendType?: 'positive' | 'negative' | 'neutral';
}

export function StatsCards() {
  const { isAuthenticated, isLoading: authLoading } = usePMAdminAuth();
  
  const { data: stats, isLoading, error } = useQuery<DashboardStats>({
    queryKey: ['dashboard-stats'],
    queryFn: dashboardApi.getStats,
    refetchInterval: 30000, // Refresh every 30 seconds
    enabled: !authLoading && isAuthenticated, // Only fetch when auth is complete and user is authenticated
  });

  const cards: StatCard[] = [
    {
      title: "Pending Queue",
      value: stats?.pendingQueue ?? 0,
      icon: ListTodo,
      description: "Roles awaiting scrape",
      trend: "Queue depth",
      trendType: 'neutral',
    },
    {
      title: "Active Scrapers",
      value: stats?.activeScrapers ?? 0,
      icon: Wifi,
      description: "Currently running",
      trend: stats?.activeScrapers ? "All healthy" : "None active",
      trendType: stats?.activeScrapers ? 'positive' : 'neutral',
    },
    {
      title: "Roles to Review",
      value: stats?.newRoles ?? 0,
      icon: Tags,
      description: "Pending normalization",
      trend: stats?.newRoles ? `${stats.newRoles} need attention` : "All clear",
      trendType: stats?.newRoles ? 'negative' : 'positive',
    },
    {
      title: "Jobs Today",
      value: stats?.jobsImported ?? 0,
      icon: Briefcase,
      description: "Imported jobs",
      trend: "Today's imports",
      trendType: 'positive',
    },
    {
      title: "Active API Keys",
      value: stats?.activeApiKeys ?? 0,
      icon: Key,
      description: "Valid scraper keys",
      trend: "Ready for use",
      trendType: 'neutral',
    },
  ];

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        {[...Array(5)].map((_, i) => (
          <Card key={i}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-4 w-4" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-8 w-16 mb-2" />
              <Skeleton className="h-3 w-32" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
        <p className="text-sm text-destructive">Failed to load dashboard statistics</p>
      </div>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
      {cards.map((card) => (
        <Card key={card.title}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              {card.title}
            </CardTitle>
            <card.icon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {card.value.toLocaleString()}
            </div>
            <p className="text-xs text-muted-foreground">
              {card.description}
            </p>
            {card.trend && (
              <p className={`text-xs mt-1 ${
                card.trendType === 'positive' ? 'text-green-600' :
                card.trendType === 'negative' ? 'text-amber-600' :
                'text-muted-foreground'
              }`}>
                {card.trend}
              </p>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
