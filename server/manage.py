"""Management CLI commands."""

import os
import sys
from datetime import datetime

from flask import Flask
from app import create_app, db


def init_db(app: Flask) -> None:
    """Initialize the database."""
    with app.app_context():
        # db.create_all() # Removed as migrations handle table creation
        app.logger.info("Database initialized successfully (schema managed by migrations)")


def drop_db(app: Flask, confirm: bool = False) -> None:
    """Drop all database tables."""
    if not confirm:
        response = input("Are you sure you want to drop all tables? [y/N]: ")
        if response.lower() != "y":
            print("Operation cancelled")
            return
    
    with app.app_context():
        db.drop_all()
        app.logger.info("Database dropped successfully")


def seed_db(app: Flask) -> None:
    """Seed the database with sample data (legacy - deprecated)."""
    print("⚠️  Legacy seed function - use 'seed-all' for tenant management system")
    print("This function is deprecated and does nothing.")


def seed_plans(app: Flask) -> None:
    """Seed subscription plans."""
    from app.seeds.subscription_plans import seed_subscription_plans
    
    with app.app_context():
        seed_subscription_plans()


def seed_pm_admin_user(app: Flask, email: str = None, password: str = None) -> None:
    """Seed PM admin user."""
    from app.seeds.pm_admin import seed_pm_admin
    
    with app.app_context():
        seed_pm_admin(email=email, password=password)


def seed_roles_and_permissions_command(app: Flask) -> None:
    """Seed system roles and permissions."""
    from app.seeds.roles_and_permissions import seed_roles_and_permissions
    
    with app.app_context():
        seed_roles_and_permissions()


def seed_tenants(app: Flask, count: int = 3) -> None:
    """Seed sample tenants."""
    from app.seeds.sample_tenants import seed_sample_tenants
    
    with app.app_context():
        seed_sample_tenants(count=count)


def seed_all(app: Flask) -> None:
    """Seed all (plans + PM admin + tenants)."""
    print("🌱 Seeding all data...")
    
    with app.app_context():
        # 1. Seed subscription plans
        from app.seeds.subscription_plans import seed_subscription_plans
        seed_subscription_plans()
        
        # 2. Seed PM admin user
        from app.seeds.pm_admin import seed_pm_admin
        seed_pm_admin()
        
        # 3. Seed tenants
        from app.seeds.tenants import seed_sample_tenants
        seed_sample_tenants(count=5)
        
    print("✅ All data seeded successfully!")


def fix_processing_candidates(app: Flask, tenant_id: int = None) -> None:
    """
    Fix candidates stuck in 'processing' status by updating them to 'pending_review'
    
    Args:
        tenant_id: Optional tenant ID to filter by. If None, fixes all tenants.
    """
    from app.models.candidate import Candidate
    from sqlalchemy import select
    
    with app.app_context():
        # Build query
        stmt = select(Candidate).where(Candidate.status == 'processing')
        if tenant_id:
            stmt = stmt.where(Candidate.tenant_id == tenant_id)
        
        stuck_candidates = list(db.session.scalars(stmt))
        
        if not stuck_candidates:
            print(f"✅ No candidates stuck in 'processing' status")
            return
        
        print(f"Found {len(stuck_candidates)} candidates stuck in 'processing' status")
        
        # Update all to pending_review
        for candidate in stuck_candidates:
            candidate.status = 'pending_review'
            print(f"  - Updated candidate {candidate.id} ({candidate.first_name} {candidate.last_name}) to 'pending_review'")
        
        db.session.commit()
        print(f"✅ Successfully updated {len(stuck_candidates)} candidates to 'pending_review' status")


def clean_data(app: Flask, confirm: bool = False) -> None:
    """
    Clean candidate and tenant data while preserving jobs.
    
    This function removes:
    - All candidate-related data (candidates, resumes, documents, matches, etc.)
    - All tenant-related data (tenants, portal users, roles, etc.)
    
    But PRESERVES:
    - Job postings (global job pool)
    - Global roles
    - Scraper configurations
    - Subscription plans
    - PM admin users
    - System permissions
    
    After cleaning, run './deploy.sh seed' to recreate tenants.
    """
    from sqlalchemy import text
    
    if not confirm:
        response = input(
            "\n⚠️  WARNING: This will delete ALL candidate and tenant data!\n"
            "   Jobs will be preserved.\n\n"
            "Are you sure you want to proceed? [yes/no]: "
        )
        if response.lower() != "yes":
            print("Operation cancelled")
            return
    
    print("\n" + "=" * 80)
    print("CLEANING CANDIDATE AND TENANT DATA")
    print("=" * 80)
    print("\nPreserving: job_postings, global_roles, scraper_*, subscription_plans, pm_admin_users")
    print()
    
    def safe_delete(table_name: str, display_name: str) -> None:
        """Safely delete from a table, handling missing tables gracefully."""
        try:
            result = db.session.execute(text(f"DELETE FROM {table_name}"))
            count = result.rowcount
            db.session.commit()
            print(f"  ✅ {display_name}: {count} rows deleted")
        except Exception as e:
            db.session.rollback()
            error_msg = str(e)
            if "UndefinedTable" in error_msg or "does not exist" in error_msg.lower():
                print(f"  ⏭️  {display_name}: table not found (skipped)")
            else:
                print(f"  ⚠️  {display_name}: {error_msg[:60]}")
    
    def safe_update(query: str, display_name: str) -> None:
        """Safely run an update query, handling missing columns gracefully."""
        try:
            result = db.session.execute(text(query))
            count = result.rowcount
            db.session.commit()
            if count > 0:
                print(f"  ✅ {display_name}: {count} rows updated")
            else:
                print(f"  ⏭️  {display_name}: no rows to update")
        except Exception as e:
            db.session.rollback()
            error_msg = str(e)
            if "UndefinedColumn" in error_msg or "does not exist" in error_msg.lower():
                print(f"  ⏭️  {display_name}: column not found (skipped)")
            elif "UndefinedTable" in error_msg:
                print(f"  ⏭️  {display_name}: table not found (skipped)")
            else:
                print(f"  ⚠️  {display_name}: {error_msg[:60]}")
    
    with app.app_context():
        # Phase 1: Delete candidate-dependent data (most dependent first)
        print("Phase 1: Cleaning candidate-related data...")
        
        candidate_tables = [
            ("submission_activities", "Submission activities"),
            ("submissions", "Submissions"),
            ("tailored_resumes", "Tailored resumes"),
            ("candidate_job_matches", "Candidate job matches"),
            ("job_applications", "Job applications"),
            ("assignment_notifications", "Assignment notifications"),
            ("candidate_assignments", "Candidate assignments"),
            ("invitation_audit_logs", "Invitation audit logs"),
            ("candidate_documents", "Candidate documents"),
            ("candidate_resumes", "Candidate resumes"),
            ("candidate_global_roles", "Candidate global roles"),
            ("candidate_invitations", "Candidate invitations"),
            ("candidates", "Candidates"),
        ]
        
        for table_name, display_name in candidate_tables:
            safe_delete(table_name, display_name)
        
        # Phase 2: Delete tenant/user-related data
        print("\nPhase 2: Cleaning tenant/user-related data...")
        
        tenant_tables = [
            ("processed_emails", "Processed emails"),
            ("user_email_integrations", "User email integrations"),
            ("user_roles", "User roles"),
            ("roles", "Custom roles"),
            ("tenant_subscription_history", "Tenant subscription history"),
            ("portal_users", "Portal users"),
            ("tenants", "Tenants"),
        ]
        
        for table_name, display_name in tenant_tables:
            safe_delete(table_name, display_name)
        
        # Phase 3: Clean up orphaned job references (set FK to NULL where allowed)
        print("\nPhase 3: Cleaning orphaned references in preserved tables...")
        
        cleanup_queries = [
            # Job postings sourced via email - clear user references
            ("UPDATE job_postings SET sourced_by_user_id = NULL WHERE sourced_by_user_id IS NOT NULL", 
             "Job posting user references"),
            # Job postings - clear tenant references for email-sourced jobs
            ("UPDATE job_postings SET source_tenant_id = NULL WHERE source_tenant_id IS NOT NULL",
             "Job posting tenant references"),
        ]
        
        for query, display_name in cleanup_queries:
            safe_update(query, display_name)
        
        # Summary
        print("\n" + "=" * 80)
        print("✅ DATA CLEANING COMPLETED!")
        print("=" * 80)
        print("\nPreserved data:")
        
        # Count preserved records
        preserved_counts = [
            ("job_postings", "Job postings"),
            ("global_roles", "Global roles"),
            ("subscription_plans", "Subscription plans"),
            ("pm_admin_users", "PM admin users"),
            ("permissions", "System permissions"),
        ]
        
        for table_name, display_name in preserved_counts:
            try:
                result = db.session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                count = result.scalar()
                print(f"  • {display_name}: {count}")
            except Exception:
                print(f"  • {display_name}: (table not found)")
        
        print("\nNext steps:")
        print("  1. Run './deploy.sh seed' to create new tenants")
        print("  2. Invite candidates via the portal")
        print("  3. Match candidates with existing jobs")
        print()


def seed_all(app: Flask) -> None:
    """Seed all data: plans, PM admin, roles, permissions, and sample tenants."""
    print("=" * 60)
    print("SEEDING ALL DATA")
    print("=" * 60)
    
    with app.app_context():
        # 1. Seed subscription plans
        print("\n1. Seeding subscription plans...")
        from app.seeds.subscription_plans import seed_subscription_plans
        seed_subscription_plans()
        
        # 2. Seed PM admin user
        print("\n2. Seeding PM admin user...")
        from app.seeds.pm_admin import seed_pm_admin
        seed_pm_admin()

        # 3. Seed roles and permissions
        print("\n3. Seeding roles and permissions...")
        from app.seeds.roles_and_permissions import seed_roles_and_permissions
        seed_roles_and_permissions()
        
        # 4. Seed sample tenants
        print("\n4. Seeding sample tenants...")
        from app.seeds.sample_tenants import seed_sample_tenants
        seed_sample_tenants(count=3)
        
        print("\n" + "=" * 60)
        print("✅ ALL DATA SEEDED SUCCESSFULLY!")
        print("=" * 60)


def migrate(app: Flask) -> None:
    """Run database migrations."""
    from alembic.config import Config
    from alembic import command
    
    alembic_cfg = Config("alembic.ini")
    
    with app.app_context():
        command.upgrade(alembic_cfg, "head")
        print("Migrations completed successfully")


def create_migration(app: Flask, message: str) -> None:
    """Create a new migration."""
    from alembic.config import Config
    from alembic import command
    
    alembic_cfg = Config("alembic.ini")
    
    with app.app_context():
        command.revision(alembic_cfg, autogenerate=True, message=message)
        print(f"Migration created with message: {message}")


def stamp_db(app: Flask, revision: str = "001") -> None:
    """Stamp database with a specific migration version without running it."""
    from alembic.config import Config
    from alembic import command
    
    alembic_cfg = Config("alembic.ini")
    
    with app.app_context():
        command.stamp(alembic_cfg, revision)
        print(f"Database stamped with revision: {revision}")


def setup_spacy(app: Flask) -> None:
    """Download and setup spaCy model."""
    import subprocess
    
    print("=" * 60)
    print("SETTING UP SPACY MODEL")
    print("=" * 60)
    
    try:
        # Downgrade to spaCy 3.7.2 if needed (more stable)
        print("\n1. Installing spaCy 3.7.2 (stable version)...")
        subprocess.run([sys.executable, "-m", "pip", "install", "spacy==3.7.2"], check=True)
        
        # Install model from wheel directly
        print("\n2. Installing en_core_web_sm model...")
        model_url = "https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl"
        subprocess.run([sys.executable, "-m", "pip", "install", model_url], check=True)
        
        # Verify installation
        print("\n3. Verifying installation...")
        import spacy
        nlp = spacy.load("en_core_web_sm")
        print("✅ spaCy model loaded successfully!")
        print(f"   Model: en_core_web_sm v{nlp.meta['version']}")
        print(f"   spaCy: v{spacy.__version__}")
        
        print("\n" + "=" * 60)
        print("✅ SPACY SETUP COMPLETE!")
        print("=" * 60)
        print("\n⚠️  Remember to restart Flask server for changes to take effect!")
    except Exception as e:
        print(f"\n❌ Error setting up spaCy: {e}")
        print("\nTry manually:")
        print("  pip install spacy==3.7.2")
        print("  pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl")
        print("\nThen verify:")
        print("  python -c \"import spacy; nlp = spacy.load('en_core_web_sm'); print('✅ Model loaded!')\"")
        sys.exit(1)


def import_jobs(app: Flask, platform: str, file_path: str, update_existing: bool = True) -> None:
    """
    Import jobs from JSON file into the GLOBAL job pool.
    
    Jobs are shared across ALL tenants. This import adds to the platform-wide job database.
    
    Args:
        platform: Platform name (indeed, dice, techfetch, glassdoor, monster)
        file_path: Path to JSON file
        update_existing: Whether to update existing jobs (default: True)
    """
    from app.services.job_import_service import JobImportService
    from pathlib import Path
    
    print("=" * 80)
    print(f"IMPORTING JOBS FROM {platform.upper()} (GLOBAL JOB POOL)")
    print("=" * 80)
    
    # Validate platform
    valid_platforms = ['indeed', 'dice', 'techfetch', 'glassdoor', 'monster']
    if platform.lower() not in valid_platforms:
        print(f"❌ Error: Invalid platform '{platform}'")
        print(f"   Valid platforms: {', '.join(valid_platforms)}")
        sys.exit(1)
    
    # Validate file exists
    file_path_obj = Path(file_path)
    if not file_path_obj.exists():
        print(f"❌ Error: File not found: {file_path}")
        sys.exit(1)
    
    print(f"\n📋 Import Configuration:")
    print(f"   Platform: {platform}")
    print(f"   File: {file_path}")
    print(f"   Job Scope: GLOBAL (shared across all tenants)")
    print(f"   Update Existing: {update_existing}")
    print(f"   File Size: {file_path_obj.stat().st_size / 1024:.2f} KB")
    print()
    
    try:
        with app.app_context():
            # Initialize service (platform-level imports by PM_ADMIN)
            service = JobImportService()
            
            # Start import
            print(f"🚀 Starting import at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("   Reading and parsing jobs into global pool...")
            
            batch = service.import_from_json(
                file_path=str(file_path_obj),
                platform=platform.lower(),
                update_existing=update_existing
            )
            
            # Display results
            print("\n" + "=" * 80)
            print("📊 IMPORT RESULTS")
            print("=" * 80)
            print(f"   Status: {batch.status}")
            print(f"   Total Jobs: {batch.total_jobs}")
            print(f"   New Jobs: {batch.new_jobs}")
            print(f"   Updated Jobs: {batch.updated_jobs}")
            print(f"   Failed Jobs: {batch.failed_jobs}")
            print(f"   Success Rate: {batch.success_rate:.1f}%")
            print(f"   Duration: {batch.duration_seconds:.2f} seconds")
            print(f"   Batch ID: {batch.batch_id}")
            
            if batch.failed_jobs > 0:
                print(f"\n⚠️  {batch.failed_jobs} jobs failed to import")
                if batch.error_log:
                    print("   First 5 errors:")
                    for i, (job_id, error) in enumerate(list(batch.error_log.items())[:5]):
                        print(f"   {i+1}. Job {job_id}: {error[:100]}")
            
            print("\n" + "=" * 80)
            if batch.status == 'COMPLETED':
                print("✅ IMPORT COMPLETED SUCCESSFULLY!")
            elif batch.status == 'COMPLETED_WITH_ERRORS':
                print("⚠️  IMPORT COMPLETED WITH SOME ERRORS")
            else:
                print("❌ IMPORT FAILED")
            print("=" * 80)
            
    except Exception as e:
        print("\n" + "=" * 80)
        print("❌ IMPORT FAILED")
        print("=" * 80)
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def generate_embeddings(app: Flask, entity_type: str = "all", batch_size: int = 15) -> None:
    """
    Generate embeddings for candidates and/or jobs that don't have embeddings yet.
    
    This is a one-time backfill operation for existing data. New candidates/jobs
    get embeddings automatically.
    
    Args:
        entity_type: What to process - 'candidates', 'jobs', or 'all' (default: 'all')
        batch_size: Number of items per batch (default: 15, max: 20)
    """
    from app.services.embedding_service import EmbeddingService
    from app.models.candidate import Candidate
    from app.models.job_posting import JobPosting
    from sqlalchemy import select
    import time
    
    print("=" * 80)
    print("EMBEDDING GENERATION - BACKFILL EXISTING DATA")
    print("=" * 80)
    
    # Validate entity type
    valid_types = ['candidates', 'jobs', 'all']
    if entity_type.lower() not in valid_types:
        print(f"❌ Error: Invalid entity_type '{entity_type}'")
        print(f"   Valid types: {', '.join(valid_types)}")
        sys.exit(1)
    
    # Validate batch size
    if batch_size < 1 or batch_size > 20:
        print(f"❌ Error: batch_size must be between 1 and 20 (got {batch_size})")
        sys.exit(1)
    
    print(f"\n📋 Configuration:")
    print(f"   Entity Type: {entity_type}")
    print(f"   Batch Size: {batch_size}")
    print(f"   API Rate Limit Protection: 0.5s delay between batches")
    print()
    
    try:
        with app.app_context():
            service = EmbeddingService()
            start_time = time.time()
            
            # Process candidates
            if entity_type.lower() in ['candidates', 'all']:
                print("=" * 80)
                print("📊 PROCESSING CANDIDATES")
                print("=" * 80)
                
                # Find candidates without embeddings
                query = select(Candidate).where(Candidate.embedding.is_(None))
                candidates = db.session.execute(query).scalars().all()
                
                total_candidates = len(candidates)
                print(f"\nFound {total_candidates} candidates without embeddings")
                
                if total_candidates > 0:
                    print(f"Processing in batches of {batch_size}...\n")
                    
                    successful = 0
                    failed = 0
                    
                    for i in range(0, total_candidates, batch_size):
                        batch = candidates[i:i + batch_size]
                        batch_num = (i // batch_size) + 1
                        total_batches = (total_candidates + batch_size - 1) // batch_size
                        
                        print(f"Batch {batch_num}/{total_batches} ({len(batch)} candidates):")
                        
                        for candidate in batch:
                            try:
                                embedding = service.generate_candidate_embedding(candidate)
                                
                                if embedding:
                                    candidate.embedding = embedding
                                    db.session.commit()
                                    successful += 1
                                    print(f"  ✅ {candidate.id}: {candidate.first_name} {candidate.last_name}")
                                else:
                                    failed += 1
                                    print(f"  ❌ {candidate.id}: Failed (embedding was None)")
                                    
                            except Exception as e:
                                failed += 1
                                print(f"  ❌ {candidate.id}: {str(e)[:80]}")
                                db.session.rollback()
                        
                        # Rate limiting delay
                        if i + batch_size < total_candidates:
                            print(f"  ⏳ Waiting 0.5s (rate limit)...\n")
                            time.sleep(0.5)
                    
                    print(f"\n📊 Candidate Results:")
                    print(f"   Total: {total_candidates}")
                    print(f"   Successful: {successful}")
                    print(f"   Failed: {failed}")
                    print(f"   Success Rate: {(successful/total_candidates*100):.1f}%")
                else:
                    print("✅ All candidates already have embeddings!")
            
            # Process jobs
            if entity_type.lower() in ['jobs', 'all']:
                print("\n" + "=" * 80)
                print("📊 PROCESSING JOB POSTINGS")
                print("=" * 80)
                
                # Find jobs without embeddings
                query = select(JobPosting).where(JobPosting.embedding.is_(None))
                jobs = db.session.execute(query).scalars().all()
                
                total_jobs = len(jobs)
                print(f"\nFound {total_jobs} jobs without embeddings")
                
                if total_jobs > 0:
                    print(f"Processing in batches of {batch_size}...\n")
                    
                    successful = 0
                    failed = 0
                    
                    for i in range(0, total_jobs, batch_size):
                        batch = jobs[i:i + batch_size]
                        batch_num = (i // batch_size) + 1
                        total_batches = (total_jobs + batch_size - 1) // batch_size
                        
                        print(f"Batch {batch_num}/{total_batches} ({len(batch)} jobs):")
                        
                        for job in batch:
                            try:
                                embedding = service.generate_job_embedding(job)
                                
                                if embedding:
                                    job.embedding = embedding
                                    db.session.commit()
                                    successful += 1
                                    print(f"  ✅ {job.id}: {job.title} @ {job.company}")
                                else:
                                    failed += 1
                                    print(f"  ❌ {job.id}: Failed (embedding was None)")
                                    
                            except Exception as e:
                                failed += 1
                                print(f"  ❌ {job.id}: {str(e)[:80]}")
                                db.session.rollback()
                        
                        # Rate limiting delay
                        if i + batch_size < total_jobs:
                            print(f"  ⏳ Waiting 0.5s (rate limit)...\n")
                            time.sleep(0.5)
                    
                    print(f"\n📊 Job Results:")
                    print(f"   Total: {total_jobs}")
                    print(f"   Successful: {successful}")
                    print(f"   Failed: {failed}")
                    print(f"   Success Rate: {(successful/total_jobs*100):.1f}%")
                else:
                    print("✅ All jobs already have embeddings!")
            
            # Final summary
            duration = time.time() - start_time
            print("\n" + "=" * 80)
            print("✅ EMBEDDING GENERATION COMPLETE!")
            print("=" * 80)
            print(f"   Total Duration: {duration:.2f} seconds")
            print(f"   Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print()
            
    except Exception as e:
        print("\n" + "=" * 80)
        print("❌ EMBEDDING GENERATION FAILED")
        print("=" * 80)
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def import_all_jobs(app: Flask, jobs_dir: str = "../jobs") -> None:
    """
    Import jobs from all platforms in the jobs directory into the GLOBAL job pool.
    
    Jobs are shared across ALL tenants. This import adds to the platform-wide job database.
    
    Args:
        jobs_dir: Directory containing job JSON files (default: "../jobs")
    """
    from pathlib import Path
    from app.services.job_import_service import JobImportService
    
    print("=" * 80)
    print("BULK IMPORT: ALL JOB PLATFORMS (GLOBAL JOB POOL)")
    print("=" * 80)
    
    jobs_path = Path(jobs_dir)
    if not jobs_path.exists():
        print(f"❌ Error: Jobs directory not found: {jobs_dir}")
        sys.exit(1)
    
    # Find all job JSON files
    platform_files = {
        'indeed': list(jobs_path.glob('indeed_jobs_*.json')),
        'dice': list(jobs_path.glob('dice_jobs_*.json')),
        'techfetch': list(jobs_path.glob('techfetch_jobs_*.json')),
        'glassdoor': list(jobs_path.glob('glassdoor_jobs_*.json')),
        'monster': list(jobs_path.glob('monster_jobs_*.json')),
    }
    
    total_files = sum(len(files) for files in platform_files.values())
    if total_files == 0:
        print(f"❌ No job files found in {jobs_dir}")
        print("   Expected files: *_jobs_*.json")
        sys.exit(1)
    
    print(f"\n📋 Found {total_files} job file(s):")
    for platform, files in platform_files.items():
        if files:
            for file in files:
                file_size = file.stat().st_size / 1024
                print(f"   • {platform}: {file.name} ({file_size:.2f} KB)")
    
    print(f"\n🚀 Starting bulk import at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("   Jobs will be added to the GLOBAL pool (shared across all tenants)")
    print()
    
    results = {}
    total_imported = 0
    total_failed = 0
    
    try:
        with app.app_context():
            # Initialize service (platform-level imports by PM_ADMIN)
            service = JobImportService()
            
            for platform, files in platform_files.items():
                if not files:
                    continue
                
                for file in files:
                    print(f"\n{'─' * 80}")
                    print(f"📥 Importing {platform.upper()}: {file.name}")
                    print(f"{'─' * 80}")
                    
                    try:
                        batch = service.import_from_json(
                            file_path=str(file),
                            platform=platform,
                            update_existing=True
                        )
                        
                        results[file.name] = {
                            'platform': platform,
                            'status': batch.status,
                            'total': batch.total_jobs,
                            'new': batch.new_jobs,
                            'updated': batch.updated_jobs,
                            'failed': batch.failed_jobs,
                            'duration': batch.duration_seconds,
                        }
                        
                        total_imported += batch.new_jobs + batch.updated_jobs
                        total_failed += batch.failed_jobs
                        
                        print(f"✅ {batch.new_jobs} new, {batch.updated_jobs} updated, {batch.failed_jobs} failed")
                        
                    except Exception as e:
                        print(f"❌ Failed: {str(e)}")
                        results[file.name] = {'status': 'FAILED', 'error': str(e)}
            
            # Summary
            print("\n" + "=" * 80)
            print("📊 BULK IMPORT SUMMARY")
            print("=" * 80)
            print(f"   Files Processed: {len(results)}")
            print(f"   Total Jobs Imported: {total_imported}")
            print(f"   Total Failed: {total_failed}")
            print()
            
            for filename, result in results.items():
                if result.get('status') == 'FAILED':
                    print(f"   ❌ {filename}: {result.get('error', 'Unknown error')}")
                else:
                    print(f"   ✅ {filename}: {result['new']} new, {result['updated']} updated ({result['duration']:.1f}s)")
            
            print("\n" + "=" * 80)
            print("✅ BULK IMPORT COMPLETED!")
            print("=" * 80)
            
    except Exception as e:
        print("\n" + "=" * 80)
        print("❌ BULK IMPORT FAILED")
        print("=" * 80)
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    app = create_app()
    
    commands = {
        "init": lambda: init_db(app),
        "drop": lambda: drop_db(app),
        "seed": lambda: seed_db(app),
        "migrate": lambda: migrate(app),
        "create-migration": lambda: create_migration(app, sys.argv[2] if len(sys.argv) > 2 else "auto"),
        "stamp": lambda: stamp_db(app, sys.argv[2] if len(sys.argv) > 2 else "001"),
        "seed-plans": lambda: seed_plans(app),
        "seed-pm-admin": lambda: seed_pm_admin_user(
            app, 
            email=sys.argv[2] if len(sys.argv) > 2 else None,
            password=sys.argv[3] if len(sys.argv) > 3 else None
        ),
        "seed-roles-and-permissions": lambda: seed_roles_and_permissions_command(app),
        "seed-tenants": lambda: seed_tenants(
            app, 
            count=int(sys.argv[2]) if len(sys.argv) > 2 else 3
        ),
        "seed-all": lambda: seed_all(app),
        "setup-spacy": lambda: setup_spacy(app),
        "import-jobs": lambda: import_jobs(
            app,
            platform=sys.argv[2] if len(sys.argv) > 2 else "",
            file_path=sys.argv[3] if len(sys.argv) > 3 else "",
            update_existing=sys.argv[4].lower() != 'false' if len(sys.argv) > 4 else True
        ),
        "import-all-jobs": lambda: import_all_jobs(
            app,
            jobs_dir=sys.argv[2] if len(sys.argv) > 2 else "../jobs"
        ),
        "generate-embeddings": lambda: generate_embeddings(
            app,
            entity_type=sys.argv[2] if len(sys.argv) > 2 else "all",
            batch_size=int(sys.argv[3]) if len(sys.argv) > 3 else 15
        ),
        "fix-processing-candidates": lambda: fix_processing_candidates(
            app,
            tenant_id=int(sys.argv[2]) if len(sys.argv) > 2 else None
        ),
        "clean-data": lambda: clean_data(
            app,
            confirm=sys.argv[2].lower() == 'yes' if len(sys.argv) > 2 else False
        ),
    }
    
    if len(sys.argv) < 2:
        print("Usage: python manage.py <command>")
        print("\nCommands:")
        print("  init                - Initialize database")
        print("  drop                - Drop all tables")
        print("  migrate             - Run migrations")
        print("  create-migration    - Create new migration")
        print("  stamp               - Mark database as at specific revision")
        print("                        Usage: stamp [revision] (default: 001)")
        print("  seed                - Seed legacy sample data")
        print("\nTenant Management Commands:")
        print("  seed-plans          - Seed subscription plans")
        print("  seed-pm-admin       - Seed PM admin user")
        print("                        Usage: seed-pm-admin [email] [password]")
        print("  seed-tenants        - Seed sample tenants")
        print("                        Usage: seed-tenants [count]")
        print("  seed-all            - Seed all (plans + PM admin + tenants)")
        print("\nJob Import Commands (GLOBAL - shared across all tenants):")
        print("  import-jobs         - Import jobs from single platform")
        print("                        Usage: import-jobs <platform> <file> [update_existing]")
        print("                        Example: import-jobs indeed ../jobs/indeed_jobs_2025-11-12.json true")
        print("  import-all-jobs     - Import jobs from all platforms in directory")
        print("                        Usage: import-all-jobs [jobs_dir]")
        print("                        Example: import-all-jobs ../jobs")
        print("\nEmbedding Commands:")
        print("  generate-embeddings - Generate embeddings for existing data without embeddings")
        print("                        Usage: generate-embeddings [entity_type] [batch_size]")
        print("                        entity_type: 'candidates', 'jobs', or 'all' (default: 'all')")
        print("                        batch_size: 1-20 (default: 15)")
        print("                        Example: generate-embeddings all 15")
        print("                        Example: generate-embeddings candidates 10")
        print("\nMaintenance Commands:")
        print("  fix-processing-candidates - Update stuck candidates from 'processing' to 'pending_review'")
        print("                        Usage: fix-processing-candidates [tenant_id]")
        print("                        Example: fix-processing-candidates 2")
        print("  clean-data            - Clean candidate/tenant data, preserve jobs")
        print("                        Usage: clean-data [yes]")
        print("                        Pass 'yes' to skip confirmation prompt")
        print("                        After cleaning, run 'seed-all' to recreate tenants")
        print("\nSetup Commands:")
        print("  setup-spacy         - Download and setup spaCy model for resume parsing")
        sys.exit(1)
    
    command = sys.argv[1]
    if command not in commands:
        print(f"Unknown command: {command}")
        sys.exit(1)
    
    commands[command]()
