#!/usr/bin/env python
"""
Job Matching System - End-to-End Test Script

This script tests the complete job matching workflow:
1. Generate embeddings for jobs
2. Create test candidates
3. Generate candidate embeddings
4. Generate matches
5. Validate results
"""

import sys
import os
import time
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models.candidate import Candidate
from app.models.job_posting import JobPosting
from app.models.candidate_job_match import CandidateJobMatch
from app.models.tenant import Tenant
from app.services.embedding_service import EmbeddingService
from app.services.job_matching_service import JobMatchingService
from sqlalchemy import select, func


def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)


def print_step(text):
    """Print formatted step"""
    print(f"\n>>> {text}")


def print_success(text):
    """Print success message"""
    print(f"✅ {text}")


def print_error(text):
    """Print error message"""
    print(f"❌ {text}")


def print_info(text):
    """Print info message"""
    print(f"ℹ️  {text}")


# Test candidate profiles
TEST_CANDIDATES = [
    {
        "first_name": "Alex",
        "last_name": "Rodriguez",
        "email": "alex.rodriguez@test.com",
        "phone": "+1-555-0101",
        "current_title": "Senior Full-Stack Engineer",
        "skills": ["Python", "JavaScript", "React", "Node.js", "AWS", "Docker", "PostgreSQL", "Redis", "Git"],
        "total_experience_years": 8,
        "location": "San Francisco, CA",
        "preferred_locations": ["San Francisco, CA", "Remote"],
        "expected_salary": "$165,000",
        "status": "APPROVED",
        "professional_summary": "Experienced full-stack engineer with 8 years building scalable web applications. Expert in Python/Django and React. Strong AWS and DevOps skills."
    },
    {
        "first_name": "Maya",
        "last_name": "Chen",
        "email": "maya.chen@test.com",
        "phone": "+1-555-0102",
        "current_title": "Junior Python Developer",
        "skills": ["Python", "Django", "REST APIs", "Git", "SQL", "HTML", "CSS"],
        "total_experience_years": 2,
        "location": "Austin, TX",
        "preferred_locations": ["Austin, TX", "Dallas, TX"],
        "expected_salary": "$80,000",
        "status": "APPROVED",
        "professional_summary": "Recent computer science graduate with 2 years of Python development experience. Built REST APIs and worked with Django framework."
    },
    {
        "first_name": "Jordan",
        "last_name": "Kim",
        "email": "jordan.kim@test.com",
        "phone": "+1-555-0103",
        "current_title": "DevOps Engineer",
        "skills": ["Kubernetes", "Docker", "AWS", "Terraform", "Jenkins", "Python", "Linux", "CI/CD"],
        "total_experience_years": 6,
        "location": "Remote",
        "preferred_locations": ["Remote"],
        "expected_salary": "$145,000",
        "status": "APPROVED",
        "professional_summary": "DevOps specialist with 6 years managing cloud infrastructure. Expert in Kubernetes, AWS, and infrastructure as code with Terraform."
    },
    {
        "first_name": "Samira",
        "last_name": "Patel",
        "email": "samira.patel@test.com",
        "phone": "+1-555-0104",
        "current_title": "Data Scientist",
        "skills": ["Python", "Machine Learning", "TensorFlow", "Pandas", "SQL", "R", "Statistics", "Data Visualization"],
        "total_experience_years": 5,
        "location": "New York, NY",
        "preferred_locations": ["New York, NY", "Boston, MA", "Remote"],
        "expected_salary": "$135,000",
        "status": "APPROVED",
        "professional_summary": "Data scientist with 5 years building ML models for business insights. Strong Python and statistical analysis background."
    },
    {
        "first_name": "Tyler",
        "last_name": "Anderson",
        "email": "tyler.anderson@test.com",
        "phone": "+1-555-0105",
        "current_title": "Frontend Developer",
        "skills": ["JavaScript", "React", "TypeScript", "HTML", "CSS", "Redux", "GraphQL", "Webpack"],
        "total_experience_years": 4,
        "location": "Seattle, WA",
        "preferred_locations": ["Seattle, WA", "Portland, OR", "Remote"],
        "expected_salary": "$115,000",
        "status": "APPROVED",
        "professional_summary": "Frontend specialist with 4 years building responsive web applications. Expert in React ecosystem and modern JavaScript."
    }
]


def test_job_embeddings(app):
    """Test 1: Generate embeddings for all jobs"""
    print_header("TEST 1: Generate Job Embeddings")
    
    # Check for Google API key first
    if not os.getenv('GOOGLE_API_KEY'):
        print_error("GOOGLE_API_KEY environment variable is not set!")
        print_info("Please set it in your .env file or export it:")
        print_info("  export GOOGLE_API_KEY='your-api-key-here'")
        return False
    
    with app.app_context():
        # Count jobs without embeddings
        total_jobs = db.session.scalar(select(func.count()).select_from(JobPosting))
        jobs_without_embeddings = db.session.scalar(
            select(func.count()).select_from(JobPosting).where(JobPosting.embedding.is_(None))
        )
        
        print_info(f"Total jobs: {total_jobs}")
        print_info(f"Jobs without embeddings: {jobs_without_embeddings}")
        
        if jobs_without_embeddings == 0:
            print_success("All jobs already have embeddings!")
            return True
        
        print_step(f"Generating embeddings for {jobs_without_embeddings} jobs...")
        
        service = EmbeddingService()
        jobs = db.session.execute(
            select(JobPosting).where(JobPosting.embedding.is_(None))
        ).scalars().all()
        
        successful = 0
        failed = 0
        batch_size = 15
        
        start_time = time.time()
        
        for i in range(0, len(jobs), batch_size):
            batch = jobs[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(jobs) + batch_size - 1) // batch_size
            
            print(f"  Batch {batch_num}/{total_batches} ({len(batch)} jobs)...")
            
            for job in batch:
                try:
                    embedding = service.generate_job_embedding(job)
                    if embedding:
                        job.embedding = embedding
                        db.session.commit()
                        successful += 1
                    else:
                        failed += 1
                        print_error(f"    Job {job.id}: Embedding was None")
                except Exception as e:
                    failed += 1
                    print_error(f"    Job {job.id}: {str(e)[:80]}")
                    db.session.rollback()
            
            # Rate limiting
            if i + batch_size < len(jobs):
                time.sleep(0.5)
        
        duration = time.time() - start_time
        
        print_info(f"Completed in {duration:.2f} seconds")
        print_success(f"Successfully generated {successful}/{len(jobs)} embeddings")
        
        if failed > 0:
            print_error(f"Failed to generate {failed} embeddings")
            return False
        
        return True


def test_create_candidates(app):
    """Test 2: Create test candidates"""
    print_header("TEST 2: Create Test Candidates")
    
    with app.app_context():
        # Get first active tenant
        from app.models.tenant import TenantStatus
        tenant = db.session.execute(select(Tenant).where(Tenant.status == TenantStatus.ACTIVE)).scalars().first()
        
        if not tenant:
            print_error("No active tenant found! Run 'python manage.py seed-all' first")
            return False
        
        print_info(f"Using tenant: {tenant.name} (ID: {tenant.id})")
        
        created_count = 0
        
        for candidate_data in TEST_CANDIDATES:
            try:
                # Check if candidate already exists
                existing = db.session.execute(
                    select(Candidate).where(Candidate.email == candidate_data['email'])
                ).scalar_one_or_none()
                
                if existing:
                    print_info(f"  Candidate {candidate_data['email']} already exists (ID: {existing.id})")
                    continue
                
                # Create new candidate
                candidate = Candidate(
                    tenant_id=tenant.id,
                    **candidate_data
                )
                
                db.session.add(candidate)
                db.session.commit()
                
                print_success(f"  Created: {candidate.first_name} {candidate.last_name} (ID: {candidate.id})")
                created_count += 1
                
            except Exception as e:
                print_error(f"  Failed to create {candidate_data['email']}: {str(e)}")
                db.session.rollback()
        
        print_info(f"Created {created_count} new candidates")
        return True


def test_candidate_embeddings(app):
    """Test 3: Generate embeddings for candidates"""
    print_header("TEST 3: Generate Candidate Embeddings")
    
    # Check for Google API key first
    if not os.getenv('GOOGLE_API_KEY'):
        print_error("GOOGLE_API_KEY environment variable is not set!")
        return False
    
    with app.app_context():
        candidates_without_embeddings = db.session.execute(
            select(Candidate).where(Candidate.embedding.is_(None))
        ).scalars().all()
        
        print_info(f"Candidates without embeddings: {len(candidates_without_embeddings)}")
        
        if len(candidates_without_embeddings) == 0:
            print_success("All candidates already have embeddings!")
            return True
        
        service = EmbeddingService()
        successful = 0
        failed = 0
        
        for candidate in candidates_without_embeddings:
            try:
                embedding = service.generate_candidate_embedding(candidate)
                if embedding:
                    candidate.embedding = embedding
                    db.session.commit()
                    successful += 1
                    print_success(f"  {candidate.first_name} {candidate.last_name}")
                else:
                    failed += 1
                    print_error(f"  {candidate.first_name} {candidate.last_name}: Embedding was None")
            except Exception as e:
                failed += 1
                print_error(f"  {candidate.first_name} {candidate.last_name}: {str(e)[:80]}")
                db.session.rollback()
            
            # Small delay
            time.sleep(0.2)
        
        print_info(f"Successfully generated {successful}/{len(candidates_without_embeddings)} embeddings")
        
        if failed > 0:
            print_error(f"Failed to generate {failed} embeddings")
            return False
        
        return True


def test_single_match_generation(app):
    """Test 4: Generate matches for single candidate"""
    print_header("TEST 4: Single Candidate Match Generation")
    
    with app.app_context():
        # Get first candidate with embedding
        candidate = db.session.execute(
            select(Candidate).where(Candidate.embedding.is_not(None))
        ).scalars().first()
        
        if not candidate:
            print_error("No candidate with embedding found!")
            return False
        
        print_info(f"Testing with: {candidate.first_name} {candidate.last_name}")
        print_info(f"  Title: {candidate.current_title}")
        # Convert skills array to list before slicing
        skills_list = list(candidate.skills) if candidate.skills is not None else []
        if skills_list:
            print_info(f"  Skills: {', '.join(skills_list[:5])}...")
        print_info(f"  Experience: {candidate.total_experience_years} years")
        
        service = JobMatchingService(tenant_id=candidate.tenant_id)
        
        start_time = time.time()
        matches = service.generate_matches_for_candidate(
            candidate_id=candidate.id,
            min_score=50.0,
            limit=50
        )
        duration = time.time() - start_time
        
        print_info(f"Generated {len(matches)} matches in {duration:.2f} seconds")
        
        if len(matches) == 0:
            print_error("No matches generated!")
            return False
        
        # Show top 5 matches
        print_step("Top 5 Matches:")
        for i, match in enumerate(matches[:5], 1):
            job = match.job_posting
            print(f"\n  {i}. {job.title} @ {job.company}")
            print(f"     Overall Score: {match.match_score}% (Grade: {match.match_grade})")
            print(f"     Skills: {match.skill_match_score}% | Experience: {match.experience_match_score}%")
            print(f"     Location: {match.location_match_score}% | Salary: {match.salary_match_score}%")
            print(f"     Semantic: {match.semantic_similarity}%")
            if match.matched_skills:
                print(f"     Matched Skills: {', '.join(match.matched_skills[:5])}...")
        
        return True


def test_bulk_match_generation(app):
    """Test 5: Generate matches for all candidates"""
    print_header("TEST 5: Bulk Match Generation")
    
    with app.app_context():
        candidates = db.session.execute(
            select(Candidate).where(Candidate.embedding.is_not(None))
        ).scalars().all()
        
        if len(candidates) == 0:
            print_error("No candidates with embeddings found!")
            return False
        
        print_info(f"Processing {len(candidates)} candidates...")
        
        # Get first tenant
        tenant_id = candidates[0].tenant_id
        service = JobMatchingService(tenant_id=tenant_id)
        
        start_time = time.time()
        stats = service.generate_matches_for_all_candidates(
            batch_size=10,
            min_score=50.0
        )
        duration = time.time() - start_time
        
        print_info(f"Completed in {duration:.2f} seconds")
        print_success(f"Total candidates: {stats['total_candidates']}")
        print_success(f"Successful: {stats['successful_candidates']}")
        print_success(f"Failed: {stats['failed_candidates']}")
        print_success(f"Total matches: {stats['total_matches']}")
        print_success(f"Avg matches per candidate: {stats['avg_matches_per_candidate']}")
        
        if stats['failed_candidates'] > 0:
            print_error(f"{stats['failed_candidates']} candidates failed")
            return False
        
        return True


def test_match_statistics(app):
    """Test 6: Verify match statistics"""
    print_header("TEST 6: Match Statistics")
    
    with app.app_context():
        # Get all candidates
        candidates = db.session.execute(select(Candidate)).scalars().all()
        candidate_ids = [c.id for c in candidates]
        
        if len(candidate_ids) == 0:
            print_error("No candidates found!")
            return False
        
        # Total matches
        total_matches = db.session.scalar(
            select(func.count()).select_from(CandidateJobMatch).where(
                CandidateJobMatch.candidate_id.in_(candidate_ids)
            )
        )
        
        # Average score
        avg_score = db.session.scalar(
            select(func.avg(CandidateJobMatch.match_score)).where(
                CandidateJobMatch.candidate_id.in_(candidate_ids)
            )
        ) or 0.0
        
        # Grade distribution
        matches = db.session.execute(
            select(CandidateJobMatch.match_score).where(
                CandidateJobMatch.candidate_id.in_(candidate_ids)
            )
        ).scalars().all()
        
        grade_dist = {'A+': 0, 'A': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0}
        for score in matches:
            score_val = float(score)
            if score_val >= 90:
                grade_dist['A+'] += 1
            elif score_val >= 80:
                grade_dist['A'] += 1
            elif score_val >= 70:
                grade_dist['B'] += 1
            elif score_val >= 60:
                grade_dist['C'] += 1
            elif score_val >= 50:
                grade_dist['D'] += 1
            else:
                grade_dist['F'] += 1
        
        print_success(f"Total matches: {total_matches}")
        print_success(f"Average score: {avg_score:.2f}%")
        print_step("Grade Distribution:")
        for grade, count in grade_dist.items():
            if count > 0:
                percentage = (count / total_matches * 100) if total_matches > 0 else 0
                print(f"  {grade}: {count} ({percentage:.1f}%)")
        
        return True


def main():
    """Run all tests"""
    print_header("JOB MATCHING SYSTEM - END-TO-END TESTS")
    print(f"Test Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    app = create_app()
    
    results = {}
    
    # Run tests
    tests = [
        ("Job Embeddings", test_job_embeddings),
        ("Create Candidates", test_create_candidates),
        ("Candidate Embeddings", test_candidate_embeddings),
        ("Single Match Generation", test_single_match_generation),
        ("Bulk Match Generation", test_bulk_match_generation),
        ("Match Statistics", test_match_statistics),
    ]
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func(app)
        except Exception as e:
            print_error(f"Test '{test_name}' crashed: {str(e)}")
            import traceback
            traceback.print_exc()
            results[test_name] = False
    
    # Summary
    print_header("TEST SUMMARY")
    
    passed = sum(1 for result in results.values() if result)
    failed = len(results) - passed
    
    print(f"\nTotal Tests: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print()
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {test_name}")
    
    print(f"\nTest Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if failed > 0:
        print("\n❌ SOME TESTS FAILED")
        sys.exit(1)
    else:
        print("\n✅ ALL TESTS PASSED!")
        sys.exit(0)


if __name__ == "__main__":
    main()
