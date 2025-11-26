"""
Candidate Service
Business logic for candidate management and resume parsing
"""
import os
from typing import Optional, Dict, Any, List
from datetime import datetime
from werkzeug.datastructures import FileStorage

from app import db
from app.models.candidate import Candidate
from app.services.file_storage import LegacyResumeStorageService
from app.services.resume_parser import ResumeParserService
from app.utils.text_extractor import TextExtractor
from app.utils.skills_matcher import SkillsMatcher


class CandidateService:
    """
    Service for candidate operations including resume parsing
    """
    
    def __init__(self):
        self.file_storage = LegacyResumeStorageService()
        self.parser = None  # Lazy initialization
        self.skills_matcher = SkillsMatcher()
    
    def _get_parser(self) -> ResumeParserService:
        """Lazy initialize parser (expensive operation)"""
        if self.parser is None:
            self.parser = ResumeParserService()
        return self.parser
    
    def upload_and_parse_resume(
        self,
        file: FileStorage,
        tenant_id: int,
        candidate_id: Optional[int] = None,
        auto_create: bool = True,
    ) -> Dict[str, Any]:
        """
        Upload resume file and parse its contents
        
        Args:
            file: Uploaded file
            tenant_id: Tenant ID
            candidate_id: Existing candidate ID (if updating)
            auto_create: Create candidate if candidate_id not provided
        
        Returns:
            {
                'candidate_id': int,
                'file_info': {...},
                'parsed_data': {...},
                'status': 'success' | 'error'
            }
        """
        try:
            # Stage 1: Upload file
            upload_result = self.file_storage.upload_resume(
                file=file,
                tenant_id=tenant_id,
                candidate_id=candidate_id,
            )
            
            # Check upload success
            if not upload_result.get('success', False):
                return {
                    'candidate_id': candidate_id,
                    'status': 'error',
                    'error': upload_result.get('error', 'File upload failed'),
                }
            
            file_path = upload_result['file_path']
            
            # Stage 2: Extract text
            print(f"[DEBUG] Extracting text from: {file_path}")
            extracted = TextExtractor.extract_from_file(file_path)
            text = TextExtractor.clean_text(extracted['text'])
            print(f"[DEBUG] Extracted {len(text)} characters")
            
            # Stage 3: Parse with hybrid approach
            print(f"[DEBUG] Parsing resume with AI...")
            parser = self._get_parser()
            parsed_data = parser.parse_resume(text, file_type=upload_result['extension'])
            print(f"[DEBUG] Parsing complete")
            
            # Stage 4: Enhance skills with matcher
            if parsed_data.get('skills'):
                skills_analysis = self.skills_matcher.extract_skills(' '.join(parsed_data['skills']))
                parsed_data['skills'] = skills_analysis['matched_skills']
                parsed_data['skills_categories'] = skills_analysis['categories']
            
            # Stage 5: Create or update candidate
            print(f"[DEBUG] Creating/updating candidate...")
            if candidate_id:
                candidate = self._update_candidate(candidate_id, parsed_data, upload_result)
            elif auto_create:
                candidate = self._create_candidate(tenant_id, parsed_data, upload_result)
            else:
                # Just return parsed data without saving
                return {
                    'candidate_id': None,
                    'file_info': upload_result,
                    'parsed_data': parsed_data,
                    'extracted_metadata': extracted,
                    'status': 'success',
                }
            
            db.session.commit()
            print(f"[DEBUG] Candidate saved: ID={candidate.id}")
            
            # Verify data was saved
            db.session.refresh(candidate)
            print(f"[DEBUG] After commit - work_experience count: {len(candidate.work_experience or [])}")
            print(f"[DEBUG] After commit - education count: {len(candidate.education or [])}")
            if candidate.work_experience:
                print(f"[DEBUG] After commit - first work_experience: {candidate.work_experience[0]}")
            
            return {
                'candidate_id': candidate.id,
                'file_info': upload_result,
                'parsed_data': parsed_data,
                'extracted_metadata': extracted,
                'status': 'success',
            }
        
        except Exception as e:
            print(f"[ERROR] Upload and parse failed: {str(e)}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            return {
                'candidate_id': candidate_id,
                'status': 'error',
                'error': str(e),
            }
    
    def _create_candidate(
        self,
        tenant_id: int,
        parsed_data: Dict,
        file_info: Dict,
    ) -> Candidate:
        """
        Create new candidate from parsed data
        """
        full_name = parsed_data.get('full_name') or 'Unknown'
        first_name = self._extract_first_name(full_name) or 'Unknown'
        last_name = self._extract_last_name(full_name) or 'Unknown'
        email = parsed_data.get('email')
        
        print(f"[DEBUG] Creating candidate: full_name={full_name}, first={first_name}, last={last_name}, email={email}")
        
        # Check for duplicate by email OR name combination
        from sqlalchemy import select, and_
        
        if email:
            # Primary check: email
            stmt = select(Candidate).where(
                Candidate.tenant_id == tenant_id,
                Candidate.email == email
            )
            existing = db.session.scalar(stmt)
            if existing:
                print(f"[WARNING] Candidate with email {email} already exists (ID: {existing.id}). Updating instead of creating.")
                return self._update_candidate(existing.id, parsed_data, file_info)
        
        # Secondary check: first_name + last_name combination (case-insensitive)
        from sqlalchemy import func
        stmt = select(Candidate).where(
            and_(
                Candidate.tenant_id == tenant_id,
                func.lower(Candidate.first_name) == func.lower(first_name),
                func.lower(Candidate.last_name) == func.lower(last_name)
            )
        )
        existing = db.session.scalar(stmt)
        if existing:
            print(f"[WARNING] Candidate with name {first_name} {last_name} already exists (ID: {existing.id}). Updating instead of creating.")
            return self._update_candidate(existing.id, parsed_data, file_info)
        
        print(f"[DEBUG] Work experience count from parsed_data: {len(parsed_data.get('work_experience', []))}")
        print(f"[DEBUG] Education count from parsed_data: {len(parsed_data.get('education', []))}")
        print(f"[DEBUG] Skills count from parsed_data: {len(parsed_data.get('skills', []))}")
        
        work_exp_data = parsed_data.get('work_experience', [])
        education_data = parsed_data.get('education', [])
        
        if work_exp_data:
            print(f"[DEBUG] First work experience: {work_exp_data[0]}")
        if education_data:
            print(f"[DEBUG] First education: {education_data[0]}")
        
        candidate = Candidate(
            tenant_id=tenant_id,
            
            # Basic info - ensure no nulls
            first_name=first_name,
            last_name=last_name,
            email=parsed_data.get('email'),
            phone=parsed_data.get('phone'),
            full_name=full_name,
            
            # Resume file
            resume_file_path=file_info['file_path'],
            resume_file_url=file_info['file_url'],
            resume_uploaded_at=datetime.utcnow(),
            resume_parsed_at=datetime.utcnow(),
            
            # Professional info
            location=parsed_data.get('location'),
            linkedin_url=parsed_data.get('linkedin_url'),
            portfolio_url=parsed_data.get('portfolio_url'),
            current_title=parsed_data.get('current_title'),
            total_experience_years=parsed_data.get('total_experience_years'),
            professional_summary=parsed_data.get('professional_summary'),
            
            # Arrays
            skills=parsed_data.get('skills', []),
            certifications=parsed_data.get('certifications', []),
            languages=parsed_data.get('languages', []),
            preferred_locations=parsed_data.get('preferred_locations', []),
            
            # JSONB data
            education=education_data,
            work_experience=work_exp_data,
            
            # Store full parsed data
            parsed_resume_data=parsed_data,
            
            # Default values
            status='new',
            source='resume_upload',
            onboarding_status='PENDING_ASSIGNMENT',  # Ready for HR to assign
        )
        
        print(f"[DEBUG] Candidate object created with work_experience: {len(candidate.work_experience or [])} items")
        print(f"[DEBUG] Candidate object created with education: {len(candidate.education or [])} items")
        
        db.session.add(candidate)
        return candidate
    
    def _update_candidate(
        self,
        candidate_id: int,
        parsed_data: Dict,
        file_info: Dict,
    ) -> Candidate:
        """
        Update existing candidate with parsed data
        """
        candidate = db.session.get(Candidate, candidate_id)
        
        if not candidate:
            raise ValueError(f"Candidate {candidate_id} not found")
        
        # Update resume file
        candidate.resume_file_path = file_info['file_path']
        candidate.resume_file_url = file_info['file_url']
        candidate.resume_uploaded_at = datetime.utcnow()
        candidate.resume_parsed_at = datetime.utcnow()
        
        # Update fields if not already set or if empty
        if not candidate.full_name and parsed_data.get('full_name'):
            candidate.full_name = parsed_data['full_name']
            candidate.first_name = self._extract_first_name(parsed_data['full_name'])
            candidate.last_name = self._extract_last_name(parsed_data['full_name'])
        
        if not candidate.email and parsed_data.get('email'):
            candidate.email = parsed_data['email']
        
        if not candidate.phone and parsed_data.get('phone'):
            candidate.phone = parsed_data['phone']
        
        if not candidate.location and parsed_data.get('location'):
            candidate.location = parsed_data['location']
        
        if not candidate.linkedin_url and parsed_data.get('linkedin_url'):
            candidate.linkedin_url = parsed_data['linkedin_url']
        
        if not candidate.current_title and parsed_data.get('current_title'):
            candidate.current_title = parsed_data['current_title']
        
        if not candidate.professional_summary and parsed_data.get('professional_summary'):
            candidate.professional_summary = parsed_data['professional_summary']
        
        # Update arrays (merge, don't replace)
        if parsed_data.get('skills'):
            existing_skills = set(candidate.skills or [])
            new_skills = set(parsed_data['skills'])
            candidate.skills = list(existing_skills | new_skills)
        
        if parsed_data.get('certifications'):
            existing_certs = set(candidate.certifications or [])
            new_certs = set(parsed_data['certifications'])
            candidate.certifications = list(existing_certs | new_certs)
        
        if parsed_data.get('languages'):
            existing_langs = set(candidate.languages or [])
            new_langs = set(parsed_data['languages'])
            candidate.languages = list(existing_langs | new_langs)
        
        # Update JSONB data
        candidate.education = parsed_data.get('education', candidate.education)
        candidate.work_experience = parsed_data.get('work_experience', candidate.work_experience)
        
        # Store full parsed data
        candidate.parsed_resume_data = parsed_data
        
        return candidate
    
    def _extract_first_name(self, full_name: Optional[str]) -> Optional[str]:
        """Extract first name from full name"""
        if not full_name:
            return None
        
        parts = full_name.strip().split()
        return parts[0] if parts else None
    
    def _extract_last_name(self, full_name: Optional[str]) -> Optional[str]:
        """Extract last name from full name"""
        if not full_name:
            return None
        
        parts = full_name.strip().split()
        if len(parts) > 1:
            return ' '.join(parts[1:])
        else:
            # If only one word, use it as last name too
            return parts[0] if parts else None
    
    def get_candidate(self, candidate_id: int, tenant_id: Optional[int] = None) -> Optional[Candidate]:
        """
        Get candidate by ID
        
        Args:
            candidate_id: Candidate ID
            tenant_id: Optional tenant ID for access control
        """
        candidate = db.session.get(Candidate, candidate_id)
        
        if candidate and tenant_id and candidate.tenant_id != tenant_id:
            return None  # Access denied
        
        return candidate
    
    def list_candidates(
        self,
        tenant_id: int,
        status: Optional[str] = None,
        skills: Optional[List[str]] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> Dict[str, Any]:
        """
        List candidates with filters
        
        Args:
            tenant_id: Tenant ID
            status: Filter by status
            skills: Filter by skills (candidates with ANY of these skills)
            page: Page number
            per_page: Items per page
        
        Returns:
            {
                'candidates': [...],
                'total': int,
                'page': int,
                'per_page': int,
                'pages': int
            }
        """
        from sqlalchemy import select, func, or_
        
        query = select(Candidate).where(Candidate.tenant_id == tenant_id)
        
        if status:
            query = query.where(Candidate.status == status)
        
        if skills:
            # PostgreSQL array overlap operator
            # Check if candidate.skills has any overlap with provided skills
            from sqlalchemy.dialects.postgresql import array
            query = query.where(Candidate.skills.overlap(skills))
        
        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = db.session.scalar(count_query)
        
        # Paginate
        query = query.order_by(Candidate.created_at.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)
        
        candidates = list(db.session.scalars(query))
        
        return {
            'candidates': candidates,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page,
        }
    
    def update_candidate(
        self,
        candidate_id: int,
        tenant_id: int,
        data: Dict[str, Any],
    ) -> Optional[Candidate]:
        """
        Update candidate fields
        
        Args:
            candidate_id: Candidate ID
            tenant_id: Tenant ID (for access control)
            data: Fields to update
        
        Returns:
            Updated candidate or None
        """
        candidate = self.get_candidate(candidate_id, tenant_id)
        
        if not candidate:
            return None
        
        # Update allowed fields
        allowed_fields = [
            'first_name', 'last_name', 'email', 'phone', 'full_name',
            'location', 'linkedin_url', 'portfolio_url', 'current_title',
            'total_experience_years', 'notice_period', 'expected_salary',
            'professional_summary', 'status', 'source',
            'skills', 'certifications', 'languages', 'preferred_locations',
            'education', 'work_experience', 'preferred_roles', 'suggested_roles',
        ]
        
        for field in allowed_fields:
            if field in data:
                setattr(candidate, field, data[field])
        
        db.session.commit()
        return candidate
    
    def delete_candidate(self, candidate_id: int, tenant_id: int) -> bool:
        """
        Delete candidate
        
        Args:
            candidate_id: Candidate ID
            tenant_id: Tenant ID (for access control)
        
        Returns:
            True if deleted, False if not found
        """
        # Use a direct query to avoid session cache issues
        from sqlalchemy import select
        from app.models.candidate_document import CandidateDocument
        from app.models.candidate_assignment import CandidateAssignment
        from app.models.assignment_notification import AssignmentNotification
        from app.models.candidate_job_match import CandidateJobMatch
        
        stmt = select(Candidate).where(
            Candidate.id == candidate_id,
            Candidate.tenant_id == tenant_id
        )
        candidate = db.session.scalar(stmt)
        
        if not candidate:
            return False
        
        # Store resume file path before deletion
        resume_file_path = candidate.resume_file_path
        
        # Get all document file paths before deletion
        doc_stmt = select(CandidateDocument).where(CandidateDocument.candidate_id == candidate_id)
        documents = db.session.scalars(doc_stmt).all()
        document_paths = [doc.file_path for doc in documents if doc.file_path]
        
        # Manually delete related records to avoid FK constraint issues
        
        # 1. Delete assignment notifications first
        assignment_stmt = select(CandidateAssignment).where(CandidateAssignment.candidate_id == candidate_id)
        assignments = db.session.scalars(assignment_stmt).all()
        for assignment in assignments:
            # Delete notifications for this assignment
            notification_stmt = select(AssignmentNotification).where(AssignmentNotification.assignment_id == assignment.id)
            notifications = db.session.scalars(notification_stmt).all()
            for notification in notifications:
                db.session.delete(notification)
        
        # 2. Delete job matches for this candidate
        job_match_stmt = select(CandidateJobMatch).where(CandidateJobMatch.candidate_id == candidate_id)
        job_matches = db.session.scalars(job_match_stmt).all()
        for job_match in job_matches:
            db.session.delete(job_match)
        
        # Delete candidate from database (this will cascade to related records)
        try:
            db.session.delete(candidate)
            db.session.commit()
            # Expire all cached objects to ensure fresh data on next query
            db.session.expire_all()
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Failed to delete candidate from database: {str(e)}")
        
        # Delete resume file after successful database deletion
        if resume_file_path:
            try:
                self.file_storage.delete_resume(resume_file_path)
            except Exception as e:
                # Log but don't fail - database deletion already succeeded
                print(f"Warning: Failed to delete resume file {resume_file_path}: {e}")
        
        # Delete document files after successful database deletion
        for doc_path in document_paths:
            try:
                self.file_storage.delete_document(doc_path)
            except Exception as e:
                # Log but don't fail - database deletion already succeeded
                print(f"Warning: Failed to delete document file {doc_path}: {e}")
        
        return True
    
    def reparse_resume(self, candidate_id: int, tenant_id: int) -> Dict[str, Any]:
        """
        Re-parse existing resume file
        
        Args:
            candidate_id: Candidate ID
            tenant_id: Tenant ID (for access control)
        
        Returns:
            Parsed data
        """
        candidate = self.get_candidate(candidate_id, tenant_id)
        
        if not candidate or not candidate.resume_file_path:
            raise ValueError("Candidate or resume file not found")
        
        # Extract text
        extracted = TextExtractor.extract_from_file(candidate.resume_file_path)
        text = TextExtractor.clean_text(extracted['text'])
        
        # Parse
        parser = self._get_parser()
        file_ext = os.path.splitext(candidate.resume_file_path)[1][1:]
        parsed_data = parser.parse_resume(text, file_type=file_ext)
        
        # Enhance skills
        if parsed_data.get('skills'):
            skills_analysis = self.skills_matcher.extract_skills(' '.join(parsed_data['skills']))
            parsed_data['skills'] = skills_analysis['matched_skills']
            parsed_data['skills_categories'] = skills_analysis['categories']
        
        # Update candidate
        candidate.parsed_resume_data = parsed_data
        candidate.resume_parsed_at = datetime.utcnow()
        
        db.session.commit()
        
        return {
            'candidate_id': candidate.id,
            'parsed_data': parsed_data,
            'extracted_metadata': extracted,
            'status': 'success',
        }
    
    # Onboarding Workflow Methods
    
    def onboard_candidate(
        self,
        candidate_id: int,
        onboarded_by_user_id: int,
        tenant_id: int
    ) -> Candidate:
        """
        Mark a candidate as onboarded.
        
        Args:
            candidate_id: Candidate ID
            onboarded_by_user_id: ID of user performing onboarding
            tenant_id: Tenant ID (for access control)
        
        Returns:
            Updated candidate
        
        Raises:
            ValueError: If candidate not found or validation fails
        """
        candidate = self.get_candidate(candidate_id, tenant_id)
        
        if not candidate:
            raise ValueError(f"Candidate with ID {candidate_id} not found")
        
        # Check if candidate is assigned
        if candidate.onboarding_status not in ['ASSIGNED', 'PENDING_ONBOARDING']:
            raise ValueError(
                f"Cannot onboard candidate with status '{candidate.onboarding_status}'. "
                "Candidate must be in 'ASSIGNED' or 'PENDING_ONBOARDING' status."
            )
        
        # Update onboarding fields
        candidate.onboarding_status = 'ONBOARDED'
        candidate.onboarded_by_user_id = onboarded_by_user_id
        candidate.onboarded_at = datetime.utcnow()
        
        db.session.commit()
        
        return candidate
    
    def approve_candidate(
        self,
        candidate_id: int,
        approved_by_user_id: int,
        tenant_id: int
    ) -> Candidate:
        """
        Approve a candidate (HR approval after onboarding).
        
        Args:
            candidate_id: Candidate ID
            approved_by_user_id: ID of user approving (must be HIRING_MANAGER)
            tenant_id: Tenant ID (for access control)
        
        Returns:
            Updated candidate
        
        Raises:
            ValueError: If candidate not found or validation fails
        """
        candidate = self.get_candidate(candidate_id, tenant_id)
        
        if not candidate:
            raise ValueError(f"Candidate with ID {candidate_id} not found")
        
        # Check if candidate is onboarded
        if candidate.onboarding_status != 'ONBOARDED':
            raise ValueError(
                f"Cannot approve candidate with status '{candidate.onboarding_status}'. "
                "Candidate must be in 'ONBOARDED' status."
            )
        
        # Check if already approved or rejected
        if candidate.approved_at:
            raise ValueError("Candidate has already been approved")
        
        if candidate.rejected_at:
            raise ValueError("Candidate has already been rejected. Cannot approve after rejection.")
        
        # Update approval fields
        candidate.onboarding_status = 'APPROVED'
        candidate.approved_by_user_id = approved_by_user_id
        candidate.approved_at = datetime.utcnow()
        
        db.session.commit()
        
        return candidate
    
    def reject_candidate(
        self,
        candidate_id: int,
        rejected_by_user_id: int,
        rejection_reason: str,
        tenant_id: int
    ) -> Candidate:
        """
        Reject a candidate (HR rejection after onboarding).
        
        Args:
            candidate_id: Candidate ID
            rejected_by_user_id: ID of user rejecting (must be HIRING_MANAGER)
            rejection_reason: Reason for rejection
            tenant_id: Tenant ID (for access control)
        
        Returns:
            Updated candidate
        
        Raises:
            ValueError: If candidate not found or validation fails
        """
        candidate = self.get_candidate(candidate_id, tenant_id)
        
        if not candidate:
            raise ValueError(f"Candidate with ID {candidate_id} not found")
        
        # Check if candidate is onboarded
        if candidate.onboarding_status != 'ONBOARDED':
            raise ValueError(
                f"Cannot reject candidate with status '{candidate.onboarding_status}'. "
                "Candidate must be in 'ONBOARDED' status."
            )
        
        # Check if already approved or rejected
        if candidate.approved_at:
            raise ValueError("Candidate has already been approved. Cannot reject after approval.")
        
        if candidate.rejected_at:
            raise ValueError("Candidate has already been rejected")
        
        # Validate rejection reason
        if not rejection_reason or not rejection_reason.strip():
            raise ValueError("Rejection reason is required")
        
        # Update rejection fields
        candidate.onboarding_status = 'REJECTED'
        candidate.rejected_by_user_id = rejected_by_user_id
        candidate.rejected_at = datetime.utcnow()
        candidate.rejection_reason = rejection_reason.strip()
        
        db.session.commit()
        
        return candidate
    
    def get_candidates_for_onboarding(
        self,
        tenant_id: int,
        status_filter: Optional[str] = None,
        assigned_to_user_id: Optional[int] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """
        Get candidates ready for onboarding with filtering.
        
        Args:
            tenant_id: Tenant ID
            status_filter: Optional filter by onboarding_status 
                          (PENDING_ASSIGNMENT, ASSIGNED, PENDING_ONBOARDING, ONBOARDED, APPROVED, REJECTED)
            assigned_to_user_id: Optional filter by assigned user (manager or recruiter)
            page: Page number (1-indexed)
            per_page: Items per page
        
        Returns:
            {
                'candidates': [...],
                'total': int,
                'page': int,
                'per_page': int,
                'pages': int
            }
        """
        query = db.session.query(Candidate).filter(Candidate.tenant_id == tenant_id)
        
        # Filter by onboarding status (supports comma-separated values)
        if status_filter:
            # Support multiple statuses separated by comma
            if ',' in status_filter:
                statuses = [s.strip() for s in status_filter.split(',')]
                query = query.filter(Candidate.onboarding_status.in_(statuses))
            else:
                query = query.filter(Candidate.onboarding_status == status_filter)
        else:
            # By default, show candidates in the onboarding workflow
            query = query.filter(
                Candidate.onboarding_status.in_([
                    'PENDING_ASSIGNMENT',
                    'ASSIGNED',
                    'PENDING_ONBOARDING',
                    'ONBOARDED',
                    'APPROVED',
                    'REJECTED'
                ])
            )
        
        # Filter by assigned user
        if assigned_to_user_id:
            query = query.filter(
                (Candidate.manager_id == assigned_to_user_id) |
                (Candidate.recruiter_id == assigned_to_user_id)
            )
        
        # Order by created date (newest first)
        query = query.order_by(Candidate.created_at.desc())
        
        # Paginate
        offset = (page - 1) * per_page
        total = query.count()
        candidates = query.limit(per_page).offset(offset).all()
        
        return {
            'candidates': [c.to_dict(include_assignments=False, include_onboarding_users=True) for c in candidates],
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page
        }
    
    def update_onboarding_status(
        self,
        candidate_id: int,
        new_status: str,
        tenant_id: int
    ) -> Candidate:
        """
        Update candidate onboarding status directly.
        
        Args:
            candidate_id: Candidate ID
            new_status: New onboarding status
            tenant_id: Tenant ID (for access control)
        
        Returns:
            Updated candidate
        
        Raises:
            ValueError: If candidate not found or invalid status
        """
        candidate = self.get_candidate(candidate_id, tenant_id)
        
        if not candidate:
            raise ValueError(f"Candidate with ID {candidate_id} not found")
        
        # Validate status
        valid_statuses = [
            'PENDING_ASSIGNMENT',
            'ASSIGNED',
            'PENDING_ONBOARDING',
            'ONBOARDED',
            'APPROVED',
            'REJECTED'
        ]
        
        if new_status not in valid_statuses:
            raise ValueError(
                f"Invalid onboarding status '{new_status}'. "
                f"Must be one of: {', '.join(valid_statuses)}"
            )
        
        candidate.onboarding_status = new_status
        db.session.commit()
        
        return candidate
