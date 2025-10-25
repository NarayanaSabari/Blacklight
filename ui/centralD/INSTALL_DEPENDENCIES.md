# Phase 3 - Dependencies Installation

Run the following commands in the `ui/centralD` directory:

```bash
# Install routing
npm install react-router-dom
npm install -D @types/react-router-dom

# Install state management
npm install @tanstack/react-query
npm install -D @tanstack/react-query-devtools

# Install HTTP client
npm install axios
```

## Verification

After installation, verify the packages are in package.json:
- react-router-dom
- @tanstack/react-query
- @tanstack/react-query-devtools (devDependencies)
- axios

## Note
All shadcn/ui components, React Hook Form, Zod, and Sonner are already installed.
