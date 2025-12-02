# Portal UI

Tenant-specific portal for recruiters, managers, team leads, and tenant administrators.

## Features

- **Authentication**: Secure login with JWT tokens
- **Multi-tenant**: Each user sees only their organization's data
- **Role-based Access**: Different permissions for Tenant Admins, Managers, Team Leads, and Recruiters
- **Modern UI**: Built with React, TypeScript, shadcn/ui, and Tailwind CSS

## Getting Started

### Prerequisites

- Node.js 18+ 
- Backend server running at `http://localhost:5000`
- A tenant with at least one portal user in the database

### Installation

```bash
# Install dependencies
npm install

# Copy environment variables
cp .env.example .env

# Start development server
npm run dev
```

The Portal UI will be available at `http://localhost:5173` (or the next available port).

### Environment Variables

Create a `.env` file with:

```env
VITE_API_BASE_URL=http://localhost:5000
VITE_API_TIMEOUT=30000
VITE_ENVIRONMENT=development
```

## Authentication Flow

1. User enters email and password on `/login`
2. Portal calls `POST /api/portal/auth/login`
3. Backend validates credentials and returns JWT tokens + user info (including tenant)
4. User redirected to `/dashboard` showing tenant name and welcome message
5. Protected routes check authentication via `PortalAuthContext`

## Testing Login

Use one of the seeded portal users (check database or Central Dashboard).

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## Tech Stack

- React 19 + TypeScript
- React Router DOM
- Axios + TanStack Query
- shadcn/ui + Tailwind CSS
- Vite

## Phase 4 Status

### ✅ Completed (Phase 4.1)

- Portal login page
- Dashboard with tenant name and user info
- Authentication context
- Protected routes
- Logout functionality

### 🔜 Future Features

- Candidate management
- Job postings
- Interview scheduling
- User management (Tenant Admins)
- Reports and analytics

