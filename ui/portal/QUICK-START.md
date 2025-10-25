# Portal UI Quick Start Guide

## Running the Application

### Development Mode
```bash
# From ui/portal directory
npm install
npm run dev
```

The Portal UI will be available at `http://localhost:5173`

### Login Credentials
Use test credentials from your backend:
- Email: (from your seeded data)
- Password: (from your seeded data)

## Project Structure

```
ui/portal/src/
├── components/
│   ├── ui/              # shadcn/ui components (DO NOT EDIT - managed by CLI)
│   └── Layout.tsx       # Main layout with sidebar navigation
├── contexts/
│   └── PortalAuthContext.tsx  # Auth state management
├── lib/
│   ├── api-client.ts    # Axios instance with Bearer token
│   └── env.ts           # Environment configuration
├── pages/               # All application pages
├── types/               # TypeScript interfaces
└── App.tsx              # Main routing component
```

## Adding a New Page

1. Create page component in `src/pages/`:
```tsx
// src/pages/MyNewPage.tsx
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

export function MyNewPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Page Title</h1>
        <p className="text-slate-600 mt-1">Page description</p>
      </div>
      
      {/* Your content here */}
    </div>
  );
}
```

2. Add route to `App.tsx`:
```tsx
import { MyNewPage } from '@/pages/MyNewPage';

// In the Routes section:
<Route path="/my-new-page" element={<MyNewPage />} />
```

3. Add navigation item to `Layout.tsx`:
```tsx
const navigation = [
  // ... existing items
  {
    name: 'My Page',
    href: '/my-new-page',
    icon: MyIcon,
    roles: ['TENANT_ADMIN', 'RECRUITER', 'HIRING_MANAGER']
  },
];
```

## Adding shadcn Components

Use the shadcn CLI (DO NOT manually create):

```bash
# From ui/portal directory
npx shadcn@latest add [component-name]

# Examples:
npx shadcn@latest add dialog
npx shadcn@latest add table
npx shadcn@latest add select
```

## Styling Guidelines

### Use Tailwind Utility Classes
```tsx
// ✅ Good
<div className="flex items-center gap-4 p-6">
  <Button variant="default" size="lg" className="w-full">
    Click Me
  </Button>
</div>

// ❌ Bad - Don't use inline styles
<div style={{display: 'flex', padding: '24px'}}>
  <button style={{width: '100%'}}>Click Me</button>
</div>
```

### Use shadcn Components
```tsx
// ✅ Good - shadcn components
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';

// ❌ Bad - External UI libraries
import { MaterialButton } from '@mui/material';
import { AntCard } from 'antd';
```

### Color Palette
- Primary: `bg-primary`, `text-primary`
- Slate tones: `bg-slate-50`, `text-slate-900`, `border-slate-200`
- Muted: `text-muted-foreground`, `bg-muted`

## Common Patterns

### Stats Card
```tsx
<Card>
  <CardHeader className="pb-2">
    <CardDescription>Label</CardDescription>
    <CardTitle className="text-3xl">123</CardTitle>
  </CardHeader>
</Card>
```

### Empty State
```tsx
<div className="flex flex-col items-center justify-center py-12 text-center">
  <Icon className="h-12 w-12 text-slate-400 mb-4" />
  <h3 className="text-lg font-semibold text-slate-900 mb-2">No items yet</h3>
  <p className="text-slate-600 mb-4 max-w-sm">Description</p>
  <Button className="gap-2">
    <Plus className="h-4 w-4" />
    Call to Action
  </Button>
</div>
```

### Page Header
```tsx
<div className="flex items-center justify-between">
  <div>
    <h1 className="text-3xl font-bold text-slate-900">Page Title</h1>
    <p className="text-slate-600 mt-1">Description</p>
  </div>
  <Button className="gap-2">
    <Plus className="h-4 w-4" />
    Action
  </Button>
</div>
```

## API Integration

### Using the API Client
```tsx
import { apiClient } from '@/lib/api-client';

async function fetchData() {
  try {
    const response = await apiClient.get('/api/tenants/{slug}/candidates');
    return response.data;
  } catch (error) {
    console.error('Failed to fetch:', error);
    throw error;
  }
}
```

### Authentication Context
```tsx
import { usePortalAuth } from '@/contexts/PortalAuthContext';

function MyComponent() {
  const { user, tenantName, logout } = usePortalAuth();
  
  return (
    <div>
      <p>Welcome, {user?.first_name}!</p>
      <p>Company: {tenantName}</p>
      <Button onClick={logout}>Logout</Button>
    </div>
  );
}
```

## Role-Based Access

### Check User Role
```tsx
import { usePortalAuth } from '@/contexts/PortalAuthContext';

function MyComponent() {
  const { user } = usePortalAuth();
  const isTenantAdmin = user?.role?.name === 'TENANT_ADMIN';
  
  return (
    <>
      {isTenantAdmin && (
        <Button>Admin Only Action</Button>
      )}
    </>
  );
}
```

### Available Roles
- `TENANT_ADMIN` - Full access to all features
- `RECRUITER` - Manage candidates, jobs, applications, interviews
- `HIRING_MANAGER` - Review candidates, provide feedback

## Testing

### Run Development Server
```bash
npm run dev
```

### Build for Production
```bash
npm run build
npm run preview  # Preview production build
```

### Type Checking
```bash
npm run type-check
```

### Linting
```bash
npm run lint
```

## Common Issues

### Module Not Found
Make sure you're using the `@/` alias for imports:
```tsx
// ✅ Good
import { Button } from '@/components/ui/button';

// ❌ Bad
import { Button } from '../components/ui/button';
```

### Component Not Styled
Make sure Tailwind classes are in the `className` prop:
```tsx
// ✅ Good
<div className="flex gap-4">

// ❌ Bad
<div class="flex gap-4">  // Wrong attribute
```

### API Requests Failing
1. Check `.env` file has correct `VITE_API_BASE_URL`
2. Ensure backend server is running on port 5000
3. Verify you're logged in (token in localStorage)
4. Check browser console for CORS errors

## Environment Setup

### Required .env File
```env
VITE_API_BASE_URL=http://localhost:5000
```

### VSCode Extensions (Recommended)
- ESLint
- Tailwind CSS IntelliSense
- TypeScript and JavaScript Language Features

## Useful Commands

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Add shadcn component
npx shadcn@latest add [component-name]

# Type check
npm run type-check

# Lint code
npm run lint
```

## Resources

- [shadcn/ui Documentation](https://ui.shadcn.com)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [React Router Documentation](https://reactrouter.com)
- [Lucide Icons](https://lucide.dev/icons)

## Getting Help

1. Check this guide
2. Review existing page components for patterns
3. Consult shadcn/ui documentation
4. Review Tailwind CSS documentation
5. Check PHASE4-COMPLETE.md for detailed architecture

---

**Remember:** Always use shadcn/ui components and Tailwind CSS. Never install additional UI libraries or write custom CSS unless absolutely necessary.
