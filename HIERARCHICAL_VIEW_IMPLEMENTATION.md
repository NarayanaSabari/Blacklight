# Hierarchical "Your Candidates" Implementation Summary

## Overview
Implemented a complete drill-down hierarchical view for team candidate visibility, replacing the previous flat "Your Candidates" page with a 2-column Kanban-style interface.

## Changes Made

### 1. Frontend Component (NEW)
**File**: `ui/portal/src/pages/YourCandidatesPageNew.tsx` (380 lines)

**Features**:
- **2-Column Kanban Layout**: Team members (left) | Candidates (right)
- **Drill-Down Navigation**: Click manager → View their team (replaces left column)
- **Breadcrumb Navigation**: Shows navigation path with back button
- **Search Functionality**: Filter team members by name
- **Visual Hierarchy**: Cards with role badges, candidate counts, team member counts
- **State Management**: Navigation stack for drill-down tracking

**Key State**:
```typescript
const [navigationStack, setNavigationStack] = useState<TeamMember[]>([]);
const [selectedMemberId, setSelectedMemberId] = useState<number | null>(null);
const currentContextId = navigationStack.length > 0 
  ? navigationStack[navigationStack.length - 1].id 
  : null;
```

**API Calls**:
- `GET /api/team/my-team-members` - Get logged-in user's direct reports
- `GET /api/team/{member_id}/team-members` - Get specific member's team (for drill-down)
- `GET /api/team/members/{member_id}/candidates` - Get member's candidates

### 2. Backend Routes (UPDATED)
**File**: `server/app/routes/team_routes.py`

**New Route 1**: `GET /api/team/my-team-members`
- Returns current user's direct reports with enriched data
- Includes: candidate_count, team_member_count, has_team_members flags
- Permissions: `candidates.view_assigned`

**New Route 2**: `GET /api/team/members/<int:member_id>/candidates`
- Returns candidates assigned to specific team member
- Authorization: Verifies hierarchical access via `_is_in_hierarchy`
- Permissions: `candidates.view_assigned`

**New Route 3**: `GET /api/team/<int:member_id>/team-members`
- Returns specific member's direct reports (for drill-down)
- Authorization: Verifies hierarchical access via `_is_in_hierarchy`
- Permissions: `candidates.view_assigned`

### 3. Service Layer (UPDATED)
**File**: `server/app/services/team_management_service.py`

**Method 1**: `get_hierarchical_team_members(user_id, tenant_id)`
- Fetches direct reports for specified user
- Enriches with candidate counts (via manager_id OR recruiter_id)
- Enriches with team member counts (direct reports count)
- Returns detailed team member objects

**Method 2**: `get_team_member_candidates(member_id, requester_id, tenant_id)`
- Fetches candidates for specific team member
- Security: Calls `_is_in_hierarchy` for authorization
- Returns candidate dictionaries with assignment info

**Method 3**: `_is_in_hierarchy(manager_id, subordinate_id, tenant_id)`
- Walks up management chain (max 10 levels)
- Verifies hierarchical access permissions
- Returns True if manager is above subordinate in org chart

### 4. Routing Updates
**File**: `ui/portal/src/App.tsx`
- Updated import: `YourCandidatesPage` → `YourCandidatesPageNew`
- Updated route: `/your-candidates` now uses new component

**File**: `ui/portal/src/pages/index.ts`
- Added export for `YourCandidatesPageNew`
- Kept old `YourCandidatesPage` export for reference

## How It Works

### Navigation Flow

**Initial State**:
```
Column 1: Current user's direct reports
Column 2: "Select a team member to view their candidates"
```

**Click Team Member (Manager with team)**:
```
Column 1: [← Back to {parent}] + Manager's team members
Column 2: Still "Select a team member..."
navigationStack: [clicked_manager]
```

**Click Team Member (Recruiter or Manager without team)**:
```
Column 1: Same (current context's team)
Column 2: Selected member's candidates displayed
selectedMemberId: member_id
```

**Click Back Button**:
```
Pops from navigationStack
Returns to previous level
Clears selectedMemberId
```

### Role-Based Entry Points

**TENANT_ADMIN**:
- Entry: Should see HR-level users (not implemented yet - see TODO)
- Can drill down through entire org hierarchy

**HIRING_MANAGER (HR)**:
- Entry: Sees their managers and recruiters
- Can drill down to managers' teams, then to recruiters

**MANAGER**:
- Entry: Sees their assigned recruiters
- Can view recruiters' candidates

**RECRUITER**:
- Entry: Sees only their assigned candidates
- No drill-down (no team members to show)

### Authorization Logic

**Hierarchical Access Check** (`_is_in_hierarchy`):
```python
# Walks up subordinate's manager chain
# Returns True if requester_id found in chain
# Max 10 levels to prevent infinite loops
```

**Permission Requirements**:
- All routes require: `candidates.view_assigned`
- Additional check: Hierarchical relationship via `_is_in_hierarchy`

## Testing Guide

### 1. Test Drill-Down Navigation
```bash
# As HR (HIRING_MANAGER role)
1. Login to portal
2. Navigate to "Your Candidates"
3. Verify you see your managers and recruiters in Column 1
4. Click on a manager who has team members
5. Verify Column 1 updates to show manager's team
6. Verify breadcrumb shows: "You > Manager Name"
7. Click on a recruiter under that manager
8. Verify Column 2 shows recruiter's candidates
9. Click back button
10. Verify you return to previous level
```

### 2. Test Authorization
```bash
# Test hierarchical access control
1. Try accessing /api/team/123/team-members (not in your hierarchy)
2. Should receive 403 Forbidden
3. Try accessing /api/team/members/123/candidates (not in your hierarchy)
4. Should receive 403 Forbidden
```

### 3. Test Edge Cases
```bash
# No team members
1. Login as recruiter (no direct reports)
2. Should see message: "You don't have any team members"

# No candidates
1. Click team member with no candidates
2. Should see: "This team member has no assigned candidates"

# Search functionality
1. Type in search box
2. Verify team members filter in real-time
```

### 4. Test Different Roles

**As TENANT_ADMIN**:
- TODO: Should see HR-level entry point

**As HIRING_MANAGER**:
- Should see all managers and recruiters
- Can drill down to any level

**As MANAGER**:
- Should see only their assigned recruiters
- Can view recruiter's candidates

**As RECRUITER**:
- Should see only their candidates
- No Column 1 (no team members)

## Database Setup

The feature uses existing tables and permissions:
- `portal_users` table with `manager_id` foreign key
- `candidates` table with `manager_id` and `recruiter_id`
- `roles` and `permissions` tables for RBAC

**Required Permission**: `candidates.view_assigned`
- Already assigned to: HIRING_MANAGER, MANAGER, RECRUITER

## API Response Examples

**GET /api/team/my-team-members**:
```json
{
  "team_members": [
    {
      "id": 5,
      "full_name": "Demo Manager",
      "email": "manager@example.com",
      "role_name": "MANAGER",
      "candidate_count": 8,
      "team_member_count": 3,
      "has_team_members": true
    },
    {
      "id": 6,
      "full_name": "Demo Recruiter",
      "email": "recruiter@example.com",
      "role_name": "RECRUITER",
      "candidate_count": 5,
      "team_member_count": 0,
      "has_team_members": false
    }
  ],
  "total": 2
}
```

**GET /api/team/members/6/candidates**:
```json
{
  "candidates": [
    {
      "id": 17,
      "first_name": "John",
      "last_name": "Doe",
      "email": "john.doe@example.com",
      "phone": "+1234567890",
      "onboarding_status": "ASSIGNED",
      "current_assignment": {
        "id": 42,
        "assigned_at": "2024-01-15T10:30:00Z",
        "status": "ACTIVE"
      }
    }
  ],
  "total": 1,
  "member_id": 6
}
```

## TODO / Future Enhancements

### High Priority
1. **Role-Based Entry Point for TENANT_ADMIN**
   - Detect TENANT_ADMIN role on component mount
   - Auto-navigate to HR-level view
   - Show all HR users as starting point

2. **Loading States**
   - Add skeleton loaders for better UX
   - Show loading spinner during drill-down navigation

3. **Error Handling**
   - Add error boundaries
   - Show user-friendly error messages
   - Add retry logic for failed API calls

### Medium Priority
4. **Stats Dashboard**
   - Add summary cards at top
   - Show total team members, total candidates
   - Break down by role and status

5. **Candidate Actions**
   - Add quick actions: View details, Reassign, Message
   - Bulk actions for multiple candidates

6. **Export Functionality**
   - Export team hierarchy as CSV/Excel
   - Export candidate lists

### Low Priority
7. **Visual Enhancements**
   - Add org chart visualization option
   - Add avatars for team members
   - Add activity timeline

8. **Search & Filters**
   - Add candidate search within Column 2
   - Add filters: status, skills, experience
   - Add sorting options

9. **Performance Optimization**
   - Add pagination for large teams
   - Implement virtual scrolling
   - Cache hierarchical data

## File Structure
```
ui/portal/src/
├── pages/
│   ├── YourCandidatesPage.tsx (OLD - kept for reference)
│   └── YourCandidatesPageNew.tsx (NEW - active implementation)
│
server/app/
├── routes/
│   └── team_routes.py (3 new routes added)
├── services/
│   └── team_management_service.py (3 new methods added)
└── models/ (no changes - uses existing models)
```

## Rollback Plan
If issues arise, revert to old component:
```typescript
// In ui/portal/src/App.tsx
import { ManageTeamPage, YourCandidatesPage, CandidateManagementPage } from '@/pages';

// In route
<Route path="/your-candidates" element={<YourCandidatesPage />} />
```

## Notes
- All TypeScript errors have been fixed
- Backend routes are fully implemented with authorization
- Drill-down navigation properly refetches data for selected member
- Old component (`YourCandidatesPage.tsx`) retained for reference
- No database migrations required (uses existing schema)
