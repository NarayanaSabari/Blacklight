# PORTAL (Recruiter Interface)

**Location:** `./ui/portal/`  
**Language:** TypeScript  
**Framework:** React 18 + Vite

## OVERVIEW
Main recruiter/HR interface. Multi-tenant with role-based access (TENANT_ADMIN, MANAGER, TEAM_LEAD, RECRUITER).

## STRUCTURE
```
ui/portal/
├── src/
│   ├── components/    # 99 files → see src/components/AGENTS.md
│   ├── pages/         # 27 files → see src/pages/AGENTS.md
│   ├── lib/           # API client, utilities
│   ├── hooks/         # Custom React hooks
│   └── types/         # TypeScript types (12 files)
├── package.json       # Dependencies
├── vite.config.ts     # Dev server config
└── tsconfig.json      # TypeScript config
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| UI components | `src/components/ui/` | 54 shadcn/ui primitives |
| Feature components | `src/components/` | Candidates, settings, onboarding |
| Pages/routes | `src/pages/` | 27 route components |
| API calls | `src/lib/api/` | Axios-based API client |
| Types | `src/types/` | Shared TypeScript types |

## STYLING (STRICT RULES)

### shadcn/ui ONLY
```tsx
// ✅ Correct - Use shadcn/ui primitives
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Dialog, DialogTrigger, DialogContent } from "@/components/ui/dialog"

// ❌ NEVER install or use other UI libraries
import { Button } from '@mui/material'  // FORBIDDEN
import { Button } from 'antd'           // FORBIDDEN
import { Button } from '@chakra-ui/react' // FORBIDDEN
```

### Tailwind CSS ONLY
```tsx
// ✅ Correct - Tailwind utility classes
<div className="flex items-center gap-4 p-6 bg-card rounded-lg">
  <Button variant="default" size="lg" className="w-full">
    Submit
  </Button>
</div>

// ❌ NEVER use inline styles (except for truly dynamic values)
<div style={{display: 'flex', padding: '24px'}}>  // FORBIDDEN
  
// ❌ NEVER create custom CSS files
// styles.css with custom classes  // FORBIDDEN
```

## STATE MANAGEMENT

### React Query (TanStack Query)
```tsx
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

// ✅ Use staleTime: 0 for volatile data
const { data: candidates } = useQuery({
  queryKey: ['candidates', filters],
  queryFn: () => candidateApi.listCandidates(filters),
  staleTime: 0,  // CRITICAL: Always refetch for fresh data
})

// ✅ Use refetchQueries instead of invalidateQueries
const deleteMutation = useMutation({
  mutationFn: (id) => candidateApi.deleteCandidate(id),
  onSuccess: async () => {
    // Immediate refetch ensures UI syncs with DB
    await queryClient.refetchQueries({ queryKey: ['candidates'] })
    await queryClient.refetchQueries({ queryKey: ['candidate-stats'] })
  },
  onError: async () => {
    // Force refetch even on error to sync with actual DB state
    await queryClient.refetchQueries({ queryKey: ['candidates'] })
  }
})
```

## PATH ALIASES
```tsx
// Use @ aliases (configured in tsconfig.json)
import { Button } from '@/components/ui/button'
import { candidateApi } from '@/lib/api/candidates'
import { Candidate } from '@/types/candidate'

// NOT relative paths
import { Button } from '../../../components/ui/button'  // Avoid
```

## LARGEST COMPONENTS
| Component | Lines | Complexity |
|-----------|-------|------------|
| `CandidateDetailPage.tsx` | 2138 | High - full candidate profile |
| `CandidateOnboardingFlow_v2.tsx` | 1918 | High - multi-step form with state |
| `TeamJobsPage.tsx` | 1362 | High - job management dashboard |
| `ManualResumeTailorPage.tsx` | 1042 | High - resume editing |

## ANTI-PATTERNS

1. **Non-shadcn UI libraries** - ONLY shadcn/ui allowed
2. **Custom CSS files** - Use Tailwind utilities only
3. **Inline styles** - Use Tailwind classes (except dynamic values)
4. **Long staleTime** - Use 0 or low values for changing data
5. **invalidateQueries** - Prefer refetchQueries for immediate sync
6. **Relative imports** - Use @ path aliases

## COMMANDS

```bash
# From ui/portal/ directory
npm run dev        # Dev server (port 5173)
npm run build      # Production build
npm run lint       # ESLint
tsc -b             # Type check
```

## DEV SERVER
- Port: 5173 (default)
- Hot reload: Enabled via Vite
- Proxy: API requests to `http://localhost:5000/api`
