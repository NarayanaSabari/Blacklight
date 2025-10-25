/**
 * Portal Layout Component
 * Main layout with sidebar navigation, header, and content area
 */

import { useState } from 'react';
import { useLocation, Link } from 'react-router-dom';
import { usePortalAuth } from '@/contexts/PortalAuthContext';
import {
  Bell,
  ChevronDown,
  LogOut,
  Menu,
  Users,
  Briefcase,
  BarChart3,
  Settings,
  Building2,
  FileText,
  Calendar,
  UserCog,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';

interface LayoutProps {
  children: React.ReactNode;
}

interface NavItem {
  id: string;
  label: string;
  icon: React.ElementType;
  href: string;
  roles: string[];
  badge?: string;
}

const navigation: NavItem[] = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    icon: BarChart3,
    href: '/dashboard',
    roles: ['TENANT_ADMIN', 'RECRUITER', 'HIRING_MANAGER'],
  },
  {
    id: 'candidates',
    label: 'Candidates',
    icon: Users,
    href: '/candidates',
    roles: ['TENANT_ADMIN', 'RECRUITER', 'HIRING_MANAGER'],
  },
  {
    id: 'jobs',
    label: 'Job Postings',
    icon: Briefcase,
    href: '/jobs',
    roles: ['TENANT_ADMIN', 'RECRUITER'],
  },
  {
    id: 'applications',
    label: 'Applications',
    icon: FileText,
    href: '/applications',
    roles: ['TENANT_ADMIN', 'RECRUITER', 'HIRING_MANAGER'],
  },
  {
    id: 'interviews',
    label: 'Interviews',
    icon: Calendar,
    href: '/interviews',
    roles: ['TENANT_ADMIN', 'RECRUITER', 'HIRING_MANAGER'],
  },
  {
    id: 'users',
    label: 'Team Members',
    icon: UserCog,
    href: '/users',
    roles: ['TENANT_ADMIN'],
  },
  {
    id: 'settings',
    label: 'Settings',
    icon: Settings,
    href: '/settings',
    roles: ['TENANT_ADMIN'],
  },
];

export function Layout({ children }: LayoutProps) {
  const { user, tenantName, logout } = usePortalAuth();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(true);

  if (!user) {
    return null;
  }

  // Filter navigation based on user role
  const filteredNavigation = navigation.filter(item =>
    item.roles.includes(user.role.name)
  );

  const getInitials = (name: string) => {
    return name.split(' ').map(n => n[0]).join('').toUpperCase();
  };

  const getCurrentPageTitle = () => {
    const currentPath = location.pathname;
    const currentNav = navigation.find(nav => nav.href === currentPath);
    return currentNav?.label || 'Dashboard';
  };

  const getStatusBadgeColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'active': return 'bg-green-100 text-green-800';
      case 'suspended': return 'bg-yellow-100 text-yellow-800';
      case 'inactive': return 'bg-gray-100 text-gray-800';
      default: return 'bg-blue-100 text-blue-800';
    }
  };

  return (
    <div className="h-screen bg-slate-50 overflow-hidden">
      <div className="flex h-full">
        {/* Sidebar */}
        <div className={`${sidebarOpen ? 'w-64' : 'w-16'} transition-all duration-300 bg-white border-r border-slate-200 flex flex-col flex-shrink-0`}>
          {/* Logo */}
          <div className="p-4 border-b border-slate-200 flex-shrink-0">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <Building2 className="h-8 w-8 text-primary" />
              </div>
              {sidebarOpen && (
                <div className="ml-3 min-w-0">
                  <h1 className="text-lg font-semibold text-slate-900 truncate">Portal</h1>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-sm text-slate-600 truncate">{tenantName}</span>
                    {user.tenant?.status && (
                      <Badge className={`text-xs flex-shrink-0 ${getStatusBadgeColor(user.tenant.status)}`}>
                        {user.tenant.status}
                      </Badge>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
            {filteredNavigation.map((item) => (
              <Link
                key={item.id}
                to={item.href}
                className={`w-full flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
                  location.pathname === item.href
                    ? 'bg-primary text-primary-foreground'
                    : 'text-slate-700 hover:bg-slate-100 hover:text-slate-900'
                }`}
              >
                <item.icon className="h-5 w-5 flex-shrink-0" />
                {sidebarOpen && (
                  <>
                    <span className="ml-3 truncate">{item.label}</span>
                    {item.badge && (
                      <Badge className="ml-auto text-xs flex-shrink-0">
                        {item.badge}
                      </Badge>
                    )}
                  </>
                )}
              </Link>
            ))}
          </nav>

          {/* Sidebar Toggle */}
          <div className="p-4 border-t border-slate-200 flex-shrink-0">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="w-full justify-center"
              title={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
            >
              <Menu className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          {/* Header */}
          <header className="bg-white border-b border-slate-200 px-4 sm:px-6 py-4 flex-shrink-0">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4 min-w-0">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSidebarOpen(!sidebarOpen)}
                  className="lg:hidden"
                >
                  <Menu className="h-5 w-5" />
                </Button>
                <h2 className="text-xl font-semibold text-slate-900 truncate">
                  {getCurrentPageTitle()}
                </h2>
              </div>

              <div className="flex items-center gap-2 sm:gap-4 flex-shrink-0">
                {/* Notifications */}
                <Button variant="ghost" size="sm" title="Notifications">
                  <Bell className="h-5 w-5" />
                </Button>

                {/* User Menu */}
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" className="flex items-center gap-2">
                      <Avatar className="h-8 w-8">
                        <AvatarFallback className="bg-primary text-primary-foreground">
                          {getInitials(user.full_name)}
                        </AvatarFallback>
                      </Avatar>
                      <div className="hidden sm:block text-left">
                        <div className="text-sm font-medium truncate max-w-32">
                          {user.full_name}
                        </div>
                        <div className="text-xs text-slate-500">
                          {user.role.display_name}
                        </div>
                      </div>
                      <ChevronDown className="h-4 w-4 hidden sm:block" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-56">
                    <DropdownMenuLabel>My Account</DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem disabled>
                      <div className="flex flex-col">
                        <span className="font-medium">{user.full_name}</span>
                        <span className="text-xs text-slate-500">{user.email}</span>
                      </div>
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem asChild>
                      <Link to="/settings">
                        <Settings className="mr-2 h-4 w-4" />
                        Settings
                      </Link>
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={logout} className="text-red-600">
                      <LogOut className="mr-2 h-4 w-4" />
                      Log out
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>
          </header>

          {/* Main Content Area */}
          <main className="flex-1 overflow-auto bg-slate-50">
            <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto">
              {children}
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
