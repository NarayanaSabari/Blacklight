# CentralD Dashboard - Queue Monitoring

The CentralD Dashboard provides PM_ADMIN users with comprehensive queue monitoring, role normalization management, and system oversight capabilities.

## Dashboard Overview

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        CENTRALD DASHBOARD                                    │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        STATS CARDS                                   │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │    │
│  │  │ Pending  │ │ Active   │ │ New Roles│ │ Jobs     │ │ API Keys │  │    │
│  │  │ Queue    │ │ Scrapers │ │ to Review│ │ Imported │ │ Active   │  │    │
│  │  │   247    │ │    3     │ │   89     │ │  1,543   │ │    5     │  │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                   SCRAPER MONITORING (Observability)                 │    │
│  │  ┌────────────────────┐ ┌──────────────────────────────────────┐   │    │
│  │  │ ACTIVE SESSIONS    │ │ ACTIVITY LOG                         │   │    │
│  │  │ ┌────────────────┐ │ │ Status | Scraper  | Role    | Time   │   │    │
│  │  │ │ Scraper1       │ │ │ ✓ Done | Scraper1 | React.. | 5m     │   │    │
│  │  │ │ Role: React..  │ │ │ ● Run  | Scraper2 | Python. | 2m     │   │    │
│  │  │ │ Jobs: 45       │ │ │ ✗ Fail | Scraper3 | DevOps. | Error  │   │    │
│  │  │ └────────────────┘ │ └──────────────────────────────────────┘   │    │
│  │  └────────────────────┘                                            │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌───────────────────────────────┐  ┌────────────────────────────────────┐  │
│  │     ROLE QUEUE TABLE          │  │         API KEYS MANAGER           │  │
│  │  ┌─────────────────────────┐  │  │  ┌──────────────────────────────┐  │  │
│  │  │ Role Name    | Similar  │  │  │  │ Name      | Status | Usage  │  │  │
│  │  │─────────────────────────│  │  │  │──────────────────────────────│  │  │
│  │  │ Sr. React... | 92%      │  │  │  │ Scraper1  | Active | 5,230  │  │  │
│  │  │ Full Stack...| 88%      │  │  │  │ Scraper2  | Active | 3,102  │  │  │
│  │  │ DevOps Eng...| 86%      │  │  │  │ Test Key  | Paused | 45     │  │  │
│  │  └─────────────────────────┘  │  │  └──────────────────────────────┘  │  │
│  │  [Approve] [Merge] [Reject]   │  │  [Create New Key] [Revoke]         │  │
│  └───────────────────────────────┘  └────────────────────────────────────┘  │
│                                                                              │
│  ┌───────────────────────────────┐  ┌────────────────────────────────────┐  │
│  │     JOBS PREVIEW              │  │         ACTIVITY FEED              │  │
│  │  ┌─────────────────────────┐  │  │  ┌──────────────────────────────┐  │  │
│  │  │ Recent imports from:    │  │  │  │ 10:45 - 150 jobs imported    │  │  │
│  │  │ • Monster: 89 jobs      │  │  │  │ 10:32 - Role merged: React.. │  │  │
│  │  │ • Indeed: 124 jobs      │  │  │  │ 10:15 - API key created      │  │  │
│  │  │ • Dice: 67 jobs         │  │  │  │ 09:58 - Scraper connected    │  │  │
│  │  └─────────────────────────┘  │  │  └──────────────────────────────┘  │  │
│  └───────────────────────────────┘  └────────────────────────────────────┘  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Component Structure

### Dashboard Layout

```
ui/centralD/src/pages/
├── Dashboard/
│   ├── index.tsx                  # Main dashboard page
│   └── components/
│       ├── StatsCards.tsx         # Overview statistics
│       ├── ScraperMonitoring.tsx  # Scraper observability (NEW)
│       ├── RoleQueueTable.tsx     # Pending roles management
│       ├── MergeDialog.tsx        # Role merge modal
│       ├── ApiKeysManager.tsx     # API key management
│       ├── JobsPreview.tsx        # Recent job imports
│       └── ActivityFeed.tsx       # Real-time activity log
```

## Component Implementations

### 1. StatsCards Component

```tsx
// ui/centralD/src/pages/Dashboard/components/StatsCards.tsx

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useQuery } from "@tanstack/react-query"
import { dashboardApi } from "@/services/dashboard-api"
import { 
  ListTodo, 
  Wifi, 
  Tags, 
  Briefcase, 
  Key 
} from "lucide-react"

interface Stats {
  pendingQueue: number
  activeScrapers: number
  newRoles: number
  jobsImported: number
  activeApiKeys: number
}

export function StatsCards() {
  const { data: stats, isLoading } = useQuery<Stats>({
    queryKey: ['dashboard-stats'],
    queryFn: dashboardApi.getStats,
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  const cards = [
    {
      title: "Pending Queue",
      value: stats?.pendingQueue ?? 0,
      icon: ListTodo,
      description: "Candidates awaiting scrape",
      trend: "+12 from last hour"
    },
    {
      title: "Active Scrapers",
      value: stats?.activeScrapers ?? 0,
      icon: Wifi,
      description: "Currently connected",
      trend: "All healthy"
    },
    {
      title: "Roles to Review",
      value: stats?.newRoles ?? 0,
      icon: Tags,
      description: "Pending normalization",
      trend: "89 need attention"
    },
    {
      title: "Jobs Today",
      value: stats?.jobsImported ?? 0,
      icon: Briefcase,
      description: "Imported jobs",
      trend: "+543 from yesterday"
    },
    {
      title: "Active API Keys",
      value: stats?.activeApiKeys ?? 0,
      icon: Key,
      description: "Valid scraper keys",
      trend: "2 expiring soon"
    }
  ]

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        {[...Array(5)].map((_, i) => (
          <Card key={i} className="animate-pulse">
            <CardHeader className="h-20 bg-muted" />
          </Card>
        ))}
      </div>
    )
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
      {cards.map((card) => (
        <Card key={card.title}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              {card.title}
            </CardTitle>
            <card.icon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{card.value.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">
              {card.description}
            </p>
            <p className="text-xs text-green-600 mt-1">
              {card.trend}
            </p>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
```

### 2. RoleQueueTable Component

```tsx
// ui/centralD/src/pages/Dashboard/components/RoleQueueTable.tsx

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { 
  Check, 
  GitMerge, 
  X, 
  ChevronRight 
} from "lucide-react"
import { roleApi } from "@/services/role-api"
import { MergeDialog } from "./MergeDialog"
import { toast } from "sonner"

interface PendingRole {
  id: number
  name: string
  normalizedName: string
  category: string | null
  seniorityLevel: string | null
  jobCount: number
  similarRoles: {
    id: number
    name: string
    similarity: number
  }[]
  createdAt: string
}

export function RoleQueueTable() {
  const [selectedRole, setSelectedRole] = useState<PendingRole | null>(null)
  const [mergeDialogOpen, setMergeDialogOpen] = useState(false)
  const queryClient = useQueryClient()

  const { data: roles, isLoading } = useQuery<PendingRole[]>({
    queryKey: ['pending-roles'],
    queryFn: roleApi.getPendingRoles,
    staleTime: 0,
  })

  const approveMutation = useMutation({
    mutationFn: (roleId: number) => roleApi.approveRole(roleId),
    onSuccess: () => {
      queryClient.refetchQueries({ queryKey: ['pending-roles'] })
      queryClient.refetchQueries({ queryKey: ['dashboard-stats'] })
      toast.success("Role approved successfully")
    },
    onError: () => {
      toast.error("Failed to approve role")
    }
  })

  const rejectMutation = useMutation({
    mutationFn: (roleId: number) => roleApi.rejectRole(roleId),
    onSuccess: () => {
      queryClient.refetchQueries({ queryKey: ['pending-roles'] })
      queryClient.refetchQueries({ queryKey: ['dashboard-stats'] })
      toast.success("Role rejected")
    },
    onError: () => {
      toast.error("Failed to reject role")
    }
  })

  const handleMerge = (role: PendingRole) => {
    setSelectedRole(role)
    setMergeDialogOpen(true)
  }

  if (isLoading) {
    return (
      <div className="rounded-md border">
        <div className="h-64 flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
        </div>
      </div>
    )
  }

  return (
    <>
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[300px]">Role Name</TableHead>
              <TableHead>Category</TableHead>
              <TableHead>Seniority</TableHead>
              <TableHead className="text-right">Jobs</TableHead>
              <TableHead>Similar Roles</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {roles?.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                  No roles pending review
                </TableCell>
              </TableRow>
            ) : (
              roles?.map((role) => (
                <TableRow key={role.id}>
                  <TableCell className="font-medium">
                    <div>
                      <div>{role.name}</div>
                      <div className="text-xs text-muted-foreground">
                        {role.normalizedName}
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    {role.category ? (
                      <Badge variant="outline">{role.category}</Badge>
                    ) : (
                      <span className="text-muted-foreground">-</span>
                    )}
                  </TableCell>
                  <TableCell>
                    {role.seniorityLevel ? (
                      <Badge variant="secondary">{role.seniorityLevel}</Badge>
                    ) : (
                      <span className="text-muted-foreground">-</span>
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    {role.jobCount.toLocaleString()}
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-col gap-1">
                      {role.similarRoles.slice(0, 2).map((similar) => (
                        <div key={similar.id} className="flex items-center gap-2 text-sm">
                          <ChevronRight className="h-3 w-3 text-muted-foreground" />
                          <span className="truncate max-w-[150px]">{similar.name}</span>
                          <Badge 
                            variant={similar.similarity >= 90 ? "default" : "secondary"}
                            className="text-xs"
                          >
                            {similar.similarity}%
                          </Badge>
                        </div>
                      ))}
                      {role.similarRoles.length === 0 && (
                        <span className="text-muted-foreground text-sm">No matches</span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => approveMutation.mutate(role.id)}
                        disabled={approveMutation.isPending}
                      >
                        <Check className="h-4 w-4" />
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleMerge(role)}
                        disabled={role.similarRoles.length === 0}
                      >
                        <GitMerge className="h-4 w-4" />
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        className="text-destructive"
                        onClick={() => rejectMutation.mutate(role.id)}
                        disabled={rejectMutation.isPending}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <MergeDialog
        open={mergeDialogOpen}
        onOpenChange={setMergeDialogOpen}
        sourceRole={selectedRole}
        onMergeComplete={() => {
          setMergeDialogOpen(false)
          setSelectedRole(null)
          queryClient.refetchQueries({ queryKey: ['pending-roles'] })
          queryClient.refetchQueries({ queryKey: ['dashboard-stats'] })
        }}
      />
    </>
  )
}
```

### 3. MergeDialog Component

```tsx
// ui/centralD/src/pages/Dashboard/components/MergeDialog.tsx

import { useState } from "react"
import { useMutation } from "@tanstack/react-query"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { ArrowRight, GitMerge } from "lucide-react"
import { roleApi } from "@/services/role-api"
import { toast } from "sonner"

interface MergeDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  sourceRole: {
    id: number
    name: string
    similarRoles: { id: number; name: string; similarity: number }[]
  } | null
  onMergeComplete: () => void
}

export function MergeDialog({ 
  open, 
  onOpenChange, 
  sourceRole, 
  onMergeComplete 
}: MergeDialogProps) {
  const [selectedTarget, setSelectedTarget] = useState<string>("")

  const mergeMutation = useMutation({
    mutationFn: ({ sourceId, targetId }: { sourceId: number; targetId: number }) => 
      roleApi.mergeRoles(sourceId, targetId),
    onSuccess: () => {
      toast.success("Roles merged successfully")
      onMergeComplete()
    },
    onError: () => {
      toast.error("Failed to merge roles")
    }
  })

  const handleMerge = () => {
    if (!sourceRole || !selectedTarget) return
    
    mergeMutation.mutate({
      sourceId: sourceRole.id,
      targetId: parseInt(selectedTarget)
    })
  }

  if (!sourceRole) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <GitMerge className="h-5 w-5" />
            Merge Role
          </DialogTitle>
          <DialogDescription>
            Select which existing role to merge "{sourceRole.name}" into.
          </DialogDescription>
        </DialogHeader>

        <div className="py-4">
          <div className="mb-4 p-3 bg-muted rounded-lg">
            <div className="text-sm font-medium">Source Role (will be merged)</div>
            <div className="mt-1 font-semibold">{sourceRole.name}</div>
          </div>

          <div className="flex items-center justify-center mb-4">
            <ArrowRight className="h-5 w-5 text-muted-foreground" />
          </div>

          <div className="space-y-2">
            <div className="text-sm font-medium mb-3">Merge into:</div>
            <RadioGroup 
              value={selectedTarget} 
              onValueChange={setSelectedTarget}
              className="space-y-2"
            >
              {sourceRole.similarRoles.map((target) => (
                <div 
                  key={target.id} 
                  className="flex items-center space-x-3 p-3 border rounded-lg hover:bg-muted/50 cursor-pointer"
                >
                  <RadioGroupItem value={target.id.toString()} id={`target-${target.id}`} />
                  <Label 
                    htmlFor={`target-${target.id}`} 
                    className="flex-1 cursor-pointer"
                  >
                    <div className="flex items-center justify-between">
                      <span>{target.name}</span>
                      <Badge 
                        variant={target.similarity >= 90 ? "default" : "secondary"}
                      >
                        {target.similarity}% match
                      </Badge>
                    </div>
                  </Label>
                </div>
              ))}
            </RadioGroup>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button 
            onClick={handleMerge} 
            disabled={!selectedTarget || mergeMutation.isPending}
          >
            {mergeMutation.isPending ? "Merging..." : "Merge Roles"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
```

### 4. ApiKeysManager Component

```tsx
// ui/centralD/src/pages/Dashboard/components/ApiKeysManager.tsx

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { 
  Plus, 
  Copy, 
  Trash2, 
  Pause, 
  Play,
  Key
} from "lucide-react"
import { apiKeyService } from "@/services/api-key-service"
import { toast } from "sonner"
import { formatDistanceToNow } from "date-fns"

interface ApiKey {
  id: number
  name: string
  key: string // Only shown on creation
  keyPreview: string // e.g., "sk-...xyz123"
  isActive: boolean
  usageCount: number
  lastUsedAt: string | null
  expiresAt: string | null
  createdAt: string
}

export function ApiKeysManager() {
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [newKeyName, setNewKeyName] = useState("")
  const [createdKey, setCreatedKey] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const { data: apiKeys, isLoading } = useQuery<ApiKey[]>({
    queryKey: ['api-keys'],
    queryFn: apiKeyService.listKeys,
  })

  const createMutation = useMutation({
    mutationFn: (name: string) => apiKeyService.createKey(name),
    onSuccess: (data) => {
      setCreatedKey(data.key)
      queryClient.refetchQueries({ queryKey: ['api-keys'] })
      queryClient.refetchQueries({ queryKey: ['dashboard-stats'] })
      toast.success("API key created")
    },
    onError: () => {
      toast.error("Failed to create API key")
    }
  })

  const toggleMutation = useMutation({
    mutationFn: ({ id, isActive }: { id: number; isActive: boolean }) => 
      apiKeyService.toggleKey(id, isActive),
    onSuccess: () => {
      queryClient.refetchQueries({ queryKey: ['api-keys'] })
      toast.success("API key updated")
    }
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => apiKeyService.deleteKey(id),
    onSuccess: () => {
      queryClient.refetchQueries({ queryKey: ['api-keys'] })
      queryClient.refetchQueries({ queryKey: ['dashboard-stats'] })
      toast.success("API key deleted")
    }
  })

  const handleCreate = () => {
    if (!newKeyName.trim()) return
    createMutation.mutate(newKeyName.trim())
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    toast.success("Copied to clipboard")
  }

  const resetDialog = () => {
    setNewKeyName("")
    setCreatedKey(null)
    setCreateDialogOpen(false)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">API Keys</h3>
        <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button size="sm">
              <Plus className="h-4 w-4 mr-2" />
              Create Key
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create API Key</DialogTitle>
              <DialogDescription>
                Create a new API key for external scraper authentication.
              </DialogDescription>
            </DialogHeader>

            {createdKey ? (
              <div className="py-4">
                <div className="p-3 bg-muted rounded-lg">
                  <div className="text-sm font-medium mb-2 flex items-center gap-2 text-green-600">
                    <Key className="h-4 w-4" />
                    Key Created Successfully
                  </div>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 p-2 bg-background rounded text-sm break-all">
                      {createdKey}
                    </code>
                    <Button
                      size="icon"
                      variant="outline"
                      onClick={() => copyToClipboard(createdKey)}
                    >
                      <Copy className="h-4 w-4" />
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground mt-2">
                    ⚠️ Copy this key now. You won't be able to see it again.
                  </p>
                </div>
                <DialogFooter className="mt-4">
                  <Button onClick={resetDialog}>Done</Button>
                </DialogFooter>
              </div>
            ) : (
              <>
                <div className="py-4">
                  <Label htmlFor="key-name">Key Name</Label>
                  <Input
                    id="key-name"
                    value={newKeyName}
                    onChange={(e) => setNewKeyName(e.target.value)}
                    placeholder="e.g., Production Scraper 1"
                    className="mt-2"
                  />
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>
                    Cancel
                  </Button>
                  <Button 
                    onClick={handleCreate}
                    disabled={!newKeyName.trim() || createMutation.isPending}
                  >
                    {createMutation.isPending ? "Creating..." : "Create Key"}
                  </Button>
                </DialogFooter>
              </>
            )}
          </DialogContent>
        </Dialog>
      </div>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Key</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Usage</TableHead>
              <TableHead>Last Used</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-8">
                  Loading...
                </TableCell>
              </TableRow>
            ) : apiKeys?.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                  No API keys created
                </TableCell>
              </TableRow>
            ) : (
              apiKeys?.map((key) => (
                <TableRow key={key.id}>
                  <TableCell className="font-medium">{key.name}</TableCell>
                  <TableCell>
                    <code className="text-sm text-muted-foreground">
                      {key.keyPreview}
                    </code>
                  </TableCell>
                  <TableCell>
                    <Badge variant={key.isActive ? "default" : "secondary"}>
                      {key.isActive ? "Active" : "Paused"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    {key.usageCount.toLocaleString()}
                  </TableCell>
                  <TableCell>
                    {key.lastUsedAt ? (
                      formatDistanceToNow(new Date(key.lastUsedAt), { addSuffix: true })
                    ) : (
                      <span className="text-muted-foreground">Never</span>
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-2">
                      <Button
                        size="icon"
                        variant="outline"
                        onClick={() => toggleMutation.mutate({ 
                          id: key.id, 
                          isActive: !key.isActive 
                        })}
                      >
                        {key.isActive ? (
                          <Pause className="h-4 w-4" />
                        ) : (
                          <Play className="h-4 w-4" />
                        )}
                      </Button>
                      <Button
                        size="icon"
                        variant="outline"
                        className="text-destructive"
                        onClick={() => deleteMutation.mutate(key.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
```

### 5. JobsPreview Component

```tsx
// ui/centralD/src/pages/Dashboard/components/JobsPreview.tsx

import { useQuery } from "@tanstack/react-query"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { jobsApi } from "@/services/jobs-api"
import { formatDistanceToNow } from "date-fns"

interface JobImportStats {
  source: string
  jobsImported: number
  lastImportAt: string
  status: "active" | "idle" | "error"
}

interface RecentImport {
  id: number
  batchId: string
  source: string
  jobCount: number
  successCount: number
  failedCount: number
  importedAt: string
}

export function JobsPreview() {
  const { data: sourceStats } = useQuery<JobImportStats[]>({
    queryKey: ['job-source-stats'],
    queryFn: jobsApi.getSourceStats,
    refetchInterval: 60000, // Refresh every minute
  })

  const { data: recentImports } = useQuery<RecentImport[]>({
    queryKey: ['recent-imports'],
    queryFn: () => jobsApi.getRecentImports(5),
    refetchInterval: 30000,
  })

  const sourceColors: Record<string, string> = {
    monster: "bg-purple-500",
    indeed: "bg-blue-500",
    dice: "bg-green-500",
    glassdoor: "bg-orange-500",
    techfetch: "bg-red-500"
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Jobs by Source (Today)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {sourceStats?.map((stat) => (
            <div key={stat.source} className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className={`w-3 h-3 rounded-full ${sourceColors[stat.source.toLowerCase()] || "bg-gray-500"}`} />
                  <span className="font-medium capitalize">{stat.source}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold">
                    {stat.jobsImported.toLocaleString()}
                  </span>
                  <Badge 
                    variant={
                      stat.status === "active" ? "default" :
                      stat.status === "error" ? "destructive" : "secondary"
                    }
                    className="text-xs"
                  >
                    {stat.status}
                  </Badge>
                </div>
              </div>
              <Progress 
                value={Math.min((stat.jobsImported / 500) * 100, 100)} 
                className="h-2" 
              />
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recent Imports</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {recentImports?.map((imp) => (
              <div 
                key={imp.id} 
                className="flex items-center justify-between p-2 bg-muted/50 rounded-lg"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="capitalize">
                      {imp.source}
                    </Badge>
                    <span className="text-sm font-medium">
                      {imp.successCount}/{imp.jobCount} jobs
                    </span>
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">
                    {formatDistanceToNow(new Date(imp.importedAt), { addSuffix: true })}
                  </div>
                </div>
                {imp.failedCount > 0 && (
                  <Badge variant="destructive" className="text-xs">
                    {imp.failedCount} failed
                  </Badge>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
```

### 6. ActivityFeed Component

```tsx
// ui/centralD/src/pages/Dashboard/components/ActivityFeed.tsx

import { useQuery } from "@tanstack/react-query"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { 
  GitMerge, 
  CheckCircle, 
  XCircle, 
  Upload, 
  Key, 
  Wifi 
} from "lucide-react"
import { activityApi } from "@/services/activity-api"
import { formatDistanceToNow } from "date-fns"

interface Activity {
  id: number
  type: "role_merged" | "role_approved" | "role_rejected" | "jobs_imported" | "api_key_created" | "scraper_connected"
  message: string
  metadata: Record<string, any>
  createdAt: string
}

const activityIcons = {
  role_merged: GitMerge,
  role_approved: CheckCircle,
  role_rejected: XCircle,
  jobs_imported: Upload,
  api_key_created: Key,
  scraper_connected: Wifi
}

const activityColors = {
  role_merged: "text-blue-500",
  role_approved: "text-green-500",
  role_rejected: "text-red-500",
  jobs_imported: "text-purple-500",
  api_key_created: "text-orange-500",
  scraper_connected: "text-cyan-500"
}

export function ActivityFeed() {
  const { data: activities } = useQuery<Activity[]>({
    queryKey: ['activity-feed'],
    queryFn: () => activityApi.getRecent(20),
    refetchInterval: 15000, // Refresh every 15 seconds
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Activity Feed</CardTitle>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[400px] pr-4">
          <div className="space-y-4">
            {activities?.map((activity) => {
              const Icon = activityIcons[activity.type]
              const colorClass = activityColors[activity.type]
              
              return (
                <div 
                  key={activity.id} 
                  className="flex items-start gap-3 pb-3 border-b last:border-0"
                >
                  <div className={`mt-0.5 ${colorClass}`}>
                    <Icon className="h-4 w-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm">{activity.message}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs text-muted-foreground">
                        {formatDistanceToNow(new Date(activity.createdAt), { addSuffix: true })}
                      </span>
                      {activity.metadata.count && (
                        <Badge variant="secondary" className="text-xs">
                          {activity.metadata.count} items
                        </Badge>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}

            {(!activities || activities.length === 0) && (
              <div className="text-center py-8 text-muted-foreground">
                No recent activity
              </div>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}
```

### 7. ScraperMonitoring Component (Observability)

```tsx
// ui/centralD/src/pages/Dashboard/components/ScraperMonitoring.tsx

import { useQuery } from "@tanstack/react-query"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Progress } from "@/components/ui/progress"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { 
  Activity, 
  Clock, 
  CheckCircle, 
  AlertCircle,
  Loader2,
  Timer
} from "lucide-react"
import { scraperApi } from "@/services/scraper-api"
import { formatDistanceToNow, format } from "date-fns"

interface ScraperStats {
  activeScrapers: number
  totals: {
    jobs_found: number
    jobs_imported: number
    avg_duration_seconds: number
  }
  perScraper: {
    scraper_name: string
    scraper_key_id: number
    session_count: number
    jobs_imported: number
    current_role: string | null
    last_activity: string | null
  }[]
}

interface ScraperActivity {
  id: number
  session_id: string
  scraper_name: string
  current_role: string | null
  status: "in_progress" | "completed" | "failed" | "timeout"
  started_at: string
  completed_at: string | null
  duration_seconds: number | null
  jobs_found: number
  jobs_imported: number
  jobs_skipped: number
  platforms_scraped: string[]
  error_message: string | null
}

const statusIcons = {
  in_progress: Loader2,
  completed: CheckCircle,
  failed: AlertCircle,
  timeout: Clock
}

const statusColors = {
  in_progress: "text-blue-500",
  completed: "text-green-500",
  failed: "text-red-500",
  timeout: "text-orange-500"
}

export function ScraperMonitoring() {
  const { data: stats, isLoading: statsLoading } = useQuery<ScraperStats>({
    queryKey: ['scraper-stats'],
    queryFn: () => scraperApi.getStats(24),
    refetchInterval: 10000, // Refresh every 10 seconds
  })

  const { data: activities, isLoading: activitiesLoading } = useQuery<ScraperActivity[]>({
    queryKey: ['scraper-activity'],
    queryFn: () => scraperApi.getActivity(24, 50),
    refetchInterval: 10000,
  })

  const formatDuration = (seconds: number | null) => {
    if (seconds === null) return "-"
    if (seconds < 60) return `${seconds}s`
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`
    return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Activity className="h-5 w-5" />
          Scraper Monitoring
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="overview">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="activity">Activity Log</TabsTrigger>
            <TabsTrigger value="scrapers">Per Scraper</TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-4">
            <div className="grid gap-4 md:grid-cols-4">
              <Card>
                <CardContent className="pt-4">
                  <div className="text-2xl font-bold text-green-600">
                    {stats?.activeScrapers ?? 0}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Active Scrapers
                  </p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-4">
                  <div className="text-2xl font-bold">
                    {(stats?.totals.jobs_found ?? 0).toLocaleString()}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Jobs Found (24h)
                  </p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-4">
                  <div className="text-2xl font-bold text-blue-600">
                    {(stats?.totals.jobs_imported ?? 0).toLocaleString()}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Jobs Imported (24h)
                  </p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-4">
                  <div className="text-2xl font-bold flex items-center gap-1">
                    <Timer className="h-5 w-5 text-muted-foreground" />
                    {formatDuration(stats?.totals.avg_duration_seconds ?? 0)}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Avg Session Duration
                  </p>
                </CardContent>
              </Card>
            </div>

            {/* Currently Active Sessions */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Currently Active</CardTitle>
              </CardHeader>
              <CardContent>
                {activities?.filter(a => a.status === "in_progress").length === 0 ? (
                  <p className="text-muted-foreground text-center py-4">
                    No active sessions
                  </p>
                ) : (
                  <div className="space-y-3">
                    {activities?.filter(a => a.status === "in_progress").map((activity) => (
                      <div 
                        key={activity.id}
                        className="flex items-center justify-between p-3 bg-muted/50 rounded-lg"
                      >
                        <div className="flex items-center gap-3">
                          <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />
                          <div>
                            <p className="font-medium">{activity.scraper_name}</p>
                            <p className="text-sm text-muted-foreground">
                              {activity.current_role || "No role assigned"}
                            </p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="font-medium">{activity.jobs_imported} imported</p>
                          <p className="text-xs text-muted-foreground">
                            Started {formatDistanceToNow(new Date(activity.started_at), { addSuffix: true })}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Activity Log Tab */}
          <TabsContent value="activity">
            <div className="rounded-md border max-h-[500px] overflow-auto">
              <Table>
                <TableHeader className="sticky top-0 bg-background">
                  <TableRow>
                    <TableHead>Status</TableHead>
                    <TableHead>Scraper</TableHead>
                    <TableHead>Current Role</TableHead>
                    <TableHead>Duration</TableHead>
                    <TableHead className="text-right">Jobs</TableHead>
                    <TableHead>Platforms</TableHead>
                    <TableHead>Started</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {activitiesLoading ? (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center py-8">
                        Loading...
                      </TableCell>
                    </TableRow>
                  ) : activities?.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                        No activity in the last 24 hours
                      </TableCell>
                    </TableRow>
                  ) : (
                    activities?.map((activity) => {
                      const StatusIcon = statusIcons[activity.status]
                      const statusColor = statusColors[activity.status]
                      
                      return (
                        <TableRow key={activity.id}>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <StatusIcon 
                                className={`h-4 w-4 ${statusColor} ${
                                  activity.status === "in_progress" ? "animate-spin" : ""
                                }`} 
                              />
                              <Badge 
                                variant={
                                  activity.status === "completed" ? "default" :
                                  activity.status === "in_progress" ? "secondary" :
                                  "destructive"
                                }
                              >
                                {activity.status}
                              </Badge>
                            </div>
                          </TableCell>
                          <TableCell className="font-medium">
                            {activity.scraper_name}
                          </TableCell>
                          <TableCell>
                            {activity.current_role || (
                              <span className="text-muted-foreground">-</span>
                            )}
                          </TableCell>
                          <TableCell>
                            {formatDuration(activity.duration_seconds)}
                          </TableCell>
                          <TableCell className="text-right">
                            <div>
                              <span className="font-medium">{activity.jobs_imported}</span>
                              <span className="text-muted-foreground">/{activity.jobs_found}</span>
                            </div>
                            {activity.jobs_skipped > 0 && (
                              <span className="text-xs text-muted-foreground">
                                ({activity.jobs_skipped} skipped)
                              </span>
                            )}
                          </TableCell>
                          <TableCell>
                            <div className="flex flex-wrap gap-1">
                              {activity.platforms_scraped?.map((platform) => (
                                <Badge key={platform} variant="outline" className="text-xs capitalize">
                                  {platform}
                                </Badge>
                              ))}
                            </div>
                          </TableCell>
                          <TableCell>
                            <span className="text-sm text-muted-foreground">
                              {format(new Date(activity.started_at), "MMM d, HH:mm")}
                            </span>
                          </TableCell>
                        </TableRow>
                      )
                    })
                  )}
                </TableBody>
              </Table>
            </div>
          </TabsContent>

          {/* Per Scraper Tab */}
          <TabsContent value="scrapers">
            <div className="space-y-4">
              {statsLoading ? (
                <div className="text-center py-8">Loading...</div>
              ) : stats?.perScraper?.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  No scraper activity in the last 24 hours
                </div>
              ) : (
                stats?.perScraper?.map((scraper) => (
                  <Card key={scraper.scraper_key_id}>
                    <CardContent className="pt-4">
                      <div className="flex items-center justify-between mb-3">
                        <div>
                          <p className="font-semibold">{scraper.scraper_name}</p>
                          <p className="text-sm text-muted-foreground">
                            {scraper.session_count} sessions today
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-lg font-bold">
                            {scraper.jobs_imported.toLocaleString()}
                          </p>
                          <p className="text-xs text-muted-foreground">jobs imported</p>
                        </div>
                      </div>
                      
                      <div className="flex items-center justify-between text-sm">
                        <div>
                          <span className="text-muted-foreground">Current Role: </span>
                          <span className="font-medium">
                            {scraper.current_role || "Idle"}
                          </span>
                        </div>
                        {scraper.last_activity && (
                          <span className="text-muted-foreground">
                            Last active: {formatDistanceToNow(new Date(scraper.last_activity), { addSuffix: true })}
                          </span>
                        )}
                      </div>
                      
                      <Progress 
                        value={(scraper.jobs_imported / 1000) * 100} 
                        className="h-2 mt-3" 
                      />
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}
```

### Scraper API Service

```typescript
// ui/centralD/src/services/scraper-api.ts

import { apiClient } from "./api-client"

export const scraperApi = {
  getStats: async (hours: number = 24) => {
    const response = await apiClient.get(`/api/scrape-activity/stats?hours=${hours}`)
    return response.data
  },
  
  getActivity: async (hours: number = 24, limit: number = 50) => {
    const response = await apiClient.get(`/api/scrape-activity/activity?hours=${hours}&limit=${limit}`)
    return response.data.activities
  },
  
  getScraperActivity: async (scraperKeyId: number, hours: number = 24) => {
    const response = await apiClient.get(
      `/api/scrape-activity/activity?scraper_key_id=${scraperKeyId}&hours=${hours}`
    )
    return response.data.activities
  }
}
```

## Main Dashboard Page

```tsx
// ui/centralD/src/pages/Dashboard/index.tsx

import { StatsCards } from "./components/StatsCards"
import { RoleQueueTable } from "./components/RoleQueueTable"
import { ApiKeysManager } from "./components/ApiKeysManager"
import { JobsPreview } from "./components/JobsPreview"
import { ActivityFeed } from "./components/ActivityFeed"
import { ScraperMonitoring } from "./components/ScraperMonitoring"

export function Dashboard() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Monitor job scraping, role normalization, and system health.
        </p>
      </div>

      {/* Stats Overview */}
      <StatsCards />

      {/* Scraper Monitoring - Full Width */}
      <ScraperMonitoring />

      {/* Main Grid */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Role Queue - Takes 2 columns */}
        <div className="lg:col-span-2 space-y-6">
          <div>
            <h2 className="text-xl font-semibold mb-4">Role Normalization Queue</h2>
            <RoleQueueTable />
          </div>
          
          <ApiKeysManager />
        </div>

        {/* Right Sidebar */}
        <div className="space-y-6">
          <JobsPreview />
          <ActivityFeed />
        </div>
      </div>
    </div>
  )
}
```

## API Service Layer

```typescript
// ui/centralD/src/services/dashboard-api.ts

import { apiClient } from "./api-client"

export const dashboardApi = {
  getStats: async () => {
    const response = await apiClient.get("/api/dashboard/stats")
    return response.data
  }
}

export const roleApi = {
  getPendingRoles: async () => {
    const response = await apiClient.get("/api/roles/pending")
    return response.data.roles
  },
  
  approveRole: async (roleId: number) => {
    const response = await apiClient.post(`/api/roles/${roleId}/approve`)
    return response.data
  },
  
  rejectRole: async (roleId: number) => {
    const response = await apiClient.post(`/api/roles/${roleId}/reject`)
    return response.data
  },
  
  mergeRoles: async (sourceId: number, targetId: number) => {
    const response = await apiClient.post(`/api/roles/${sourceId}/merge`, {
      target_role_id: targetId
    })
    return response.data
  }
}

export const apiKeyService = {
  listKeys: async () => {
    const response = await apiClient.get("/api/scraper-keys")
    return response.data.keys
  },
  
  createKey: async (name: string) => {
    const response = await apiClient.post("/api/scraper-keys", { name })
    return response.data
  },
  
  toggleKey: async (id: number, isActive: boolean) => {
    const response = await apiClient.patch(`/api/scraper-keys/${id}`, { is_active: isActive })
    return response.data
  },
  
  deleteKey: async (id: number) => {
    await apiClient.delete(`/api/scraper-keys/${id}`)
  }
}
```

## See Also

- [09-SCRAPE-QUEUE-SYSTEM.md](./09-SCRAPE-QUEUE-SYSTEM.md) - Backend queue system
- [10-AI-ROLE-NORMALIZATION.md](./10-AI-ROLE-NORMALIZATION.md) - Role normalization logic
- [08-API-ENDPOINTS.md](./08-API-ENDPOINTS.md) - Backend API reference
