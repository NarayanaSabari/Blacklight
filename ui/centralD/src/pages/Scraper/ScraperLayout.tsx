/**
 * Scraper Layout
 * Main layout for scraper monitoring with sub-navigation for different sections
 */

import { NavLink, Outlet } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { 
  Zap, 
  History, 
  MapPin,
  Activity
} from "lucide-react";

const scraperNavItems = [
  { 
    name: 'Active Sessions', 
    href: '/scraper/active', 
    icon: Zap,
  },
  { 
    name: 'Recent Activity', 
    href: '/scraper/recent', 
    icon: History 
  },
  { 
    name: 'Location Analytics', 
    href: '/scraper/locations', 
    icon: MapPin 
  },
];

export function ScraperLayout() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="space-y-2">
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
          <Activity className="h-8 w-8 text-primary" />
          Scraper Monitoring
        </h1>
        <p className="text-muted-foreground">
          Real-time monitoring and analytics for scraper sessions
        </p>
      </div>

      {/* Sub-navigation */}
      <nav className="flex items-center space-x-1 rounded-lg bg-muted p-1 overflow-x-auto">
        {scraperNavItems.map((item) => (
          <NavLink
            key={item.href}
            to={item.href}
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

export default ScraperLayout;
