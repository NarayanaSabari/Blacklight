# PORTAL PAGES

**Location:** `./ui/portal/src/pages/`  
**Files:** 27 TypeScript files

## OVERVIEW
Top-level route components. Handle data fetching, layout, and coordinate child components.

## LARGEST PAGES
| Page | Lines | Purpose |
|------|-------|---------|
| `CandidateDetailPage.tsx` | 2138 | Full candidate profile with tabs |
| `TeamJobsPage.tsx` | 1362 | Job management dashboard |
| `SubmissionDetailPage.tsx` | 1083 | Candidate submission details |
| `ManualResumeTailorPage.tsx` | 1042 | Resume editing interface |
| `ResumeTailorPage.tsx` | 964 | AI-assisted resume tailoring |

## PAGE STRUCTURE

```tsx
// Typical page pattern
function CandidatePage() {
  // 1. Data fetching at page level
  const { data: candidates, isLoading } = useQuery({
    queryKey: ['candidates'],
    queryFn: candidateApi.listCandidates,
    staleTime: 0,
  })
  
  // 2. Page-level state
  const [filters, setFilters] = useState({})
  const [selectedId, setSelectedId] = useState<number | null>(null)
  
  // 3. Mutations with refetch
  const deleteMutation = useMutation({
    mutationFn: candidateApi.deleteCandidate,
    onSuccess: async () => {
      await queryClient.refetchQueries({ queryKey: ['candidates'] })
    }
  })
  
  // 4. Layout with components
  return (
    <div className="container mx-auto p-6">
      <PageHeader />
      <FilterBar filters={filters} onChange={setFilters} />
      <CandidateList 
        candidates={candidates}
        onSelect={setSelectedId}
        onDelete={deleteMutation.mutate}
      />
    </div>
  )
}
```

## DATA FETCHING PATTERNS

### List Pages
```tsx
// Fetch list with filters, use staleTime: 0
const { data, isLoading } = useQuery({
  queryKey: ['candidates', filters],  // Include filters in key
  queryFn: () => candidateApi.listCandidates(filters),
  staleTime: 0,  // Always fetch fresh data
})
```

### Detail Pages
```tsx
// Fetch single item by ID
const { id } = useParams()
const { data: candidate } = useQuery({
  queryKey: ['candidate', id],
  queryFn: () => candidateApi.getCandidate(id),
  staleTime: 0,
})
```

### Parallel Queries
```tsx
// Fetch multiple resources in parallel
const { data: candidate } = useQuery(['candidate', id], ...)
const { data: submissions } = useQuery(['submissions', id], ...)
const { data: assignments } = useQuery(['assignments', id], ...)
```

## LAYOUT PATTERNS

### Tabbed Pages
```tsx
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'

function CandidateDetailPage() {
  return (
    <Tabs defaultValue="profile">
      <TabsList>
        <TabsTrigger value="profile">Profile</TabsTrigger>
        <TabsTrigger value="submissions">Submissions</TabsTrigger>
        <TabsTrigger value="documents">Documents</TabsTrigger>
      </TabsList>
      
      <TabsContent value="profile">
        <CandidateProfile />
      </TabsContent>
      <TabsContent value="submissions">
        <SubmissionList />
      </TabsContent>
    </Tabs>
  )
}
```

### Protected Routes
```tsx
// Pages are protected by auth at router level
<Route
  path="/candidates"
  element={
    <ProtectedRoute permission="candidates.view">
      <CandidatesPage />
    </ProtectedRoute>
  }
/>
```

## ANTI-PATTERNS

1. **Business logic in pages** - Delegate to services/hooks
2. **Direct API calls** - Use React Query hooks
3. **Long staleTime** - Use 0 for changing data
4. **Missing loading states** - Always handle isLoading
5. **Prop drilling** - Use context or React Query for deep state
