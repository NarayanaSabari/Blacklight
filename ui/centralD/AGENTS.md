# CENTRALD (Super-Admin Dashboard)

**Location:** `./ui/centralD/`  
**Language:** TypeScript  
**Framework:** React 18 + Vite

## OVERVIEW
Super-admin (PM_ADMIN) interface for platform-wide management. Different from portal: manages ALL tenants, not tenant-scoped operations.

## STRUCTURE
```
ui/centralD/
├── src/
│   ├── components/    # 73 files → see src/components/AGENTS.md
│   ├── pages/         # 42 files - admin dashboard pages
│   ├── lib/           # API client (dashboard-api.ts: 1772 lines)
│   ├── hooks/         # Custom hooks (api/ subdirectory)
│   └── types/         # TypeScript types
├── package.json       # Dependencies
├── vite.config.ts     # Dev server config (port 5174)
└── tsconfig.json      # TypeScript config
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Tenant management | `src/components/tenants/` | Tenant CRUD, subscriptions |
| Monitoring | `src/components/` | Scraper monitoring (988 lines) |
| Dashboard API | `src/lib/dashboard-api.ts` | 1772 lines - all API calls |
| Pages | `src/pages/` | 42 route components |
| API hooks | `src/hooks/api/` | 19 custom React Query hooks |

## KEY DIFFERENCES FROM PORTAL

| Portal | CentralD |
|--------|----------|
| Tenant-scoped (single tenant) | Platform-wide (all tenants) |
| TENANT_ADMIN, MANAGER, RECRUITER | PM_ADMIN only |
| Candidate/job management | Tenant/platform management |
| `g.tenant_id` from JWT | No tenant scoping |
| `/api/*` routes | `/api/pm/*` routes |

## LARGEST FILES

| File | Lines | Purpose |
|------|-------|---------|
| `dashboard-api.ts` | 1772 | All API client functions |
| `ScraperMonitoring.tsx` | 988 | Web scraper monitoring dashboard |
| `SessionDetailPage.tsx` | 952 | User session details |

## STYLING & STATE

Same as portal:
- **shadcn/ui ONLY** - no other UI libraries
- **Tailwind CSS ONLY** - no custom CSS
- **React Query** - staleTime: 0, refetchQueries pattern

## TENANT MANAGEMENT

```tsx
// Tenant CRUD operations
import { useQuery, useMutation } from '@tanstack/react-query'
import { dashboardApi } from '@/lib/dashboard-api'

function TenantManagement() {
  // List all tenants (PM_ADMIN can see all)
  const { data: tenants } = useQuery({
    queryKey: ['tenants'],
    queryFn: dashboardApi.listTenants,
    staleTime: 0,
  })
  
  // Create tenant
  const createMutation = useMutation({
    mutationFn: dashboardApi.createTenant,
    onSuccess: async () => {
      await queryClient.refetchQueries({ queryKey: ['tenants'] })
    }
  })
}
```

## PLATFORM ANALYTICS

```tsx
// Cross-tenant analytics
const { data: stats } = useQuery({
  queryKey: ['platform-stats'],
  queryFn: dashboardApi.getPlatformStats,
  staleTime: 0,
})

// Stats include:
// - Total tenants, active/inactive
// - Total candidates across all tenants
// - Total jobs, submissions
// - System health metrics
```

## ANTI-PATTERNS

1. **Same as portal** - All portal anti-patterns apply
2. **Assuming tenant context** - CentralD has NO tenant scoping
3. **Using portal API routes** - Use `/api/pm/*` routes instead

## COMMANDS

```bash
# From ui/centralD/ directory
npm run dev        # Dev server (port 5174)
npm run build      # Production build
npm run lint       # ESLint
tsc -b             # Type check
```

## DEV SERVER
- Port: 5174 (different from portal: 5173)
- Hot reload: Enabled via Vite
- Proxy: API requests to `http://localhost:5000/api/pm`
