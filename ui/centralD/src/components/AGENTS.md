# CENTRALD COMPONENTS

**Location:** `./ui/centralD/src/components/`  
**Files:** 73 TypeScript files

## OVERVIEW
Admin-focused component library. Mix of shadcn/ui primitives (53 in `ui/`) and platform management components.

## STRUCTURE
```
components/
├── ui/          # 53 shadcn/ui primitives
├── tenants/     # 8 files - tenant management UI
├── dialogs/     # 8 files - modal dialogs
└── [monitoring, analytics, etc.]
```

## KEY COMPONENTS

### ScraperMonitoring.tsx (988 lines)
Complex monitoring dashboard for web scraper:
```tsx
// Real-time scraper status
const { data: scraperStatus } = useQuery({
  queryKey: ['scraper-status'],
  queryFn: dashboardApi.getScraperStatus,
  refetchInterval: 5000,  // Poll every 5 seconds
  staleTime: 0,
})

// Displays:
// - Active/queued/failed scrapes
// - Performance metrics
// - Error logs
// - Scraper control (start/stop/restart)
```

### Tenant Components (`tenants/`)
```tsx
// TenantTable - List all tenants
// TenantDialog - Create/edit tenant
// TenantSubscription - Manage subscription plans
// TenantSettings - Platform-wide settings per tenant
```

### Dialog Components (`dialogs/`)
```tsx
// Modal dialogs for admin actions
import { Dialog, DialogTrigger, DialogContent } from '@/components/ui/dialog'

// Common pattern:
function CreateTenantDialog() {
  const [open, setOpen] = useState(false)
  
  const createMutation = useMutation({
    mutationFn: dashboardApi.createTenant,
    onSuccess: async () => {
      setOpen(false)
      await queryClient.refetchQueries({ queryKey: ['tenants'] })
    }
  })
  
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>Create Tenant</Button>
      </DialogTrigger>
      <DialogContent>
        <TenantForm onSubmit={createMutation.mutate} />
      </DialogContent>
    </Dialog>
  )
}
```

## MONITORING PATTERNS

### Real-time Data
```tsx
// Use refetchInterval for live updates
const { data } = useQuery({
  queryKey: ['live-stats'],
  queryFn: dashboardApi.getLiveStats,
  refetchInterval: 3000,  // Update every 3 seconds
  staleTime: 0,
})
```

### Error Handling
```tsx
// Display errors from platform operations
const { error } = useQuery(...)

if (error) {
  return (
    <Alert variant="destructive">
      <AlertTitle>Error</AlertTitle>
      <AlertDescription>{error.message}</AlertDescription>
    </Alert>
  )
}
```

## STYLING & CONVENTIONS

Same as portal:
- **shadcn/ui primitives only**
- **Tailwind CSS utilities only**
- **No custom CSS files**
- **Path aliases**: `@/components`, `@/lib`

## ANTI-PATTERNS

1. **Same as portal** - All portal component anti-patterns apply
2. **Tenant-scoped operations** - CentralD is platform-wide, not tenant-scoped
3. **Missing real-time updates** - Monitoring components should use refetchInterval
