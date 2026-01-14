/**
 * Credentials Layout
 * Main layout for credentials management with sub-navigation for different platforms
 */

import { NavLink, Outlet } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { cn } from '@/lib/utils';
import { Skeleton } from '@/components/ui/skeleton';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { scraperCredentialsApi, type CredentialStats } from '@/lib/dashboard-api';
import { Linkedin, Building2, Briefcase, Key } from 'lucide-react';

const credentialNavItems = [
  {
    name: 'LinkedIn',
    href: '/credentials/linkedin',
    icon: Linkedin,
    platform: 'linkedin' as const,
  },
  {
    name: 'Glassdoor',
    href: '/credentials/glassdoor',
    icon: Building2,
    platform: 'glassdoor' as const,
  },
  {
    name: 'Techfetch',
    href: '/credentials/techfetch',
    icon: Briefcase,
    platform: 'techfetch' as const,
  },
];

function StatsCard({ stats, platform }: { stats: CredentialStats; platform: string }) {
  const icons: Record<string, React.ReactNode> = {
    linkedin: <Linkedin className="h-5 w-5 text-blue-600" />,
    glassdoor: <Building2 className="h-5 w-5 text-green-600" />,
    techfetch: <Briefcase className="h-5 w-5 text-purple-600" />,
  };

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center gap-2">
          {icons[platform] || <Key className="h-5 w-5" />}
          <CardTitle className="text-lg capitalize">{platform}</CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-4 gap-4 text-sm">
          <div>
            <p className="text-muted-foreground">Total</p>
            <p className="text-2xl font-bold">{stats.total}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Available</p>
            <p className="text-2xl font-bold text-green-600">{stats.available}</p>
          </div>
          <div>
            <p className="text-muted-foreground">In Use</p>
            <p className="text-2xl font-bold text-blue-600">{stats.inUse}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Failed</p>
            <p className="text-2xl font-bold text-red-600">{stats.failed}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export function CredentialsLayout() {
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['credentials-stats'],
    queryFn: scraperCredentialsApi.getAllStats,
    staleTime: 30000,
  });

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="space-y-2">
        <h1 className="text-3xl font-bold tracking-tight">Scraper Credentials</h1>
        <p className="text-muted-foreground">
          Manage login credentials for LinkedIn, Glassdoor, and Techfetch scrapers
        </p>
      </div>

      {/* Stats Overview */}
      {statsLoading ? (
        <div className="grid gap-4 md:grid-cols-3">
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
        </div>
      ) : stats ? (
        <div className="grid gap-4 md:grid-cols-3">
          <StatsCard stats={stats.linkedin} platform="linkedin" />
          <StatsCard stats={stats.glassdoor} platform="glassdoor" />
          <StatsCard stats={stats.techfetch} platform="techfetch" />
        </div>
      ) : null}

      {/* Sub-navigation */}
      <nav className="flex items-center space-x-1 rounded-lg bg-muted p-1 overflow-x-auto">
        {credentialNavItems.map((item) => (
          <NavLink
            key={item.href}
            to={item.href}
            className={({ isActive }) =>
              cn(
                'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md px-4 py-2 text-sm font-medium transition-all',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
                isActive
                  ? 'bg-background text-foreground shadow-sm'
                  : 'text-muted-foreground hover:bg-background/50 hover:text-foreground'
              )
            }
          >
            <item.icon className="h-4 w-4" />
            <span>{item.name}</span>
          </NavLink>
        ))}
      </nav>

      {/* Sub-route content */}
      <div className="space-y-6">
        <Outlet />
      </div>
    </div>
  );
}

export default CredentialsLayout;
