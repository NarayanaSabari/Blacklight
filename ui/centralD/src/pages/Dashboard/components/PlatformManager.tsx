/**
 * Platform Manager Component
 * CRUD interface for managing scraper platforms (LinkedIn, Monster, Indeed, etc.)
 * Allows PM_ADMIN to add new platforms, toggle active status, set priorities
 */

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  scraperPlatformApi,
} from "@/lib/dashboard-api";
import type {
  ScraperPlatform,
  CreatePlatformRequest,
} from "@/lib/dashboard-api";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Textarea } from "@/components/ui/textarea";
import {
  Plus,
  Pencil,
  Trash2,
  Globe,
  Loader2,
  AlertCircle,
  RefreshCw,
  ArrowUp,
  ArrowDown,
} from "lucide-react";
import { toast } from "sonner";

export function PlatformManager() {
  const queryClient = useQueryClient();
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [editingPlatform, setEditingPlatform] = useState<ScraperPlatform | null>(null);

  // Fetch platforms
  const {
    data: platforms = [],
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ["scraper-platforms"],
    queryFn: scraperPlatformApi.getPlatforms,
    staleTime: 0,
  });

  // Create platform mutation
  const createMutation = useMutation({
    mutationFn: scraperPlatformApi.createPlatform,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["scraper-platforms"] });
      setIsCreateDialogOpen(false);
      toast.success("Platform created successfully");
    },
    onError: (error: Error) => {
      toast.error(`Failed to create platform: ${error.message}`);
    },
  });

  // Update platform mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<CreatePlatformRequest> }) =>
      scraperPlatformApi.updatePlatform(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["scraper-platforms"] });
      setEditingPlatform(null);
      toast.success("Platform updated successfully");
    },
    onError: (error: Error) => {
      toast.error(`Failed to update platform: ${error.message}`);
    },
  });

  // Delete platform mutation
  const deleteMutation = useMutation({
    mutationFn: scraperPlatformApi.deletePlatform,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["scraper-platforms"] });
      toast.success("Platform deleted successfully");
    },
    onError: (error: Error) => {
      toast.error(`Failed to delete platform: ${error.message}`);
    },
  });

  // Toggle active status mutation
  const toggleMutation = useMutation({
    mutationFn: ({ id, isActive }: { id: number; isActive: boolean }) =>
      scraperPlatformApi.togglePlatform(id, isActive),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["scraper-platforms"] });
    },
    onError: (error: Error) => {
      toast.error(`Failed to toggle platform: ${error.message}`);
    },
  });

  // Handle form submission for create
  const handleCreate = (formData: FormData) => {
    const data: CreatePlatformRequest = {
      name: formData.get("name") as string,
      display_name: formData.get("display_name") as string,
      base_url: (formData.get("base_url") as string) || undefined,
      priority: parseInt(formData.get("priority") as string) || 10,
      description: (formData.get("description") as string) || undefined,
      is_active: formData.get("is_active") === "on",
    };
    createMutation.mutate(data);
  };

  // Handle form submission for update
  const handleUpdate = (formData: FormData) => {
    if (!editingPlatform) return;

    const data: Partial<CreatePlatformRequest> = {
      display_name: formData.get("display_name") as string,
      base_url: (formData.get("base_url") as string) || undefined,
      priority: parseInt(formData.get("priority") as string) || 10,
      description: (formData.get("description") as string) || undefined,
    };
    updateMutation.mutate({ id: editingPlatform.id, data });
  };

  // Sort platforms by priority
  const sortedPlatforms = [...platforms].sort((a, b) => a.priority - b.priority);
  const activePlatforms = sortedPlatforms.filter((p) => p.isActive);
  const inactivePlatforms = sortedPlatforms.filter((p) => !p.isActive);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Globe className="h-5 w-5" />
            Platform Manager
          </CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Globe className="h-5 w-5" />
            Platform Manager
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <AlertCircle className="h-12 w-12 text-destructive mb-4" />
            <p className="text-muted-foreground mb-4">Failed to load platforms</p>
            <Button onClick={() => refetch()} variant="outline">
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Globe className="h-5 w-5" />
              Platform Manager
            </CardTitle>
            <CardDescription>
              Manage job scraping platforms. Active platforms will be included in scrape sessions.
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Button onClick={() => refetch()} variant="outline" size="sm">
              <RefreshCw className="h-4 w-4" />
            </Button>
            <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
              <DialogTrigger asChild>
                <Button size="sm">
                  <Plus className="h-4 w-4 mr-2" />
                  Add Platform
                </Button>
              </DialogTrigger>
              <DialogContent>
                <form onSubmit={(e) => { e.preventDefault(); handleCreate(new FormData(e.currentTarget)); }}>
                  <DialogHeader>
                    <DialogTitle>Add New Platform</DialogTitle>
                    <DialogDescription>
                      Add a new job platform for the scraper to collect jobs from.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="grid gap-4 py-4">
                    <div className="grid gap-2">
                      <Label htmlFor="name">Platform ID *</Label>
                      <Input
                        id="name"
                        name="name"
                        placeholder="e.g., linkedin, ziprecruiter"
                        pattern="[a-z0-9_-]+"
                        title="Lowercase letters, numbers, hyphens, and underscores only"
                        required
                      />
                      <p className="text-xs text-muted-foreground">
                        Unique identifier (lowercase, no spaces)
                      </p>
                    </div>
                    <div className="grid gap-2">
                      <Label htmlFor="display_name">Display Name *</Label>
                      <Input
                        id="display_name"
                        name="display_name"
                        placeholder="e.g., LinkedIn Jobs"
                        required
                      />
                    </div>
                    <div className="grid gap-2">
                      <Label htmlFor="base_url">Base URL</Label>
                      <Input
                        id="base_url"
                        name="base_url"
                        type="url"
                        placeholder="https://www.linkedin.com/jobs"
                      />
                    </div>
                    <div className="grid gap-2">
                      <Label htmlFor="priority">Priority</Label>
                      <Input
                        id="priority"
                        name="priority"
                        type="number"
                        min="1"
                        max="100"
                        defaultValue="10"
                      />
                      <p className="text-xs text-muted-foreground">
                        Lower number = higher priority (1-100)
                      </p>
                    </div>
                    <div className="grid gap-2">
                      <Label htmlFor="description">Description</Label>
                      <Textarea
                        id="description"
                        name="description"
                        placeholder="Brief description of this platform"
                        rows={2}
                      />
                    </div>
                    <div className="flex items-center gap-2">
                      <Switch id="is_active" name="is_active" defaultChecked />
                      <Label htmlFor="is_active">Active</Label>
                    </div>
                  </div>
                  <DialogFooter>
                    <Button type="button" variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
                      Cancel
                    </Button>
                    <Button type="submit" disabled={createMutation.isPending}>
                      {createMutation.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                      Create Platform
                    </Button>
                  </DialogFooter>
                </form>
              </DialogContent>
            </Dialog>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {/* Stats Summary */}
        <div className="flex gap-4 mb-6">
          <div className="flex items-center gap-2">
            <Badge variant="default" className="bg-green-500">
              {activePlatforms.length} Active
            </Badge>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="secondary">
              {inactivePlatforms.length} Inactive
            </Badge>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="outline">
              {platforms.length} Total
            </Badge>
          </div>
        </div>

        {/* Platforms Table */}
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[50px]">Priority</TableHead>
                <TableHead>Platform</TableHead>
                <TableHead>URL</TableHead>
                <TableHead className="w-[100px] text-center">Status</TableHead>
                <TableHead className="w-[120px] text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sortedPlatforms.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center py-12 text-muted-foreground">
                    No platforms configured. Add a platform to get started.
                  </TableCell>
                </TableRow>
              ) : (
                sortedPlatforms.map((platform) => (
                  <TableRow key={platform.id} className={!platform.isActive ? "opacity-60" : ""}>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <span className="font-mono text-sm">{platform.priority}</span>
                        <div className="flex flex-col">
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-4 w-4"
                            onClick={() =>
                              updateMutation.mutate({
                                id: platform.id,
                                data: { priority: Math.max(1, platform.priority - 1) },
                              })
                            }
                            disabled={platform.priority <= 1}
                          >
                            <ArrowUp className="h-3 w-3" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-4 w-4"
                            onClick={() =>
                              updateMutation.mutate({
                                id: platform.id,
                                data: { priority: platform.priority + 1 },
                              })
                            }
                          >
                            <ArrowDown className="h-3 w-3" />
                          </Button>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-col">
                        <span className="font-medium">{platform.displayName}</span>
                        <span className="text-xs text-muted-foreground font-mono">
                          {platform.name}
                        </span>
                        {platform.description && (
                          <span className="text-xs text-muted-foreground mt-1">
                            {platform.description}
                          </span>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      {platform.baseUrl ? (
                        <a
                          href={platform.baseUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm text-blue-600 hover:underline truncate max-w-[200px] block"
                        >
                          {platform.baseUrl}
                        </a>
                      ) : (
                        <span className="text-muted-foreground text-sm">—</span>
                      )}
                    </TableCell>
                    <TableCell className="text-center">
                      <Switch
                        checked={platform.isActive}
                        onCheckedChange={(checked) =>
                          toggleMutation.mutate({ id: platform.id, isActive: checked })
                        }
                        disabled={toggleMutation.isPending}
                      />
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1">
                        {/* Edit Button */}
                        <Dialog
                          open={editingPlatform?.id === platform.id}
                          onOpenChange={(open) => setEditingPlatform(open ? platform : null)}
                        >
                          <DialogTrigger asChild>
                            <Button variant="ghost" size="icon" className="h-8 w-8">
                              <Pencil className="h-4 w-4" />
                            </Button>
                          </DialogTrigger>
                          <DialogContent>
                            <form onSubmit={(e) => { e.preventDefault(); handleUpdate(new FormData(e.currentTarget)); }}>
                              <DialogHeader>
                                <DialogTitle>Edit Platform</DialogTitle>
                                <DialogDescription>
                                  Update platform settings. Platform ID cannot be changed.
                                </DialogDescription>
                              </DialogHeader>
                              <div className="grid gap-4 py-4">
                                <div className="grid gap-2">
                                  <Label>Platform ID</Label>
                                  <Input value={platform.name} disabled />
                                </div>
                                <div className="grid gap-2">
                                  <Label htmlFor="edit_display_name">Display Name *</Label>
                                  <Input
                                    id="edit_display_name"
                                    name="display_name"
                                    defaultValue={platform.displayName}
                                    required
                                  />
                                </div>
                                <div className="grid gap-2">
                                  <Label htmlFor="edit_base_url">Base URL</Label>
                                  <Input
                                    id="edit_base_url"
                                    name="base_url"
                                    type="url"
                                    defaultValue={platform.baseUrl}
                                  />
                                </div>
                                <div className="grid gap-2">
                                  <Label htmlFor="edit_priority">Priority</Label>
                                  <Input
                                    id="edit_priority"
                                    name="priority"
                                    type="number"
                                    min="1"
                                    max="100"
                                    defaultValue={platform.priority}
                                  />
                                </div>
                                <div className="grid gap-2">
                                  <Label htmlFor="edit_description">Description</Label>
                                  <Textarea
                                    id="edit_description"
                                    name="description"
                                    defaultValue={platform.description || ""}
                                    rows={2}
                                  />
                                </div>
                              </div>
                              <DialogFooter>
                                <Button
                                  type="button"
                                  variant="outline"
                                  onClick={() => setEditingPlatform(null)}
                                >
                                  Cancel
                                </Button>
                                <Button type="submit" disabled={updateMutation.isPending}>
                                  {updateMutation.isPending && (
                                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                  )}
                                  Save Changes
                                </Button>
                              </DialogFooter>
                            </form>
                          </DialogContent>
                        </Dialog>

                        {/* Delete Button */}
                        <AlertDialog>
                          <AlertDialogTrigger asChild>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 text-destructive hover:text-destructive"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogHeader>
                              <AlertDialogTitle>Delete Platform</AlertDialogTitle>
                              <AlertDialogDescription>
                                Are you sure you want to delete "{platform.displayName}"? This action
                                cannot be undone.
                              </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                              <AlertDialogCancel>Cancel</AlertDialogCancel>
                              <AlertDialogAction
                                onClick={() => deleteMutation.mutate(platform.id)}
                                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                              >
                                Delete
                              </AlertDialogAction>
                            </AlertDialogFooter>
                          </AlertDialogContent>
                        </AlertDialog>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>

        {/* Help Text */}
        <div className="mt-4 text-sm text-muted-foreground">
          <p>
            <strong>Note:</strong> Only <span className="text-green-600">active</span> platforms
            will be included when the scraper requests jobs. Toggle a platform off to temporarily
            exclude it from scraping without deleting it.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
