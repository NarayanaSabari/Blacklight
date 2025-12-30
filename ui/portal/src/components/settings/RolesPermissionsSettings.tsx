/**
 * Roles & Permissions Settings Component
 * Manage custom roles and assign permissions within settings
 */

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
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
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { toast } from 'sonner';
import {
  Loader2,
  PlusCircle,
  Edit,
  Trash2,
  ChevronDown,
  ChevronRight,
  CheckSquare,
  Square,
  Shield,
  AlertCircle,
} from 'lucide-react';
import { usePortalAuth } from '@/contexts/PortalAuthContext';
import { apiRequest } from '@/lib/api-client';

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
  user_count?: number;
}

interface RoleFormData {
  name: string;
  display_name: string;
  description: string;
  permission_ids: number[];
}

const fetchRoles = async (_tenantId: number): Promise<Role[]> => {
  const data = await apiRequest.get<{ roles: Role[] }>(
    `/api/portal/roles?include_permissions=true&include_user_counts=true`
  );
  return data.roles;
};

const fetchPermissions = async (): Promise<Permission[]> => {
  const data = await apiRequest.get<{ permissions: Permission[] }>('/api/portal/permissions');
  return data.permissions;
};

const createRole = async (tenantId: number, roleData: RoleFormData): Promise<Role> => {
  return await apiRequest.post(`/api/tenants/${tenantId}/roles`, roleData);
};

const updateRole = async (
  tenantId: number,
  roleId: number,
  roleData: Partial<RoleFormData>
): Promise<Role> => {
  return await apiRequest.put(`/api/tenants/${tenantId}/roles/${roleId}`, roleData);
};

const updateRolePermissions = async (
  tenantId: number,
  roleId: number,
  permissionIds: number[]
): Promise<Role> => {
  return await apiRequest.put(`/api/tenants/${tenantId}/roles/${roleId}/permissions`, {
    permission_ids: permissionIds,
  });
};

const deleteRole = async (tenantId: number, roleId: number): Promise<void> => {
  await apiRequest.delete(`/api/tenants/${tenantId}/roles/${roleId}`);
};

// Role hierarchy for sorting (System Roles)
const ROLE_ORDER: Record<string, number> = {
  TENANT_ADMIN: 1,
  MANAGER: 2,
  TEAM_LEAD: 3,
  RECRUITER: 4,
};

export function RolesPermissionsSettings() {
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

  const groupedPermissions = allPermissions?.reduce((acc, perm) => {
    const category = perm.category || 'Uncategorized';
    if (!acc[category]) {
      acc[category] = [];
    }
    acc[category].push(perm);
    return acc;
  }, {} as Record<string, Permission[]>);

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

  const updateRolePermissionsMutation = useMutation<
    Role,
    Error,
    { roleId: number; permissionIds: number[] }
  >({
    mutationFn: ({ roleId, permissionIds }) =>
      updateRolePermissions(tenantId!, roleId, permissionIds),
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
      updateRoleMutation.mutate({
        roleId: editingRole.id,
        data: {
          display_name: formData.display_name,
          description: formData.description,
        },
      });
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

  // Sort roles by hierarchy
  const sortedRoles = roles?.slice().sort((a, b) => {
    if (a.is_system_role && b.is_system_role) {
      const orderA = ROLE_ORDER[a.name] || 999;
      const orderB = ROLE_ORDER[b.name] || 999;
      return orderA - orderB;
    }
    if (a.is_system_role && !b.is_system_role) return -1;
    if (!a.is_system_role && b.is_system_role) return 1;
    return a.display_name.localeCompare(b.display_name);
  });

  // Loading state
  if (isAuthLoading || isLoadingRoles || isLoadingPermissions) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Roles & Permissions
          </CardTitle>
          <CardDescription>Manage custom roles and assign permissions</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[...Array(4)].map((_, i) => (
              <Skeleton key={i} className="h-16 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  // Auth check
  if (!isAuthenticated) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Authentication Required</AlertTitle>
        <AlertDescription>Please log in to view this page.</AlertDescription>
      </Alert>
    );
  }

  // Permission check
  if (!isTenantAdmin) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Roles & Permissions
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Access Denied</AlertTitle>
            <AlertDescription>
              Only Tenant Admins can manage roles and permissions.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  // Error states
  if (rolesError) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Error</AlertTitle>
        <AlertDescription>Error loading roles: {rolesError.message}</AlertDescription>
      </Alert>
    );
  }

  if (permissionsError) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Error</AlertTitle>
        <AlertDescription>Error loading permissions: {permissionsError.message}</AlertDescription>
      </Alert>
    );
  }

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5" />
                Roles & Permissions
              </CardTitle>
              <CardDescription>
                Create custom roles and manage permissions for your organization
              </CardDescription>
            </div>
            <Button onClick={openCreateForm}>
              <PlusCircle className="mr-2 h-4 w-4" /> Create New Role
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {/* Roles Table */}
          <div className="rounded-md border">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="px-6 py-3 text-left text-sm font-medium">Role Name</th>
                  <th className="px-6 py-3 text-left text-sm font-medium">Type</th>
                  <th className="px-6 py-3 text-left text-sm font-medium">Users</th>
                  <th className="px-6 py-3 text-left text-sm font-medium">Permissions</th>
                  <th className="px-6 py-3 text-left text-sm font-medium">Status</th>
                  <th className="px-6 py-3 text-right text-sm font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {sortedRoles && sortedRoles.length > 0 ? (
                  sortedRoles.map((role) => (
                    <tr key={role.id} className="border-b last:border-0 hover:bg-muted/30">
                      <td className="px-6 py-4">
                        <div>
                          <div className="font-medium">{role.display_name}</div>
                          <div className="text-sm text-muted-foreground">
                            <code className="text-xs">{role.name}</code>
                          </div>
                          {role.description && (
                            <div className="text-sm text-muted-foreground mt-1">
                              {role.description}
                            </div>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <Badge variant={role.is_system_role ? 'secondary' : 'default'}>
                          {role.is_system_role ? 'System' : 'Custom'}
                        </Badge>
                      </td>
                      <td className="px-6 py-4">
                        <Badge variant="outline">
                          {role.user_count ?? 0} {role.user_count === 1 ? 'user' : 'users'}
                        </Badge>
                      </td>
                      <td className="px-6 py-4">
                        <span className="text-sm text-muted-foreground">
                          {role.permissions?.length || 0} permissions
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <Badge variant={role.is_active ? 'default' : 'destructive'}>
                          {role.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <div className="flex justify-end gap-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => openEditForm(role)}
                            disabled={role.is_system_role}
                            title={role.is_system_role ? 'System roles cannot be edited' : 'Edit role'}
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => deleteRoleMutation.mutate(role.id)}
                            disabled={role.is_system_role || deleteRoleMutation.isPending}
                            title={
                              role.is_system_role ? 'System roles cannot be deleted' : 'Delete role'
                            }
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6} className="px-6 py-8 text-center text-muted-foreground">
                      No roles found
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Create/Edit Role Dialog */}
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
                                <label htmlFor={`perm-${perm.id}`} className="flex-1 cursor-pointer">
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
              <Button type="button" variant="outline" onClick={() => setIsFormOpen(false)}>
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
    </>
  );
}
