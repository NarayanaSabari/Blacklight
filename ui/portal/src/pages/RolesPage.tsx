import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { Loader2, PlusCircle, Edit, Trash2, ChevronDown, ChevronRight, CheckSquare, Square } from 'lucide-react';
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

import { apiRequest } from '@/lib/api-client';

const fetchRoles = async (_tenantId: number): Promise<Role[]> => {
  const data = await apiRequest.get<{ roles: Role[] }>(`/api/roles?include_permissions=true`);
  return data.roles;
};

const fetchPermissions = async (): Promise<Permission[]> => {
  const data = await apiRequest.get<{ permissions: Permission[] }>('/api/permissions');
  return data.permissions;
};

const createRole = async (tenantId: number, roleData: RoleFormData): Promise<Role> => {
  return await apiRequest.post(`/api/tenants/${tenantId}/roles`, roleData);
};

const updateRole = async (tenantId: number, roleId: number, roleData: Partial<RoleFormData>): Promise<Role> => {
  return await apiRequest.put(`/api/tenants/${tenantId}/roles/${roleId}`, roleData);
};

const updateRolePermissions = async (tenantId: number, roleId: number, permissionIds: number[]): Promise<Role> => {
  return await apiRequest.put(`/api/tenants/${tenantId}/roles/${roleId}/permissions`, { permission_ids: permissionIds });
};

const deleteRole = async (tenantId: number, roleId: number): Promise<void> => {
  await apiRequest.delete(`/api/tenants/${tenantId}/roles/${roleId}`);
};

export function RolesPage() {
  const { user, isAuthenticated, isLoading: isAuthLoading } = usePortalAuth();
  const queryClient = useQueryClient();

  const tenantId = user?.tenant_id;
  const isTenantAdmin = user?.roles?.some((r) => r.name === 'TENANT_ADMIN');

  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingRole, setEditingRole] = useState<Role | null>(null);
  const [formData, setFormData] = useState<RoleFormData>({
    name: '',
    display_name: '',
    description: '',
    permission_ids: [],
  });
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());

  const {
    data: roles,
    isLoading: isLoadingRoles,
    error: rolesError,
  } = useQuery<Role[], Error>({
    queryKey: ['roles', tenantId],
    queryFn: () => fetchRoles(tenantId!),
    enabled: isAuthenticated && !!tenantId,
  });

  const {
    data: allPermissions,
    isLoading: isLoadingPermissions,
    error: permissionsError,
  } = useQuery<Permission[], Error>({
    queryKey: ['permissions'],
    queryFn: () => fetchPermissions(),
    enabled: isAuthenticated,
  });

  const createRoleMutation = useMutation<Role, Error, RoleFormData>({
    mutationFn: (newRole) => createRole(tenantId!, newRole),
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
    mutationFn: ({ roleId, data }) => updateRole(tenantId!, roleId, data),
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
    mutationFn: ({ roleId, permissionIds }) => updateRolePermissions(tenantId!, roleId, permissionIds),
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
    mutationFn: (roleId) => deleteRole(tenantId!, roleId),
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
    // Expand all categories by default for easier navigation
    if (groupedPermissions) {
      setExpandedCategories(new Set(Object.keys(groupedPermissions)));
    }
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
    // Expand categories that have selected permissions
    if (groupedPermissions) {
      const categoriesToExpand = new Set<string>();
      Object.entries(groupedPermissions).forEach(([category, perms]) => {
        if (perms.some((p) => role.permissions.some((rp) => rp.id === p.id))) {
          categoriesToExpand.add(category);
        }
      });
      setExpandedCategories(categoriesToExpand);
    }
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
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle>{editingRole ? 'Edit Role' : 'Create New Role'}</DialogTitle>
            <DialogDescription>
              {editingRole
                ? 'Edit the details and permissions for this role.'
                : 'Create a new custom role for your tenant.'}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="flex flex-col gap-6 overflow-hidden">
            {/* Role Details Section */}
            <div className="space-y-4">
              <div className="grid gap-2">
                <Label htmlFor="display_name">
                  Display Name <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="display_name"
                  value={formData.display_name}
                  onChange={handleInputChange}
                  placeholder="e.g., Senior Recruiter"
                  required
                />
              </div>
              {!editingRole && (
                <div className="grid gap-2">
                  <Label htmlFor="name">
                    Internal Name <span className="text-destructive">*</span>
                  </Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={handleInputChange}
                    placeholder="e.g., SENIOR_RECRUITER (UPPERCASE, alphanumeric, underscores)"
                    required
                  />
                  <p className="text-xs text-muted-foreground">
                    Must be UPPERCASE with underscores. Cannot be changed after creation.
                  </p>
                </div>
              )}
              <div className="grid gap-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  value={formData.description}
                  onChange={handleInputChange}
                  placeholder="Brief description of this role's responsibilities..."
                  rows={3}
                />
              </div>
            </div>

            <Separator />

            {/* Permissions Section */}
            <div className="flex-1 overflow-hidden flex flex-col">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <h3 className="text-lg font-semibold">Permissions</h3>
                  <p className="text-sm text-muted-foreground">
                    Select permissions for this role ({formData.permission_ids.length} selected)
                  </p>
                </div>
                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      if (groupedPermissions) {
                        const allPermIds = Object.values(groupedPermissions)
                          .flat()
                          .map((p) => p.id);
                        setFormData((prev) => ({ ...prev, permission_ids: allPermIds }));
                      }
                    }}
                  >
                    <CheckSquare className="mr-2 h-4 w-4" />
                    Select All
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setFormData((prev) => ({ ...prev, permission_ids: [] }))}
                  >
                    <Square className="mr-2 h-4 w-4" />
                    Clear All
                  </Button>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto pr-2 space-y-2">
                {groupedPermissions &&
                  Object.entries(groupedPermissions).map(([category, perms]) => {
                    const categoryPermIds = perms.map((p) => p.id);
                    const selectedInCategory = categoryPermIds.filter((id) =>
                      formData.permission_ids.includes(id)
                    ).length;
                    const isExpanded = expandedCategories.has(category);

                    return (
                      <Collapsible
                        key={category}
                        open={isExpanded}
                        onOpenChange={(open) => {
                          setExpandedCategories((prev) => {
                            const newSet = new Set(prev);
                            if (open) {
                              newSet.add(category);
                            } else {
                              newSet.delete(category);
                            }
                            return newSet;
                          });
                        }}
                        className="border rounded-lg"
                      >
                        <CollapsibleTrigger asChild>
                          <div className="flex items-center justify-between p-4 hover:bg-accent cursor-pointer">
                            <div className="flex items-center gap-3">
                              {isExpanded ? (
                                <ChevronDown className="h-4 w-4 text-muted-foreground" />
                              ) : (
                                <ChevronRight className="h-4 w-4 text-muted-foreground" />
                              )}
                              <h4 className="font-semibold capitalize">{category}</h4>
                              <Badge variant="secondary">
                                {selectedInCategory}/{perms.length}
                              </Badge>
                            </div>
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation();
                                const allSelected = categoryPermIds.every((id) =>
                                  formData.permission_ids.includes(id)
                                );
                                setFormData((prev) => ({
                                  ...prev,
                                  permission_ids: allSelected
                                    ? prev.permission_ids.filter((id) => !categoryPermIds.includes(id))
                                    : [...new Set([...prev.permission_ids, ...categoryPermIds])],
                                }));
                              }}
                            >
                              {selectedInCategory === perms.length ? 'Deselect All' : 'Select All'}
                            </Button>
                          </div>
                        </CollapsibleTrigger>
                        <CollapsibleContent>
                          <div className="px-4 pb-4 pt-2 grid grid-cols-1 md:grid-cols-2 gap-3">
                            {perms.map((perm) => (
                              <div
                                key={perm.id}
                                className="flex items-start space-x-3 p-3 rounded-md hover:bg-accent/50 transition-colors"
                              >
                                <Checkbox
                                  id={`perm-${perm.id}`}
                                  checked={formData.permission_ids.includes(perm.id)}
                                  onCheckedChange={(checked) =>
                                    handlePermissionChange(perm.id, checked as boolean)
                                  }
                                  className="mt-1"
                                />
                                <label
                                  htmlFor={`perm-${perm.id}`}
                                  className="flex-1 cursor-pointer"
                                >
                                  <div className="font-medium text-sm">{perm.display_name}</div>
                                  <p className="text-xs text-muted-foreground mt-1">
                                    {perm.description}
                                  </p>
                                </label>
                              </div>
                            ))}
                          </div>
                        </CollapsibleContent>
                      </Collapsible>
                    );
                  })}
              </div>
            </div>

            <DialogFooter className="flex-shrink-0">
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsFormOpen(false)}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={
                  createRoleMutation.isPending ||
                  updateRoleMutation.isPending ||
                  updateRolePermissionsMutation.isPending
                }
              >
                {createRoleMutation.isPending ||
                updateRoleMutation.isPending ||
                updateRolePermissionsMutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    {editingRole ? 'Saving...' : 'Creating...'}
                  </>
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

      <div className="space-y-4">
        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-card border rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Roles</p>
                <p className="text-2xl font-bold">{roles?.length || 0}</p>
              </div>
              <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
                <PlusCircle className="h-6 w-6 text-primary" />
              </div>
            </div>
          </div>
          <div className="bg-card border rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">System Roles</p>
                <p className="text-2xl font-bold">
                  {roles?.filter((r) => r.is_system_role).length || 0}
                </p>
              </div>
              <div className="h-12 w-12 rounded-full bg-blue-500/10 flex items-center justify-center">
                <Badge className="h-6 w-6 text-blue-500" />
              </div>
            </div>
          </div>
          <div className="bg-card border rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Custom Roles</p>
                <p className="text-2xl font-bold">
                  {roles?.filter((r) => !r.is_system_role).length || 0}
                </p>
              </div>
              <div className="h-12 w-12 rounded-full bg-green-500/10 flex items-center justify-center">
                <Edit className="h-6 w-6 text-green-500" />
              </div>
            </div>
          </div>
        </div>

        {/* Roles Cards Grid */}
        <div className="grid grid-cols-1 gap-4">
          {roles?.map((role) => (
            <div
              key={role.id}
              className="bg-card border rounded-lg p-6 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 space-y-3">
                  <div className="flex items-center gap-3">
                    <h3 className="text-lg font-semibold">{role.display_name}</h3>
                    <Badge variant={role.is_system_role ? 'secondary' : 'default'}>
                      {role.is_system_role ? 'System' : 'Custom'}
                    </Badge>
                    <Badge variant={role.is_active ? 'default' : 'destructive'}>
                      {role.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <code className="px-2 py-1 bg-muted rounded text-xs font-mono">
                      {role.name}
                    </code>
                    <span>•</span>
                    <span>{role.permissions?.length || 0} permissions</span>
                  </div>
                  <p className="text-sm text-muted-foreground">{role.description}</p>
                </div>
                <div className="flex gap-2 ml-4">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => openEditForm(role)}
                    disabled={role.is_system_role}
                    title={role.is_system_role ? 'System roles cannot be edited' : 'Edit role'}
                  >
                    <Edit className="h-4 w-4 mr-2" />
                    Edit
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => deleteRoleMutation.mutate(role.id)}
                    disabled={role.is_system_role || deleteRoleMutation.isPending}
                    title={role.is_system_role ? 'System roles cannot be deleted' : 'Delete role'}
                  >
                    <Trash2 className="h-4 w-4 mr-2" />
                    Delete
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
