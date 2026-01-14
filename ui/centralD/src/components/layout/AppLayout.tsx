/**
 * Application Layout with Sidebar Navigation
 * Features collapsible Dashboard dropdown with sub-navigation items
 */

import { Link, Outlet, useLocation } from 'react-router-dom';
import { 
  Building2, 
  Users, 
  CreditCard, 
  Menu, 
  LayoutDashboard, 
  Briefcase, 
  Key,
  ChevronDown,
  ChevronRight,
  Clock,
  MapPin,
  Tags,
  Globe,
  Zap
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { UserProfileMenu } from '@/components/layout/UserProfileMenu';
import { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

// Dashboard sub-navigation items
const dashboardSubItems = [
  { name: 'Overview', href: '/dashboard', icon: LayoutDashboard, exact: true },
  { name: 'Active Sessions', href: '/dashboard/scraper/active', icon: Zap },
  { name: 'Recent Activity', href: '/dashboard/scraper/recent', icon: Clock },
  { name: 'Location Analytics', href: '/dashboard/scraper/locations', icon: MapPin },
  { name: 'API Keys', href: '/dashboard/api-keys', icon: Key },
  { name: 'Jobs Overview', href: '/dashboard/jobs', icon: Briefcase },
  { name: 'Scraper Queue', href: '/dashboard/queue', icon: Tags },
  { name: 'Platforms', href: '/dashboard/platforms', icon: Globe },
];

// Main navigation items
const navigation = [
  { 
    name: 'Dashboard', 
    href: '/dashboard', 
    icon: LayoutDashboard,
    hasDropdown: true,
    subItems: dashboardSubItems
  },
  { name: 'Tenants', href: '/tenants', icon: Building2 },
  { name: 'Jobs', href: '/jobs', icon: Briefcase },
  { name: 'Credentials', href: '/credentials', icon: Key },
  { name: 'Subscription Plans', href: '/plans', icon: CreditCard },
  { name: 'Admin Users', href: '/admins', icon: Users },
];

export function AppLayout() {
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [dashboardExpanded, setDashboardExpanded] = useState(true);

  // Auto-expand dashboard dropdown when on a dashboard page
  useEffect(() => {
    if (location.pathname.startsWith('/dashboard')) {
      setDashboardExpanded(true);
    }
  }, [location.pathname]);

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 w-64 bg-card border-r transform transition-transform duration-200 ease-in-out lg:translate-x-0 lg:static lg:inset-auto',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <div className="flex h-16 items-center border-b px-6">
          <h1 className="text-xl font-bold">Blacklight</h1>
        </div>

        <nav className="flex-1 space-y-1 px-3 py-4 overflow-y-auto max-h-[calc(100vh-4rem)]">
          {navigation.map((item) => {
            const isActive = location.pathname.startsWith(item.href);
            
            // Render collapsible for dashboard
            if (item.hasDropdown && item.subItems) {
              return (
                <Collapsible
                  key={item.name}
                  open={dashboardExpanded}
                  onOpenChange={setDashboardExpanded}
                >
                  <CollapsibleTrigger asChild>
                    <button
                      className={cn(
                        'flex items-center justify-between w-full gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                        isActive
                          ? 'bg-primary/10 text-primary'
                          : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                      )}
                    >
                      <div className="flex items-center gap-3">
                        <item.icon className="h-5 w-5" />
                        {item.name}
                      </div>
                      {dashboardExpanded ? (
                        <ChevronDown className="h-4 w-4" />
                      ) : (
                        <ChevronRight className="h-4 w-4" />
                      )}
                    </button>
                  </CollapsibleTrigger>
                  <CollapsibleContent className="pl-4 mt-1 space-y-1">
                    {item.subItems.map((subItem) => {
                      const isSubActive = subItem.exact 
                        ? location.pathname === subItem.href
                        : location.pathname.startsWith(subItem.href);
                      
                      return (
                        <Link
                          key={subItem.href}
                          to={subItem.href}
                          onClick={() => setSidebarOpen(false)}
                          className={cn(
                            'flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors',
                            isSubActive
                              ? 'bg-primary text-primary-foreground'
                              : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                          )}
                        >
                          <subItem.icon className="h-4 w-4" />
                          {subItem.name}
                        </Link>
                      );
                    })}
                  </CollapsibleContent>
                </Collapsible>
              );
            }

            // Regular navigation item
            return (
              <Link
                key={item.name}
                to={item.href}
                onClick={() => setSidebarOpen(false)}
                className={cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                )}
              >
                <item.icon className="h-5 w-5" />
                {item.name}
              </Link>
            );
          })}
        </nav>
      </aside>

      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-background/80 backdrop-blur-sm lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Header */}
        <header className="flex h-16 items-center gap-4 border-b bg-card px-6">
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu className="h-6 w-6" />
          </Button>
          <div className="flex-1" />

          {/* User Profile Menu in top-right */}
          <UserProfileMenu />
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
