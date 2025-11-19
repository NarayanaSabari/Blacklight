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
from app.models.tenant import Tenant
from app.models.portal_user import PortalUser
from app.models.role import Role
from app.services.email_service import EmailService
from app.services.resume_parser import ResumeParserService
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
                "submitted": 0,
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
        
        # Send confirmation email to candidate via Inngest
        try:
            from app.inngest import inngest_client
            import inngest
            
            candidate_name = f"{invitation.first_name} {invitation.last_name}".strip() if invitation.first_name else "Candidate"
            
            logger.info(f"[INNGEST] Attempting to send event 'email/submission.confirmation' for invitation {invitation.id}")
            
            event_result = inngest_client.send_sync(
                inngest.Event(
                    name="email/submission.confirmation",
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
            
            # Get all recruiters and admins for this tenant
            hr_users = db.session.execute(
                select(PortalUser)
                .join(Role)
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
                
                logger.info(f"[INNGEST] Attempting to send event 'email/hr.notification' for invitation {invitation.id}")
                
                event_result = inngest_client.send_sync(
                    inngest.Event(
                        name="email/hr.notification",
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
        
        if invitation.status != 'submitted':
            raise ValueError(f"Only submitted invitations can be approved (current status: {invitation.status})")
        
        if not invitation.invitation_data:
            raise ValueError("No invitation data to create candidate from")
        
        # Extract data from invitation_data and merge with HR edits
        data = invitation.invitation_data.copy()
        if edited_data:
            # Merge HR edits (HR edits take precedence)
            data.update(edited_data)
            logger.info(f"Merged HR edits for invitation {invitation_id}: {list(edited_data.keys())}")
        
        # Create candidate record
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

        candidate = Candidate(
            tenant_id=invitation.tenant_id,
            first_name=data.get('first_name') or invitation.first_name or '',
            last_name=data.get('last_name') or invitation.last_name or '',
            email=invitation.email,
            phone=data.get('phone'),
            status='NEW',
            source='self_onboarding',
            onboarding_status='PENDING_ASSIGNMENT',
            
            # Professional details - use smart getter
            full_name=full_name,
            location=get_field('location'),
            linkedin_url=get_field('linkedin_url'),
            portfolio_url=get_field('portfolio_url'),
            current_title=position or get_field('current_title'),
            total_experience_years=experience_years or get_field('total_experience_years'),
            professional_summary=summary or get_field('professional_summary'),
            
            # Arrays - ensure always lists, prefer parsed data
            skills=ensure_list(get_field('skills', default=[])),
            certifications=ensure_list(get_field('certifications', default=[])),
            languages=ensure_list(get_field('languages', default=[])),
            preferred_locations=ensure_list(get_field('preferred_locations', default=[])),
            
            # JSONB structured data - use parsed or fallback to structured text
            education=education_data,
            work_experience=work_exp_data,
            
            # Store full parsed data for reference
            parsed_resume_data=parsed_resume if parsed_resume else None,
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
                'has_notes': bool(notes),
                'hr_edited_fields': list(edited_data.keys()) if edited_data else None
            }
        )
        
        db.session.commit()
        
        logger.info(f"Approved invitation {invitation.id}, created candidate {candidate.id}")
        
        # Send approval email to candidate via Inngest
        try:
            from app.inngest import inngest_client
            import inngest
            
            candidate_name = f"{candidate.first_name} {candidate.last_name}".strip() if candidate.first_name else "Candidate"
            
            logger.info(f"[INNGEST] Attempting to send event 'email/invitation.approved' for invitation {invitation.id}")
            
            event_result = inngest_client.send_sync(
                inngest.Event(
                    name="email/invitation.approved",
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
            logger.error(f"Failed to send Inngest event for approval email: {e}")
        
        # Trigger async resume re-parsing
        try:
            ResumeParserService.parse_candidate_resume_async(candidate.id)
            logger.info(f"Triggered async resume parsing for candidate {candidate.id}")
        except Exception as e:
            logger.error(f"Failed to trigger async resume parsing for candidate {candidate.id}: {e}")
        
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
        
        # Send rejection email to candidate via Inngest
        try:
            from app.inngest import inngest_client
            import inngest
            
            candidate_name = f"{invitation.first_name} {invitation.last_name}".strip() if invitation.first_name else "Candidate"
            
            logger.info(f"[INNGEST] Attempting to send event 'email/invitation.rejected' for invitation {invitation.id}")
            
            event_result = inngest_client.send_sync(
                inngest.Event(
                    name="email/invitation.rejected",
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
