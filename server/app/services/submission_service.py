"""
Submission Service
Business logic for tracking candidate submissions to job postings.
Core service for the ATS (Applicant Tracking System) functionality.
"""
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import select, and_, or_, func, desc

from app import db
from app.models.submission import Submission, SubmissionStatus
from app.models.submission_activity import SubmissionActivity, ActivityType
from app.models.candidate import Candidate
from app.models.job_posting import JobPosting


logger = logging.getLogger(__name__)


class SubmissionService:
    """
    Service for managing candidate submissions to job postings.
    
    Handles:
    - CRUD operations for submissions
    - Status transitions with activity logging
    - Activity/note management
    - Statistics and reporting
    - Duplicate detection
    """
    
    def __init__(self, tenant_id: int):
        """
        Initialize SubmissionService for a specific tenant.
        
        Args:
            tenant_id: Tenant ID for multi-tenant isolation
        """
        self.tenant_id = tenant_id
    
    # ==================== CRUD Operations ====================
    
    def create_submission(
        self,
        user_id: int,
        candidate_id: int,
        job_posting_id: int,
        vendor_company: Optional[str] = None,
        vendor_contact_name: Optional[str] = None,
        vendor_contact_email: Optional[str] = None,
        vendor_contact_phone: Optional[str] = None,
        client_company: Optional[str] = None,
        bill_rate: Optional[float] = None,
        pay_rate: Optional[float] = None,
        rate_type: str = 'HOURLY',
        currency: str = 'USD',
        submission_notes: Optional[str] = None,
        cover_letter: Optional[str] = None,
        tailored_resume_id: Optional[int] = None,
        priority: str = 'MEDIUM',
        is_hot: bool = False,
        follow_up_date: Optional[datetime] = None
    ) -> Submission:
        """
        Create a new submission.
        
        Args:
            user_id: ID of user creating the submission
            candidate_id: ID of candidate being submitted
            job_posting_id: ID of job posting
            vendor_company: Vendor/staffing agency name
            vendor_contact_name: Vendor contact name
            vendor_contact_email: Vendor contact email
            vendor_contact_phone: Vendor contact phone
            client_company: End client company name
            bill_rate: Bill rate ($/hr)
            pay_rate: Pay rate ($/hr)
            rate_type: HOURLY, DAILY, WEEKLY, MONTHLY, ANNUAL
            currency: Currency code (USD)
            submission_notes: Notes about the submission
            cover_letter: Cover letter text
            tailored_resume_id: ID of tailored resume used
            priority: HIGH, MEDIUM, LOW
            is_hot: Whether this is a hot/urgent submission
            follow_up_date: When to follow up
            
        Returns:
            Created Submission instance
            
        Raises:
            ValueError: If candidate/job not found or duplicate exists
        """
        # Validate candidate exists and belongs to tenant
        candidate = db.session.get(Candidate, candidate_id)
        if not candidate:
            raise ValueError(f"Candidate {candidate_id} not found")
        if candidate.tenant_id != self.tenant_id:
            raise ValueError(f"Candidate {candidate_id} does not belong to this tenant")
        
        # Validate job posting exists
        job_posting = db.session.get(JobPosting, job_posting_id)
        if not job_posting:
            raise ValueError(f"Job posting {job_posting_id} not found")
        
        # Check for duplicate submission
        existing = self.check_duplicate(candidate_id, job_posting_id)
        if existing:
            raise ValueError(
                f"Duplicate submission: Candidate {candidate_id} already submitted to job {job_posting_id} "
                f"(submission ID: {existing.id}, status: {existing.status})"
            )
        
        # Create submission
        submission = Submission(
            candidate_id=candidate_id,
            job_posting_id=job_posting_id,
            submitted_by_user_id=user_id,
            tenant_id=self.tenant_id,
            status=SubmissionStatus.SUBMITTED,
            status_changed_at=datetime.utcnow(),
            status_changed_by_id=user_id,
            vendor_company=vendor_company,
            vendor_contact_name=vendor_contact_name,
            vendor_contact_email=vendor_contact_email,
            vendor_contact_phone=vendor_contact_phone,
            client_company=client_company,
            bill_rate=Decimal(str(bill_rate)) if bill_rate else None,
            pay_rate=Decimal(str(pay_rate)) if pay_rate else None,
            rate_type=rate_type,
            currency=currency,
            submission_notes=submission_notes,
            cover_letter=cover_letter,
            tailored_resume_id=tailored_resume_id,
            priority=priority,
            is_hot=is_hot,
            follow_up_date=follow_up_date,
            submitted_at=datetime.utcnow(),
        )
        
        db.session.add(submission)
        db.session.flush()  # Get submission ID for activity
        
        # Create initial activity
        activity = SubmissionActivity(
            submission_id=submission.id,
            created_by_id=user_id,
            activity_type=ActivityType.CREATED,
            content=f"Submission created for {candidate.first_name} {candidate.last_name} to {job_posting.title} at {job_posting.company}",
            activity_metadata={
                'candidate_name': f"{candidate.first_name} {candidate.last_name}",
                'job_title': job_posting.title,
                'company': job_posting.company,
                'vendor_company': vendor_company,
            }
        )
        db.session.add(activity)
        
        db.session.commit()
        
        logger.info(f"Created submission {submission.id} for candidate {candidate_id} to job {job_posting_id}")
        
        return submission
    
    def create_external_submission(
        self,
        user_id: int,
        candidate_id: int,
        external_job_title: str,
        external_job_company: str,
        external_job_location: Optional[str] = None,
        external_job_url: Optional[str] = None,
        external_job_description: Optional[str] = None,
        vendor_company: Optional[str] = None,
        vendor_contact_name: Optional[str] = None,
        vendor_contact_email: Optional[str] = None,
        vendor_contact_phone: Optional[str] = None,
        client_company: Optional[str] = None,
        bill_rate: Optional[float] = None,
        pay_rate: Optional[float] = None,
        rate_type: str = 'HOURLY',
        currency: str = 'USD',
        submission_notes: Optional[str] = None,
        priority: str = 'MEDIUM',
        is_hot: bool = False,
        follow_up_date: Optional[datetime] = None
    ) -> Submission:
        """
        Create a submission for an external job (not in the job_postings table).
        
        This allows recruiters to track submissions to jobs they found outside
        the portal (LinkedIn, Dice, company websites, etc.).
        
        Args:
            user_id: ID of user creating the submission
            candidate_id: ID of candidate being submitted
            external_job_title: Job title
            external_job_company: Company name
            external_job_location: Job location
            external_job_url: URL to the original job posting
            external_job_description: Brief description or notes
            vendor_company: Vendor/staffing agency name
            vendor_contact_name: Vendor contact name
            vendor_contact_email: Vendor contact email
            vendor_contact_phone: Vendor contact phone
            client_company: End client company name
            bill_rate: Bill rate ($/hr)
            pay_rate: Pay rate ($/hr)
            rate_type: HOURLY, DAILY, WEEKLY, MONTHLY, ANNUAL
            currency: Currency code (USD)
            submission_notes: Notes about the submission
            priority: HIGH, MEDIUM, LOW
            is_hot: Whether this is a hot/urgent submission
            follow_up_date: When to follow up
            
        Returns:
            Created Submission instance
            
        Raises:
            ValueError: If candidate not found or required fields missing
        """
        # Validate required fields
        if not external_job_title or not external_job_title.strip():
            raise ValueError("Job title is required for external submissions")
        if not external_job_company or not external_job_company.strip():
            raise ValueError("Company name is required for external submissions")
        
        # Validate candidate exists and belongs to tenant
        candidate = db.session.get(Candidate, candidate_id)
        if not candidate:
            raise ValueError(f"Candidate {candidate_id} not found")
        if candidate.tenant_id != self.tenant_id:
            raise ValueError(f"Candidate {candidate_id} does not belong to this tenant")
        
        # Create submission with external job data
        submission = Submission(
            candidate_id=candidate_id,
            job_posting_id=None,  # No internal job posting
            is_external_job=True,
            external_job_title=external_job_title.strip(),
            external_job_company=external_job_company.strip(),
            external_job_location=external_job_location.strip() if external_job_location else None,
            external_job_url=external_job_url.strip() if external_job_url else None,
            external_job_description=external_job_description,
            submitted_by_user_id=user_id,
            tenant_id=self.tenant_id,
            status=SubmissionStatus.SUBMITTED,
            status_changed_at=datetime.utcnow(),
            status_changed_by_id=user_id,
            vendor_company=vendor_company,
            vendor_contact_name=vendor_contact_name,
            vendor_contact_email=vendor_contact_email,
            vendor_contact_phone=vendor_contact_phone,
            client_company=client_company,
            bill_rate=Decimal(str(bill_rate)) if bill_rate else None,
            pay_rate=Decimal(str(pay_rate)) if pay_rate else None,
            rate_type=rate_type,
            currency=currency,
            submission_notes=submission_notes,
            priority=priority,
            is_hot=is_hot,
            follow_up_date=follow_up_date,
            submitted_at=datetime.utcnow(),
        )
        
        db.session.add(submission)
        db.session.flush()  # Get submission ID for activity
        
        # Create initial activity
        activity = SubmissionActivity(
            submission_id=submission.id,
            created_by_id=user_id,
            activity_type=ActivityType.CREATED,
            content=f"Submission created for {candidate.first_name} {candidate.last_name} to {external_job_title} at {external_job_company} (external job)",
            activity_metadata={
                'candidate_name': f"{candidate.first_name} {candidate.last_name}",
                'job_title': external_job_title,
                'company': external_job_company,
                'is_external_job': True,
                'vendor_company': vendor_company,
                'job_url': external_job_url,
            }
        )
        db.session.add(activity)
        
        db.session.commit()
        
        logger.info(f"Created external submission {submission.id} for candidate {candidate_id} to {external_job_title} at {external_job_company}")
        
        return submission
    
    def get_submission(
        self,
        submission_id: int,
        include_candidate: bool = False,
        include_job: bool = False,
        include_activities: bool = False
    ) -> Optional[Submission]:
        """
        Get a submission by ID.
        
        Args:
            submission_id: Submission ID
            include_candidate: Whether to eagerly load candidate
            include_job: Whether to eagerly load job posting
            include_activities: Whether to eagerly load activities
            
        Returns:
            Submission instance or None if not found
        """
        query = select(Submission).where(
            and_(
                Submission.id == submission_id,
                Submission.tenant_id == self.tenant_id
            )
        )
        
        submission = db.session.scalar(query)
        
        if submission:
            # Force load relationships if requested
            if include_candidate and submission.candidate:
                _ = submission.candidate.first_name
            if include_job and submission.job_posting:
                _ = submission.job_posting.title
            if include_activities:
                _ = list(submission.activities)
        
        return submission
    
    def get_submissions(
        self,
        status: Optional[str] = None,
        statuses: Optional[List[str]] = None,
        candidate_id: Optional[int] = None,
        job_posting_id: Optional[int] = None,
        submitted_by_user_id: Optional[int] = None,
        vendor_company: Optional[str] = None,
        client_company: Optional[str] = None,
        priority: Optional[str] = None,
        is_hot: Optional[bool] = None,
        is_active: Optional[bool] = None,
        submitted_after: Optional[datetime] = None,
        submitted_before: Optional[datetime] = None,
        interview_after: Optional[datetime] = None,
        interview_before: Optional[datetime] = None,
        page: int = 1,
        per_page: int = 20,
        sort_by: str = 'submitted_at',
        sort_order: str = 'desc'
    ) -> Tuple[List[Submission], int]:
        """
        Get submissions with filters and pagination.
        
        Args:
            status: Filter by single status
            statuses: Filter by multiple statuses
            candidate_id: Filter by candidate
            job_posting_id: Filter by job posting
            submitted_by_user_id: Filter by submitting user
            vendor_company: Filter by vendor company (partial match)
            client_company: Filter by client company (partial match)
            priority: Filter by priority
            is_hot: Filter by hot flag
            is_active: Filter active (non-terminal) submissions
            submitted_after: Filter by submission date
            submitted_before: Filter by submission date
            interview_after: Filter by interview date
            interview_before: Filter by interview date
            page: Page number (1-indexed)
            per_page: Items per page
            sort_by: Field to sort by
            sort_order: 'asc' or 'desc'
            
        Returns:
            Tuple of (list of submissions, total count)
        """
        query = select(Submission).where(Submission.tenant_id == self.tenant_id)
        
        # Apply filters
        if status:
            query = query.where(Submission.status == status)
        
        if statuses:
            query = query.where(Submission.status.in_(statuses))
        
        if candidate_id:
            query = query.where(Submission.candidate_id == candidate_id)
        
        if job_posting_id:
            query = query.where(Submission.job_posting_id == job_posting_id)
        
        if submitted_by_user_id:
            query = query.where(Submission.submitted_by_user_id == submitted_by_user_id)
        
        if vendor_company:
            query = query.where(Submission.vendor_company.ilike(f"%{vendor_company}%"))
        
        if client_company:
            query = query.where(Submission.client_company.ilike(f"%{client_company}%"))
        
        if priority:
            query = query.where(Submission.priority == priority)
        
        if is_hot is not None:
            query = query.where(Submission.is_hot == is_hot)
        
        if is_active is not None:
            if is_active:
                query = query.where(Submission.status.in_(SubmissionStatus.active()))
            else:
                query = query.where(Submission.status.in_(SubmissionStatus.terminal()))
        
        if submitted_after:
            query = query.where(Submission.submitted_at >= submitted_after)
        
        if submitted_before:
            query = query.where(Submission.submitted_at <= submitted_before)
        
        if interview_after:
            query = query.where(Submission.interview_scheduled_at >= interview_after)
        
        if interview_before:
            query = query.where(Submission.interview_scheduled_at <= interview_before)
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = db.session.scalar(count_query) or 0
        
        # Apply sorting
        sort_column = getattr(Submission, sort_by, Submission.submitted_at)
        if sort_order == 'desc':
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)
        
        # Apply pagination
        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)
        
        submissions = list(db.session.scalars(query))
        
        return submissions, total
    
    def update_submission(
        self,
        submission_id: int,
        user_id: int,
        data: Dict[str, Any]
    ) -> Submission:
        """
        Update a submission.
        
        Args:
            submission_id: Submission ID
            user_id: ID of user making the update
            data: Fields to update
            
        Returns:
            Updated Submission instance
            
        Raises:
            ValueError: If submission not found
        """
        submission = self.get_submission(submission_id)
        if not submission:
            raise ValueError(f"Submission {submission_id} not found")
        
        # Track changes for activity log
        changes = []
        
        # Allowed update fields
        allowed_fields = [
            'vendor_company', 'vendor_contact_name', 'vendor_contact_email',
            'vendor_contact_phone', 'client_company', 'submission_notes',
            'cover_letter', 'tailored_resume_id', 'interview_notes',
            'interview_feedback', 'priority', 'is_hot', 'follow_up_date'
        ]
        
        for field in allowed_fields:
            if field in data:
                old_value = getattr(submission, field)
                new_value = data[field]
                if old_value != new_value:
                    setattr(submission, field, new_value)
                    changes.append(f"{field}: {old_value} -> {new_value}")
        
        # Handle rate updates specially (creates activity)
        if 'bill_rate' in data or 'pay_rate' in data:
            old_bill = float(submission.bill_rate) if submission.bill_rate else None
            old_pay = float(submission.pay_rate) if submission.pay_rate else None
            
            if 'bill_rate' in data:
                submission.bill_rate = Decimal(str(data['bill_rate'])) if data['bill_rate'] else None
            if 'pay_rate' in data:
                submission.pay_rate = Decimal(str(data['pay_rate'])) if data['pay_rate'] else None
            if 'rate_type' in data:
                submission.rate_type = data['rate_type']
            if 'currency' in data:
                submission.currency = data['currency']
            
            new_bill = float(submission.bill_rate) if submission.bill_rate else None
            new_pay = float(submission.pay_rate) if submission.pay_rate else None
            
            if old_bill != new_bill or old_pay != new_pay:
                activity = SubmissionActivity(
                    submission_id=submission_id,
                    created_by_id=user_id,
                    activity_type=ActivityType.RATE_UPDATED,
                    content=f"Rates updated: Bill ${old_bill} -> ${new_bill}, Pay ${old_pay} -> ${new_pay}",
                    activity_metadata={
                        'old_bill_rate': old_bill,
                        'new_bill_rate': new_bill,
                        'old_pay_rate': old_pay,
                        'new_pay_rate': new_pay,
                    }
                )
                db.session.add(activity)
        
        # Handle priority change (creates activity)
        if 'priority' in data:
            old_priority = submission.priority
            if old_priority != data['priority']:
                activity = SubmissionActivity(
                    submission_id=submission_id,
                    created_by_id=user_id,
                    activity_type=ActivityType.PRIORITY_CHANGED,
                    old_value=old_priority,
                    new_value=data['priority'],
                    content=f"Priority changed from {old_priority} to {data['priority']}",
                )
                db.session.add(activity)
        
        # Handle vendor update (creates activity)
        vendor_fields = ['vendor_company', 'vendor_contact_name', 'vendor_contact_email', 'vendor_contact_phone']
        vendor_changed = any(f in data for f in vendor_fields)
        if vendor_changed:
            activity = SubmissionActivity(
                submission_id=submission_id,
                created_by_id=user_id,
                activity_type=ActivityType.VENDOR_UPDATED,
                content="Vendor information updated",
                activity_metadata={f: data.get(f) for f in vendor_fields if f in data}
            )
            db.session.add(activity)
        
        # Handle follow-up date (creates activity)
        if 'follow_up_date' in data:
            follow_up = data['follow_up_date']
            if follow_up:
                activity = SubmissionActivity(
                    submission_id=submission_id,
                    created_by_id=user_id,
                    activity_type=ActivityType.FOLLOW_UP_SET,
                    content=f"Follow-up scheduled for {follow_up.strftime('%B %d, %Y') if hasattr(follow_up, 'strftime') else follow_up}",
                    activity_metadata={'follow_up_date': follow_up.isoformat() if hasattr(follow_up, 'isoformat') else str(follow_up)}
                )
                db.session.add(activity)
        
        db.session.commit()
        
        logger.info(f"Updated submission {submission_id}: {', '.join(changes) if changes else 'no field changes'}")
        
        return submission
    
    def update_status(
        self,
        submission_id: int,
        user_id: int,
        new_status: str,
        note: Optional[str] = None,
        rejection_reason: Optional[str] = None,
        rejection_stage: Optional[str] = None,
        withdrawal_reason: Optional[str] = None,
        placement_start_date: Optional[datetime] = None,
        placement_end_date: Optional[datetime] = None,
        placement_duration_months: Optional[int] = None
    ) -> Submission:
        """
        Update submission status with activity logging.
        
        Args:
            submission_id: Submission ID
            user_id: ID of user making the change
            new_status: New status value
            note: Optional note about the status change
            rejection_reason: Reason if rejecting
            rejection_stage: Stage at which rejected
            withdrawal_reason: Reason if withdrawing
            placement_start_date: Start date if placed
            placement_end_date: End date if placed
            placement_duration_months: Duration if placed
            
        Returns:
            Updated Submission instance
            
        Raises:
            ValueError: If submission not found or invalid status
        """
        submission = self.get_submission(submission_id)
        if not submission:
            raise ValueError(f"Submission {submission_id} not found")
        
        # Validate status
        if new_status not in SubmissionStatus.all():
            raise ValueError(f"Invalid status: {new_status}. Must be one of: {', '.join(SubmissionStatus.all())}")
        
        old_status = submission.status
        
        # Prevent changing from terminal status (unless withdrawing)
        if submission.is_terminal and new_status != SubmissionStatus.WITHDRAWN:
            raise ValueError(f"Cannot change status from terminal status {old_status}")
        
        # Update status
        submission.status = new_status
        submission.status_changed_at = datetime.utcnow()
        submission.status_changed_by_id = user_id
        
        # Handle status-specific fields
        if new_status == SubmissionStatus.REJECTED:
            submission.rejection_reason = rejection_reason
            submission.rejection_stage = rejection_stage or old_status
        
        if new_status == SubmissionStatus.WITHDRAWN:
            submission.withdrawal_reason = withdrawal_reason
        
        if new_status == SubmissionStatus.PLACED:
            submission.placement_start_date = placement_start_date
            submission.placement_end_date = placement_end_date
            submission.placement_duration_months = placement_duration_months
        
        # Create status change activity
        activity = SubmissionActivity.create_status_change(
            submission_id=submission_id,
            old_status=old_status,
            new_status=new_status,
            created_by_id=user_id,
            note=note
        )
        db.session.add(activity)
        
        db.session.commit()
        
        logger.info(f"Submission {submission_id} status changed: {old_status} -> {new_status}")
        
        return submission
    
    def delete_submission(self, submission_id: int) -> bool:
        """
        Delete a submission.
        
        Args:
            submission_id: Submission ID
            
        Returns:
            True if deleted, False if not found
        """
        submission = self.get_submission(submission_id)
        if not submission:
            return False
        
        db.session.delete(submission)
        db.session.commit()
        
        logger.info(f"Deleted submission {submission_id}")
        
        return True
    
    # ==================== Relationship Queries ====================
    
    def get_candidate_submissions(
        self,
        candidate_id: int,
        include_job: bool = True
    ) -> List[Submission]:
        """
        Get all submissions for a candidate.
        
        Args:
            candidate_id: Candidate ID
            include_job: Whether to eagerly load job data
            
        Returns:
            List of submissions sorted by date (newest first)
        """
        query = select(Submission).where(
            and_(
                Submission.candidate_id == candidate_id,
                Submission.tenant_id == self.tenant_id
            )
        ).order_by(desc(Submission.submitted_at))
        
        submissions = list(db.session.scalars(query))
        
        # Force load job if requested
        if include_job:
            for sub in submissions:
                if sub.job_posting:
                    _ = sub.job_posting.title
        
        return submissions
    
    def get_job_submissions(
        self,
        job_posting_id: int,
        include_candidate: bool = True
    ) -> List[Submission]:
        """
        Get all submissions for a job posting.
        
        Args:
            job_posting_id: Job posting ID
            include_candidate: Whether to eagerly load candidate data
            
        Returns:
            List of submissions sorted by date (newest first)
        """
        query = select(Submission).where(
            and_(
                Submission.job_posting_id == job_posting_id,
                Submission.tenant_id == self.tenant_id
            )
        ).order_by(desc(Submission.submitted_at))
        
        submissions = list(db.session.scalars(query))
        
        # Force load candidate if requested
        if include_candidate:
            for sub in submissions:
                if sub.candidate:
                    _ = sub.candidate.first_name
        
        return submissions
    
    def get_user_submissions(
        self,
        user_id: int,
        is_active_only: bool = False
    ) -> List[Submission]:
        """
        Get all submissions made by a user.
        
        Args:
            user_id: User ID
            is_active_only: Only return active (non-terminal) submissions
            
        Returns:
            List of submissions sorted by date (newest first)
        """
        query = select(Submission).where(
            and_(
                Submission.submitted_by_user_id == user_id,
                Submission.tenant_id == self.tenant_id
            )
        )
        
        if is_active_only:
            query = query.where(Submission.status.in_(SubmissionStatus.active()))
        
        query = query.order_by(desc(Submission.submitted_at))
        
        return list(db.session.scalars(query))
    
    # ==================== Activity Management ====================
    
    def add_activity(
        self,
        submission_id: int,
        user_id: int,
        activity_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None
    ) -> SubmissionActivity:
        """
        Add an activity/note to a submission.
        
        Args:
            submission_id: Submission ID
            user_id: ID of user creating the activity
            activity_type: Type of activity (NOTE, EMAIL_SENT, CALL_LOGGED, etc.)
            content: Activity content/description
            metadata: Additional metadata (email details, etc.)
            old_value: Previous value (for change tracking)
            new_value: New value (for change tracking)
            
        Returns:
            Created SubmissionActivity instance
            
        Raises:
            ValueError: If submission not found or invalid activity type
        """
        # Validate submission exists
        submission = self.get_submission(submission_id)
        if not submission:
            raise ValueError(f"Submission {submission_id} not found")
        
        # Validate activity type
        if activity_type not in ActivityType.all():
            raise ValueError(f"Invalid activity type: {activity_type}. Must be one of: {', '.join(ActivityType.all())}")
        
        activity = SubmissionActivity(
            submission_id=submission_id,
            created_by_id=user_id,
            activity_type=activity_type,
            content=content,
            activity_metadata=metadata or {},
            old_value=old_value,
            new_value=new_value,
        )
        
        db.session.add(activity)
        db.session.commit()
        
        logger.info(f"Added {activity_type} activity to submission {submission_id}")
        
        return activity
    
    def get_activities(
        self,
        submission_id: int,
        limit: int = 50,
        activity_type: Optional[str] = None
    ) -> List[SubmissionActivity]:
        """
        Get activities for a submission.
        
        Args:
            submission_id: Submission ID
            limit: Maximum number of activities to return
            activity_type: Filter by activity type
            
        Returns:
            List of activities sorted by date (newest first)
        """
        query = select(SubmissionActivity).where(
            SubmissionActivity.submission_id == submission_id
        )
        
        if activity_type:
            query = query.where(SubmissionActivity.activity_type == activity_type)
        
        query = query.order_by(desc(SubmissionActivity.created_at)).limit(limit)
        
        return list(db.session.scalars(query))
    
    # ==================== Interview Scheduling ====================
    
    def schedule_interview(
        self,
        submission_id: int,
        user_id: int,
        interview_scheduled_at: datetime,
        interview_type: str,
        interview_location: Optional[str] = None,
        interview_notes: Optional[str] = None
    ) -> Submission:
        """
        Schedule an interview for a submission.
        
        Args:
            submission_id: Submission ID
            user_id: ID of user scheduling the interview
            interview_scheduled_at: Interview date/time
            interview_type: Type of interview (PHONE, VIDEO, ONSITE, TECHNICAL)
            interview_location: Location or video link
            interview_notes: Notes about the interview
            
        Returns:
            Updated Submission instance
            
        Raises:
            ValueError: If submission not found
        """
        submission = self.get_submission(submission_id)
        if not submission:
            raise ValueError(f"Submission {submission_id} not found")
        
        # Update interview fields
        submission.interview_scheduled_at = interview_scheduled_at
        submission.interview_type = interview_type
        submission.interview_location = interview_location
        submission.interview_notes = interview_notes
        
        # Auto-update status to INTERVIEW_SCHEDULED if currently SUBMITTED or CLIENT_REVIEW
        if submission.status in [SubmissionStatus.SUBMITTED, SubmissionStatus.CLIENT_REVIEW]:
            old_status = submission.status
            submission.status = SubmissionStatus.INTERVIEW_SCHEDULED
            submission.status_changed_at = datetime.utcnow()
            submission.status_changed_by_id = user_id
            
            # Create status change activity
            status_activity = SubmissionActivity.create_status_change(
                submission_id=submission_id,
                old_status=old_status,
                new_status=SubmissionStatus.INTERVIEW_SCHEDULED,
                created_by_id=user_id,
                note="Status auto-updated when interview was scheduled"
            )
            db.session.add(status_activity)
        
        # Create interview scheduled activity
        activity = SubmissionActivity.create_interview_scheduled(
            submission_id=submission_id,
            interview_date=interview_scheduled_at,
            interview_type=interview_type,
            created_by_id=user_id,
            note=interview_notes,
            location=interview_location
        )
        db.session.add(activity)
        
        db.session.commit()
        
        logger.info(f"Interview scheduled for submission {submission_id} at {interview_scheduled_at}")
        
        return submission
    
    # ==================== Statistics ====================
    
    def get_stats(
        self,
        user_id: Optional[int] = None,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """
        Get submission statistics.
        
        Args:
            user_id: Optional filter by user (for personal stats)
            days_back: Number of days to look back for time-based stats
            
        Returns:
            Dictionary with:
            - total: Total submissions
            - by_status: Count by status
            - submitted_this_week: Submissions in last 7 days
            - submitted_this_month: Submissions in last 30 days
            - interviews_scheduled: Count of scheduled interviews
            - placements_this_month: Placements in last 30 days
            - average_days_to_placement: Average time to placement
            - interview_rate: % of submissions that got interviews
            - placement_rate: % of submissions that got placed
        """
        base_query = select(Submission).where(Submission.tenant_id == self.tenant_id)
        
        if user_id:
            base_query = base_query.where(Submission.submitted_by_user_id == user_id)
        
        # Total count
        total_query = select(func.count()).select_from(base_query.subquery())
        total = db.session.scalar(total_query) or 0
        
        # Count by status
        status_query = select(
            Submission.status,
            func.count(Submission.id)
        ).where(Submission.tenant_id == self.tenant_id)
        
        if user_id:
            status_query = status_query.where(Submission.submitted_by_user_id == user_id)
        
        status_query = status_query.group_by(Submission.status)
        status_results = db.session.execute(status_query).all()
        by_status = {status: count for status, count in status_results}
        
        # Time-based calculations
        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        # Submitted this week
        week_query = select(func.count()).where(
            and_(
                Submission.tenant_id == self.tenant_id,
                Submission.submitted_at >= week_ago
            )
        )
        if user_id:
            week_query = week_query.where(Submission.submitted_by_user_id == user_id)
        submitted_this_week = db.session.scalar(week_query) or 0
        
        # Submitted this month
        month_query = select(func.count()).where(
            and_(
                Submission.tenant_id == self.tenant_id,
                Submission.submitted_at >= month_ago
            )
        )
        if user_id:
            month_query = month_query.where(Submission.submitted_by_user_id == user_id)
        submitted_this_month = db.session.scalar(month_query) or 0
        
        # Interviews scheduled (submissions in INTERVIEW_SCHEDULED status or with upcoming interviews)
        interview_query = select(func.count()).where(
            and_(
                Submission.tenant_id == self.tenant_id,
                or_(
                    Submission.status == SubmissionStatus.INTERVIEW_SCHEDULED,
                    Submission.interview_scheduled_at >= now
                )
            )
        )
        if user_id:
            interview_query = interview_query.where(Submission.submitted_by_user_id == user_id)
        interviews_scheduled = db.session.scalar(interview_query) or 0
        
        # Placements this month
        placement_query = select(func.count()).where(
            and_(
                Submission.tenant_id == self.tenant_id,
                Submission.status == SubmissionStatus.PLACED,
                Submission.status_changed_at >= month_ago
            )
        )
        if user_id:
            placement_query = placement_query.where(Submission.submitted_by_user_id == user_id)
        placements_this_month = db.session.scalar(placement_query) or 0
        
        # Calculate rates
        interview_statuses = [
            SubmissionStatus.INTERVIEW_SCHEDULED,
            SubmissionStatus.INTERVIEWED,
            SubmissionStatus.OFFERED,
            SubmissionStatus.PLACED
        ]
        interview_count = sum(by_status.get(s, 0) for s in interview_statuses)
        interview_rate = round((interview_count / total) * 100, 2) if total > 0 else 0.0
        
        placement_count = by_status.get(SubmissionStatus.PLACED, 0)
        placement_rate = round((placement_count / total) * 100, 2) if total > 0 else 0.0
        
        # Average days to placement (for placed submissions)
        # This would require more complex calculation using status_changed_at vs submitted_at
        # For now, return None if no data
        avg_days_to_placement = None
        if placement_count > 0:
            # Calculate average for placed submissions
            placed_query = select(
                func.avg(
                    func.extract('epoch', Submission.status_changed_at) - 
                    func.extract('epoch', Submission.submitted_at)
                ) / 86400  # Convert seconds to days
            ).where(
                and_(
                    Submission.tenant_id == self.tenant_id,
                    Submission.status == SubmissionStatus.PLACED
                )
            )
            if user_id:
                placed_query = placed_query.where(Submission.submitted_by_user_id == user_id)
            
            avg_seconds = db.session.scalar(placed_query)
            if avg_seconds:
                avg_days_to_placement = round(float(avg_seconds), 1)
        
        return {
            'total': total,
            'by_status': by_status,
            'submitted_this_week': submitted_this_week,
            'submitted_this_month': submitted_this_month,
            'interviews_scheduled': interviews_scheduled,
            'placements_this_month': placements_this_month,
            'average_days_to_placement': avg_days_to_placement,
            'interview_rate': interview_rate,
            'placement_rate': placement_rate,
        }
    
    # ==================== Utilities ====================
    
    def check_duplicate(
        self,
        candidate_id: int,
        job_posting_id: int
    ) -> Optional[Submission]:
        """
        Check if a submission already exists for this candidate-job pair.
        
        Args:
            candidate_id: Candidate ID
            job_posting_id: Job posting ID
            
        Returns:
            Existing Submission if found, None otherwise
        """
        query = select(Submission).where(
            and_(
                Submission.candidate_id == candidate_id,
                Submission.job_posting_id == job_posting_id,
                Submission.tenant_id == self.tenant_id
            )
        )
        
        return db.session.scalar(query)
    
    def get_upcoming_follow_ups(
        self,
        user_id: Optional[int] = None,
        days_ahead: int = 7
    ) -> List[Submission]:
        """
        Get submissions with upcoming follow-up dates.
        
        Args:
            user_id: Optional filter by user
            days_ahead: Number of days ahead to look
            
        Returns:
            List of submissions with follow-ups in the specified window
        """
        now = datetime.utcnow()
        future = now + timedelta(days=days_ahead)
        
        query = select(Submission).where(
            and_(
                Submission.tenant_id == self.tenant_id,
                Submission.follow_up_date >= now,
                Submission.follow_up_date <= future,
                Submission.status.in_(SubmissionStatus.active())
            )
        )
        
        if user_id:
            query = query.where(Submission.submitted_by_user_id == user_id)
        
        query = query.order_by(Submission.follow_up_date)
        
        return list(db.session.scalars(query))
    
    def get_overdue_follow_ups(
        self,
        user_id: Optional[int] = None
    ) -> List[Submission]:
        """
        Get submissions with overdue follow-up dates.
        
        Args:
            user_id: Optional filter by user
            
        Returns:
            List of submissions with past follow-up dates (still active)
        """
        now = datetime.utcnow()
        
        query = select(Submission).where(
            and_(
                Submission.tenant_id == self.tenant_id,
                Submission.follow_up_date < now,
                Submission.status.in_(SubmissionStatus.active())
            )
        )
        
        if user_id:
            query = query.where(Submission.submitted_by_user_id == user_id)
        
        query = query.order_by(Submission.follow_up_date)
        
        return list(db.session.scalars(query))
