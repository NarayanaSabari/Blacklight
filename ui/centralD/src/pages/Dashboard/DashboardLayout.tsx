/**
 * Dashboard Layout
 * Main layout for dashboard with sub-navigation for different sections
 */

import { NavLink, Outlet } from 'react-router-dom';
import { StatsCards } from './components';
import { cn } from '@/lib/utils';
import { 
  LayoutDashboard, 
  Key, 
  Briefcase, 
  Tags,
  Globe
} from "lucide-react";

const dashboardNavItems = [
  { 
    name: 'Overview', 
    href: '/dashboard', 
    icon: LayoutDashboard,
    end: true // Only match exact path
  },
  { 
    name: 'API Keys', 
    href: '/dashboard/api-keys', 
    icon: Key 
  },
  { 
    name: 'Jobs Overview', 
    href: '/dashboard/jobs', 
    icon: Briefcase 
  },
  { 
    name: 'Scraper Queue', 
    href: '/dashboard/queue', 
    icon: Tags 
  },
  { 
    name: 'Platforms', 
    href: '/dashboard/platforms', 
    icon: Globe 
  },
];

export function DashboardLayout() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="space-y-2">
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Job matching system monitoring and management
        </p>
      </div>

      {/* Stats Cards - Always visible */}
      <StatsCards />

      {/* Sub-navigation */}
      <nav className="flex items-center space-x-1 rounded-lg bg-muted p-1 overflow-x-auto">
        {dashboardNavItems.map((item) => (
          <NavLink
            key={item.href}
            to={item.href}
            end={item.end}
            className={({ isActive }) =>
              cn(
                "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md px-4 py-2 text-sm font-medium transition-all",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                isActive
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:bg-background/50 hover:text-foreground"
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

export default DashboardLayout;
