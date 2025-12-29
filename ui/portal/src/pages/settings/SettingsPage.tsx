/**
 * Settings Page
 * Modern settings page with sidebar navigation
 */

import { useSearchParams, useNavigate, useParams } from 'react-router-dom';
import { useMemo, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { 
  User, 
  Building2, 
  Users, 
  FileCheck, 
  Link2, 
  Bell, 
  Shield,
  ChevronRight,
  Settings,
} from 'lucide-react';
import { 
  DocumentRequirementsSettings, 
  EmailIntegrationsSettings, 
  TeamMembersSettings,
  ProfileSettings,
  OrganizationSettings
} from '@/components/settings';

// Navigation items configuration
const navigationItems = [
  {
    id: 'profile',
    label: 'Profile',
    description: 'Your personal information',
    icon: User,
    component: ProfileSettings,
  },
  {
    id: 'organization',
    label: 'Organization',
    description: 'Company details and subscription',
    icon: Building2,
    component: OrganizationSettings,
  },
  {
    id: 'team',
    label: 'Team',
    description: 'Team hierarchy and managers',
    icon: Users,
    component: TeamMembersSettings,
  },
  {
    id: 'onboarding',
    label: 'Onboarding',
    description: 'Document requirements',
    icon: FileCheck,
    component: DocumentRequirementsSettings,
  },
  {
    id: 'integrations',
    label: 'Integrations',
    description: 'Email and third-party services',
    icon: Link2,
    component: EmailIntegrationsSettings,
  },
  {
    id: 'notifications',
    label: 'Notifications',
    description: 'Notification preferences',
    icon: Bell,
    component: null, // Coming soon
  },
  {
    id: 'security',
    label: 'Security',
    description: 'Security and privacy settings',
    icon: Shield,
    component: null, // Coming soon
  },
];

// Coming Soon placeholder component
function ComingSoon({ title, icon: Icon }: { title: string; icon: React.ElementType }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="w-16 h-16 rounded-full bg-slate-100 flex items-center justify-center mb-4">
        <Icon className="h-8 w-8 text-slate-400" />
      </div>
      <h3 className="text-xl font-semibold text-slate-900 mb-2">{title}</h3>
      <p className="text-slate-600 max-w-sm">
        This feature is coming soon. We're working hard to bring you more options.
      </p>
    </div>
  );
}

export function SettingsPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { tab } = useParams<{ tab?: string }>();

  // Valid tab names
  const validTabs = navigationItems.map(item => item.id);

  // Determine active tab
  const activeTab = useMemo(() => {
    // URL path takes precedence
    if (tab && validTabs.includes(tab)) {
      return tab;
    }
    // Then check OAuth callback params
    const hasOAuthParams = searchParams.has('success') || searchParams.has('error');
    const provider = searchParams.get('provider');
    if (hasOAuthParams && (provider === 'gmail' || provider === 'outlook')) {
      return 'integrations';
    }
    return 'profile';
  }, [searchParams, tab, validTabs]);

  // Redirect to default tab if at /settings root
  useEffect(() => {
    if (!tab) {
      navigate(`/settings/${activeTab}`, { replace: true });
    }
  }, [tab, activeTab, navigate]);

  // Handle navigation item click
  const handleNavClick = (itemId: string) => {
    navigate(`/settings/${itemId}`);
  };

  // Get active navigation item
  const activeItem = navigationItems.find(item => item.id === activeTab);
  const ActiveComponent = activeItem?.component;

  return (
    <div className="min-h-[calc(100vh-8rem)]">
      {/* Main Layout */}
      <div className="flex gap-6">
        {/* Sidebar Navigation */}
        <nav className="w-72 flex-shrink-0">
          <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
            <div className="p-4 border-b bg-slate-50">
              <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">
                Settings Menu
              </h2>
            </div>
            <div className="p-2">
              {navigationItems.map((item) => {
                const isActive = activeTab === item.id;
                const Icon = item.icon;
                
                return (
                  <button
                    key={item.id}
                    onClick={() => handleNavClick(item.id)}
                    className={cn(
                      "w-full flex items-center gap-3 px-3 py-3 rounded-lg text-left transition-all duration-150 group",
                      isActive
                        ? "bg-blue-50 text-blue-700"
                        : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                    )}
                  >
                    <div className={cn(
                      "p-2 rounded-lg transition-colors",
                      isActive 
                        ? "bg-blue-100" 
                        : "bg-slate-100 group-hover:bg-slate-200"
                    )}>
                      <Icon className={cn(
                        "h-4 w-4",
                        isActive ? "text-blue-600" : "text-slate-500"
                      )} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className={cn(
                        "font-medium text-sm",
                        isActive ? "text-blue-700" : "text-slate-900"
                      )}>
                        {item.label}
                      </div>
                      <div className={cn(
                        "text-xs truncate",
                        isActive ? "text-blue-600" : "text-slate-500"
                      )}>
                        {item.description}
                      </div>
                    </div>
                    <ChevronRight className={cn(
                      "h-4 w-4 transition-transform",
                      isActive 
                        ? "text-blue-500 translate-x-0" 
                        : "text-slate-400 -translate-x-1 opacity-0 group-hover:translate-x-0 group-hover:opacity-100"
                    )} />
                  </button>
                );
              })}
            </div>
          </div>

          {/* Help Card */}
          <div className="mt-4 p-4 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl border border-blue-100">
            <h3 className="font-semibold text-slate-900 mb-1">Need Help?</h3>
            <p className="text-sm text-slate-600 mb-3">
              Check our documentation or contact support for assistance.
            </p>
            <a 
              href="mailto:support@blacklight.com"
              className="text-sm font-medium text-blue-600 hover:text-blue-700 transition-colors"
            >
              Contact Support
            </a>
          </div>
        </nav>

        {/* Content Area */}
        <div className="flex-1 min-w-0">
          {ActiveComponent ? (
            <ActiveComponent />
          ) : (
            <div className="bg-white rounded-xl border shadow-sm p-8">
              <ComingSoon 
                title={activeItem?.label || 'Coming Soon'} 
                icon={activeItem?.icon || Settings} 
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
