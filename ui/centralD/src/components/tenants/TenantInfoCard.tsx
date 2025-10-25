/**
 * Tenant Info Card
 * Displays basic tenant information
 */

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Building2, Mail, Phone, Calendar, Link2 } from 'lucide-react';
import type { Tenant } from '@/types';

interface TenantInfoCardProps {
  tenant: Tenant;
}

export function TenantInfoCard({ tenant }: TenantInfoCardProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ACTIVE':
        return 'bg-green-500/10 text-green-500 hover:bg-green-500/20';
      case 'SUSPENDED':
        return 'bg-yellow-500/10 text-yellow-500 hover:bg-yellow-500/20';
      case 'INACTIVE':
        return 'bg-gray-500/10 text-gray-500 hover:bg-gray-500/20';
      default:
        return 'bg-gray-500/10 text-gray-500 hover:bg-gray-500/20';
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Building2 className="h-5 w-5" />
            Company Information
          </CardTitle>
          <Badge className={getStatusColor(tenant.status)}>{tenant.status}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-1">
            <div className="text-sm text-muted-foreground">Company Name</div>
            <div className="font-medium">{tenant.name}</div>
          </div>

          <div className="space-y-1">
            <div className="text-sm text-muted-foreground flex items-center gap-1">
              <Link2 className="h-3 w-3" />
              Tenant Slug
            </div>
            <div className="font-mono text-sm">{tenant.slug}</div>
          </div>

          <div className="space-y-1">
            <div className="text-sm text-muted-foreground flex items-center gap-1">
              <Mail className="h-3 w-3" />
              Company Email
            </div>
            <div className="font-medium">{tenant.company_email}</div>
          </div>

          <div className="space-y-1">
            <div className="text-sm text-muted-foreground flex items-center gap-1">
              <Phone className="h-3 w-3" />
              Company Phone
            </div>
            <div className="font-medium">{tenant.company_phone || 'Not provided'}</div>
          </div>

          <div className="space-y-1">
            <div className="text-sm text-muted-foreground flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              Created
            </div>
            <div className="font-medium">
              {new Date(tenant.created_at).toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
              })}
            </div>
          </div>

          <div className="space-y-1">
            <div className="text-sm text-muted-foreground flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              Last Updated
            </div>
            <div className="font-medium">
              {new Date(tenant.updated_at).toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
              })}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
