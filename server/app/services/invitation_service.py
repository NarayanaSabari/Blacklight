"""
Invitation Service
Business logic for managing candidate invitations
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import joinedload

from app import db
from app.models.candidate_invitation import CandidateInvitation
from app.models.invitation_audit_log import InvitationAuditLog
from app.models.candidate import Candidate
from app.models.candidate_document import CandidateDocument
from app.models.tenant import Tenant
from app.models.portal_user import PortalUser
from app.services.email_service import EmailService
from config.settings import Settings

logger = logging.getLogger(__name__)
settings = Settings()


class InvitationService:
    """Service for managing candidate invitations"""
    
    @staticmethod
    def create_invitation(
        tenant_id: int,
        email: str,
        invited_by_id: int,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        expiry_hours: Optional[int] = None
    ) -> CandidateInvitation:
        """
        Create a new candidate invitation.
        
        Args:
            tenant_id: ID of the tenant
            email: Candidate's email address
            invited_by_id: ID of the portal user sending the invitation
            first_name: Optional first name
            last_name: Optional last name
            expiry_hours: Hours until invitation expires (default: from settings or 168=7 days)
            
        Returns:
            CandidateInvitation: Created invitation
            
        Raises:
            ValueError: If validation fails
        """
        # Validate email format
        email = email.lower().strip()
        if not email or '@' not in email:
            raise ValueError("Invalid email address")
        
        # Check for existing invitations
        duplicate = InvitationService.check_duplicate(tenant_id, email)
        
        # If there's an active invitation, reject
        if duplicate and duplicate.status in ['sent', 'opened', 'in_progress', 'submitted']:
            raise ValueError(f"Invitation already exists with status: {duplicate.status}. Use resend instead.")
        
        # Calculate expiry
        if expiry_hours is None:
            expiry_hours = getattr(settings, 'INVITATION_EXPIRY_HOURS', 168)  # Default 7 days
        expires_at = datetime.utcnow() + timedelta(hours=expiry_hours)
        
        # If there's a cancelled, expired, rejected, or approved invitation, reuse it
        is_reused = False
        if duplicate and duplicate.status in ['cancelled', 'expired', 'rejected', 'approved']:
            logger.info(f"Reusing existing invitation {duplicate.id} (status: {duplicate.status}) for {email}")
            
            old_status = duplicate.status
            # Reset invitation to 'sent' state
            invitation = duplicate
            invitation.first_name = first_name
            invitation.last_name = last_name
            invitation.token = CandidateInvitation.generate_token()  # Generate new token
            invitation.expires_at = expires_at
            invitation.status = 'sent'
            invitation.invited_by_id = invited_by_id
            invitation.invited_at = datetime.utcnow()
            invitation.updated_at = datetime.utcnow()
            is_reused = True
        else:
            # Create new invitation
            token = CandidateInvitation.generate_token()
            
            invitation = CandidateInvitation(
                tenant_id=tenant_id,
                email=email,
                first_name=first_name,
                last_name=last_name,
                token=token,
                expires_at=expires_at,
                status='sent',
                invited_by_id=invited_by_id,
                invited_at=datetime.utcnow()
            )
            
            db.session.add(invitation)
        db.session.flush()  # Get the ID without committing
        
        # Log the action
        InvitationAuditLog.log_action(
            invitation_id=invitation.id,
            action='invitation_resent' if is_reused else 'invitation_sent',
            performed_by=f'portal_user:{invited_by_id}',
            extra_data={
                'email': email, 
                'expiry_hours': expiry_hours,
                'reused': is_reused,
                'previous_status': old_status if is_reused else None
            }
        )
        
        db.session.commit()
        
        logger.info(f"Created invitation {invitation.id} for {email} in tenant {tenant_id}")
        
        # Send invitation email via Inngest (async/non-blocking)
        try:
            from app.inngest import inngest_client
            import inngest
            
            logger.info(f"[INNGEST] Attempting to send event 'email/invitation' for invitation {invitation.id}")
            
            event_result = inngest_client.send_sync(
                inngest.Event(
                    name="email/invitation",
                    data={
                        "invitation_id": invitation.id,
                        "tenant_id": tenant_id
                    }
                )
            )
            
            logger.info(f"[INNGEST] ✅ Event sent successfully for {email}. Result: {event_result}")
        except ImportError:
            # Fallback to synchronous email if Inngest not available
            logger.warning("Inngest not available, sending email synchronously")
            try:
                candidate_name = f"{first_name} {last_name}".strip() if first_name else None
                onboarding_url = f"{settings.frontend_base_url}/onboard/{token}"
                expiry_date = expires_at.strftime("%B %d, %Y at %I:%M %p UTC")
                
                EmailService.send_invitation_email(
                    tenant_id=tenant_id,
                    to_email=email,
                    candidate_name=candidate_name,
                    onboarding_url=onboarding_url,
                    expiry_date=expiry_date
                )
                logger.info(f"Sent invitation email to {email} (sync fallback)")
            except Exception as email_error:
                logger.error(f"Failed to send invitation email: {email_error}")
        except Exception as e:
            logger.error(f"Failed to send Inngest event: {e}")
        
        return invitation
    
    @staticmethod
    def get_by_id(invitation_id: int, tenant_id: Optional[int] = None) -> Optional[CandidateInvitation]:
        """
        Get invitation by ID with optional tenant check.
        
        Args:
            invitation_id: Invitation ID
            tenant_id: Optional tenant ID for isolation check
            
        Returns:
            CandidateInvitation or None
        """
        query = select(CandidateInvitation).where(CandidateInvitation.id == invitation_id)
        
        if tenant_id:
            query = query.where(CandidateInvitation.tenant_id == tenant_id)
        
        invitation = db.session.execute(query).scalar_one_or_none()
        return invitation
    
    @staticmethod
    def get_by_token(token: str) -> Optional[CandidateInvitation]:
        """
        Get invitation by token.
        
        Args:
            token: Invitation token
            
        Returns:
            CandidateInvitation or None
        """
        query = select(CandidateInvitation).where(CandidateInvitation.token == token)
        invitation = db.session.execute(query).scalar_one_or_none()
        return invitation
    
    @staticmethod
    def check_duplicate(tenant_id: int, email: str) -> Optional[CandidateInvitation]:
        """
        Check for existing invitation with this email.
        
        Args:
            tenant_id: Tenant ID
            email: Email address
            
        Returns:
            Most recent CandidateInvitation or None
        """
        query = (
            select(CandidateInvitation)
            .where(
                and_(
                    CandidateInvitation.tenant_id == tenant_id,
                    CandidateInvitation.email == email.lower().strip()
                )
            )
            .order_by(CandidateInvitation.created_at.desc())
        )
        
        invitation = db.session.execute(query).scalar_one_or_none()
        return invitation
    
    @staticmethod
    def resend_invitation(
        invitation_id: int,
        resent_by_id: int,
        expiry_hours: Optional[int] = None
    ) -> CandidateInvitation:
        """
        Resend invitation with NEW token (invalidates old token).
        
        Args:
            invitation_id: ID of invitation to resend
            resent_by_id: ID of portal user resending
            expiry_hours: Hours until new invitation expires
            
        Returns:
            Updated invitation with new token
            
        Raises:
            ValueError: If invitation cannot be resent
        """
        invitation = InvitationService.get_by_id(invitation_id)
        if not invitation:
            raise ValueError("Invitation not found")
        
        if not invitation.can_be_resent:
            raise ValueError(f"Invitation with status '{invitation.status}' cannot be resent")
        
        # Generate NEW token
        old_token = invitation.token
        invitation.token = CandidateInvitation.generate_token()
        
        # Reset expiry
        if expiry_hours is None:
            expiry_hours = getattr(settings, 'INVITATION_EXPIRY_HOURS', 168)
        invitation.expires_at = datetime.utcnow() + timedelta(hours=expiry_hours)
        
        # Reset status if expired or cancelled
        if invitation.status in ['expired', 'cancelled']:
            invitation.status = 'sent'
        
        # Update timestamp
        invitation.updated_at = datetime.utcnow()
        
        # Log the action
        InvitationAuditLog.log_action(
            invitation_id=invitation.id,
            action='invitation_resent',
            performed_by=f'portal_user:{resent_by_id}',
            extra_data={
                'old_token_invalidated': old_token[:10] + '...',
                'new_expiry_hours': expiry_hours
            }
        )
        
        db.session.commit()
        
        logger.info(f"Resent invitation {invitation.id}, new token generated")
        
        # Send invitation email with new token
        try:
            candidate_name = f"{invitation.first_name} {invitation.last_name}".strip() if invitation.first_name else None
            onboarding_url = f"{settings.frontend_base_url}/onboard/{invitation.token}"
            expiry_date = invitation.expires_at.strftime("%B %d, %Y at %I:%M %p UTC")
            
            EmailService.send_invitation_email(
                tenant_id=invitation.tenant_id,
                to_email=invitation.email,
                candidate_name=candidate_name,
                onboarding_url=onboarding_url,
                expiry_date=expiry_date
            )
            logger.info(f"Sent resend invitation email to {invitation.email}")
        except Exception as e:
            logger.error(f"Failed to send resend invitation email: {e}")
        
        return invitation
    
    @staticmethod
    def list_invitations(
        tenant_id: int,
        status_filter: Optional[str] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Tuple[List[CandidateInvitation], int]:
        """
        List invitations for a tenant with optional filtering.
        
        Args:
            tenant_id: Tenant ID
            status_filter: Optional status to filter by
            page: Page number (1-indexed)
            per_page: Results per page
            
        Returns:
            Tuple of (invitations list, total count)
        """
        query = select(CandidateInvitation).where(CandidateInvitation.tenant_id == tenant_id)
        
        if status_filter:
            query = query.where(CandidateInvitation.status == status_filter)
        
        # Order by most recent first
        query = query.order_by(CandidateInvitation.created_at.desc())
        
        # Get total count
        count_query = select(db.func.count()).select_from(query.subquery())
        total = db.session.execute(count_query).scalar()
        
        # Paginate
        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)
        
        invitations = db.session.execute(query).scalars().all()
        
        return list(invitations), total
    
    @staticmethod
    def submit_invitation(
        token: str,
        invitation_data: Dict,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> CandidateInvitation:
        """
        Submit candidate's self-onboarding data.
        
        Args:
            token: Invitation token
            invitation_data: Form data submitted by candidate (as dict)
            ip_address: IP address of candidate
            user_agent: User agent string
            
        Returns:
            Updated invitation
            
        Raises:
            ValueError: If token is invalid or expired
        """
        invitation = InvitationService.get_by_token(token)
        if not invitation:
            raise ValueError("Invalid invitation token")
        
        if not invitation.is_valid:
            if invitation.is_expired:
                raise ValueError("Invitation has expired")
            raise ValueError(f"Invitation is no longer valid (status: {invitation.status})")
        
        # Update invitation
        invitation.invitation_data = invitation_data
        invitation.status = 'submitted'
        invitation.submitted_at = datetime.utcnow()
        invitation.updated_at = datetime.utcnow()
        
        # Log the action
        InvitationAuditLog.log_action(
            invitation_id=invitation.id,
            action='invitation_submitted',
            performed_by='candidate',
            ip_address=ip_address,
            user_agent=user_agent,
            extra_data={'data_keys': list(invitation_data.keys()) if invitation_data else []}
        )
        
        db.session.commit()
        
        logger.info(f"Invitation {invitation.id} submitted by candidate")
        
        # Send confirmation email to candidate
        try:
            candidate_name = f"{invitation.first_name} {invitation.last_name}".strip() if invitation.first_name else "Candidate"
            EmailService.send_submission_confirmation(
                tenant_id=invitation.tenant_id,
                to_email=invitation.email,
                candidate_name=candidate_name
            )
            logger.info(f"Sent submission confirmation to {invitation.email}")
        except Exception as e:
            logger.error(f"Failed to send submission confirmation: {e}")
        
        # Send notification to HR team
        try:
            # Get all recruiters and admins for this tenant
            hr_users = db.session.execute(
                select(PortalUser)
                .where(
                    and_(
                        PortalUser.tenant_id == invitation.tenant_id,
                        PortalUser.is_active == True
                    )
                )
            ).scalars().all()
            
            hr_emails = [user.email for user in hr_users if user.email]
            
            if hr_emails:
                review_url = f"{settings.frontend_base_url}/invitations/{invitation.id}"
                EmailService.send_hr_notification(
                    tenant_id=invitation.tenant_id,
                    hr_emails=hr_emails,
                    candidate_name=candidate_name,
                    candidate_email=invitation.email,
                    invitation_id=invitation.id,
                    review_url=review_url
                )
                logger.info(f"Sent HR notification to {len(hr_emails)} recipients")
        except Exception as e:
            logger.error(f"Failed to send HR notification: {e}")
        
        return invitation
    
    @staticmethod
    def approve_invitation(
        invitation_id: int,
        tenant_id: int,
        reviewed_by_id: int,
        notes: Optional[str] = None
    ) -> Candidate:
        """
        Approve invitation and create candidate record.
        
        This method:
        1. Creates a Candidate from invitation data
        2. Moves documents from invitation to candidate
        3. Triggers resume re-parsing
        4. Updates invitation status
        5. Logs audit trail
        
        Args:
            invitation_id: Invitation ID
            tenant_id: Tenant ID for isolation
            reviewed_by_id: ID of portal user approving
            notes: Optional review notes
            
        Returns:
            Created Candidate record
            
        Raises:
            ValueError: If invitation cannot be approved
        """
        invitation = InvitationService.get_by_id(invitation_id, tenant_id)
        if not invitation:
            raise ValueError("Invitation not found")
        
        if invitation.status != 'submitted':
            raise ValueError(f"Only submitted invitations can be approved (current status: {invitation.status})")
        
        if not invitation.invitation_data:
            raise ValueError("No invitation data to create candidate from")
        
        # Extract data from invitation_data
        data = invitation.invitation_data
        
        # Create candidate record
        candidate = Candidate(
            tenant_id=invitation.tenant_id,
            first_name=data.get('first_name') or invitation.first_name or '',
            last_name=data.get('last_name') or invitation.last_name,
            email=invitation.email,
            phone=data.get('phone'),
            status='NEW',  # Default status for new candidates
            source='self_onboarding',
            onboarding_type='self_onboarding',
            
            # Professional details from form
            full_name=data.get('full_name'),
            location=data.get('location'),
            linkedin_url=data.get('linkedin_url'),
            portfolio_url=data.get('portfolio_url'),
            current_title=data.get('current_title'),
            total_experience_years=data.get('total_experience_years'),
            professional_summary=data.get('professional_summary'),
            
            # Arrays
            skills=data.get('skills'),
            certifications=data.get('certifications'),
            languages=data.get('languages'),
            preferred_locations=data.get('preferred_locations'),
            
            # JSONB structured data
            education=data.get('education'),
            work_experience=data.get('work_experience'),
            parsed_resume_data=data.get('parsed_resume_data'),  # From AI parsing during onboarding
        )
        
        db.session.add(candidate)
        db.session.flush()  # Get candidate.id
        
        # Move documents from invitation to candidate
        documents = db.session.execute(
            select(CandidateDocument).where(CandidateDocument.invitation_id == invitation.id)
        ).scalars().all()
        
        for doc in documents:
            doc.candidate_id = candidate.id
            # Keep invitation_id for audit trail
            logger.debug(f"Moved document {doc.id} to candidate {candidate.id}")
        
        # Update invitation
        invitation.status = 'approved'
        invitation.candidate_id = candidate.id
        invitation.reviewed_by_id = reviewed_by_id
        invitation.reviewed_at = datetime.utcnow()
        invitation.review_notes = notes
        invitation.updated_at = datetime.utcnow()
        
        # Link invitation to candidate
        candidate.invitation_id = invitation.id
        
        # Log the action
        InvitationAuditLog.log_action(
            invitation_id=invitation.id,
            action='invitation_approved',
            performed_by=f'portal_user:{reviewed_by_id}',
            extra_data={
                'candidate_id': candidate.id,
                'documents_moved': len(documents),
                'has_notes': bool(notes)
            }
        )
        
        db.session.commit()
        
        logger.info(f"Approved invitation {invitation.id}, created candidate {candidate.id}")
        
        # Send approval email to candidate
        try:
            candidate_name = f"{candidate.first_name} {candidate.last_name}".strip() if candidate.first_name else "Candidate"
            EmailService.send_approval_email(
                tenant_id=invitation.tenant_id,
                to_email=invitation.email,
                candidate_name=candidate_name
            )
            logger.info(f"Sent approval email to {invitation.email}")
        except Exception as e:
            logger.error(f"Failed to send approval email: {e}")
        
        # TODO: Trigger async resume re-parsing here
        # from app.services.resume_parser import ResumeParser
        # ResumeParser.parse_candidate_resume_async(candidate.id)
        
        return candidate
    
    @staticmethod
    def reject_invitation(
        invitation_id: int,
        tenant_id: int,
        reviewed_by_id: int,
        reason: str,
        notes: Optional[str] = None
    ) -> CandidateInvitation:
        """
        Reject invitation with reason.
        
        Args:
            invitation_id: Invitation ID
            tenant_id: Tenant ID for isolation
            reviewed_by_id: ID of portal user rejecting
            reason: Rejection reason (required)
            notes: Optional review notes
            
        Returns:
            Updated invitation
            
        Raises:
            ValueError: If invitation cannot be rejected or reason missing
        """
        if not reason or not reason.strip():
            raise ValueError("Rejection reason is required")
        
        invitation = InvitationService.get_by_id(invitation_id, tenant_id)
        if not invitation:
            raise ValueError("Invitation not found")
        
        if invitation.status != 'submitted':
            raise ValueError(f"Only submitted invitations can be rejected (current status: {invitation.status})")
        
        # Update invitation
        invitation.status = 'rejected'
        invitation.reviewed_by_id = reviewed_by_id
        invitation.reviewed_at = datetime.utcnow()
        invitation.rejection_reason = reason
        invitation.review_notes = notes
        invitation.updated_at = datetime.utcnow()
        
        # Log the action
        InvitationAuditLog.log_action(
            invitation_id=invitation.id,
            action='invitation_rejected',
            performed_by=f'portal_user:{reviewed_by_id}',
            extra_data={'reason_length': len(reason)}
        )
        
        db.session.commit()
        
        logger.info(f"Rejected invitation {invitation.id}")
        
        # Send rejection email to candidate
        try:
            candidate_name = f"{invitation.first_name} {invitation.last_name}".strip() if invitation.first_name else "Candidate"
            EmailService.send_rejection_email(
                tenant_id=invitation.tenant_id,
                to_email=invitation.email,
                candidate_name=candidate_name,
                reason=reason
            )
            logger.info(f"Sent rejection email to {invitation.email}")
        except Exception as e:
            logger.error(f"Failed to send rejection email: {e}")
        
        return invitation
    
    @staticmethod
    def cancel_invitation(
        invitation_id: int,
        tenant_id: int,
        cancelled_by_id: int
    ) -> CandidateInvitation:
        """
        Cancel a pending invitation.
        
        Args:
            invitation_id: Invitation ID
            tenant_id: Tenant ID for isolation
            cancelled_by_id: ID of portal user cancelling
            
        Returns:
            Updated invitation
            
        Raises:
            ValueError: If invitation cannot be cancelled
        """
        invitation = InvitationService.get_by_id(invitation_id, tenant_id)
        if not invitation:
            raise ValueError("Invitation not found")
        
        if invitation.status in ['approved', 'rejected', 'cancelled']:
            raise ValueError(f"Cannot cancel invitation with status: {invitation.status}")
        
        invitation.status = 'cancelled'
        invitation.updated_at = datetime.utcnow()
        
        # Log the action
        InvitationAuditLog.log_action(
            invitation_id=invitation.id,
            action='invitation_cancelled',
            performed_by=f'portal_user:{cancelled_by_id}'
        )
        
        db.session.commit()
        
        logger.info(f"Cancelled invitation {invitation.id}")
        return invitation
    
    @staticmethod
    def get_invitation_audit_trail(invitation_id: int) -> List[InvitationAuditLog]:
        """
        Get audit trail for an invitation.
        
        Args:
            invitation_id: Invitation ID
            
        Returns:
            List of audit log entries ordered by timestamp
        """
        query = (
            select(InvitationAuditLog)
            .where(InvitationAuditLog.invitation_id == invitation_id)
            .order_by(InvitationAuditLog.timestamp.asc())
        )
        
        logs = db.session.execute(query).scalars().all()
        return list(logs)
    
    @staticmethod
    def mark_as_opened(token: str, ip_address: Optional[str] = None, user_agent: Optional[str] = None):
        """
        Mark invitation as opened (candidate clicked link).
        
        Args:
            token: Invitation token
            ip_address: IP address
            user_agent: User agent string
        """
        invitation = InvitationService.get_by_token(token)
        if invitation and invitation.status == 'sent':
            invitation.status = 'opened'
            invitation.updated_at = datetime.utcnow()
            
            InvitationAuditLog.log_action(
                invitation_id=invitation.id,
                action='invitation_opened',
                performed_by='candidate',
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            db.session.commit()
            logger.info(f"Marked invitation {invitation.id} as opened")
    
    @staticmethod
    def mark_as_in_progress(token: str):
        """
        Mark invitation as in progress (candidate started filling form).
        
        Args:
            token: Invitation token
        """
        invitation = InvitationService.get_by_token(token)
        if invitation and invitation.status in ['sent', 'opened']:
            invitation.status = 'in_progress'
            invitation.updated_at = datetime.utcnow()
            
            InvitationAuditLog.log_action(
                invitation_id=invitation.id,
                action='invitation_in_progress',
                performed_by='candidate'
            )
            
            db.session.commit()
            logger.info(f"Marked invitation {invitation.id} as in_progress")
