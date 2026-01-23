# PORTAL COMPONENTS

**Location:** `./ui/portal/src/components/`  
**Files:** 99 TypeScript files

## OVERVIEW
Component library for portal interface. Mix of shadcn/ui primitives (54 files in `ui/`) and custom feature components.

## STRUCTURE
```
components/
├── ui/               # 54 shadcn/ui primitives (Button, Card, Dialog, etc.)
├── candidates/       # 13 files - candidate-specific components
├── settings/         # 7 files - settings UI
├── onboarding/       # Onboarding flow components
└── [other features]
```

## SHADCN/UI PRIMITIVES (`ui/`)

54 pre-built components from shadcn/ui:
```tsx
// Core UI primitives - use these to build everything
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Dialog, DialogTrigger, DialogContent, DialogHeader } from '@/components/ui/dialog'
import { Form, FormField, FormItem, FormLabel, FormControl } from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { Select, SelectTrigger, SelectContent, SelectItem } from '@/components/ui/select'
import { Table, TableHeader, TableBody, TableRow, TableCell } from '@/components/ui/table'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
// ... 46 more primitives
```

**NEVER** install other UI libraries (Material-UI, Ant Design, Chakra, etc.)

## LARGEST COMPONENTS

### CandidateOnboardingFlow_v2.tsx (1918 lines)
Complex multi-step form with state management:
```tsx
// Multi-step wizard pattern
const [currentStep, setCurrentStep] = useState(1)
const [formData, setFormData] = useState({})

// React Hook Form integration
const form = useForm<FormData>()

// Validation per step
const validateStep = (step: number) => { ... }

// Progress tracking
<Tabs value={`step-${currentStep}`}>
  <TabsList>
    <TabsTrigger value="step-1">Personal Info</TabsTrigger>
    <TabsTrigger value="step-2">Documents</TabsTrigger>
  </TabsList>
</Tabs>
```

## COMPONENT PATTERNS

### Composition with shadcn/ui
```tsx
// Build complex UIs from primitives
function CandidateCard({ candidate }: Props) {
  return (
    <Card className="hover:shadow-lg transition-shadow">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-xl">{candidate.name}</CardTitle>
        <Button variant="ghost" size="icon">
          <MoreVertical className="h-4 w-4" />
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-2">
          <Mail className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm">{candidate.email}</span>
        </div>
      </CardContent>
    </Card>
  )
}
```

### Form Components with react-hook-form
```tsx
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

const schema = z.object({
  name: z.string().min(1, 'Name required'),
  email: z.string().email('Invalid email'),
})

function CandidateForm() {
  const form = useForm({
    resolver: zodResolver(schema),
  })
  
  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)}>
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Name</FormLabel>
              <FormControl>
                <Input {...field} />
              </FormControl>
            </FormItem>
          )}
        />
      </form>
    </Form>
  )
}
```

## STYLING CONVENTIONS

```tsx
// Use Tailwind utility classes exclusively
<div className="flex items-center justify-between gap-4 p-6 rounded-lg bg-card border">
  
// Use CSS variables from shadcn theme (in index.css)
<div className="bg-primary text-primary-foreground">  // theme colors
<div className="text-muted-foreground">              // semantic colors

// Responsive modifiers
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">

// State modifiers
<Button className="hover:bg-accent active:scale-95 transition-all">
```

## ANTI-PATTERNS

1. **Non-shadcn components** - Use shadcn/ui primitives only
2. **Custom CSS classes** - Tailwind utilities only
3. **Inline styles** - className with Tailwind (except truly dynamic)
4. **Prop drilling** - Use React Context or React Query for shared state
5. **Large monolithic components** - Break down >500 lines into smaller pieces
