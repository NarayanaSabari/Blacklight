/**
 * Credentials Page
 * Manage scraper credentials for LinkedIn, Glassdoor, and Techfetch platforms
 */

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
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
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
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
  scraperCredentialsApi,
  type CredentialPlatform,
  type ScraperCredential,
  type CredentialStats,
} from "@/lib/dashboard-api";
import { toast } from "sonner";
import { formatDistanceToNow } from "date-fns";
import {
  Plus,
  RefreshCw,
  MoreHorizontal,
  Trash2,
  Power,
  PowerOff,
  RotateCcw,
  CheckCircle2,
  XCircle,
  Clock,
  Loader2,
  AlertTriangle,
  Eye,
  EyeOff,
  Linkedin,
  Building2,
  Briefcase,
  Key,
} from "lucide-react";

// ============================================================================
// HELPER COMPONENTS
// ============================================================================

function StatusBadge({ status }: { status: string }) {
  const statusConfig: Record<string, { className: string; icon: React.ReactNode }> = {
    available: {
      className: "bg-green-100 text-green-800 border-green-300",
      icon: <CheckCircle2 className="h-3 w-3 mr-1" />,
    },
    in_use: {
      className: "bg-blue-100 text-blue-800 border-blue-300",
      icon: <Loader2 className="h-3 w-3 mr-1 animate-spin" />,
    },
    failed: {
      className: "bg-red-100 text-red-800 border-red-300",
      icon: <XCircle className="h-3 w-3 mr-1" />,
    },
    disabled: {
      className: "bg-gray-100 text-gray-800 border-gray-300",
      icon: <PowerOff className="h-3 w-3 mr-1" />,
    },
    cooldown: {
      className: "bg-yellow-100 text-yellow-800 border-yellow-300",
      icon: <Clock className="h-3 w-3 mr-1" />,
    },
  };

  const config = statusConfig[status] || statusConfig.available;

  return (
    <Badge variant="outline" className={`flex items-center w-fit ${config.className}`}>
      {config.icon}
      {status.replace('_', ' ')}
    </Badge>
  );
}

function StatsCard({ stats, platform }: { stats: CredentialStats; platform: string }) {
  const icons: Record<string, React.ReactNode> = {
    linkedin: <Linkedin className="h-5 w-5 text-blue-600" />,
    glassdoor: <Building2 className="h-5 w-5 text-green-600" />,
    techfetch: <Briefcase className="h-5 w-5 text-purple-600" />,
  };

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center gap-2">
          {icons[platform] || <Key className="h-5 w-5" />}
          <CardTitle className="text-lg capitalize">{platform}</CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-4 gap-4 text-sm">
          <div>
            <p className="text-muted-foreground">Total</p>
            <p className="text-2xl font-bold">{stats.total}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Available</p>
            <p className="text-2xl font-bold text-green-600">{stats.available}</p>
          </div>
          <div>
            <p className="text-muted-foreground">In Use</p>
            <p className="text-2xl font-bold text-blue-600">{stats.inUse}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Failed</p>
            <p className="text-2xl font-bold text-red-600">{stats.failed}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ============================================================================
// ADD CREDENTIAL DIALOG
// ============================================================================

interface AddCredentialDialogProps {
  platform: CredentialPlatform;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

function AddCredentialDialog({ platform, open, onOpenChange, onSuccess }: AddCredentialDialogProps) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [jsonData, setJsonData] = useState("");
  const [notes, setNotes] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const isJsonPlatform = platform === "glassdoor";

  const createMutation = useMutation({
    mutationFn: async () => {
      if (isJsonPlatform) {
        const parsed = JSON.parse(jsonData);
        return scraperCredentialsApi.createJsonCredential({
          platform: "glassdoor",
          name,
          json_credentials: parsed,
          notes: notes || undefined,
        });
      } else {
        return scraperCredentialsApi.createEmailCredential({
          platform: platform as "linkedin" | "techfetch",
          name,
          email,
          password,
          notes: notes || undefined,
        });
      }
    },
    onSuccess: () => {
      toast.success("Credential created successfully");
      onSuccess();
      onOpenChange(false);
      resetForm();
    },
    onError: (error: Error) => {
      toast.error(`Failed to create credential: ${error.message}`);
    },
  });

  const resetForm = () => {
    setName("");
    setEmail("");
    setPassword("");
    setJsonData("");
    setNotes("");
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isJsonPlatform) {
      try {
        JSON.parse(jsonData);
      } catch {
        toast.error("Invalid JSON format");
        return;
      }
    }
    createMutation.mutate();
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle className="capitalize">Add {platform} Credential</DialogTitle>
            <DialogDescription>
              {isJsonPlatform
                ? "Add JSON credentials (cookies, tokens, etc.)"
                : "Add email and password for scraper login"}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                placeholder={`${platform} Account 1`}
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>

            {isJsonPlatform ? (
              <div className="space-y-2">
                <Label htmlFor="json">JSON Credentials</Label>
                <Textarea
                  id="json"
                  placeholder='{"cookies": [...], "token": "..."}'
                  value={jsonData}
                  onChange={(e) => setJsonData(e.target.value)}
                  rows={6}
                  className="font-mono text-sm"
                  required
                />
              </div>
            ) : (
              <>
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="user@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="password">Password</Label>
                  <div className="relative">
                    <Input
                      id="password"
                      type={showPassword ? "text" : "password"}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="absolute right-0 top-0 h-full px-3"
                      onClick={() => setShowPassword(!showPassword)}
                    >
                      {showPassword ? (
                        <EyeOff className="h-4 w-4" />
                      ) : (
                        <Eye className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                </div>
              </>
            )}

            <div className="space-y-2">
              <Label htmlFor="notes">Notes (Optional)</Label>
              <Textarea
                id="notes"
                placeholder="Optional notes about this credential"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={2}
              />
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Creating...
                </>
              ) : (
                "Create Credential"
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ============================================================================
// CREDENTIAL TABLE
// ============================================================================

interface CredentialTableProps {
  platform: CredentialPlatform;
  credentials: ScraperCredential[];
  onRefresh: () => void;
}

function CredentialTable({ platform, credentials, onRefresh }: CredentialTableProps) {
  const [deleteId, setDeleteId] = useState<number | null>(null);

  const enableMutation = useMutation({
    mutationFn: scraperCredentialsApi.enable,
    onSuccess: () => {
      toast.success("Credential enabled");
      onRefresh();
    },
    onError: () => toast.error("Failed to enable credential"),
  });

  const disableMutation = useMutation({
    mutationFn: scraperCredentialsApi.disable,
    onSuccess: () => {
      toast.success("Credential disabled");
      onRefresh();
    },
    onError: () => toast.error("Failed to disable credential"),
  });

  const resetMutation = useMutation({
    mutationFn: scraperCredentialsApi.reset,
    onSuccess: () => {
      toast.success("Credential reset to available");
      onRefresh();
    },
    onError: () => toast.error("Failed to reset credential"),
  });

  const deleteMutation = useMutation({
    mutationFn: scraperCredentialsApi.delete,
    onSuccess: () => {
      toast.success("Credential deleted");
      setDeleteId(null);
      onRefresh();
    },
    onError: () => toast.error("Failed to delete credential"),
  });

  const isJsonPlatform = platform === "glassdoor";

  return (
    <>
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              {!isJsonPlatform && <TableHead>Email</TableHead>}
              <TableHead>Status</TableHead>
              <TableHead className="text-center">Success</TableHead>
              <TableHead className="text-center">Failures</TableHead>
              <TableHead>Last Used</TableHead>
              <TableHead>Last Error</TableHead>
              <TableHead className="w-[70px]">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {credentials.length === 0 ? (
              <TableRow>
                <TableCell colSpan={isJsonPlatform ? 7 : 8} className="text-center py-8 text-muted-foreground">
                  No credentials found. Add your first {platform} credential.
                </TableCell>
              </TableRow>
            ) : (
              credentials.map((cred) => (
                <TableRow key={cred.id}>
                  <TableCell className="font-medium">{cred.name}</TableCell>
                  {!isJsonPlatform && <TableCell>{cred.email || "-"}</TableCell>}
                  <TableCell>
                    <StatusBadge status={cred.status} />
                  </TableCell>
                  <TableCell className="text-center">
                    <span className="text-green-600 font-medium">{cred.successCount}</span>
                  </TableCell>
                  <TableCell className="text-center">
                    <span className="text-red-600 font-medium">{cred.failureCount}</span>
                  </TableCell>
                  <TableCell>
                    {cred.lastSuccessAt ? (
                      <span className="text-sm text-muted-foreground">
                        {formatDistanceToNow(new Date(cred.lastSuccessAt), { addSuffix: true })}
                      </span>
                    ) : (
                      <span className="text-sm text-muted-foreground">Never</span>
                    )}
                  </TableCell>
                  <TableCell>
                    {cred.lastFailureMessage ? (
                      <div className="flex items-center gap-1 max-w-[200px]">
                        <AlertTriangle className="h-4 w-4 text-red-500 flex-shrink-0" />
                        <span
                          className="text-sm text-red-600 truncate"
                          title={cred.lastFailureMessage}
                        >
                          {cred.lastFailureMessage}
                        </span>
                      </div>
                    ) : (
                      <span className="text-sm text-muted-foreground">-</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        {cred.status === "disabled" ? (
                          <DropdownMenuItem
                            onClick={() => enableMutation.mutate(cred.id)}
                            disabled={enableMutation.isPending}
                          >
                            <Power className="h-4 w-4 mr-2" />
                            Enable
                          </DropdownMenuItem>
                        ) : (
                          <DropdownMenuItem
                            onClick={() => disableMutation.mutate(cred.id)}
                            disabled={disableMutation.isPending}
                          >
                            <PowerOff className="h-4 w-4 mr-2" />
                            Disable
                          </DropdownMenuItem>
                        )}
                        {(cred.status === "failed" || cred.status === "cooldown" || cred.status === "in_use") && (
                          <DropdownMenuItem
                            onClick={() => resetMutation.mutate(cred.id)}
                            disabled={resetMutation.isPending}
                          >
                            <RotateCcw className="h-4 w-4 mr-2" />
                            {cred.status === "in_use" ? "Force Release" : "Reset to Available"}
                          </DropdownMenuItem>
                        )}
                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                          className="text-red-600"
                          onClick={() => setDeleteId(cred.id)}
                        >
                          <Trash2 className="h-4 w-4 mr-2" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteId !== null} onOpenChange={() => setDeleteId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Credential</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this credential? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-red-600 hover:bg-red-700"
              onClick={() => deleteId && deleteMutation.mutate(deleteId)}
            >
              {deleteMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                "Delete"
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}

// ============================================================================
// PLATFORM TAB CONTENT
// ============================================================================

interface PlatformTabProps {
  platform: CredentialPlatform;
}

function PlatformTab({ platform }: PlatformTabProps) {
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const queryClient = useQueryClient();

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["credentials", platform],
    queryFn: () => scraperCredentialsApi.getByPlatform(platform),
    staleTime: 30000,
  });

  const handleRefresh = () => {
    refetch();
    queryClient.invalidateQueries({ queryKey: ["credentials-stats"] });
  };

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="py-8 text-center">
          <p className="text-red-600">Failed to load credentials</p>
          <Button variant="ghost" onClick={() => refetch()} className="mt-2">
            <RefreshCw className="h-4 w-4 mr-2" />
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Stats Card */}
      {data && <StatsCard stats={data.stats} platform={platform} />}

      {/* Credentials Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="capitalize">{platform} Credentials</CardTitle>
              <CardDescription>
                {platform === "glassdoor"
                  ? "Manage JSON credentials (cookies, tokens)"
                  : "Manage email/password login credentials"}
              </CardDescription>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => refetch()}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh
              </Button>
              <Button size="sm" onClick={() => setAddDialogOpen(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Add Credential
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {data && (
            <CredentialTable
              platform={platform}
              credentials={data.credentials}
              onRefresh={handleRefresh}
            />
          )}
        </CardContent>
      </Card>

      {/* Add Dialog */}
      <AddCredentialDialog
        platform={platform}
        open={addDialogOpen}
        onOpenChange={setAddDialogOpen}
        onSuccess={handleRefresh}
      />
    </div>
  );
}

// ============================================================================
// MAIN PAGE COMPONENT
// ============================================================================

export function CredentialsPage() {
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ["credentials-stats"],
    queryFn: scraperCredentialsApi.getAllStats,
    staleTime: 30000,
  });

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="space-y-2">
        <h1 className="text-3xl font-bold tracking-tight">Scraper Credentials</h1>
        <p className="text-muted-foreground">
          Manage login credentials for LinkedIn, Glassdoor, and Techfetch scrapers
        </p>
      </div>

      {/* Stats Overview */}
      {statsLoading ? (
        <div className="grid gap-4 md:grid-cols-3">
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
        </div>
      ) : stats ? (
        <div className="grid gap-4 md:grid-cols-3">
          <StatsCard stats={stats.linkedin} platform="linkedin" />
          <StatsCard stats={stats.glassdoor} platform="glassdoor" />
          <StatsCard stats={stats.techfetch} platform="techfetch" />
        </div>
      ) : null}

      {/* Platform Tabs */}
      <Tabs defaultValue="linkedin" className="space-y-6">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="linkedin" className="flex items-center gap-2">
            <Linkedin className="h-4 w-4" />
            LinkedIn
          </TabsTrigger>
          <TabsTrigger value="glassdoor" className="flex items-center gap-2">
            <Building2 className="h-4 w-4" />
            Glassdoor
          </TabsTrigger>
          <TabsTrigger value="techfetch" className="flex items-center gap-2">
            <Briefcase className="h-4 w-4" />
            Techfetch
          </TabsTrigger>
        </TabsList>

        <TabsContent value="linkedin">
          <PlatformTab platform="linkedin" />
        </TabsContent>

        <TabsContent value="glassdoor">
          <PlatformTab platform="glassdoor" />
        </TabsContent>

        <TabsContent value="techfetch">
          <PlatformTab platform="techfetch" />
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default CredentialsPage;
