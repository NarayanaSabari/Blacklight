#!/usr/bin/env python3
"""
Blacklight Scraper Queue Test Script

A comprehensive test script to simulate the full scraper workflow:
1. Authenticate with API key
2. Get next role (or role+location) from queue
3. Simulate job scraping for each platform
4. Submit jobs per platform
5. Complete the session

Usage:
    # Set environment variables
    export SCRAPER_API_KEY="your-api-key"
    export SCRAPER_API_URL="http://localhost"  # or your server URL (no /api suffix)
    
    # Run the test
    python test_scraper_queue.py
    
    # With options
    python test_scraper_queue.py --mode role-location --jobs 10 --fail-platform indeed
"""

import os
import sys
import json
import time
import random
import argparse
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class ScraperConfig:
    """Configuration for the test scraper."""
    api_url: str = "http://localhost"
    api_key: str = ""
    mode: str = "role-location"  # "role-location" (default) or "role" (legacy)
    jobs_per_platform: int = 5
    fail_platforms: List[str] = field(default_factory=list)
    delay_between_platforms: float = 1.0
    simulate_real_delay: bool = True
    verbose: bool = True


# ============================================================================
# API CLIENT
# ============================================================================

class ScraperApiClient:
    """Client for interacting with Blacklight Scraper API."""
    
    def __init__(self, config: ScraperConfig):
        self.config = config
        self.session_id: Optional[str] = None
        self.role: Optional[Dict] = None
        self.location: Optional[str] = None
        self.platforms: List[Dict] = []
        
    def _headers(self) -> Dict[str, str]:
        return {
            "X-Scraper-API-Key": self.config.api_key,
            "Content-Type": "application/json"
        }
    
    def _log(self, message: str, level: str = "INFO"):
        if self.config.verbose:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] [{level}] {message}")
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> requests.Response:
        url = f"{self.config.api_url}{endpoint}"
        
        if method == "GET":
            response = requests.get(url, headers=self._headers())
        elif method == "POST":
            response = requests.post(url, headers=self._headers(), json=data)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        return response
    
    # -------------------------------------------------------------------------
    # Step 1: Check for existing session
    # -------------------------------------------------------------------------
    
    def check_current_session(self) -> Optional[Dict]:
        """Check if there's an active session for this scraper."""
        self._log("Checking for existing active session...")
        
        response = self._make_request("GET", "/api/scraper/queue/current-session")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("has_active_session"):
                session = data["session"]
                self._log(f"Found active session: {session['session_id']}", "WARNING")
                if session.get('location'):
                    self._log(f"  Location: {session['location']}", "WARNING")
                return session
            else:
                self._log("No active session found")
                return None
        else:
            self._log(f"Error checking session: {response.status_code}", "ERROR")
            return None
    
    # -------------------------------------------------------------------------
    # Step 2: Get next role from queue
    # -------------------------------------------------------------------------
    
    def get_next_role(self) -> bool:
        """Get next role from the queue. Returns True if successful."""
        endpoint = "/api/scraper/queue/next-role"
        if self.config.mode == "role-location":
            endpoint = "/api/scraper/queue/next-role-location"
        
        self._log(f"Requesting next {self.config.mode} from queue...")
        
        response = self._make_request("GET", endpoint)
        
        if response.status_code == 204:
            self._log("Queue is empty - no roles to scrape", "WARNING")
            return False
        
        if response.status_code == 409:
            error = response.json()
            self._log(f"Conflict: {error.get('message')}", "ERROR")
            return False
        
        if response.status_code != 200:
            self._log(f"Error getting next role: {response.status_code}", "ERROR")
            self._log(f"Response: {response.text}", "ERROR")
            return False
        
        data = response.json()
        self.session_id = data["session_id"]
        self.role = data["role"]
        self.platforms = data.get("platforms", [])
        self.location = data.get("location")
        
        self._log(f"✓ Session started: {self.session_id}")
        self._log(f"  Role: {self.role['name']} (ID: {self.role['id']})")
        if self.location:
            self._log(f"  Location: {self.location}")
        self._log(f"  Platforms: {', '.join(p['name'] for p in self.platforms)}")
        self._log(f"  Candidates waiting: {self.role.get('candidate_count', 0)}")
        
        return True
    
    # -------------------------------------------------------------------------
    # Step 3: Generate mock jobs for a platform
    # -------------------------------------------------------------------------
    
    def generate_mock_jobs(self, platform: str, count: int) -> List[Dict]:
        """Generate mock job postings for testing."""
        jobs = []
        
        role_name = self.role["name"]
        location = self.location or "Remote"
        
        companies = [
            "TechCorp", "InnovateTech", "DataDriven Inc", "CloudNine Systems",
            "AI Solutions", "DevOps Masters", "CodeFactory", "ByteWorks",
            "Digital Dynamics", "Software Synergy", "Tech Titans", "Cloud Computing Co"
        ]
        
        job_types = ["Full-time", "Contract", "Contract-to-Hire"]
        experience_levels = ["Entry Level", "Mid Level", "Senior", "Lead", "Principal"]
        
        for i in range(count):
            job = {
                "external_job_id": f"{platform}-{self.role['id']}-{int(time.time())}-{i}",
                "title": f"{random.choice(experience_levels)} {role_name}",
                "company": random.choice(companies),
                "location": location,
                "job_type": random.choice(job_types),
                "description": f"We are looking for a talented {role_name} to join our team...",
                "requirements": [
                    f"5+ years of experience in {role_name.lower()} roles",
                    "Strong communication skills",
                    "Experience with modern tools and technologies"
                ],
                "salary_range": f"${random.randint(80, 180)}K - ${random.randint(180, 250)}K",
                "posted_date": datetime.now().strftime("%Y-%m-%d"),
                "source_url": f"https://{platform}.com/jobs/{i}",
                "source_platform": platform
            }
            jobs.append(job)
        
        return jobs
    
    # -------------------------------------------------------------------------
    # Step 4: Submit jobs for a platform
    # -------------------------------------------------------------------------
    
    def submit_platform_jobs(self, platform: Dict, jobs: List[Dict], simulate_failure: bool = False) -> bool:
        """Submit jobs for a specific platform."""
        platform_name = platform["name"]
        
        if simulate_failure:
            self._log(f"  [{platform_name}] Simulating failure...", "WARNING")
            
            response = self._make_request("POST", "/api/scraper/queue/jobs", {
                "session_id": self.session_id,
                "platform": platform_name,
                "status": "failed",
                "error_message": "Simulated failure for testing",
                "jobs": []
            })
        else:
            self._log(f"  [{platform_name}] Submitting {len(jobs)} jobs...")
            
            response = self._make_request("POST", "/api/scraper/queue/jobs", {
                "session_id": self.session_id,
                "platform": platform_name,
                "jobs": jobs
            })
        
        if response.status_code == 202:
            data = response.json()
            progress = data.get("progress", {})
            self._log(
                f"  [{platform_name}] ✓ Accepted - "
                f"Progress: {progress.get('completed', 0)}/{progress.get('total_platforms', 0)} platforms"
            )
            return True
        else:
            self._log(f"  [{platform_name}] ✗ Error: {response.status_code}", "ERROR")
            self._log(f"  Response: {response.text}", "ERROR")
            return False
    
    # -------------------------------------------------------------------------
    # Step 5: Complete the session
    # -------------------------------------------------------------------------
    
    def complete_session(self) -> bool:
        """Complete the scrape session."""
        self._log("Completing session...")
        
        response = self._make_request("POST", "/api/scraper/queue/complete", {
            "session_id": self.session_id
        })
        
        if response.status_code == 200:
            data = response.json()
            summary = data.get("summary", {})
            jobs = data.get("jobs", {})
            
            self._log("=" * 60)
            self._log("SESSION COMPLETED SUCCESSFULLY")
            self._log("=" * 60)
            self._log(f"Session ID: {data['session_id']}")
            self._log(f"Role: {data['role_name']}")
            if data.get('location'):
                self._log(f"Location: {data['location']}")
            self._log(f"Duration: {data.get('duration_seconds', 0)} seconds")
            self._log("")
            self._log("Platform Summary:")
            self._log(f"  - Total: {summary.get('total_platforms', 0)}")
            self._log(f"  - Successful: {summary.get('successful_platforms', 0)}")
            self._log(f"  - Failed: {summary.get('failed_platforms', 0)}")
            
            if summary.get("failed_platform_details"):
                self._log("  - Failed Details:")
                for detail in summary["failed_platform_details"]:
                    self._log(f"      {detail['platform']}: {detail['error']}")
            
            self._log("")
            self._log("Jobs Summary:")
            self._log(f"  - Found: {jobs.get('total_found', 0)}")
            self._log(f"  - Imported: {jobs.get('total_imported', 0)}")
            self._log(f"  - Skipped: {jobs.get('total_skipped', 0)}")
            self._log("")
            self._log(f"Matching Triggered: {data.get('matching_triggered', False)}")
            self._log("=" * 60)
            
            return True
        else:
            self._log(f"Error completing session: {response.status_code}", "ERROR")
            self._log(f"Response: {response.text}", "ERROR")
            return False
    
    # -------------------------------------------------------------------------
    # Run full workflow
    # -------------------------------------------------------------------------
    
    def run_full_workflow(self) -> bool:
        """Run the complete scraper workflow."""
        self._log("=" * 60)
        self._log("BLACKLIGHT SCRAPER TEST - STARTING")
        self._log("=" * 60)
        self._log(f"API URL: {self.config.api_url}")
        self._log(f"Mode: {self.config.mode}")
        self._log(f"Jobs per platform: {self.config.jobs_per_platform}")
        if self.config.fail_platforms:
            self._log(f"Simulating failures for: {', '.join(self.config.fail_platforms)}")
        self._log("=" * 60)
        self._log("")
        
        # Step 1: Check for existing session
        existing = self.check_current_session()
        if existing:
            self._log("Cannot start new session - complete the existing one first", "ERROR")
            return False
        
        # Step 2: Get next role
        if not self.get_next_role():
            return False
        
        self._log("")
        
        # Step 3 & 4: Scrape and submit jobs for each platform
        self._log("Processing platforms...")
        self._log("-" * 40)
        
        for platform in self.platforms:
            platform_name = platform["name"]
            
            # Simulate scraping delay
            if self.config.simulate_real_delay:
                delay = random.uniform(0.5, 2.0)
                time.sleep(delay)
            
            # Check if we should simulate failure
            should_fail = platform_name.lower() in [p.lower() for p in self.config.fail_platforms]
            
            if should_fail:
                self.submit_platform_jobs(platform, [], simulate_failure=True)
            else:
                # Generate mock jobs
                jobs = self.generate_mock_jobs(platform_name, self.config.jobs_per_platform)
                self.submit_platform_jobs(platform, jobs)
            
            # Delay between platforms
            if self.config.delay_between_platforms > 0:
                time.sleep(self.config.delay_between_platforms)
        
        self._log("-" * 40)
        self._log("")
        
        # Step 5: Complete session
        return self.complete_session()


# ============================================================================
# QUEUE STATS VIEWER
# ============================================================================

def view_queue_stats(config: ScraperConfig):
    """View current queue statistics."""
    headers = {
        "X-Scraper-API-Key": config.api_key,
        "Content-Type": "application/json"
    }
    
    print("=" * 60)
    print("QUEUE STATISTICS")
    print("=" * 60)
    
    # Role queue stats
    response = requests.get(
        f"{config.api_url}/api/scraper/queue/stats",
        headers=headers
    )
    
    if response.status_code == 200:
        stats = response.json()
        print("\nRole Queue:")
        print(f"  Queue depth: {stats.get('queue_depth', 0)} roles ready to scrape")
        print(f"  Total pending candidates: {stats.get('total_pending_candidates', 0)}")
        print("\n  By Status:")
        for status, count in stats.get('by_status', {}).items():
            print(f"    - {status}: {count}")
        print("\n  By Priority:")
        for priority, count in stats.get('by_priority', {}).items():
            print(f"    - {priority}: {count}")
    else:
        print(f"Error getting stats: {response.status_code}")
    
    # Location queue stats
    response = requests.get(
        f"{config.api_url}/api/scraper/queue/location-stats",
        headers=headers
    )
    
    if response.status_code == 200:
        stats = response.json()
        print("\n\nRole+Location Queue:")
        print(f"  Queue depth: {stats.get('queue_depth', 0)} entries ready to scrape")
        print(f"  Total entries: {stats.get('total_location_entries', 0)}")
        print(f"  Unique roles: {stats.get('unique_roles', 0)}")
        print(f"  Unique locations: {stats.get('unique_locations', 0)}")
        print("\n  By Status:")
        for status, count in stats.get('by_status', {}).items():
            print(f"    - {status}: {count}")
    
    print("=" * 60)


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Test the Blacklight Scraper Queue API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Default: Role+location scraping test
    python test_scraper_queue.py
    
    # Legacy role-only scraping (not recommended)
    python test_scraper_queue.py --mode role
    
    # Generate 20 jobs per platform
    python test_scraper_queue.py --jobs 20
    
    # Simulate failure for Indeed platform
    python test_scraper_queue.py --fail-platform indeed
    
    # View queue statistics only
    python test_scraper_queue.py --stats-only
    
    # Use custom API URL
    python test_scraper_queue.py --url http://api.example.com
        """
    )
    
    parser.add_argument(
        "--url", 
        default=os.getenv("SCRAPER_API_URL", "http://localhost"),
        help="API base URL (default: SCRAPER_API_URL env or http://localhost)"
    )
    parser.add_argument(
        "--key",
        default=os.getenv("SCRAPER_API_KEY", ""),
        help="Scraper API key (default: SCRAPER_API_KEY env)"
    )
    parser.add_argument(
        "--mode",
        choices=["role-location", "role"],
        default="role-location",
        help="Scraping mode: 'role-location' (default) for location-specific or 'role' for legacy role-only"
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=5,
        help="Number of mock jobs to generate per platform (default: 5)"
    )
    parser.add_argument(
        "--fail-platform",
        action="append",
        dest="fail_platforms",
        default=[],
        help="Platform name to simulate failure for (can be used multiple times)"
    )
    parser.add_argument(
        "--no-delay",
        action="store_true",
        help="Disable simulated delays between operations"
    )
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Only view queue statistics, don't run scraper test"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce output verbosity"
    )
    
    args = parser.parse_args()
    
    if not args.key:
        print("ERROR: Scraper API key required.")
        print("Set SCRAPER_API_KEY environment variable or use --key option.")
        sys.exit(1)
    
    config = ScraperConfig(
        api_url=args.url.rstrip("/"),
        api_key=args.key,
        mode=args.mode,
        jobs_per_platform=args.jobs,
        fail_platforms=args.fail_platforms or [],
        simulate_real_delay=not args.no_delay,
        verbose=not args.quiet
    )
    
    if args.stats_only:
        view_queue_stats(config)
    else:
        client = ScraperApiClient(config)
        success = client.run_full_workflow()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
