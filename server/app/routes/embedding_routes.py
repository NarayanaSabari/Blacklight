"""
Embedding Management Routes (PM_ADMIN only)
API endpoints for generating and managing embeddings
"""
import logging
from flask import Blueprint, request, jsonify
from sqlalchemy import select

from app import db
from app.models.candidate import Candidate
from app.models.job_posting import JobPosting
from app.services.embedding_service import EmbeddingService
from app.middleware.pm_admin import require_pm_admin
import time

logger = logging.getLogger(__name__)

embedding_bp = Blueprint('embeddings', __name__, url_prefix='/api/embeddings')


def error_response(message: str, status: int = 400, details: dict = None):
    """Helper to create error responses"""
    response = {
        'error': 'Error',
        'message': message,
        'status': status
    }
    if details:
        response['details'] = details
    return jsonify(response), status


@embedding_bp.route('/generate', methods=['POST'])
@require_pm_admin
def generate_embeddings():
    """
    Generate embeddings for candidates and/or jobs without embeddings.
    
    POST /api/embeddings/generate
    
    Request body:
    {
        "entity_type": "all",  // "candidates", "jobs", or "all" (default: "all")
        "batch_size": 15,      // 1-20 (default: 15)
        "tenant_id": 123       // Optional: Only process this tenant's candidates
    }
    
    Permissions: PM_ADMIN only
    
    This is a one-time backfill operation for existing data.
    New candidates/jobs get embeddings automatically.
    """
    try:
        data = request.get_json() or {}
        entity_type = data.get('entity_type', 'all').lower()
        batch_size = data.get('batch_size', 15)
        tenant_id = data.get('tenant_id')
        
        # Validate entity type
        valid_types = ['candidates', 'jobs', 'all']
        if entity_type not in valid_types:
            return error_response(f"Invalid entity_type. Must be one of: {', '.join(valid_types)}")
        
        # Validate batch size
        if not isinstance(batch_size, int) or batch_size < 1 or batch_size > 20:
            return error_response("batch_size must be between 1 and 20")
        
        service = EmbeddingService()
        results = {
            'entity_type': entity_type,
            'batch_size': batch_size,
            'tenant_id': tenant_id
        }
        start_time = time.time()
        
        # Process candidates
        if entity_type in ['candidates', 'all']:
            logger.info(f"[EMBEDDINGS] Starting candidate embedding generation")
            
            query = select(Candidate).where(Candidate.embedding.is_(None))
            if tenant_id:
                query = query.where(Candidate.tenant_id == tenant_id)
            
            candidates = db.session.execute(query).scalars().all()
            
            candidate_stats = {
                'total': len(candidates),
                'successful': 0,
                'failed': 0,
                'errors': []
            }
            
            for i in range(0, len(candidates), batch_size):
                batch = candidates[i:i + batch_size]
                
                for candidate in batch:
                    try:
                        if service.save_candidate_embedding(candidate):
                            candidate_stats['successful'] += 1
                        else:
                            candidate_stats['failed'] += 1
                            candidate_stats['errors'].append({
                                'id': candidate.id,
                                'error': 'Embedding generation returned None'
                            })
                    except Exception as e:
                        candidate_stats['failed'] += 1
                        candidate_stats['errors'].append({
                            'id': candidate.id,
                            'error': str(e)
                        })
                
                # Rate limiting
                if i + batch_size < len(candidates):
                    time.sleep(0.5)
            
            results['candidates'] = candidate_stats
            logger.info(
                f"[EMBEDDINGS] Candidate generation complete: "
                f"{candidate_stats['successful']}/{candidate_stats['total']} successful"
            )
        
        # Process jobs
        if entity_type in ['jobs', 'all']:
            logger.info(f"[EMBEDDINGS] Starting job embedding generation")
            
            query = select(JobPosting).where(JobPosting.embedding.is_(None))
            jobs = db.session.execute(query).scalars().all()
            
            job_stats = {
                'total': len(jobs),
                'successful': 0,
                'failed': 0,
                'errors': []
            }
            
            for i in range(0, len(jobs), batch_size):
                batch = jobs[i:i + batch_size]
                
                for job in batch:
                    try:
                        if service.save_job_embedding(job):
                            job_stats['successful'] += 1
                        else:
                            job_stats['failed'] += 1
                            job_stats['errors'].append({
                                'id': job.id,
                                'error': 'Embedding generation returned None'
                            })
                    except Exception as e:
                        job_stats['failed'] += 1
                        job_stats['errors'].append({
                            'id': job.id,
                            'error': str(e)
                        })
                
                # Rate limiting
                if i + batch_size < len(jobs):
                    time.sleep(0.5)
            
            results['jobs'] = job_stats
            logger.info(
                f"[EMBEDDINGS] Job generation complete: "
                f"{job_stats['successful']}/{job_stats['total']} successful"
            )
        
        results['processing_time_seconds'] = round(time.time() - start_time, 2)
        
        return jsonify({
            'message': 'Embedding generation complete',
            'results': results
        }), 200
        
    except Exception as e:
        logger.error(f"[EMBEDDINGS] Error generating embeddings: {str(e)}")
        return error_response("Failed to generate embeddings", 500)


@embedding_bp.route('/stats', methods=['GET'])
@require_pm_admin
def get_embedding_stats():
    """
    Get statistics about embeddings coverage.
    
    GET /api/embeddings/stats?tenant_id=123
    
    Query params:
    - tenant_id: Optional, filter candidates by tenant
    
    Permissions: PM_ADMIN only
    
    Returns counts of entities with/without embeddings.
    """
    try:
        tenant_id = request.args.get('tenant_id', type=int)
        
        # Candidate stats
        candidate_query = select(Candidate)
        if tenant_id:
            candidate_query = candidate_query.where(Candidate.tenant_id == tenant_id)
        
        total_candidates = db.session.scalar(
            select(db.func.count()).select_from(candidate_query.subquery())
        ) or 0
        
        candidates_with_embeddings = db.session.scalar(
            select(db.func.count()).select_from(
                candidate_query.where(Candidate.embedding.is_not(None)).subquery()
            )
        ) or 0
        
        candidates_without_embeddings = total_candidates - candidates_with_embeddings
        
        # Job stats
        total_jobs = db.session.scalar(
            select(db.func.count()).select_from(JobPosting)
        ) or 0
        
        jobs_with_embeddings = db.session.scalar(
            select(db.func.count()).select_from(JobPosting).where(
                JobPosting.embedding.is_not(None)
            )
        ) or 0
        
        jobs_without_embeddings = total_jobs - jobs_with_embeddings
        
        return jsonify({
            'candidates': {
                'total': total_candidates,
                'with_embeddings': candidates_with_embeddings,
                'without_embeddings': candidates_without_embeddings,
                'coverage_percentage': round(
                    (candidates_with_embeddings / total_candidates * 100) if total_candidates > 0 else 0,
                    2
                )
            },
            'jobs': {
                'total': total_jobs,
                'with_embeddings': jobs_with_embeddings,
                'without_embeddings': jobs_without_embeddings,
                'coverage_percentage': round(
                    (jobs_with_embeddings / total_jobs * 100) if total_jobs > 0 else 0,
                    2
                )
            },
            'tenant_id': tenant_id
        }), 200
        
    except Exception as e:
        logger.error(f"[EMBEDDINGS] Error fetching embedding stats: {str(e)}")
        return error_response("Failed to fetch embedding statistics", 500)


@embedding_bp.route('/regenerate', methods=['POST'])
@require_pm_admin
def regenerate_embeddings():
    """
    Regenerate embeddings for specific entities (force update).
    
    POST /api/embeddings/regenerate
    
    Request body:
    {
        "entity_type": "candidate",  // "candidate" or "job"
        "entity_ids": [1, 2, 3]      // Array of entity IDs to regenerate
    }
    
    Permissions: PM_ADMIN only
    
    Use this to regenerate embeddings when entity content has changed
    or to fix corrupted embeddings.
    """
    try:
        data = request.get_json()
        if not data:
            return error_response("Request body is required")
        
        entity_type = data.get('entity_type', '').lower()
        entity_ids = data.get('entity_ids', [])
        
        # Validate entity type
        if entity_type not in ['candidate', 'job']:
            return error_response("entity_type must be 'candidate' or 'job'")
        
        # Validate entity_ids
        if not isinstance(entity_ids, list) or len(entity_ids) == 0:
            return error_response("entity_ids must be a non-empty array")
        
        if len(entity_ids) > 50:
            return error_response("Cannot regenerate more than 50 entities at once")
        
        service = EmbeddingService()
        results = {
            'entity_type': entity_type,
            'total': len(entity_ids),
            'successful': 0,
            'failed': 0,
            'errors': []
        }
        
        if entity_type == 'candidate':
            for entity_id in entity_ids:
                try:
                    candidate = db.session.get(Candidate, entity_id)
                    if not candidate:
                        results['failed'] += 1
                        results['errors'].append({
                            'id': entity_id,
                            'error': 'Candidate not found'
                        })
                        continue
                    
                    if service.save_candidate_embedding(candidate):
                        results['successful'] += 1
                    else:
                        results['failed'] += 1
                        results['errors'].append({
                            'id': entity_id,
                            'error': 'Embedding generation returned None'
                        })
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append({
                        'id': entity_id,
                        'error': str(e)
                    })
                
                # Small delay to avoid rate limits
                if len(entity_ids) > 1:
                    time.sleep(0.1)
        
        else:  # job
            for entity_id in entity_ids:
                try:
                    job = db.session.get(JobPosting, entity_id)
                    if not job:
                        results['failed'] += 1
                        results['errors'].append({
                            'id': entity_id,
                            'error': 'Job not found'
                        })
                        continue
                    
                    if service.save_job_embedding(job):
                        results['successful'] += 1
                    else:
                        results['failed'] += 1
                        results['errors'].append({
                            'id': entity_id,
                            'error': 'Embedding generation returned None'
                        })
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append({
                        'id': entity_id,
                        'error': str(e)
                    })
                
                # Small delay to avoid rate limits
                if len(entity_ids) > 1:
                    time.sleep(0.1)
        
        return jsonify({
            'message': 'Embedding regeneration complete',
            'results': results
        }), 200
        
    except Exception as e:
        logger.error(f"[EMBEDDINGS] Error regenerating embeddings: {str(e)}")
        return error_response("Failed to regenerate embeddings", 500)
