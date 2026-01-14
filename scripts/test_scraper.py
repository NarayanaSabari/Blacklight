#!/usr/bin/env python3
"""
Scraper API Test Script

This script tests the scraper API endpoints by simulating a complete scraping workflow:
1. Get next role from queue
2. Submit jobs for each platform
3. Complete the session

Usage:
    python test_scraper.py --api-key YOUR_API_KEY [--base-url http://localhost:5000]

Options:
    --api-key, -k     Your scraper API key (required)
    --base-url, -u    Base URL of the API (default: http://localhost:5000)
    --mode, -m        Scraping mode: 'role' or 'role-location' (default: role)
    --dry-run, -d     Only fetch role, don't submit fake jobs
    --verbose, -v     Enable verbose output
"""

import argparse
import json
import random
import string
import sys
from datetime import datetime, timedelta
from typing import Any, Optional

try:
    import requests
except ImportError:
    print("Error: 'requests' package is required. Install with: pip install requests")
    sys.exit(1)


# Sample job data for testing
SAMPLE_COMPANIES = [
    "TechCorp Inc", "DataFlow Systems", "CloudNine Solutions", "AI Innovations",
    "CyberSecure Ltd", "FinTech Global", "HealthTech Pro", "GreenEnergy Corp",
    "SmartLogistics", "DigitalFirst Agency", "CodeCraft Studios", "NetWorks Plus",
    "Quantum Computing Co", "AutoDrive Tech", "SpaceX Clone", "MetaVerse Labs"
]

SAMPLE_LOCATIONS = [
    "San Francisco, CA", "New York, NY", "Austin, TX", "Seattle, WA",
    "Boston, MA", "Denver, CO", "Los Angeles, CA", "Chicago, IL",
    "Atlanta, GA", "Miami, FL", "Portland, OR", "Remote"
]

SAMPLE_DESCRIPTIONS = [
    "We are looking for a talented {role} to join our dynamic team.",
    "Join our innovative company as a {role} and help us build the future.",
    "Exciting opportunity for a {role} with experience in modern technologies.",
    "We're hiring a {role} to work on cutting-edge projects.",
    "Looking for a passionate {role} to drive our technical initiatives.",
]


class ScraperAPIClient:
    """Client for interacting with the Scraper API."""
    
    def __init__(self, base_url: str, api_key: str, verbose: bool = False):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.verbose = verbose
        self.session = requests.Session()
        self.session.headers.update({
            'X-Scraper-API-Key': api_key,
            'Content-Type': 'application/json'
        })
    
    def _log(self, message: str):
        """Print message if verbose mode is enabled."""
        if self.verbose:
            print(f"  [DEBUG] {message}")
    
    def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Make an API request and return JSON response."""
        url = f"{self.base_url}{endpoint}"
        self._log(f"{method.upper()} {url}")
        
        if 'json' in kwargs:
            self._log(f"Payload: {json.dumps(kwargs['json'], indent=2)[:500]}...")
        
        response = self.session.request(method, url, **kwargs)
        
        self._log(f"Status: {response.status_code}")
        
        try:
            data = response.json()
        except json.JSONDecodeError:
            data = {'error': response.text, 'status_code': response.status_code}
        
        if not response.ok:
            raise APIError(response.status_code, data)
        
        return data
    
    def health_check(self) -> dict:
        """Check if the API is healthy."""
        return self._request('GET', '/api/scraper/health')
    
    def get_queue_stats(self) -> dict:
        """Get queue statistics."""
        return self._request('GET', '/api/scraper/queue/stats')
    
    def get_location_queue_stats(self) -> dict:
        """Get role+location queue statistics."""
        return self._request('GET', '/api/scraper/queue/location-stats')
    
    def get_current_session(self) -> dict:
        """Check if there's an active session."""
        return self._request('GET', '/api/scraper/queue/current-session')
    
    def get_next_role(self) -> dict:
        """Get the next role from the queue."""
        return self._request('GET', '/api/scraper/queue/next-role')
    
    def get_next_role_location(self) -> dict:
        """Get the next role+location combination."""
        return self._request('GET', '/api/scraper/queue/next-role-location')
    
    def submit_jobs(self, session_id: str, platform: str, jobs: list, 
                    batch_index: int = 0, total_batches: int = 1) -> dict:
        """Submit jobs for a platform."""
        payload = {
            'session_id': session_id,
            'platform': platform,
            'jobs': jobs,
            'batch_index': batch_index,
            'total_batches': total_batches
        }
        return self._request('POST', '/api/scraper/queue/jobs', json=payload)
    
    def complete_session(self, session_id: str) -> dict:
        """Complete a scraping session."""
        return self._request('POST', '/api/scraper/queue/complete', json={
            'session_id': session_id
        })
    
    def fail_session(self, session_id: str, error_message: str) -> dict:
        """Report session failure."""
        return self._request('POST', '/api/scraper/queue/fail', json={
            'session_id': session_id,
            'error_message': error_message
        })
    
    def get_credential(self, platform: str, session_id: str) -> dict:
        """Get next available credential for a platform."""
        return self._request('GET', f'/api/scraper-credentials/queue/{platform}/next', 
                           params={'session_id': session_id})
    
    def release_credential(self, credential_id: int) -> dict:
        """Release a credential without reporting success/failure."""
        return self._request('POST', f'/api/scraper-credentials/queue/{credential_id}/release')


class APIError(Exception):
    """API error with status code and response data."""
    
    def __init__(self, status_code: int, data: dict):
        self.status_code = status_code
        self.data = data
        message = data.get('error') or data.get('message') or str(data)
        super().__init__(f"API Error {status_code}: {message}")


def generate_job_id() -> str:
    """Generate a random job ID."""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))


def generate_fake_job(role_name: str, platform: str, location: Optional[str] = None, 
                      job_id: Optional[str] = None, company: Optional[str] = None) -> dict:
    """Generate a fake job posting for testing.
    
    Args:
        role_name: The role name for the job
        platform: Platform name (e.g., 'linkedin', 'monster')
        location: Job location (optional, random if not provided)
        job_id: Custom job ID (optional, for creating duplicates)
        company: Custom company name (optional, for creating duplicates)
    """
    company = company or random.choice(SAMPLE_COMPANIES)
    job_location = location or random.choice(SAMPLE_LOCATIONS)
    description_template = random.choice(SAMPLE_DESCRIPTIONS)
    
    # Create a more detailed description
    description = f"""
{description_template.format(role=role_name)}

About the Role:
We are seeking an experienced {role_name} to join our team at {company}. 
This is an exciting opportunity to work on challenging projects and grow your career.

Requirements:
- 3+ years of relevant experience
- Strong communication skills
- Team player with problem-solving abilities
- Bachelor's degree or equivalent experience

Benefits:
- Competitive salary
- Health, dental, and vision insurance
- 401(k) matching
- Flexible work arrangements
- Professional development opportunities

Location: {job_location}
    """.strip()
    
    # Random salary range
    salary_min = random.randint(60, 150) * 1000
    salary_max = salary_min + random.randint(20, 50) * 1000
    
    # Use provided job_id or generate new one
    platform_job_id = job_id or f"{platform}_{generate_job_id()}"
    
    job = {
        # Use 'jobId' - the primary field name expected by backend
        'jobId': platform_job_id,
        # Also include alternate field names for compatibility
        'platform_job_id': platform_job_id,
        'external_job_id': platform_job_id,
        'title': f"{role_name} - {random.choice(['Senior', 'Mid-Level', 'Lead', 'Staff', 'Principal'])}",
        'company': company,
        'location': job_location,
        'description': description,
        # Use 'jobUrl' - the field name expected by backend
        'jobUrl': f"https://{platform}.com/jobs/{platform_job_id}",
        'url': f"https://{platform}.com/jobs/{platform_job_id}",
        'salary_min': salary_min,
        'salary_max': salary_max,
        'salary_currency': 'USD',
        # Use 'jobType' - the field name expected by backend
        'jobType': random.choice(['full_time', 'contract', 'full_time', 'full_time']),
        'job_type': random.choice(['full_time', 'contract', 'full_time', 'full_time']),
        'experience_level': random.choice(['mid', 'senior', 'mid', 'senior', 'entry']),
        # Use 'postedDate' - the field name expected by backend
        'postedDate': (datetime.now() - timedelta(days=random.randint(0, 30))).strftime('%Y-%m-%d'),
        'posted_date': (datetime.now() - timedelta(days=random.randint(0, 30))).strftime('%Y-%m-%d'),
        # Use 'isRemote' - the field name expected by backend
        'isRemote': job_location == 'Remote' or random.random() < 0.3,
        'is_remote': job_location == 'Remote' or random.random() < 0.3
    }
    
    return job


def generate_jobs_batch(role_name: str, platform: str, location: Optional[str],
                        total_jobs: int, unique_percent: int = 70) -> list:
    """Generate a batch of jobs with specified unique/duplicate ratio.
    
    Args:
        role_name: The role name for the jobs
        platform: Platform name
        location: Job location
        total_jobs: Total number of jobs to generate
        unique_percent: Percentage of unique jobs (default 70%)
    
    Returns:
        List of job dictionaries
    """
    unique_count = int(total_jobs * unique_percent / 100)
    duplicate_count = total_jobs - unique_count
    
    jobs = []
    
    # Generate unique jobs
    print(f"      Generating {unique_count} unique jobs...")
    for i in range(unique_count):
        job = generate_fake_job(role_name, platform, location)
        jobs.append(job)
    
    # Generate duplicates by reusing some job IDs and companies from unique jobs
    if duplicate_count > 0 and unique_count > 0:
        print(f"      Generating {duplicate_count} duplicate jobs...")
        # Pick random jobs to duplicate
        jobs_to_duplicate = random.choices(jobs[:unique_count], k=duplicate_count)
        for original_job in jobs_to_duplicate:
            # Create duplicate with same platform_job_id (will be detected as duplicate)
            duplicate = generate_fake_job(
                role_name, 
                platform, 
                location,
                job_id=original_job['platform_job_id'],  # Same job ID = duplicate
                company=original_job['company']
            )
            jobs.append(duplicate)
    
    # Shuffle to mix unique and duplicates
    random.shuffle(jobs)
    
    return jobs


def print_header(title: str):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


def print_success(message: str):
    """Print a success message."""
    print(f"✓ {message}")


def print_error(message: str):
    """Print an error message."""
    print(f"✗ {message}")


def print_info(message: str):
    """Print an info message."""
    print(f"→ {message}")


def run_tests(client: ScraperAPIClient, mode: str = 'role', dry_run: bool = False,
               total_jobs: int = 5, unique_percent: int = 70):
    """Run the scraper API tests.
    
    Args:
        client: API client instance
        mode: Scraping mode ('role' or 'role-location')
        dry_run: If True, only fetch role without submitting jobs
        total_jobs: Total number of jobs to generate and submit
        unique_percent: Percentage of unique jobs (rest are duplicates)
    """
    
    print_header("Scraper API Test Suite")
    print(f"Base URL: {client.base_url}")
    print(f"Mode: {mode}")
    print(f"Dry Run: {dry_run}")
    print(f"Total Jobs: {total_jobs} ({unique_percent}% unique, {100-unique_percent}% duplicates)")
    
    # Test 1: Health Check
    print_header("1. Health Check")
    try:
        result = client.health_check()
        print_success(f"API is healthy: {result}")
    except APIError as e:
        print_error(f"Health check failed: {e}")
        return False
    
    # Test 2: Queue Stats
    print_header("2. Queue Statistics")
    try:
        if mode == 'role-location':
            stats = client.get_location_queue_stats()
            print_success(f"Location Queue Stats:")
            print(f"   Total entries: {stats.get('total_location_entries', 0)}")
            print(f"   Unique roles: {stats.get('unique_roles', 0)}")
            print(f"   Unique locations: {stats.get('unique_locations', 0)}")
            print(f"   By status: {json.dumps(stats.get('by_status', {}), indent=6)}")
        else:
            stats = client.get_queue_stats()
            print_success(f"Queue Stats:")
            print(f"   Queue depth: {stats.get('queue_depth', 0)}")
            print(f"   Total pending candidates: {stats.get('total_pending_candidates', 0)}")
            print(f"   By status: {json.dumps(stats.get('by_status', {}), indent=6)}")
    except APIError as e:
        print_error(f"Failed to get stats: {e}")
    
    # Test 3: Check Current Session
    print_header("3. Check Current Session")
    try:
        session_check = client.get_current_session()
        if session_check.get('has_active_session'):
            print_info(f"Active session exists: {session_check.get('session', {}).get('session_id')}")
            print_info("You may need to complete or fail this session first.")
        else:
            print_success("No active session")
    except APIError as e:
        print_error(f"Failed to check session: {e}")
    
    # Test 4: Get Next Role
    print_header(f"4. Get Next Role ({mode})")
    try:
        if mode == 'role-location':
            role_data = client.get_next_role_location()
        else:
            role_data = client.get_next_role()
        
        session_id = role_data.get('session_id')
        role = role_data.get('role', {})
        platforms = role_data.get('platforms', [])
        location = role_data.get('location')
        
        print_success(f"Got role: {role.get('name')}")
        print(f"   Session ID: {session_id}")
        print(f"   Role ID: {role.get('id')}")
        if location:
            print(f"   Location: {location}")
        print(f"   Platforms: {', '.join([p.get('name', p) for p in platforms])}")
        
    except APIError as e:
        if e.status_code == 404:
            print_info("No roles available in queue")
            return True
        elif e.status_code == 409:
            print_error("Conflict: Active session already exists")
            return False
        else:
            print_error(f"Failed to get role: {e}")
            return False
    
    if dry_run:
        print_header("5. Dry Run - Skipping Job Submission")
        print_info("Dry run mode - not submitting fake jobs")
        print_info(f"Would submit jobs for platforms: {[p.get('name') for p in platforms]}")
        
        # Fail the session to release the role back to queue
        print_header("6. Releasing Session (Fail)")
        try:
            result = client.fail_session(session_id, "Dry run test - releasing role back to queue")
            print_success(f"Session released: {result.get('status')}")
        except APIError as e:
            print_error(f"Failed to release session: {e}")
        
        return True
    
    # Test 5: Submit Jobs for Each Platform
    print_header("5. Submit Jobs")
    role_name = role.get('name', 'Software Engineer')
    
    # Track totals across all platforms
    grand_total_submitted = 0
    grand_total_imported = 0
    grand_total_skipped = 0
    
    for platform_info in platforms:
        platform_name = platform_info.get('name') if isinstance(platform_info, dict) else platform_info
        
        print(f"\n   Platform: {platform_name}")
        print(f"   Generating {total_jobs} jobs ({unique_percent}% unique)...")
        
        # Generate all jobs for this platform
        all_jobs = generate_jobs_batch(role_name, platform_name, location, total_jobs, unique_percent)
        
        print(f"   Submitting {len(all_jobs)} jobs in a single request...")
        print(f"   (Backend will split into batches of 20 for Inngest processing)")
        
        try:
            # Send ALL jobs in a single API request
            # The backend handles batching internally for Inngest
            result = client.submit_jobs(
                session_id=session_id,
                platform=platform_name,
                jobs=all_jobs,
                batch_index=0,
                total_batches=1
            )
            
            # Parse response
            jobs_count = result.get('jobs_count', len(all_jobs))
            batches = result.get('batches', 1)
            status = result.get('platform_status', 'unknown')
            
            print_success(f"Submitted {jobs_count} jobs")
            print(f"      Status: {status}")
            print(f"      Backend batches: {batches}")
            
            grand_total_submitted += jobs_count
            
            # Note: imported/skipped counts won't be available immediately
            # since Inngest processes asynchronously
            print(f"      Note: Jobs are being processed asynchronously by Inngest")
            
        except APIError as e:
            print_error(f"Failed to submit jobs: {e}")
    
    # Summary
    print(f"\n   {'='*50}")
    print(f"   TOTAL SUBMITTED: {grand_total_submitted} jobs")
    print(f"   (Check Inngest dashboard for processing status)")
    
    # Test 6: Complete Session
    print_header("6. Complete Session")
    try:
        result = client.complete_session(session_id)
        print_success(f"Session completed!")
        print(f"   Role: {result.get('role_name')}")
        if result.get('location'):
            print(f"   Location: {result.get('location')}")
        
        # Handle different response structures
        summary = result.get('summary', {})
        if isinstance(summary, dict):
            print(f"   Total platforms: {summary.get('total_platforms', 0)}")
            print(f"   Platforms completed: {summary.get('platforms_completed', 0)}")
            print(f"   Duration: {summary.get('duration_seconds', 0)}s")
        
        jobs_summary = result.get('jobs', {})
        if isinstance(jobs_summary, dict):
            print(f"   Jobs found: {jobs_summary.get('found', 0)}")
            print(f"   Jobs imported: {jobs_summary.get('imported', 0)}")
            print(f"   Jobs skipped: {jobs_summary.get('skipped', 0)}")
        
    except APIError as e:
        print_error(f"Failed to complete session: {e}")
        return False
    
    print_header("Test Complete")
    print_success("All tests passed!")
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Test the Scraper API endpoints',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic test with role mode (submits 5 jobs by default)
  python test_scraper.py -k YOUR_API_KEY

  # Submit 1000 jobs (70% unique, 30% duplicates) to test batch processing
  python test_scraper.py -k YOUR_API_KEY --jobs 1000

  # Submit 500 jobs with 80% unique
  python test_scraper.py -k YOUR_API_KEY --jobs 500 --unique-percent 80

  # Test with role-location mode
  python test_scraper.py -k YOUR_API_KEY -m role-location

  # Dry run (don't submit fake jobs)
  python test_scraper.py -k YOUR_API_KEY --dry-run

  # Custom API URL
  python test_scraper.py -k YOUR_API_KEY -u https://api.example.com

  # Verbose output
  python test_scraper.py -k YOUR_API_KEY -v

  # Fail/release a stuck session
  python test_scraper.py -k YOUR_API_KEY --fail-session SESSION_ID

  # Check current session status
  python test_scraper.py -k YOUR_API_KEY --status
        """
    )
    
    parser.add_argument(
        '-k', '--api-key',
        required=True,
        help='Your Scraper API key'
    )
    
    parser.add_argument(
        '-u', '--base-url',
        default='https://blacklight-backend-259077698611.asia-south1.run.app',
        help='Base URL of the API (default: https://blacklight-backend-259077698611.asia-south1.run.app)'
    )
    
    parser.add_argument(
        '-m', '--mode',
        choices=['role', 'role-location'],
        default='role',
        help='Scraping mode (default: role)'
    )
    
    parser.add_argument(
        '-d', '--dry-run',
        action='store_true',
        help='Only fetch role, do not submit fake jobs'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--fail-session',
        metavar='SESSION_ID',
        help='Fail/release a stuck session by its ID'
    )
    
    parser.add_argument(
        '--status',
        action='store_true',
        help='Only check current session status and queue stats'
    )
    
    parser.add_argument(
        '-j', '--jobs',
        type=int,
        default=5,
        help='Total number of jobs to generate per platform (default: 5)'
    )
    
    parser.add_argument(
        '--unique-percent',
        type=int,
        default=70,
        choices=range(0, 101),
        metavar='0-100',
        help='Percentage of unique jobs, rest are duplicates (default: 70)'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.jobs < 1:
        parser.error("--jobs must be at least 1")
    
    # Create client
    client = ScraperAPIClient(
        base_url=args.base_url,
        api_key=args.api_key,
        verbose=args.verbose
    )
    
    try:
        # Handle --fail-session command
        if args.fail_session:
            print_header("Failing Session")
            print(f"Session ID: {args.fail_session}")
            try:
                result = client.fail_session(args.fail_session, "Manual session termination via test script")
                print_success(f"Session failed successfully!")
                print(f"   Status: {result.get('status')}")
                print(f"   Message: {result.get('error_message', 'Session terminated')}")
            except APIError as e:
                print_error(f"Failed to terminate session: {e}")
                sys.exit(1)
            sys.exit(0)
        
        # Handle --status command
        if args.status:
            print_header("Scraper Status Check")
            print(f"Base URL: {client.base_url}")
            
            # Health check
            try:
                result = client.health_check()
                print_success(f"API is healthy")
            except APIError as e:
                print_error(f"API health check failed: {e}")
                sys.exit(1)
            
            # Check current session
            try:
                session_check = client.get_current_session()
                if session_check.get('has_active_session'):
                    session = session_check.get('session', {})
                    print_info(f"Active session found:")
                    print(f"   Session ID: {session.get('session_id')}")
                    print(f"   Role: {session.get('role_name')}")
                    print(f"   Location: {session.get('location', 'N/A')}")
                    print(f"   Started: {session.get('started_at')}")
                    print(f"\n   To release this session, run:")
                    print(f"   python test_scraper.py -k {args.api_key[:8]}... --fail-session {session.get('session_id')}")
                else:
                    print_success("No active session")
            except APIError as e:
                print_error(f"Failed to check session: {e}")
            
            # Queue stats
            try:
                if args.mode == 'role-location':
                    stats = client.get_location_queue_stats()
                    print(f"\nLocation Queue Stats:")
                    print(f"   Total entries: {stats.get('total_location_entries', 0)}")
                    print(f"   Unique roles: {stats.get('unique_roles', 0)}")
                    print(f"   Unique locations: {stats.get('unique_locations', 0)}")
                else:
                    stats = client.get_queue_stats()
                    print(f"\nQueue Stats:")
                    print(f"   Queue depth: {stats.get('queue_depth', 0)}")
                    print(f"   Total pending candidates: {stats.get('total_pending_candidates', 0)}")
            except APIError as e:
                print_error(f"Failed to get stats: {e}")
            
            sys.exit(0)
        
        # Run full tests
        success = run_tests(
            client, 
            mode=args.mode, 
            dry_run=args.dry_run,
            total_jobs=args.jobs,
            unique_percent=args.unique_percent
        )
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
