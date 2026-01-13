"""
Invitation Service
Business logic for managing candidate invitations
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import joinedload

from app import db
from app.models.candidate_invitation import CandidateInvitation
from app.models.invitation_audit_log import InvitationAuditLog
from app.models.candidate import Candidate
from app.models.candidate_document import CandidateDocument
from app.models.candidate_resume import CandidateResume
from app.models.tenant import Tenant
from app.models.portal_user import PortalUser
from app.models.role import Role
from app.services.email_service import EmailService
from app.services.resume_parser import ResumeParserService
from config.settings import settings  # Use global settings instance

logger = logging.getLogger(__name__)


class InvitationService:
    """Service for managing candidate invitations"""
    
    @staticmethod
    def create_invitation(
        tenant_id: int,
        email: str,
        invited_by_id: int,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        position: Optional[str] = None,
        recruiter_notes: Optional[str] = None,
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
            position: Optional position/role for the candidate
            recruiter_notes: Optional internal notes for the HR team
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
        if duplicate and duplicate.status in ['sent', 'opened', 'in_progress', 'pending_review']:
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
            invitation.position = position
            invitation.recruiter_notes = recruiter_notes
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
                position=position,
                recruiter_notes=recruiter_notes,
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
        
        # Calculate email details for Inngest event or synchronous fallback
        candidate_name = f"{first_name} {last_name}".strip() if first_name else None
        onboarding_url = f"{settings.frontend_base_url}/onboard/{invitation.token}"
        expiry_date_str = expires_at.strftime("%B %d, %Y at %I:%M %p UTC")
        
        # Send invitation email via Inngest (async/non-blocking)
        try:
            from app.inngest import inngest_client
            import inngest
            
            logger.info(f"[INNGEST] Attempting to send event 'email/invitation' for invitation {invitation.id}")
            
            # Use event ID for deduplication (prevents duplicate emails within 24h)
            event_id = f"invitation-{invitation.id}-{invitation.token[:16]}"
            
            event_result = inngest_client.send_sync(
                inngest.Event(
                    id=event_id,
                    name="email/invitation",
                    data={
                        "invitation_id": invitation.id,
                        "tenant_id": tenant_id,
                        "to_email": email,
                        "candidate_name": candidate_name,
                        "onboarding_url": onboarding_url,
                        "expiry_date": expiry_date_str
                    }
                )
            )
            
            logger.info(f"[INNGEST] ✅ Event sent successfully for {email}. Result: {event_result}")
        except ImportError:
            # Fallback to synchronous email if Inngest not available
            logger.warning("Inngest not available, sending email synchronously")
            try:
                EmailService.send_invitation_email(
                    tenant_id=tenant_id,
                    to_email=email,
                    candidate_name=candidate_name,
                    onboarding_url=onboarding_url,
                    expiry_date=expiry_date_str
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
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[SERVICE] get_by_token called with: {token} (type: {type(token).__name__})")
        logger.info(f"[SERVICE] CandidateInvitation.token column type: {CandidateInvitation.token.type}")
        
        query = select(CandidateInvitation).where(CandidateInvitation.token == token)
        logger.info(f"[SERVICE] Query compiled: {query}")
        
        invitation = db.session.execute(query).scalar_one_or_none()
        logger.info(f"[SERVICE] Result: {invitation}")
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
        
        # Prevent duplicate resends within 5 seconds (handles double-clicks)
        if invitation.updated_at:
            time_since_update = (datetime.utcnow() - invitation.updated_at).total_seconds()
            if time_since_update < 5:
                logger.warning(f"Prevented duplicate resend for invitation {invitation_id} (last updated {time_since_update:.2f}s ago)")
                return invitation  # Return existing invitation without resending
        
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
        
        # Send invitation email with new token via Inngest
        try:
            from app.inngest import inngest_client
            import inngest
            
            candidate_name = f"{invitation.first_name} {invitation.last_name}".strip() if invitation.first_name else None
            onboarding_url = f"{settings.frontend_base_url}/onboard/{invitation.token}"
            expiry_date = invitation.expires_at.strftime("%B %d, %Y at %I:%M %p UTC")

            logger.info(f"[INNGEST] Attempting to send event 'email/invitation' for invitation {invitation.id} (RESEND)")
            
            # Use unique event ID for each resend (includes token to allow resends)
            event_id = f"invitation-{invitation.id}-{invitation.token[:16]}"
            
            event_result = inngest_client.send_sync(
                inngest.Event(
                    id=event_id,
                    name="email/invitation",
                    data={
                        "invitation_id": invitation.id,
                        "tenant_id": invitation.tenant_id,
                        "to_email": invitation.email,
                        "candidate_name": candidate_name,
                        "onboarding_url": onboarding_url,
                        "expiry_date": expiry_date
                    }
                )
            )
            
            logger.info(f"[INNGEST] ✅ Event sent successfully for {invitation.email}. Result: {event_result}")
        except Exception as e:
            logger.error(f"Failed to send Inngest event for resend invitation: {e}")
        
        return invitation
    
    @staticmethod
    def list_invitations(
        tenant_id: int,
        status_filter: Optional[str] = None,
        email_filter: Optional[str] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Tuple[List[CandidateInvitation], int]:
        """
        List invitations for a tenant with optional filtering.
        
        Args:
            tenant_id: Tenant ID
            status_filter: Optional status to filter by
            email_filter: Optional email to search for (case-insensitive)
            page: Page number (1-indexed)
            per_page: Results per page
            
        Returns:
            Tuple of (invitations list, total count)
        """
        query = select(CandidateInvitation).where(CandidateInvitation.tenant_id == tenant_id)
        
        if status_filter:
            query = query.where(CandidateInvitation.status == status_filter)
        
        if email_filter:
            query = query.where(CandidateInvitation.email.ilike(f"%{email_filter.strip()}%"))
        
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
    def get_invitation_stats(tenant_id: int) -> Dict[str, any]:
        """
        Get invitation statistics for a tenant efficiently from the database.

        Args:
            tenant_id: Tenant ID

        Returns:
            Dictionary with statistics
        """
        # Query for counts of each status
        status_counts_query = (
            select(CandidateInvitation.status, func.count(CandidateInvitation.id))
            .where(CandidateInvitation.tenant_id == tenant_id)
            .group_by(CandidateInvitation.status)
        )
        status_results = db.session.execute(status_counts_query).all()

        # Initialize stats dictionary with all possible statuses
        stats = {
            "total": 0,
            "by_status": {
                "invited": 0,
                "opened": 0,
                "in_progress": 0,
                "pending_review": 0,
                "approved": 0,
                "rejected": 0,
                "cancelled": 0,
                "expired": 0,
            },
        }

        # Map DB status 'sent' to API status 'invited'
        status_map = {
            "sent": "invited"
        }

        total_count = 0
        for status, count in status_results:
            key = status_map.get(status, status)
            if key in stats["by_status"]:
                stats["by_status"][key] = count
            total_count += count
        
        stats["total"] = total_count

        return stats
    
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
            ValueError: If token is invalid or expired or required documents missing
        """
        invitation = InvitationService.get_by_token(token)
        if not invitation:
            raise ValueError("Invalid invitation token")
        
        if not invitation.is_valid:
            if invitation.is_expired:
                raise ValueError("Invitation has expired")
            raise ValueError(f"Invitation is no longer valid (status: {invitation.status})")
        
        # Validate required documents are uploaded (grandfathers existing - only checks at submission time)
        from app.services import TenantService
        from app.models.candidate_document import CandidateDocument
        
        required_documents = TenantService.get_document_requirements(invitation.tenant_id)
        if required_documents:
            # Get uploaded document types for this invitation
            uploaded_docs = db.session.execute(
                select(CandidateDocument.document_type).where(
                    CandidateDocument.invitation_id == invitation.id
                )
            ).scalars().all()
            uploaded_doc_types = set(uploaded_docs)
            
            # Check which required documents are missing
            missing_documents = []
            for req in required_documents:
                if req.get('is_required', True) and req.get('document_type') not in uploaded_doc_types:
                    missing_documents.append({
                        'document_type': req.get('document_type'),
                        'label': req.get('label', req.get('document_type'))
                    })
            
            if missing_documents:
                missing_labels = [doc['label'] for doc in missing_documents]
                raise ValueError(f"Missing required documents: {', '.join(missing_labels)}")
        
        # Update invitation
        invitation.invitation_data = invitation_data
        invitation.status = 'pending_review'
        invitation.submitted_at = datetime.utcnow()
        invitation.updated_at = datetime.utcnow()
        
        # Track created resume for polish trigger later
        # Store IDs before commit to avoid DetachedInstanceError after db.session.commit()
        created_resume = None
        resume_id_for_polish = None
        resume_candidate_id = None
        resume_tenant_id = None
        resume_has_parsed_data = False
        
        # Auto-create a Candidate record in pending_review so email submissions
        # behave like resume uploads (visible in Review Submissions + All Candidates)
        if not invitation.candidate_id:
            data = invitation_data or {}
            first_name = data.get('first_name') or invitation.first_name or ''
            last_name = data.get('last_name') or invitation.last_name or ''

            # Optional parsed resume data (structured) from the onboarding flow
            parsed_resume = data.get('parsed_resume_data') or {}

            # Basic fields
            full_name = data.get('full_name') or f"{first_name} {last_name}".strip()
            position = data.get('position') or data.get('current_job_title') or data.get('current_title')
            experience_years = data.get('experience_years') or data.get('years_of_experience') or data.get('total_experience_years')
            expected_salary = data.get('expected_salary')
            summary = data.get('summary') or data.get('professional_summary')

            # Skills and simple arrays
            skills = data.get('skills') or parsed_resume.get('skills') or []
            if isinstance(skills, str):
                # Just in case skills were sent as comma-separated string
                skills = [s.strip() for s in skills.split(',') if s.strip()]

            # Extract preferred roles
            preferred_roles = data.get('preferred_roles') or parsed_resume.get('preferred_roles') or []
            if isinstance(preferred_roles, str):
                # Handle comma-separated string
                preferred_roles = [r.strip() for r in preferred_roles.split(',') if r.strip()]
            elif not isinstance(preferred_roles, list):
                preferred_roles = []
            
            # Validate max 10 roles
            if len(preferred_roles) > 10:
                logger.warning(f"Preferred roles truncated from {len(preferred_roles)} to 10")
                preferred_roles = preferred_roles[:10]

            # Extract preferred locations
            preferred_locations = data.get('preferred_locations') or parsed_resume.get('preferred_locations') or []
            if isinstance(preferred_locations, str):
                # Handle comma-separated string
                preferred_locations = [loc.strip() for loc in preferred_locations.split(',') if loc.strip()]
            elif not isinstance(preferred_locations, list):
                preferred_locations = []

            # Simple education/work_experience as text fallbacks
            education_text = data.get('education')
            work_exp_text = data.get('work_experience')

            education_data = None
            if parsed_resume.get('education') and isinstance(parsed_resume.get('education'), list):
                education_data = parsed_resume['education']
            elif education_text and isinstance(education_text, str) and education_text.strip():
                education_data = [{
                    'degree': 'Not specified',
                    'field_of_study': None,
                    'institution': 'Not specified',
                    'graduation_year': None,
                    'description': education_text.strip(),
                }]

            work_exp_data = None
            if parsed_resume.get('work_experience') and isinstance(parsed_resume.get('work_experience'), list):
                work_exp_data = parsed_resume['work_experience']
            elif work_exp_text and isinstance(work_exp_text, str) and work_exp_text.strip():
                work_exp_data = [{
                    'title': 'Not specified',
                    'company': 'Not specified',
                    'location': None,
                    'start_date': None,
                    'end_date': None,
                    'is_current': False,
                    'description': work_exp_text.strip(),
                }]

            candidate = Candidate(
                tenant_id=invitation.tenant_id,
                first_name=first_name,
                last_name=last_name,
                email=invitation.email,
                phone=data.get('phone'),
                status='pending_review',
                source='email_invitation',
                full_name=full_name,
                location=data.get('location') or parsed_resume.get('location'),
                linkedin_url=data.get('linkedin_url') or parsed_resume.get('linkedin_url'),
                portfolio_url=data.get('portfolio_url') or parsed_resume.get('portfolio_url'),
                current_title=position or parsed_resume.get('current_title'),
                total_experience_years=experience_years or parsed_resume.get('total_experience_years'),
                expected_salary=expected_salary,
                visa_type=data.get('visa_type'),
                professional_summary=summary or parsed_resume.get('professional_summary'),
                skills=skills,
                preferred_roles=preferred_roles,
                preferred_locations=preferred_locations,
                education=education_data,
                work_experience=work_exp_data,
                # NOTE: parsed_resume_data is now stored in CandidateResume table, not Candidate
                # It will be set when CandidateResume is created below
            )

            db.session.add(candidate)
            db.session.flush()  # populate candidate.id

            invitation.candidate_id = candidate.id
            logger.info(f"Created candidate {candidate.id} from submitted invitation {invitation.id}")
            
            # Link resume file from invitation documents to candidate via CandidateResume table
            resume_doc = db.session.execute(
                select(CandidateDocument).where(
                    CandidateDocument.invitation_id == invitation.id,
                    CandidateDocument.document_type == 'resume'
                ).order_by(CandidateDocument.uploaded_at.desc())
            ).scalar()
            
            if resume_doc:
                # Create CandidateResume record instead of setting fields on Candidate
                try:
                    from app.services.candidate_resume_service import CandidateResumeService
                    created_resume = CandidateResumeService.create_resume(
                        candidate_id=candidate.id,
                        tenant_id=invitation.tenant_id,
                        file_key=resume_doc.file_key,
                        storage_backend=resume_doc.storage_backend or 'gcs',
                        original_filename=resume_doc.file_name or 'resume',
                        file_size=resume_doc.file_size,
                        mime_type=resume_doc.mime_type,
                        is_primary=True,
                        uploaded_by_user_id=None,
                        uploaded_by_candidate=True,
                        parsed_resume_data=parsed_resume or None,
                    )
                    # Store IDs before commit to avoid DetachedInstanceError
                    # After db.session.commit(), the created_resume object may be detached
                    resume_id_for_polish = created_resume.id
                    resume_candidate_id = created_resume.candidate_id
                    resume_tenant_id = created_resume.tenant_id
                    resume_has_parsed_data = bool(created_resume.parsed_resume_data)
                    logger.info(f"Created CandidateResume {created_resume.id} for candidate {candidate.id} from invitation document")
                except Exception as resume_error:
                    logger.error(f"Failed to create CandidateResume for candidate {candidate.id}: {resume_error}", exc_info=True)
                    # Continue without resume - candidate can still be created
        
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
        db.session.expire_all()  # Ensure fresh data on next access
        
        logger.info(f"Invitation {invitation.id} submitted by candidate")
        
        # Send confirmation email to candidate via Inngest
        try:
            from app.inngest import inngest_client
            import inngest
            
            candidate_name = f"{invitation.first_name} {invitation.last_name}".strip() if invitation.first_name else "Candidate"
            
            logger.info(f"[INNGEST] Attempting to send event 'email/submission-confirmation' for invitation {invitation.id}")
            
            event_result = inngest_client.send_sync(
                inngest.Event(
                    name="email/submission-confirmation",
                    data={
                        "invitation_id": invitation.id,
                        "tenant_id": invitation.tenant_id,
                        "to_email": invitation.email,
                        "candidate_name": candidate_name
                    }
                )
            )
            logger.info(f"[INNGEST] ✅ Event sent successfully for {invitation.email}. Result: {event_result}")
        except Exception as e:
            logger.error(f"Failed to send Inngest event for submission confirmation: {e}")
        
        # Send notification to HR team via Inngest
        try:
            from app.inngest import inngest_client
            import inngest
            from app.models.user_role import UserRole
            
            # Get all recruiters and admins for this tenant
            # Join through the user_roles association table
            hr_users = db.session.execute(
                select(PortalUser)
                .join(UserRole, PortalUser.id == UserRole.user_id)
                .join(Role, UserRole.role_id == Role.id)
                .where(
                    and_(
                        PortalUser.tenant_id == invitation.tenant_id,
                        PortalUser.is_active == True,
                        Role.name.in_(['TENANT_ADMIN', 'RECRUITER'])
                    )
                )
            ).scalars().all()
            
            hr_emails = [user.email for user in hr_users if user.email]
            
            if hr_emails:
                review_url = f"{settings.frontend_base_url}/invitations/{invitation.id}"
                
                logger.info(f"[INNGEST] Attempting to send event 'email/hr-notification' for invitation {invitation.id}")
                
                event_result = inngest_client.send_sync(
                    inngest.Event(
                        name="email/hr-notification",
                        data={
                            "invitation_id": invitation.id,
                            "tenant_id": invitation.tenant_id,
                            "hr_emails": hr_emails,
                            "candidate_name": candidate_name,
                            "candidate_email": invitation.email,
                            "review_url": review_url
                        }
                    )
                )
                logger.info(f"[INNGEST] ✅ Event sent successfully to HR. Result: {event_result}")
        except Exception as e:
            logger.error(f"Failed to send Inngest event for HR notification: {e}")
        
        # Trigger resume polishing if we created a resume with parsed data
        # Use the stored IDs (resume_id_for_polish, etc.) to avoid DetachedInstanceError
        if created_resume and resume_has_parsed_data:
            try:
                from app.inngest import inngest_client
                import inngest
                
                logger.info(f"[INNGEST] Triggering resume polish for candidate {resume_candidate_id}, resume {resume_id_for_polish}")
                
                polish_result = inngest_client.send_sync(
                    inngest.Event(
                        name="candidate-resume/polish",
                        data={
                            "candidate_id": resume_candidate_id,
                            "tenant_id": resume_tenant_id,
                            "resume_id": resume_id_for_polish
                        }
                    )
                )
                logger.info(f"[INNGEST] ✅ Resume polish event sent for candidate {resume_candidate_id}, resume {resume_id_for_polish}. Result: {polish_result}")
            except Exception as e:
                logger.error(f"Failed to send Inngest event for resume polishing: {e}")
        elif invitation.candidate_id:
            logger.info(f"[INNGEST] Skipping resume polish - candidate {invitation.candidate_id} has no resume with parsed data (created_resume={created_resume})")
        
        return invitation
    
    @staticmethod
    def approve_invitation(
        invitation_id: int,
        tenant_id: int,
        reviewed_by_id: int,
        notes: Optional[str] = None,
        edited_data: Optional[Dict] = None
    ) -> Candidate:
        """
        Approve invitation and create candidate record.
        
        This method:
        1. Creates a Candidate from invitation data (with optional HR edits)
        2. Moves documents from invitation to candidate
        3. Triggers resume re-parsing
        4. Updates invitation status
        5. Logs audit trail
        
        Args:
            invitation_id: Invitation ID
            tenant_id: Tenant ID for isolation
            reviewed_by_id: ID of portal user approving
            notes: Optional review notes
            edited_data: Optional dict of HR-edited fields to override submission data
            
        Returns:
            Created Candidate record
            
        Raises:
            ValueError: If invitation cannot be approved
        """
        invitation = InvitationService.get_by_id(invitation_id, tenant_id)
        if not invitation:
            raise ValueError("Invitation not found")
        
        if invitation.status != 'pending_review':
            raise ValueError(f"Only pending_review invitations can be approved (current status: {invitation.status})")
        
        if not invitation.invitation_data:
            raise ValueError("No invitation data to create candidate from")
        
        # VALIDATION: Check preferred_roles is filled (required for job scraping)
        data_for_validation = invitation.invitation_data.copy()
        if edited_data:
            data_for_validation.update(edited_data)
        
        preferred_roles = data_for_validation.get('preferred_roles', [])
        if not preferred_roles or len(preferred_roles) == 0:
            raise ValueError(
                "Preferred roles are required for approval. "
                "Please add at least one preferred role for the candidate."
            )
        
        # Extract data from invitation_data and merge with HR edits
        data = invitation.invitation_data.copy()
        if edited_data:
            # Merge HR edits (HR edits take precedence)
            data.update(edited_data)
            logger.info(f"Merged HR edits for invitation {invitation_id}: {list(edited_data.keys())}")
        
        # Create or reuse candidate record
        # Build full_name from parts if not provided
        full_name = data.get('full_name')
        if not full_name:
            first_name = data.get('first_name') or invitation.first_name or ''
            last_name = data.get('last_name') or invitation.last_name or ''
            full_name = f"{first_name} {last_name}".strip()
        
        # Get experience years from either field name
        experience_years = data.get('experience_years') or data.get('years_of_experience') or data.get('total_experience_years')
        
        # Get professional summary
        summary = data.get('summary') or data.get('professional_summary')
        
        # Get position/title
        position = data.get('position') or data.get('current_job_title') or data.get('current_title')

        # 🆕 SMART DATA EXTRACTION
        # Priority: parsed_resume_data > form data > defaults
        parsed_resume = data.get('parsed_resume_data', {}) or {}

        # Helper to get value with fallback chain
        def get_field(form_key, parsed_key=None, default=None):
            """
            Get value from form data or parsed resume data
            Priority: form data > parsed resume > default
            """
            parsed_key = parsed_key or form_key
            form_value = data.get(form_key)
            
            # If form has explicit value, use it
            if form_value is not None and form_value != '':
                return form_value
            
            # Otherwise try parsed resume
            return parsed_resume.get(parsed_key, default)

        # Helper to ensure lists
        def ensure_list(value):
            """Convert None/empty to [], otherwise ensure it's a list"""
            if value is None or value == '':
                return []
            if isinstance(value, list):
                return value
            return [value]

        # Extract education - prefer structured, fallback to text
        education_data = None
        if parsed_resume and isinstance(parsed_resume.get('education'), list):
            # Use parsed structured data
            education_data = parsed_resume['education']
            logger.info(f"Using parsed education data: {len(education_data)} entries")
        elif parsed_resume and isinstance(parsed_resume.get('education'), str):
            # Handle string from parsed data (convert to structured format)
            edu_text = parsed_resume['education']
            if edu_text and edu_text.strip():
                education_data = [{
                    'degree': 'Not specified',
                    'field_of_study': None,
                    'institution': 'Not specified',
                    'graduation_year': None,
                    'description': edu_text.strip()
                }]
                logger.info("Using parsed 'education' string (converted to structured)")
            else:
                education_data = []
        else:
            # Fallback: convert form text to single structured entry
            edu_text = data.get('education')
            if edu_text and isinstance(edu_text, str) and edu_text.strip():
                education_data = [{
                    'degree': 'Not specified',
                    'field_of_study': None,
                    'institution': 'Not specified',
                    'graduation_year': None,
                    'description': edu_text.strip()
                }]
                logger.info("Using form text for education (no parsed data)")
            else:
                education_data = []

        # Extract work experience - prefer structured, fallback to text
        work_exp_data = None
        # Check both 'work_experience' and 'experience' field names (frontend inconsistency)
        if parsed_resume and isinstance(parsed_resume.get('work_experience'), list):
            # Use parsed structured data (correct field name)
            work_exp_data = parsed_resume['work_experience']
            logger.info(f"Using parsed work_experience: {len(work_exp_data)} entries")
        elif parsed_resume and isinstance(parsed_resume.get('experience'), list):
            # Use parsed structured data (legacy field name from frontend)
            work_exp_data = parsed_resume['experience']
            logger.info(f"Using parsed experience: {len(work_exp_data)} entries")
        elif parsed_resume and isinstance(parsed_resume.get('experience'), str):
            # Handle string from parsed data (convert to structured format)
            exp_text = parsed_resume['experience']
            if exp_text and exp_text.strip():
                work_exp_data = [{
                    'title': 'Not specified',
                    'company': 'Not specified',
                    'location': None,
                    'start_date': None,
                    'end_date': None,
                    'is_current': False,
                    'description': exp_text.strip()
                }]
                logger.info("Using parsed 'experience' string (converted to structured)")
            else:
                work_exp_data = []
        else:
            # Fallback: convert form text to single structured entry
            exp_text = data.get('work_experience')
            if exp_text and isinstance(exp_text, str) and exp_text.strip():
                work_exp_data = [{
                    'title': 'Not specified',
                    'company': 'Not specified',
                    'location': None,
                    'start_date': None,
                    'end_date': None,
                    'is_current': False,
                    'description': exp_text.strip()
                }]
                logger.info("Using form text for work experience (no parsed data)")
            else:
                work_exp_data = []

        # Create candidate record
        # For email invitations, we want the same review flow as async resume uploads:
        #   - status='pending_review' so it appears in the Review Submissions tab
        #   - source='email_invitation' to distinguish origin
        # Prefer the candidate created at submission time, if any
        candidate = None
        if invitation.candidate_id:
            # Eagerly load resumes to avoid lazy loading issues with primary_resume property
            from sqlalchemy.orm import joinedload
            stmt = select(Candidate).where(
                Candidate.id == invitation.candidate_id
            ).options(joinedload(Candidate.resumes))
            candidate = db.session.scalar(stmt)
            if candidate:
                logger.info(f"Using existing candidate {candidate.id} for approved invitation {invitation.id}")
        
        # If no existing candidate (legacy or backfilled invitations), create one now
        if not candidate:
            candidate = Candidate(
                tenant_id=invitation.tenant_id,
                first_name=data.get('first_name') or invitation.first_name or '',
                last_name=data.get('last_name') or invitation.last_name or '',
                email=invitation.email,
                phone=data.get('phone'),
                status='pending_review',
                source='email_invitation',
            )
            db.session.add(candidate)
            db.session.flush()
            invitation.candidate_id = candidate.id
            logger.info(f"Created candidate {candidate.id} while approving invitation {invitation.id}")
        
        # Update candidate details from parsed/form data
        candidate.full_name = full_name
        candidate.location = get_field('location')
        candidate.linkedin_url = get_field('linkedin_url')
        candidate.portfolio_url = get_field('portfolio_url')
        candidate.current_title = position or get_field('current_title')
        candidate.total_experience_years = experience_years or get_field('total_experience_years')
        candidate.professional_summary = summary or get_field('professional_summary')
        
        candidate.skills = ensure_list(get_field('skills', default=[]))
        candidate.certifications = ensure_list(get_field('certifications', default=[]))
        candidate.languages = ensure_list(get_field('languages', default=[]))
        candidate.preferred_locations = ensure_list(get_field('preferred_locations', default=[]))
        
        # Extract preferred roles (max 10)
        preferred_roles = ensure_list(get_field('preferred_roles', default=[]))
        if len(preferred_roles) > 10:
            logger.warning(f"Preferred roles truncated from {len(preferred_roles)} to 10")
            preferred_roles = preferred_roles[:10]
        candidate.preferred_roles = preferred_roles
        
        # Visa type
        candidate.visa_type = get_field('visa_type')
        
        # Set status to ready_for_assignment (approval means ready for job matching)
        candidate.status = 'ready_for_assignment'
        
        candidate.education = education_data
        candidate.work_experience = work_exp_data
        
        # NOTE: parsed_resume_data is now stored in CandidateResume table
        # The primary resume's parsed data will be updated after documents are moved
        
        # Move documents from invitation to candidate (includes file move in GCS/local storage)
        from app.services.document_service import DocumentService
        moved_count, move_error = DocumentService.move_documents_to_candidate(
            invitation_id=invitation.id,
            candidate_id=candidate.id,
            tenant_id=invitation.tenant_id
        )
        if move_error:
            logger.warning(f"Document move had issues: {move_error}")
        else:
            logger.info(f"Moved {moved_count} documents from invitation {invitation.id} to candidate {candidate.id}")
        
        # Update parsed_resume_data on the primary resume if it exists
        if parsed_resume:
            primary_resume = candidate.primary_resume
            if primary_resume:
                primary_resume.parsed_resume_data = parsed_resume
                logger.info(f"Updated parsed_resume_data on primary resume {primary_resume.id}")
            else:
                # If no primary resume exists yet, we'll need to create one or wait for document move
                # This can happen if the invitation didn't have a resume document
                logger.warning(f"No primary resume found for candidate {candidate.id} to update parsed data")
        
        # Update invitation
        invitation.status = 'approved'
        invitation.candidate_id = candidate.id
        invitation.reviewed_by_id = reviewed_by_id
        invitation.reviewed_at = datetime.utcnow()
        invitation.review_notes = notes
        invitation.updated_at = datetime.utcnow()
        
        # Log the action
        InvitationAuditLog.log_action(
            invitation_id=invitation.id,
            action='invitation_approved',
            performed_by=f'portal_user:{reviewed_by_id}',
            extra_data={
                'candidate_id': candidate.id,
                'documents_moved': moved_count,
                'has_notes': bool(notes),
                'hr_edited_fields': list(edited_data.keys()) if edited_data else None
            }
        )
        
        db.session.commit()
        db.session.expire_all()  # Ensure fresh data on next access
        
        logger.info(f"Approved invitation {invitation.id}, created candidate {candidate.id}")
        
        # Send approval email to candidate via Inngest with full candidate details
        try:
            from app.inngest import inngest_client
            import inngest
            
            candidate_name = f"{candidate.first_name} {candidate.last_name}".strip() if candidate.first_name else "Candidate"
            
            # Build comprehensive candidate data for the approval email
            candidate_data = {
                "first_name": candidate.first_name,
                "last_name": candidate.last_name,
                "full_name": candidate.full_name or candidate_name,
                "email": candidate.email,
                "phone": candidate.phone,
                "location": candidate.location,
                "linkedin_url": candidate.linkedin_url,
                "portfolio_url": candidate.portfolio_url,
                "current_title": candidate.current_title,
                "total_experience_years": candidate.total_experience_years,
                "expected_salary": candidate.expected_salary,
                "visa_type": candidate.visa_type,
                "professional_summary": candidate.professional_summary,
                "skills": candidate.skills or [],
                "certifications": candidate.certifications or [],
                "languages": candidate.languages or [],
                "preferred_locations": candidate.preferred_locations or [],
                "preferred_roles": candidate.preferred_roles or [],
                "education": candidate.education or [],
                "work_experience": candidate.work_experience or [],
            }
            
            # Track which fields were edited by HR
            hr_edited_fields = list(edited_data.keys()) if edited_data else []
            
            logger.info(f"[INNGEST] Attempting to send event 'email/approval' for invitation {invitation.id}")
            
            event_result = inngest_client.send_sync(
                inngest.Event(
                    name="email/approval",
                    data={
                        "invitation_id": invitation.id,
                        "tenant_id": invitation.tenant_id,
                        "to_email": invitation.email,
                        "candidate_name": candidate_name,
                        "candidate_data": candidate_data,
                        "hr_edited_fields": hr_edited_fields
                    }
                )
            )
            logger.info(f"[INNGEST] ✅ Event sent successfully for {invitation.email}. Result: {event_result}")
        except Exception as e:
            logger.error(f"Failed to send Inngest event for approval email: {e}")
        
        # Trigger async resume re-parsing
        try:
            ResumeParserService.parse_candidate_resume_async(candidate.id)
            logger.info(f"Triggered async resume parsing for candidate {candidate.id}")
        except Exception as e:
            logger.error(f"Failed to trigger async resume parsing for candidate {candidate.id}: {e}")
        
        # Normalize preferred roles and add to global_roles table for job scraping
        if candidate.preferred_roles:
            try:
                from app.services.ai_role_normalization_service import AIRoleNormalizationService
                
                # Instantiate the service (required - normalize_candidate_role is an instance method)
                role_normalizer = AIRoleNormalizationService()
                
                logger.info(f"Starting role normalization for candidate {candidate.id} with roles: {candidate.preferred_roles}")
                
                for raw_role in candidate.preferred_roles:
                    if raw_role and raw_role.strip():
                        try:
                            global_role, similarity, method = role_normalizer.normalize_candidate_role(
                                raw_role=raw_role.strip(),
                                candidate_id=candidate.id
                            )
                            logger.info(
                                f"Normalized role '{raw_role}' -> '{global_role.name}' "
                                f"(similarity: {similarity:.2%}, method: {method}, role_id: {global_role.id})"
                            )
                        except Exception as role_error:
                            # Rollback to clear failed transaction state
                            db.session.rollback()
                            logger.error(f"Failed to normalize role '{raw_role}' for candidate {candidate.id}: {role_error}")
                            # Continue with other roles even if one fails
                
                logger.info(f"Completed role normalization for candidate {candidate.id}")
            except Exception as e:
                # Rollback to clear failed transaction state
                db.session.rollback()
                logger.error(f"Failed to normalize roles for candidate {candidate.id}: {e}")
        
        # Trigger job matching workflow via Inngest
        try:
            from app.inngest import inngest_client
            import inngest
            
            logger.info(f"[INNGEST] Triggering job matching for candidate {candidate.id}")
            
            event_result = inngest_client.send_sync(
                inngest.Event(
                    name="job-match/generate-candidate",
                    data={
                        "candidate_id": candidate.id,
                        "tenant_id": tenant_id,
                        "trigger_source": "invitation_approval",
                        "preferred_roles": candidate.preferred_roles or []
                    }
                )
            )
            logger.info(f"[INNGEST] ✅ Job matching event sent for candidate {candidate.id}. Result: {event_result}")
        except Exception as e:
            logger.error(f"Failed to trigger job matching for candidate {candidate.id}: {e}")
        
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
        
        if invitation.status != 'pending_review':
            raise ValueError(f"Only pending_review invitations can be rejected (current status: {invitation.status})")
        
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
        
        # Send rejection email to candidate via Inngest
        try:
            from app.inngest import inngest_client
            import inngest
            
            candidate_name = f"{invitation.first_name} {invitation.last_name}".strip() if invitation.first_name else "Candidate"
            
            logger.info(f"[INNGEST] Attempting to send event 'email/rejection' for invitation {invitation.id}")
            
            event_result = inngest_client.send_sync(
                inngest.Event(
                    name="email/rejection",
                    data={
                        "invitation_id": invitation.id,
                        "tenant_id": invitation.tenant_id,
                        "to_email": invitation.email,
                        "candidate_name": candidate_name,
                        "reason": reason
                    }
                )
            )
            logger.info(f"[INNGEST] ✅ Event sent successfully for {invitation.email}. Result: {event_result}")
        except Exception as e:
            logger.error(f"Failed to send Inngest event for rejection email: {e}")
        
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
