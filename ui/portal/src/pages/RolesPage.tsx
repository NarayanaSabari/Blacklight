import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import { toast } from 'sonner';
import { Loader2, PlusCircle, Edit, Trash2 } from 'lucide-react';
import { usePortalAuth } from '@/contexts/PortalAuthContext';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

interface Permission {
  id: number;
  name: string;
  display_name: string;
  category: string;
  description: string;
}

interface Role {
  id: number;
  name: string;
  display_name: string;
  description: string;
  is_system_role: boolean;
  is_active: boolean;
  tenant_id: number | null;
  permissions: Permission[];
}

interface RoleFormData {
  name: string;
  display_name: string;
  description: string;
  permission_ids: number[];
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api';

const fetchRoles = async (tenantId: number, token: string): Promise<Role[]> => {
  const response = await fetch(`${API_BASE_URL}/tenants/${tenantId}/roles?include_permissions=true`, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });
  if (!response.ok) {
    throw new Error('Failed to fetch roles');
  }
  const data = await response.json();
  return data.roles;
};

const fetchPermissions = async (token: string): Promise<Permission[]> => {
  const response = await fetch(`${API_BASE_URL}/permissions`, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });
  if (!response.ok) {
    throw new Error('Failed to fetch permissions');
  }
  const data = await response.json();
  return data.permissions;
};

const createRole = async (tenantId: number, roleData: RoleFormData, token: string): Promise<Role> => {
  const response = await fetch(`${API_BASE_URL}/tenants/${tenantId}/roles`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(roleData),
  });
  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.error || 'Failed to create role');
  }
  return response.json();
};

const updateRole = async (tenantId: number, roleId: number, roleData: Partial<RoleFormData>, token: string): Promise<Role> => {
  const response = await fetch(`${API_BASE_URL}/tenants/${tenantId}/roles/${roleId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(roleData),
  });
  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.error || 'Failed to update role');
  }
  return response.json();
};

const updateRolePermissions = async (tenantId: number, roleId: number, permissionIds: number[], token: string): Promise<Role> => {
  const response = await fetch(`${API_BASE_URL}/tenants/${tenantId}/roles/${roleId}/permissions`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({ permission_ids: permissionIds }),
  });
  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.error || 'Failed to update role permissions');
  }
  return response.json();
};

const deleteRole = async (tenantId: number, roleId: number, token: string): Promise<void> => {
  const response = await fetch(`${API_BASE_URL}/tenants/${tenantId}/roles/${roleId}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });
  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.error || 'Failed to delete role');
  }
};

export function RolesPage() {
  const { user, accessToken, isAuthenticated, isLoading: isAuthLoading } = usePortalAuth();
  const queryClient = useQueryClient();

  const tenantId = user?.tenant_id;
  const isTenantAdmin = user?.roles?.some((r: any) => r.name === 'TENANT_ADMIN');

  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingRole, setEditingRole] = useState<Role | null>(null);
  const [formData, setFormData] = useState<RoleFormData>({
    name: '',
    display_name: '',
    description: '',
    permission_ids: [],
  });

  const {
    data: roles,
    isLoading: isLoadingRoles,
    error: rolesError,
  } = useQuery<Role[], Error>({
    queryKey: ['roles', tenantId, accessToken],
    queryFn: () => fetchRoles(tenantId!, accessToken!),
    enabled: isAuthenticated && !!tenantId && !!accessToken,
  });

  const {
    data: allPermissions,
    isLoading: isLoadingPermissions,
    error: permissionsError,
  } = useQuery<Permission[], Error>({
    queryKey: ['permissions', accessToken],
    queryFn: () => fetchPermissions(accessToken!),
    enabled: isAuthenticated && !!accessToken,
  });

  const createRoleMutation = useMutation<Role, Error, RoleFormData>({
    mutationFn: (newRole) => createRole(tenantId!, newRole, accessToken!),
    onSuccess: () => {
      toast.success('Role created successfully!');
      queryClient.invalidateQueries({ queryKey: ['roles'] });
      setIsFormOpen(false);
    },
    onError: (error) => {
      toast.error(`Error creating role: ${error.message}`);
    },
  });

  const updateRoleMutation = useMutation<Role, Error, { roleId: number; data: Partial<RoleFormData> }>({
    mutationFn: ({ roleId, data }) => updateRole(tenantId!, roleId, data, accessToken!),
    onSuccess: () => {
      toast.success('Role updated successfully!');
      queryClient.invalidateQueries({ queryKey: ['roles'] });
      setIsFormOpen(false);
      setEditingRole(null);
    },
    onError: (error) => {
      toast.error(`Error updating role: ${error.message}`);
    },
  });

  const updateRolePermissionsMutation = useMutation<Role, Error, { roleId: number; permissionIds: number[] }>({
    mutationFn: ({ roleId, permissionIds }) => updateRolePermissions(tenantId!, roleId, permissionIds, accessToken!),
    onSuccess: () => {
      toast.success('Role permissions updated successfully!');
      queryClient.invalidateQueries({ queryKey: ['roles'] });
      setIsFormOpen(false);
      setEditingRole(null);
    },
    onError: (error) => {
      toast.error(`Error updating role permissions: ${error.message}`);
    },
  });

  const deleteRoleMutation = useMutation<void, Error, number>({
    mutationFn: (roleId) => deleteRole(tenantId!, roleId, accessToken!),
    onSuccess: () => {
      toast.success('Role deleted successfully!');
      queryClient.invalidateQueries({ queryKey: ['roles'] });
    },
    onError: (error) => {
      toast.error(`Error deleting role: ${error.message}`);
    },
  });

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { id, value } = e.target;
    setFormData((prev) => ({ ...prev, [id]: value }));
  };

  const handlePermissionChange = (permissionId: number, checked: boolean) => {
    setFormData((prev) => {
      const newPermissionIds = checked
        ? [...prev.permission_ids, permissionId]
        : prev.permission_ids.filter((id) => id !== permissionId);
      return { ...prev, permission_ids: newPermissionIds };
    });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (editingRole) {
      // Update role details
      updateRoleMutation.mutate({
        roleId: editingRole.id,
        data: {
          display_name: formData.display_name,
          description: formData.description,
        },
      });
      // Update role permissions
      updateRolePermissionsMutation.mutate({
        roleId: editingRole.id,
        permissionIds: formData.permission_ids,
      });
    } else {
      createRoleMutation.mutate(formData);
    }
  };

  const openCreateForm = () => {
    setEditingRole(null);
    setFormData({ name: '', display_name: '', description: '', permission_ids: [] });
    setIsFormOpen(true);
  };

  const openEditForm = (role: Role) => {
    setEditingRole(role);
    setFormData({
      name: role.name,
      display_name: role.display_name,
      description: role.description,
      permission_ids: role.permissions.map((p) => p.id),
    });
    setIsFormOpen(true);
  };

  if (isAuthLoading || isLoadingRoles || isLoadingPermissions) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Authentication Required</AlertTitle>
        <AlertDescription>Please log in to view this page.</AlertDescription>
      </Alert>
    );
  }

  if (!isTenantAdmin) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Access Denied</AlertTitle>
        <AlertDescription>You do not have permission to manage roles.</AlertDescription>
      </Alert>
    );
  }

  if (rolesError) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Error</AlertTitle>
        <AlertDescription>Error loading roles: {rolesError.message}</AlertDescription>
      </Alert>
    );
  }

  if (permissionsError) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Error</AlertTitle>
        <AlertDescription>Error loading permissions: {permissionsError.message}</AlertDescription>
      </Alert>
    );
  }

  const groupedPermissions = allPermissions?.reduce((acc, perm) => {
    const category = perm.category || 'Uncategorized';
    if (!acc[category]) {
      acc[category] = [];
    }
    acc[category].push(perm);
    return acc;
  }, {} as Record<string, Permission[]>);

  return (
    <div className="container mx-auto py-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Roles Management</h1>
        <Button onClick={openCreateForm}>
          <PlusCircle className="mr-2 h-4 w-4" /> Create New Role
        </Button>
      </div>

      <Dialog open={isFormOpen} onOpenChange={setIsFormOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingRole ? 'Edit Role' : 'Create New Role'}</DialogTitle>
            <DialogDescription>
              {editingRole
                ? 'Edit the details and permissions for this role.'
                : 'Create a new custom role for your tenant.'}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="grid gap-4 py-4">
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="display_name" className="text-right">
                Display Name
              </Label>
              <Input
                id="display_name"
                value={formData.display_name}
                onChange={handleInputChange}
                className="col-span-3"
                required
              />
            </div>
            {!editingRole && (
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="name" className="text-right">
                  Internal Name
                </Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={handleInputChange}
                  className="col-span-3"
                  placeholder="e.g., CUSTOM_HR_ROLE (UPPERCASE, alphanumeric, underscores)"
                  required
                />
              </div>
            )}
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="description" className="text-right">
                Description
              </Label>
              <Textarea
                id="description"
                value={formData.description}
                onChange={handleInputChange}
                className="col-span-3"
              />
            </div>

            <div className="col-span-4">
              <h3 className="text-lg font-semibold mb-2">Permissions</h3>
              {groupedPermissions &&
                Object.entries(groupedPermissions).map(([category, perms]) => (
                  <div key={category} className="mb-4">
                    <h4 className="font-medium text-gray-700 dark:text-gray-300 mb-2">{category}</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                      {perms.map((perm) => (
                        <div key={perm.id} className="flex items-center space-x-2">
                          <Checkbox
                            id={`perm-${perm.id}`}
                            checked={formData.permission_ids.includes(perm.id)}
                            onCheckedChange={(checked) =>
                              handlePermissionChange(perm.id, checked as boolean)
                            }
                          />
                          <label
                            htmlFor={`perm-${perm.id}`}
                            className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                          >
                            {perm.display_name}
                            <p className="text-xs text-muted-foreground">{perm.description}</p>
                          </label>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
            </div>

            <DialogFooter>
              <Button type="submit" disabled={createRoleMutation.isPending || updateRoleMutation.isPending || updateRolePermissionsMutation.isPending}>
                {createRoleMutation.isPending || updateRoleMutation.isPending || updateRolePermissionsMutation.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : editingRole ? (
                  'Save Changes'
                ) : (
                  'Create Role'
                )}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Display Name</TableHead>
              <TableHead>Internal Name</TableHead>
              <TableHead>Description</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {roles?.map((role) => (
              <TableRow key={role.id}>
                <TableCell className="font-medium">{role.display_name}</TableCell>
                <TableCell>{role.name}</TableCell>
                <TableCell>{role.description}</TableCell>
                <TableCell>{role.is_system_role ? 'System' : 'Custom'}</TableCell>
                <TableCell>{role.is_active ? 'Active' : 'Inactive'}</TableCell>
                <TableCell className="text-right">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => openEditForm(role)}
                    className="mr-2"
                    disabled={role.is_system_role} // Prevent editing system roles
                  >
                    <Edit className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => deleteRoleMutation.mutate(role.id)}
                    disabled={role.is_system_role || deleteRoleMutation.isPending} // Prevent deleting system roles
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
