#!/usr/bin/env python3
"""
Script to generate embeddings for email-sourced jobs that are missing embeddings.

Usage:
    python scripts/generate_job_embeddings.py

Can also be called via Flask CLI:
    flask generate-job-embeddings
"""
import sys
import os

# Add the server directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.job_posting import JobPosting
from app.services.embedding_service import EmbeddingService
from sqlalchemy import select


def generate_embeddings_for_email_jobs():
    """Generate embeddings for all email-sourced jobs missing embeddings."""
    app = create_app()
    
    with app.app_context():
        # Find email-sourced jobs without embeddings
        stmt = select(JobPosting).where(
            JobPosting.is_email_sourced == True,
            JobPosting.embedding.is_(None)
        )
        jobs = list(db.session.scalars(stmt).all())
        
        if not jobs:
            print("No email-sourced jobs found without embeddings")
            return
        
        print(f"Found {len(jobs)} email-sourced jobs without embeddings")
        
        embedding_service = EmbeddingService()
        success_count = 0
        error_count = 0
        
        for job in jobs:
            print(f"\n[{job.id}] {job.title}")
            print(f"    Company: {job.company}")
            print(f"    Has description: {bool(job.description)}")
            print(f"    Has skills: {bool(job.skills)}")
            
            try:
                embedding = embedding_service.generate_job_embedding(job)
                if embedding:
                    job.embedding = embedding
                    db.session.commit()
                    success_count += 1
                    print(f"    ✓ Embedding generated (length: {len(embedding)})")
                else:
                    error_count += 1
                    print(f"    ✗ Embedding service returned None")
            except Exception as e:
                error_count += 1
                print(f"    ✗ Error: {e}")
                db.session.rollback()
        
        print(f"\n{'='*50}")
        print(f"Summary: {success_count} successful, {error_count} failed")
        print(f"{'='*50}")


if __name__ == "__main__":
    generate_embeddings_for_email_jobs()
