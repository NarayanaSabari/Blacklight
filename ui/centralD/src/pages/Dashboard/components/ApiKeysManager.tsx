/**
 * API Keys Manager Component
 * Manage scraper API keys
 */

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { apiKeysApi, type ScraperApiKey } from "@/lib/dashboard-api";
import { 
  Key, 
  Plus, 
  MoreHorizontal,
  Pause,
  Play,
  Trash2,
  Copy,
  RefreshCw,
  AlertTriangle
} from "lucide-react";
import { toast } from "sonner";
import { formatDistanceToNow } from "date-fns";

function KeyStatusBadge({ status }: { status: ScraperApiKey['status'] }) {
  const variants: Record<ScraperApiKey['status'], { variant: "default" | "secondary" | "destructive" | "outline"; label: string }> = {
    active: { variant: "default", label: "Active" },
    paused: { variant: "secondary", label: "Paused" },
    revoked: { variant: "destructive", label: "Revoked" },
  };

  const { variant, label } = variants[status];
  return <Badge variant={variant}>{label}</Badge>;
}

interface CreateKeyDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreate: (name: string) => void;
  isLoading: boolean;
}

function CreateKeyDialog({ open, onOpenChange, onCreate, isLoading }: CreateKeyDialogProps) {
  const [name, setName] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (name.trim()) {
      onCreate(name.trim());
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Create API Key</DialogTitle>
            <DialogDescription>
              Create a new API key for external scrapers. 
              The key will only be shown once after creation.
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">Key Name</Label>
              <Input
                id="name"
                placeholder="e.g., Production Scraper 1"
                value={name}
                onChange={(e) => setName(e.target.value)}
                autoFocus
              />
              <p className="text-xs text-muted-foreground">
                A descriptive name to identify this API key
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={!name.trim() || isLoading}>
              {isLoading ? (
                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Plus className="h-4 w-4 mr-2" />
              )}
              Create Key
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

interface ShowKeyDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  keyName: string;
  rawKey: string;
}

function ShowKeyDialog({ open, onOpenChange, keyName, rawKey }: ShowKeyDialogProps) {
  const copyToClipboard = () => {
    navigator.clipboard.writeText(rawKey);
    toast.success("API key copied to clipboard");
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>API Key Created</DialogTitle>
          <DialogDescription>
            <span className="flex items-center gap-2 text-amber-600">
              <AlertTriangle className="h-4 w-4" />
              Copy this key now. It won't be shown again!
            </span>
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label>Key Name</Label>
            <p className="text-sm font-medium">{keyName}</p>
          </div>
          
          <div className="space-y-2">
            <Label>API Key</Label>
            <div className="flex gap-2">
              <code className="flex-1 p-3 bg-muted rounded-md text-sm font-mono break-all">
                {rawKey}
              </code>
              <Button variant="outline" size="icon" onClick={copyToClipboard}>
                <Copy className="h-4 w-4" />
              </Button>
            </div>
          </div>

          <div className="rounded-md bg-amber-50 border border-amber-200 p-3">
            <p className="text-sm text-amber-800">
              <strong>Usage:</strong> Include this key in the <code className="bg-amber-100 px-1 rounded">X-Scraper-API-Key</code> header when making requests to the scraper API.
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button onClick={() => onOpenChange(false)}>
            I've Copied the Key
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function ApiKeysManager() {
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [showKeyDialog, setShowKeyDialog] = useState(false);
  const [newKey, setNewKey] = useState<{ name: string; rawKey: string } | null>(null);
  const [revokeKeyId, setRevokeKeyId] = useState<number | null>(null);
  const queryClient = useQueryClient();

  const { data: keys, isLoading, error, refetch } = useQuery({
    queryKey: ['api-keys'],
    queryFn: apiKeysApi.getKeys,
  });

  const createMutation = useMutation({
    mutationFn: (name: string) => apiKeysApi.createKey({ name }),
    onSuccess: (result) => {
      setCreateDialogOpen(false);
      setNewKey({ name: result.key.name, rawKey: result.rawKey });
      setShowKeyDialog(true);
      queryClient.refetchQueries({ queryKey: ['api-keys'] });
      queryClient.refetchQueries({ queryKey: ['dashboard-stats'] });
      toast.success("API key created successfully");
    },
    onError: () => {
      toast.error("Failed to create API key");
    },
  });

  const updateStatusMutation = useMutation({
    mutationFn: ({ keyId, status }: { keyId: number; status: 'active' | 'paused' }) => 
      apiKeysApi.updateKeyStatus(keyId, status),
    onSuccess: () => {
      queryClient.refetchQueries({ queryKey: ['api-keys'] });
      toast.success("API key status updated");
    },
    onError: () => {
      toast.error("Failed to update API key status");
    },
  });

  const revokeMutation = useMutation({
    mutationFn: (keyId: number) => apiKeysApi.revokeKey(keyId),
    onSuccess: () => {
      setRevokeKeyId(null);
      queryClient.refetchQueries({ queryKey: ['api-keys'] });
      queryClient.refetchQueries({ queryKey: ['dashboard-stats'] });
      toast.success("API key revoked");
    },
    onError: () => {
      toast.error("Failed to revoke API key");
    },
  });

  const activeKeys = keys?.filter(k => k.status !== 'revoked') || [];

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-64" />
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[...Array(3)].map((_, i) => (
              <Skeleton key={i} className="h-16 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="py-8">
          <div className="text-center">
            <p className="text-sm text-destructive">Failed to load API keys</p>
            <Button variant="ghost" size="sm" onClick={() => refetch()} className="mt-2">
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Key className="h-5 w-5" />
                API Keys
              </CardTitle>
              <CardDescription>
                {activeKeys.length} active key{activeKeys.length !== 1 ? 's' : ''}
              </CardDescription>
            </div>
            <Button size="sm" onClick={() => setCreateDialogOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Create Key
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {keys?.length === 0 ? (
            <div className="text-center py-8">
              <Key className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
              <p className="text-sm text-muted-foreground">No API keys created</p>
              <Button 
                variant="outline" 
                size="sm" 
                className="mt-4"
                onClick={() => setCreateDialogOpen(true)}
              >
                <Plus className="h-4 w-4 mr-2" />
                Create First Key
              </Button>
            </div>
          ) : (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Jobs Scraped</TableHead>
                    <TableHead>Last Used</TableHead>
                    <TableHead className="text-right w-[80px]">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {keys?.map((key) => (
                    <TableRow key={key.id} className={key.status === 'revoked' ? 'opacity-50' : ''}>
                      <TableCell>
                        <div>
                          <p className="font-medium">{key.name}</p>
                          <p className="text-xs text-muted-foreground font-mono">
                            {key.keyPrefix}...
                          </p>
                        </div>
                      </TableCell>
                      <TableCell>
                        <KeyStatusBadge status={key.status} />
                      </TableCell>
                      <TableCell className="text-right">
                        {key.totalJobsScraped.toLocaleString()}
                      </TableCell>
                      <TableCell>
                        {key.lastUsedAt ? (
                          <span className="text-sm">
                            {formatDistanceToNow(new Date(key.lastUsedAt), { addSuffix: true })}
                          </span>
                        ) : (
                          <span className="text-sm text-muted-foreground">Never</span>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        {key.status !== 'revoked' && (
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="icon">
                                <MoreHorizontal className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              {key.status === 'active' ? (
                                <DropdownMenuItem 
                                  onClick={() => updateStatusMutation.mutate({ 
                                    keyId: key.id, 
                                    status: 'paused' 
                                  })}
                                >
                                  <Pause className="h-4 w-4 mr-2" />
                                  Pause
                                </DropdownMenuItem>
                              ) : (
                                <DropdownMenuItem 
                                  onClick={() => updateStatusMutation.mutate({ 
                                    keyId: key.id, 
                                    status: 'active' 
                                  })}
                                >
                                  <Play className="h-4 w-4 mr-2" />
                                  Activate
                                </DropdownMenuItem>
                              )}
                              <DropdownMenuItem 
                                className="text-destructive"
                                onClick={() => setRevokeKeyId(key.id)}
                              >
                                <Trash2 className="h-4 w-4 mr-2" />
                                Revoke
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      <CreateKeyDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        onCreate={(name) => createMutation.mutate(name)}
        isLoading={createMutation.isPending}
      />

      {newKey && (
        <ShowKeyDialog
          open={showKeyDialog}
          onOpenChange={setShowKeyDialog}
          keyName={newKey.name}
          rawKey={newKey.rawKey}
        />
      )}

      <AlertDialog open={!!revokeKeyId} onOpenChange={() => setRevokeKeyId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Revoke API Key?</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. The API key will be permanently revoked 
              and any scrapers using it will stop working.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => revokeKeyId && revokeMutation.mutate(revokeKeyId)}
            >
              Revoke Key
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
