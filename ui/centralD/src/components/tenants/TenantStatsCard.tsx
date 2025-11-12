/**
 * Tenant Stats Card
 * Displays usage statistics with progress bars
 */

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { BarChart3, Users, Briefcase, FileText, HardDrive } from 'lucide-react';
import type { Tenant } from '@/types';

interface TenantStatsCardProps {
  tenant: Tenant;
  stats?: {
    user_count: number;
    candidates_count: number;
    jobs_count: number;
    storage_used_gb: number;
  };
}

export function TenantStatsCard({ tenant, stats }: TenantStatsCardProps) {
  const plan = tenant.subscription_plan;

  if (!plan) {
    return null;
  }

  // Use provided stats or default to 0
  const currentStats = stats || {
    user_count: 0,
    candidates_count: 0,
    jobs_count: 0,
    storage_used_gb: 0,
  };

  const getUsagePercentage = (current: number, max: number) => {
    if (max === 0) return 0;
    return Math.min((current / max) * 100, 100);
  };

  const statItems = [
    {
      label: 'Users',
      icon: Users,
      current: currentStats.user_count,
      max: plan.max_users,
      percentage: getUsagePercentage(currentStats.user_count, plan.max_users),
    },
    {
      label: 'Candidates',
      icon: FileText,
      current: currentStats.candidates_count,
      max: plan.max_candidates,
      percentage: getUsagePercentage(currentStats.candidates_count, plan.max_candidates),
    },
    {
      label: 'Jobs',
      icon: Briefcase,
      current: currentStats.jobs_count,
      max: plan.max_jobs,
      percentage: getUsagePercentage(currentStats.jobs_count, plan.max_jobs),
    },
    {
      label: 'Storage',
      icon: HardDrive,
      current: currentStats.storage_used_gb,
      max: plan.max_storage_gb,
      percentage: getUsagePercentage(currentStats.storage_used_gb, plan.max_storage_gb),
      unit: 'GB',
    },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BarChart3 className="h-5 w-5" />
          Usage Statistics
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {statItems.map((item) => {
          const Icon = item.icon;
          const percentage = item.percentage;
          const isNearLimit = percentage >= 75;
          const isOverLimit = percentage >= 90;

          return (
            <div key={item.label} className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Icon className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm font-medium">{item.label}</span>
                </div>
                <div className="text-sm font-medium">
                  {item.current} / {item.max}
                  {item.unit ? ` ${item.unit}` : ''}
                </div>
              </div>
              <div className="space-y-1">
                <Progress
                  value={percentage}
                  className="h-2"
                />
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">
                    {percentage.toFixed(1)}% used
                  </span>
                  {isOverLimit && (
                    <span className="text-destructive font-medium">Approaching limit!</span>
                  )}
                  {!isOverLimit && isNearLimit && (
                    <span className="text-warning font-medium">High usage</span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
