"""Pydantic schemas for request/response validation."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr, field_validator


class TimestampedSchema(BaseModel):
    """Base schema with timestamps."""
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ErrorResponseSchema(BaseModel):
    """Schema for error responses."""
    
    error: str
    message: str
    status: int
    details: Optional[dict] = None


class HealthCheckSchema(BaseModel):
    """Schema for health check response."""
    
    status: str
    timestamp: datetime
    environment: str


class AppInfoSchema(BaseModel):
    """Schema for app info response."""
    
    name: str
    version: str
    environment: str
    debug: bool
    timestamp: datetime


# Import tenant management schemas
from app.schemas.subscription_plan_schema import (
    SubscriptionPlanCreateSchema,
    SubscriptionPlanUpdateSchema,
    SubscriptionPlanResponseSchema,
    SubscriptionPlanListResponseSchema,
    SubscriptionPlanUsageSchema,
)

from app.schemas.tenant_schema import (
    TenantCreateSchema,
    TenantUpdateSchema,
    TenantChangePlanSchema,
    TenantSuspendSchema,
    TenantFilterSchema,
    TenantResponseSchema,
    TenantListResponseSchema,
    TenantStatsSchema,
    TenantDeleteResponseSchema,
)

from app.schemas.portal_user_schema import (
    PortalUserCreateSchema,
    PortalUserUpdateSchema,
    PortalUserResetPasswordSchema,
    PortalUserResponseSchema,
    PortalUserListResponseSchema,
    PortalLoginSchema,
    PortalLoginResponseSchema,
)

from app.schemas.pm_admin_schema import (
    PMAdminUserCreateSchema,
    PMAdminUserUpdateSchema,
    PMAdminUserResponseSchema,
    PMAdminUserListResponseSchema,
    PMAdminLoginSchema,
    PMAdminLoginResponseSchema,
    ResetTenantAdminPasswordSchema,
)

from app.schemas.role_schema import (
    PermissionBase,
    PermissionResponse,
    PermissionListResponse,
    RoleBase,
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    RoleWithPermissions,
    RoleAssignPermissions,
    RoleListResponse,
)

from app.schemas.candidate_schema import (
    CandidateCreateSchema,
    CandidateUpdateSchema,
    CandidateFilterSchema,
    CandidateResponseSchema,
    CandidateListItemSchema,
    CandidateListResponseSchema,
    UploadResumeResponseSchema,
    ReparseResumeResponseSchema,
    CandidateStatsSchema,
    EducationSchema,
    WorkExperienceSchema,
)

from app.schemas.invitation_schema import (
    InvitationCreateSchema,
    InvitationResendSchema,
    InvitationSubmitSchema,
    InvitationReviewSchema,
    InvitationResponseSchema,
    InvitationDetailResponseSchema,
    InvitationListResponseSchema,
    InvitationAuditLogResponseSchema,
)

from app.schemas.document_schema import (
    DocumentUploadSchema,
    DocumentVerifySchema,
    DocumentResponseSchema,
    DocumentListResponseSchema,
    DocumentTypeConfigSchema,
    DocumentTypesConfigResponseSchema,
)
