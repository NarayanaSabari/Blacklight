# Role System Refactor Plan - Dynamic Roles Implementation

## 📋 Current State Analysis

### Current Implementation:
- **Hardcoded roles** in `portal_users` table as ENUM or string column
- Role values: `TENANT_ADMIN`, `RECRUITER`, `HIRING_MANAGER`
- No flexibility to add new roles without schema migration
- No role-based permissions management
- Limited scalability for future role types

### Problems with Current Approach:
1. ❌ Cannot add new roles dynamically
2. ❌ Cannot customize role permissions per tenant
3. ❌ No granular permission control
4. ❌ Role changes require database schema changes
5. ❌ Cannot track role metadata (description, permissions, etc.)

---

## 🎯 Proposed Solution: Dynamic Role System

### New Database Schema:

#### 1. `roles` Table (Master Role Definitions)
```sql
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,              -- e.g., 'TENANT_ADMIN', 'RECRUITER', 'HIRING_MANAGER'
    display_name VARCHAR(100) NOT NULL,            -- e.g., 'Tenant Administrator', 'Recruiter'
    description TEXT,                              -- Role description
    is_system_role BOOLEAN DEFAULT FALSE,          -- Cannot be deleted if true
    is_active BOOLEAN DEFAULT TRUE,                -- Can be disabled without deletion
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for faster lookups
CREATE INDEX idx_roles_name ON roles(name);
CREATE INDEX idx_roles_is_active ON roles(is_active);
```

**Initial Seed Data:**
```sql
INSERT INTO roles (name, display_name, description, is_system_role, is_active) VALUES
('TENANT_ADMIN', 'Tenant Administrator', 'Full access to tenant settings, users, and all recruitment features', TRUE, TRUE),
('RECRUITER', 'Recruiter', 'Manage candidates, jobs, interviews, and client communications', TRUE, TRUE),
('HIRING_MANAGER', 'Hiring Manager', 'View candidates and jobs, participate in interviews, limited editing', TRUE, TRUE);
```

#### 2. `permissions` Table (Optional - For Future RBAC)
```sql
CREATE TABLE permissions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,             -- e.g., 'candidates.create', 'jobs.delete'
    display_name VARCHAR(150) NOT NULL,            -- e.g., 'Create Candidates', 'Delete Jobs'
    category VARCHAR(50),                          -- e.g., 'candidates', 'jobs', 'settings'
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_permissions_category ON permissions(category);
```

**Permission Categories:**
- `candidates.*` - Candidate management permissions
- `jobs.*` - Job posting permissions
- `interviews.*` - Interview scheduling permissions
- `clients.*` - Client communication permissions
- `users.*` - User management permissions (tenant admins only)
- `settings.*` - Tenant settings permissions
- `reports.*` - Reports and analytics permissions

**Sample Permissions:**
```sql
INSERT INTO permissions (name, display_name, category, description) VALUES
-- Candidate permissions
('candidates.view', 'View Candidates', 'candidates', 'View candidate list and details'),
('candidates.create', 'Create Candidates', 'candidates', 'Add new candidates'),
('candidates.edit', 'Edit Candidates', 'candidates', 'Update candidate information'),
('candidates.delete', 'Delete Candidates', 'candidates', 'Remove candidates'),

-- Job permissions
('jobs.view', 'View Jobs', 'jobs', 'View job postings'),
('jobs.create', 'Create Jobs', 'jobs', 'Create new job postings'),
('jobs.edit', 'Edit Jobs', 'jobs', 'Update job postings'),
('jobs.delete', 'Delete Jobs', 'jobs', 'Remove job postings'),

-- User management permissions
('users.view', 'View Users', 'users', 'View portal users'),
('users.create', 'Create Users', 'users', 'Add new portal users'),
('users.edit', 'Edit Users', 'users', 'Update user information'),
('users.delete', 'Delete Users', 'users', 'Remove users'),
('users.manage_roles', 'Manage User Roles', 'users', 'Assign/change user roles'),

-- Settings permissions
('settings.view', 'View Settings', 'settings', 'View tenant settings'),
('settings.edit', 'Edit Settings', 'settings', 'Update tenant settings'),

-- Reports permissions
('reports.view', 'View Reports', 'reports', 'Access reports and analytics'),
('reports.export', 'Export Reports', 'reports', 'Export report data');
```

#### 3. `role_permissions` Table (Many-to-Many)
```sql
CREATE TABLE role_permissions (
    id SERIAL PRIMARY KEY,
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(role_id, permission_id)
);

CREATE INDEX idx_role_permissions_role_id ON role_permissions(role_id);
CREATE INDEX idx_role_permissions_permission_id ON role_permissions(permission_id);
```

**Initial Role-Permission Mappings:**
```sql
-- TENANT_ADMIN: All permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN permissions p
WHERE r.name = 'TENANT_ADMIN';

-- RECRUITER: Most permissions except user management and settings
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN permissions p
WHERE r.name = 'RECRUITER'
  AND p.category IN ('candidates', 'jobs', 'interviews', 'clients', 'reports');

-- HIRING_MANAGER: View and limited edit permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN permissions p
WHERE r.name = 'HIRING_MANAGER'
  AND p.name IN (
    'candidates.view', 
    'jobs.view', 
    'interviews.view', 
    'reports.view'
  );
```

#### 4. Update `portal_users` Table
```sql
-- Add foreign key to roles table
ALTER TABLE portal_users 
ADD COLUMN role_id INTEGER REFERENCES roles(id) ON DELETE RESTRICT;

-- Migrate existing data
UPDATE portal_users pu
SET role_id = r.id
FROM roles r
WHERE r.name = pu.role;  -- Assuming current column is named 'role'

-- Make role_id NOT NULL after migration
ALTER TABLE portal_users ALTER COLUMN role_id SET NOT NULL;

-- Drop old role column (after migration is verified)
-- ALTER TABLE portal_users DROP COLUMN role;

-- Create index for faster lookups
CREATE INDEX idx_portal_users_role_id ON portal_users(role_id);
```

---

## 🔄 Migration Strategy

### Step 1: Create New Tables
```sql
-- migrations/versions/YYYYMMDD_HHMMSS_create_roles_system.py
"""Create dynamic roles system

Revision ID: xxxxx
Revises: yyyyy
Create Date: 2025-10-25
"""

def upgrade():
    # Create roles table
    op.create_table(
        'roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('display_name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_system_role', sa.Boolean(), default=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Create permissions table
    op.create_table(
        'permissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('display_name', sa.String(150), nullable=False),
        sa.Column('category', sa.String(50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Create role_permissions junction table
    op.create_table(
        'role_permissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('permission_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('role_id', 'permission_id')
    )
    
    # Create indexes
    op.create_index('idx_roles_name', 'roles', ['name'])
    op.create_index('idx_roles_is_active', 'roles', ['is_active'])
    op.create_index('idx_permissions_category', 'permissions', ['category'])
    op.create_index('idx_role_permissions_role_id', 'role_permissions', ['role_id'])
    op.create_index('idx_role_permissions_permission_id', 'role_permissions', ['permission_id'])


def downgrade():
    op.drop_table('role_permissions')
    op.drop_table('permissions')
    op.drop_table('roles')
```

### Step 2: Seed Initial Data
```sql
-- migrations/versions/YYYYMMDD_HHMMSS_seed_roles_and_permissions.py
"""Seed roles and permissions

Revision ID: xxxxx
Revises: yyyyy
Create Date: 2025-10-25
"""

def upgrade():
    # Insert roles
    op.execute("""
        INSERT INTO roles (name, display_name, description, is_system_role, is_active) VALUES
        ('TENANT_ADMIN', 'Tenant Administrator', 'Full access to tenant settings, users, and all recruitment features', TRUE, TRUE),
        ('RECRUITER', 'Recruiter', 'Manage candidates, jobs, interviews, and client communications', TRUE, TRUE),
        ('HIRING_MANAGER', 'Hiring Manager', 'View candidates and jobs, participate in interviews, limited editing', TRUE, TRUE)
    """)
    
    # Insert permissions (see detailed list above)
    # Insert role_permissions mappings
    
def downgrade():
    op.execute("DELETE FROM role_permissions")
    op.execute("DELETE FROM permissions")
    op.execute("DELETE FROM roles")
```

### Step 3: Migrate Portal Users
```sql
-- migrations/versions/YYYYMMDD_HHMMSS_migrate_portal_users_to_roles.py
"""Migrate portal_users to use role_id

Revision ID: xxxxx
Revises: yyyyy
Create Date: 2025-10-25
"""

def upgrade():
    # Add role_id column
    op.add_column('portal_users', sa.Column('role_id', sa.Integer(), nullable=True))
    
    # Migrate existing data
    op.execute("""
        UPDATE portal_users pu
        SET role_id = r.id
        FROM roles r
        WHERE r.name = pu.role
    """)
    
    # Make role_id NOT NULL
    op.alter_column('portal_users', 'role_id', nullable=False)
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_portal_users_role_id',
        'portal_users',
        'roles',
        ['role_id'],
        ['id'],
        ondelete='RESTRICT'
    )
    
    # Create index
    op.create_index('idx_portal_users_role_id', 'portal_users', ['role_id'])
    
    # Drop old role column (commented out for safety)
    # op.drop_column('portal_users', 'role')

def downgrade():
    # Restore role column if needed
    op.drop_constraint('fk_portal_users_role_id', 'portal_users')
    op.drop_index('idx_portal_users_role_id', 'portal_users')
    op.drop_column('portal_users', 'role_id')
```

---

## 📦 Backend Implementation

### 1. Models (`server/app/models/`)

**`role.py`:**
```python
from app import db
from app.models.base import BaseModel

class Role(BaseModel):
    __tablename__ = 'roles'
    
    name = db.Column(db.String(50), unique=True, nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    is_system_role = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    users = db.relationship('PortalUser', back_populates='role', lazy='dynamic')
    permissions = db.relationship('Permission', secondary='role_permissions', back_populates='roles')
    
    def __repr__(self):
        return f'<Role {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'is_system_role': self.is_system_role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
```

**`permission.py`:**
```python
from app import db
from app.models.base import BaseModel

class Permission(BaseModel):
    __tablename__ = 'permissions'
    
    name = db.Column(db.String(100), unique=True, nullable=False)
    display_name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(50))
    description = db.Column(db.Text)
    
    # Relationships
    roles = db.relationship('Role', secondary='role_permissions', back_populates='permissions')
    
    def __repr__(self):
        return f'<Permission {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'category': self.category,
            'description': self.description
        }
```

**`role_permission.py`:**
```python
from app import db

role_permissions = db.Table(
    'role_permissions',
    db.Column('id', db.Integer, primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id', ondelete='CASCADE'), nullable=False),
    db.Column('permission_id', db.Integer, db.ForeignKey('permissions.id', ondelete='CASCADE'), nullable=False),
    db.Column('created_at', db.DateTime, server_default=db.func.current_timestamp()),
    db.UniqueConstraint('role_id', 'permission_id', name='uq_role_permission')
)
```

**Update `portal_user.py`:**
```python
class PortalUser(BaseModel):
    __tablename__ = 'portal_users'
    
    # ... existing columns ...
    
    # Replace role string with foreign key
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id', ondelete='RESTRICT'), nullable=False)
    
    # Relationships
    role = db.relationship('Role', back_populates='users')
    tenant = db.relationship('Tenant', back_populates='users')
    
    def to_dict(self):
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'phone': self.phone,
            'role': self.role.to_dict() if self.role else None,  # Include full role object
            'tenant_id': self.tenant_id,
            'is_active': self.is_active,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
```

### 2. Schemas (`server/app/schemas/`)

**`role_schema.py`:**
```python
from pydantic import BaseModel, Field
from typing import Optional, List

class RoleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    display_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    is_active: bool = True

class RoleCreate(RoleBase):
    pass

class RoleUpdate(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None

class RoleResponse(RoleBase):
    id: int
    is_system_role: bool
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True

class RoleWithPermissions(RoleResponse):
    permissions: List['PermissionResponse'] = []
```

**`permission_schema.py`:**
```python
from pydantic import BaseModel, Field
from typing import Optional

class PermissionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=150)
    category: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None

class PermissionResponse(PermissionBase):
    id: int
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True
```

### 3. Services (`server/app/services/`)

**`role_service.py`:**
```python
from app import db
from app.models import Role, Permission
from typing import List, Optional

class RoleService:
    @staticmethod
    def get_all_roles(include_inactive: bool = False) -> List[Role]:
        """Get all roles"""
        query = db.session.query(Role)
        if not include_inactive:
            query = query.filter(Role.is_active == True)
        return query.all()
    
    @staticmethod
    def get_role_by_id(role_id: int) -> Optional[Role]:
        """Get role by ID"""
        return db.session.get(Role, role_id)
    
    @staticmethod
    def get_role_by_name(name: str) -> Optional[Role]:
        """Get role by name"""
        return db.session.query(Role).filter(Role.name == name).first()
    
    @staticmethod
    def create_role(name: str, display_name: str, description: str = None) -> Role:
        """Create a new role"""
        role = Role(
            name=name,
            display_name=display_name,
            description=description,
            is_system_role=False
        )
        db.session.add(role)
        db.session.commit()
        return role
    
    @staticmethod
    def update_role(role_id: int, **kwargs) -> Role:
        """Update role"""
        role = RoleService.get_role_by_id(role_id)
        if not role:
            raise ValueError(f"Role with ID {role_id} not found")
        
        if role.is_system_role:
            # Only allow updating display_name and description for system roles
            allowed_fields = ['display_name', 'description']
            kwargs = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        for key, value in kwargs.items():
            setattr(role, key, value)
        
        db.session.commit()
        return role
    
    @staticmethod
    def delete_role(role_id: int) -> bool:
        """Delete role (only custom roles)"""
        role = RoleService.get_role_by_id(role_id)
        if not role:
            raise ValueError(f"Role with ID {role_id} not found")
        
        if role.is_system_role:
            raise ValueError("Cannot delete system roles")
        
        if role.users.count() > 0:
            raise ValueError("Cannot delete role with assigned users")
        
        db.session.delete(role)
        db.session.commit()
        return True
    
    @staticmethod
    def assign_permissions_to_role(role_id: int, permission_ids: List[int]) -> Role:
        """Assign permissions to a role"""
        role = RoleService.get_role_by_id(role_id)
        if not role:
            raise ValueError(f"Role with ID {role_id} not found")
        
        permissions = db.session.query(Permission).filter(Permission.id.in_(permission_ids)).all()
        role.permissions = permissions
        db.session.commit()
        return role
    
    @staticmethod
    def get_role_permissions(role_id: int) -> List[Permission]:
        """Get all permissions for a role"""
        role = RoleService.get_role_by_id(role_id)
        if not role:
            raise ValueError(f"Role with ID {role_id} not found")
        return role.permissions
```

### 4. API Routes (`server/app/routes/`)

**`roles.py`:**
```python
from flask import Blueprint, jsonify, request
from app.services import RoleService
from app.schemas import RoleResponse, RoleCreate, RoleUpdate
from app.utils.decorators import require_auth  # Your auth decorator

bp = Blueprint('roles', __name__, url_prefix='/api/roles')

@bp.route('', methods=['GET'])
@require_auth
def get_roles():
    """Get all roles"""
    include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'
    roles = RoleService.get_all_roles(include_inactive=include_inactive)
    return jsonify({
        'roles': [RoleResponse.model_validate(role).model_dump() for role in roles]
    }), 200

@bp.route('/<int:role_id>', methods=['GET'])
@require_auth
def get_role(role_id):
    """Get role by ID"""
    role = RoleService.get_role_by_id(role_id)
    if not role:
        return jsonify({'error': 'Role not found'}), 404
    return jsonify(RoleResponse.model_validate(role).model_dump()), 200

@bp.route('', methods=['POST'])
@require_auth  # Add PM Admin only decorator
def create_role():
    """Create new role (PM Admin only)"""
    data = RoleCreate.model_validate(request.get_json())
    role = RoleService.create_role(
        name=data.name,
        display_name=data.display_name,
        description=data.description
    )
    return jsonify(RoleResponse.model_validate(role).model_dump()), 201

@bp.route('/<int:role_id>/permissions', methods=['GET'])
@require_auth
def get_role_permissions(role_id):
    """Get permissions for a role"""
    permissions = RoleService.get_role_permissions(role_id)
    return jsonify({
        'permissions': [p.to_dict() for p in permissions]
    }), 200
```

---

## 🔐 Authorization Middleware (Future Enhancement)

```python
# server/app/utils/decorators.py

from functools import wraps
from flask import request, jsonify
from app.services import RoleService

def require_permission(permission_name: str):
    """Decorator to check if user has specific permission"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get current user from JWT or session
            current_user = get_current_user()  # Your auth implementation
            
            if not current_user or not current_user.role:
                return jsonify({'error': 'Unauthorized'}), 401
            
            # Check if user's role has the required permission
            permissions = RoleService.get_role_permissions(current_user.role_id)
            permission_names = [p.name for p in permissions]
            
            if permission_name not in permission_names:
                return jsonify({'error': 'Forbidden - Insufficient permissions'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Usage:
# @require_permission('candidates.delete')
# def delete_candidate(candidate_id):
#     ...
```

---

## 📱 Frontend Updates

### 1. Update Types (`ui/centralD/src/types/`)

**`role.ts`:**
```typescript
export interface Role {
  id: number;
  name: string;
  display_name: string;
  description: string | null;
  is_system_role: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Permission {
  id: number;
  name: string;
  display_name: string;
  category: string | null;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface RoleWithPermissions extends Role {
  permissions: Permission[];
}
```

**Update `portal-user.ts`:**
```typescript
import type { Role } from './role';

export interface PortalUser {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  phone: string | null;
  role: Role;  // Changed from role: string
  tenant_id: number;
  is_active: boolean;
  last_login: string | null;
  created_at: string;
  updated_at: string;
}
```

### 2. Update Components

**TenantUsersTable:**
```typescript
// Change from:
<Badge>{user.role}</Badge>

// To:
<Badge>{user.role.display_name}</Badge>
```

**ResetPasswordDialog:**
```typescript
// Update condition from:
{user.role === 'TENANT_ADMIN' && ...}

// To:
{user.role.name === 'TENANT_ADMIN' && ...}
```

### 3. Add Role Management Page (Future)
- List all roles
- Create custom roles
- Edit role permissions
- Assign permissions to roles

---

## ✅ Benefits of This Approach

1. ✅ **Flexibility**: Add new roles without schema changes
2. ✅ **Scalability**: Fine-grained permission control
3. ✅ **Multi-tenancy Ready**: Can add tenant-specific custom roles in future
4. ✅ **Maintainability**: Centralized role and permission management
5. ✅ **Audit Trail**: Track role and permission changes
6. ✅ **Security**: Role-based access control (RBAC) foundation
7. ✅ **Future-proof**: Easy to extend with more permissions

---

## 🚀 Implementation Timeline

### Phase 1: Database Migration (1-2 hours)
- Create roles, permissions, role_permissions tables
- Seed initial data
- Migrate portal_users table

### Phase 2: Backend Implementation (2-3 hours)
- Create models (Role, Permission)
- Create services (RoleService, PermissionService)
- Create schemas (RoleSchema, PermissionSchema)
- Create API routes

### Phase 3: Frontend Updates (1-2 hours)
- Update types
- Update existing components
- Test all role-related features

### Phase 4: Testing (1 hour)
- Unit tests for role services
- Integration tests for API
- Frontend component tests

**Total Estimated Time: 5-8 hours**

---

## 🧪 Testing Strategy

### 1. Database Tests
- Verify foreign key constraints
- Test cascade deletes
- Verify unique constraints

### 2. Backend Tests
```python
def test_create_role():
    role = RoleService.create_role('CUSTOM_ROLE', 'Custom Role', 'Description')
    assert role.name == 'CUSTOM_ROLE'
    assert role.is_system_role == False

def test_cannot_delete_system_role():
    with pytest.raises(ValueError):
        RoleService.delete_role(1)  # TENANT_ADMIN

def test_assign_permissions_to_role():
    role = RoleService.get_role_by_name('RECRUITER')
    permissions = [1, 2, 3]  # Some permission IDs
    updated_role = RoleService.assign_permissions_to_role(role.id, permissions)
    assert len(updated_role.permissions) == 3
```

### 3. Frontend Tests
- Test role display in TenantUsersTable
- Test role filtering
- Test role badge rendering

---

## 📝 Migration Rollback Plan

If migration fails:
1. Rollback database migrations in reverse order
2. Restore `role` column in `portal_users` table
3. No data loss (old role column can be kept during transition)

---

## 🎯 Next Steps After Implementation

1. **Add Role Management UI** (Central Dashboard)
   - Create/Edit/Delete custom roles
   - Assign permissions to roles
   - View role-permission matrix

2. **Implement Permission Checking**
   - Add `@require_permission` decorators to routes
   - Frontend permission checking
   - Hide UI elements based on permissions

3. **Tenant-Specific Roles** (Future)
   - Allow tenants to create custom roles
   - Tenant-specific permission overrides
   - Role templates

---

## ✅ APPROVED DECISIONS

1. ✅ **Full RBAC with permissions table NOW**
   - Implement roles, permissions, and role_permissions tables
   - Complete permission-based access control system

2. ✅ **Remove old hardcoded role column**
   - Drop the old role column after migration
   - Clean transition to role_id foreign key

3. ✅ **Build Role Management UI in Central Dashboard**
   - Create/Edit/Delete roles
   - Assign permissions to roles
   - Visual permission matrix

4. ✅ **Allow tenants to create custom roles**
   - Add tenant_id to roles table (nullable)
   - System roles (tenant_id = NULL) for default roles
   - Tenant-specific custom roles (tenant_id = tenant.id)
   - Tenants can only manage their own custom roles

---

## 🔄 Updated Schema for Tenant-Specific Roles

### Modified `roles` Table:
```sql
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,  -- NULL for system roles
    name VARCHAR(50) NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    is_system_role BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, name),  -- Unique per tenant, or globally if tenant_id is NULL
    CHECK (
        (is_system_role = TRUE AND tenant_id IS NULL) OR
        (is_system_role = FALSE)
    )
);

CREATE INDEX idx_roles_tenant_id ON roles(tenant_id);
CREATE INDEX idx_roles_name ON roles(name);
CREATE INDEX idx_roles_is_active ON roles(is_active);
```

---

**READY TO IMPLEMENT! �**
