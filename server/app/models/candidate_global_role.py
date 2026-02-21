"""
Candidate Global Role Model
Links candidates to their normalized preferred roles.

This is the key linking table for role-based queue processing:
- When a role is scraped, ALL candidates linked to it receive matches
- Enables efficient batch matching: scrape once, match to many candidates
"""
from datetime import datetime
from sqlalchemy import Integer, DateTime, ForeignKey, Index, UniqueConstraint
from app import db


class CandidateGlobalRole(db.Model):
    """
    Links candidates to their normalized preferred roles.
    
    Usage Flow:
    1. Candidate selects preferred roles during onboarding
    2. AI normalizes each role → finds/creates GlobalRole
    3. Creates CandidateGlobalRole record
    4. GlobalRole.candidate_count is incremented
    5. Role appears in scrape queue (if pending)
    6. When jobs imported for role → match to ALL linked candidates
    
    Example:
        Candidate A wants "Python Developer" → links to GlobalRole(id=1)
        Candidate B wants "Senior Python Dev" → normalizes to same GlobalRole(id=1)
        When scraper posts jobs for role 1, both A and B get matches
    """
    __tablename__ = 'candidate_global_roles'
    
    id = db.Column(Integer, primary_key=True)
    
    # Foreign Keys
    candidate_id = db.Column(
        Integer,
        ForeignKey('candidates.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    global_role_id = db.Column(
        Integer,
        ForeignKey('global_roles.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # Timestamps
    created_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    candidate = db.relationship('Candidate', back_populates='global_roles')
    global_role = db.relationship('GlobalRole', back_populates='candidate_links')
    
    # Indexes and Constraints
    # NOTE: Single-column indexes on candidate_id and global_role_id are already
    # created by inline index=True on the FK columns above. No need to duplicate.
    __table_args__ = (
        # Unique: candidate can only have each role once
        UniqueConstraint('candidate_id', 'global_role_id', name='uq_candidate_global_role'),
    )
    
    def __repr__(self):
        return f'<CandidateGlobalRole candidate={self.candidate_id} role={self.global_role_id}>'
    
    def to_dict(self, include_role=False, include_candidate=False):
        """Convert to dictionary."""
        result = {
            'id': self.id,
            'candidate_id': self.candidate_id,
            'global_role_id': self.global_role_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        
        if include_role and self.global_role:
            result['global_role'] = self.global_role.to_dict()
        
        if include_candidate and self.candidate:
            result['candidate'] = {
                'id': self.candidate.id,
                'first_name': self.candidate.first_name,
                'last_name': self.candidate.last_name,
                'email': self.candidate.email,
            }
        
        return result
