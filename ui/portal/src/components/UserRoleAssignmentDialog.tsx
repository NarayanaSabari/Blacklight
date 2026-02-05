import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { Loader2 } from 'lucide-react';
import { usePortalAuth } from '@/contexts/PortalAuthContext';
import type { PortalUserFull } from '@/types';

interface Role {
  id: number;
  name: string;
  display_name: string;
  description: string;
  is_system_role: boolean;
  is_active: boolean;
  tenant_id: number | null;
}

interface UserRoleAssignmentDialogProps {
  user: PortalUserFull | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api';

const fetchTenantRoles = async (tenantId: number, token: string): Promise<Role[]> => {
  const response = await fetch(`${API_BASE_URL}/portal/tenants/${tenantId}/roles`, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });
  if (!response.ok) {
    throw new Error('Failed to fetch tenant roles');
  }
  const data = await response.json();
  return data.roles;
};

const assignUserRoles = async (userId: number, roleIds: number[], token: string): Promise<PortalUserFull> => {
  const response = await fetch(`${API_BASE_URL}/portal/users/${userId}/roles`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({ role_ids: roleIds }),
  });
  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.error || 'Failed to assign roles');
  }
  return response.json();
};

export function UserRoleAssignmentDialog({ user, open, onOpenChange }: UserRoleAssignmentDialogProps) {
  const { accessToken, isAuthenticated, user: currentUser } = usePortalAuth();
  const queryClient = useQueryClient();
  const [selectedRoleIds, setSelectedRoleIds] = useState<number[]>([]);

  const tenantId = currentUser?.tenant_id;

  const {
    data: availableRoles,
    isLoading: isLoadingRoles,
    error: rolesError,
  } = useQuery<Role[], Error>({
    queryKey: ['tenantRoles', tenantId, accessToken],
    queryFn: () => fetchTenantRoles(tenantId!, accessToken!),
    enabled: isAuthenticated && !!tenantId && !!accessToken && open, // Only fetch when dialog is open
  });

  useEffect(() => {
    if (user && availableRoles) {
      // Initialize selected roles with user's current roles
      setSelectedRoleIds(user.roles.map(r => r.id));
    }
  }, [user, availableRoles]);

  const assignRolesMutation = useMutation<PortalUserFull, Error, { userId: number; roleIds: number[] }>({
    mutationFn: ({ userId, roleIds }) => assignUserRoles(userId, roleIds, accessToken!),
    onSuccess: () => {
      toast.success('User roles updated successfully!');
      queryClient.invalidateQueries({ queryKey: ['users'] }); // Invalidate users query to refetch
      onOpenChange(false);
    },
    onError: (error) => {
      toast.error(`Error updating user roles: ${error.message}`);
    },
  });

  const handleRoleChange = (roleId: number, checked: boolean) => {
    setSelectedRoleIds((prev) => {
      const newRoleIds = checked
        ? [...prev, roleId]
        : prev.filter((id) => id !== roleId);
      return newRoleIds;
    });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (user) {
      assignRolesMutation.mutate({ userId: user.id, roleIds: selectedRoleIds });
    }
  };

  if (!user) {
    return null;
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Assign Roles to {user.full_name}</DialogTitle>
          <DialogDescription>
            Select the roles you want to assign to this user.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="grid gap-4 py-4">
          {isLoadingRoles ? (
            <div className="flex items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
            </div>
          ) : rolesError ? (
            <p className="text-red-500">Error loading roles: {rolesError.message}</p>
          ) : (
            <div className="space-y-2">
              {availableRoles?.map((role) => (
                <div key={role.id} className="flex items-center space-x-2">
                  <Checkbox
                    id={`role-${role.id}`}
                    checked={selectedRoleIds.includes(role.id)}
                    onCheckedChange={(checked) => handleRoleChange(role.id, checked as boolean)}
                    disabled={role.is_system_role} // System roles cannot be unassigned/assigned directly here
                  />
                  <Label htmlFor={`role-${role.id}`}>
                    {role.display_name} {role.is_system_role && '(System Role)'}
                    <p className="text-xs text-muted-foreground">{role.description}</p>
                  </Label>
                </div>
              ))}
            </div>
          )}
          <DialogFooter>
            <Button type="submit" disabled={assignRolesMutation.isPending || isLoadingRoles}>
              {assignRolesMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                'Save Roles'
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
