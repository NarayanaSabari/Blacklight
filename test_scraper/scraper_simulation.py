#!/usr/bin/env python3
"""
Blacklight Scraper Simulation Script

This script simulates a real job scraper by:
1. Accepting manual API key input from user
2. Fetching next role from queue
3. Extracting platform list from response
4. Submitting dummy jobs for each platform
5. Completing the session

Usage:
    python scraper_simulation.py
    python scraper_simulation.py --api-key <your-key>
    python scraper_simulation.py --server http://localhost:5000
"""

import requests
import json
import sys
import time
import argparse
from typing import Dict, List, Optional, Any
from datetime import datetime
from uuid import UUID

# ANSI color codes for pretty output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(text: str):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*80}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{text.center(80)}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'='*80}{Colors.ENDC}\n")


def print_section(text: str):
    """Print a section header"""
    print(f"\n{Colors.CYAN}{Colors.BOLD}→ {text}{Colors.ENDC}")
    print(f"{Colors.CYAN}{'-'*80}{Colors.ENDC}")


def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}✅ {text}{Colors.ENDC}")


def print_info(text: str):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.ENDC}")


def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.ENDC}")


def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}❌ {text}{Colors.ENDC}")


def get_api_key() -> str:
    """Get API key from user input"""
    print_section("API Authentication")
    
    api_key = input(f"{Colors.YELLOW}Enter your Scraper API Key: {Colors.ENDC}").strip()
    
    if not api_key:
        print_error("API key cannot be empty")
        sys.exit(1)
    
    print_success(f"API key received: {api_key[:10]}...{api_key[-5:]}")
    return api_key


def get_server_url() -> str:
    """Get server URL from user or use default"""
    print_section("Server Configuration")
    
    default_url = "http://localhost:5000"
    url_input = input(f"{Colors.YELLOW}Enter server URL (default: {default_url}): {Colors.ENDC}").strip()
    
    server_url = url_input if url_input else default_url
    print_success(f"Using server: {server_url}")
    return server_url


def fetch_next_role(api_key: str, server_url: str) -> Optional[Dict[str, Any]]:
    """Fetch next role from queue"""
    print_section("Fetching Next Role from Queue")
    
    url = f"{server_url}/api/scraper/queue/next-role"
    headers = {
        "X-Scraper-API-Key": api_key,
        "Content-Type": "application/json"
    }
    
    try:
        print_info(f"Sending GET request to: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print_success("Successfully fetched next role")
            print_info(f"Response status: {response.status_code}")
            
            # Extract role details from nested object
            role = data.get('role', {})
            
            # Print response details
            print(f"\n{Colors.BOLD}Role Details:{Colors.ENDC}")
            print(f"  Session ID:       {Colors.CYAN}{data.get('session_id')}{Colors.ENDC}")
            print(f"  Role ID:          {Colors.CYAN}{role.get('id')}{Colors.ENDC}")
            print(f"  Role Name:        {Colors.CYAN}{role.get('name')}{Colors.ENDC}")
            print(f"  Category:         {Colors.CYAN}{role.get('category', 'N/A')}{Colors.ENDC}")
            print(f"  Candidate Count:  {Colors.CYAN}{role.get('candidate_count', 0)}{Colors.ENDC}")
            print(f"  Aliases:          {Colors.CYAN}{', '.join(role.get('aliases', []))}{Colors.ENDC}")
            
            platforms = data.get('platforms', [])
            print(f"  Platforms Count:  {Colors.CYAN}{len(platforms)}{Colors.ENDC}")
            
            if platforms:
                print(f"\n{Colors.BOLD}Available Platforms:{Colors.ENDC}")
                for i, platform in enumerate(platforms, 1):
                    print(f"  {i}. {Colors.CYAN}{platform.get('display_name')}{Colors.ENDC} "
                          f"(name: {platform.get('name')}, priority: {platform.get('priority')})")
            
            return data
        
        elif response.status_code == 404:
            print_warning("No roles in queue - check if queue has data")
            print_info(f"Response: {response.json()}")
            return None
        
        elif response.status_code == 401:
            print_error("Unauthorized - invalid API key")
            return None
        
        else:
            print_error(f"Failed to fetch role: {response.status_code}")
            print_info(f"Response: {response.text}")
            return None
    
    except requests.exceptions.Timeout:
        print_error("Request timeout - server not responding")
        return None
    except requests.exceptions.ConnectionError:
        print_error(f"Connection error - cannot connect to {server_url}")
        return None
    except Exception as e:
        print_error(f"Error fetching next role: {str(e)}")
        return None


def generate_dummy_jobs(platform_name: str, count: int = 5, unique: bool = False) -> List[Dict[str, Any]]:
    """Generate dummy job listings for a platform
    
    Args:
        platform_name: Name of the platform (e.g., 'monster', 'glassdoor')
        count: Number of jobs to generate
        unique: If True, generate unique IDs that won't be deduplicated.
                If False (default), generate stable IDs that WILL be deduplicated on re-runs.
    """
    companies = ["TechCorp", "Innovation Labs", "CloudSys", "DataWare", "AI Solutions", "DevOps Pro"]
    locations = ["San Francisco, CA", "New York, NY", "Austin, TX", "Seattle, WA", "Remote"]
    titles = [
        "Senior Software Engineer",
        "DevOps Engineer", 
        "Full Stack Developer",
        "Backend Engineer",
        "Cloud Architect",
        "Data Engineer"
    ]
    
    jobs = []
    for i in range(count):
        # Use stable IDs (deduplicatable) or unique IDs (always imported)
        if unique:
            external_id = f"{platform_name}_job_{int(time.time())}_{i}"
        else:
            # Stable ID: same every run, will be deduplicated
            external_id = f"{platform_name}_stable_job_{i:04d}"
        
        job = {
            "external_id": external_id,
            "title": f"{titles[i % len(titles)]} - {platform_name.title()}",
            "company": companies[i % len(companies)],
            "location": locations[i % len(locations)],
            "salary_min": 120000 + (i * 10000),
            "salary_max": 180000 + (i * 10000),
            "url": f"https://{platform_name}.example.com/job/{external_id}",
            "description": f"We are looking for a talented {titles[i % len(titles)]} with 5+ years of experience. "
                          f"Join {companies[i % len(companies)]} and work on cutting-edge technology.",
            "posted_date": datetime.now().isoformat()
        }
        jobs.append(job)
    
    return jobs


def submit_jobs_for_platform(
    api_key: str,
    server_url: str,
    session_id: str,
    platform_id: int,
    platform_name: str,
    jobs: List[Dict[str, Any]]
) -> bool:
    """Submit jobs for a specific platform"""
    
    url = f"{server_url}/api/scraper/queue/jobs"
    headers = {
        "X-Scraper-API-Key": api_key,
        "Content-Type": "application/json"
    }
    
    payload = {
        "session_id": session_id,
        "platform": platform_name,
        "jobs": jobs
    }
    
    try:
        print_info(f"Submitting {len(jobs)} jobs for platform: {platform_name}")
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if response.status_code in (200, 202):
            data = response.json()
            print_success(f"Platform {Colors.CYAN}{platform_name}{Colors.ENDC}: "
                         f"Submitted {Colors.GREEN}{len(jobs)}{Colors.ENDC} jobs")
            print_info(f"  Status: {data.get('status')}")
            print_info(f"  Platform status: {data.get('platform_status')}")
            return True
        else:
            print_error(f"Failed to submit jobs for {platform_name}: {response.status_code}")
            print_info(f"Response: {response.text}")
            return False
    
    except Exception as e:
        print_error(f"Error submitting jobs for {platform_name}: {str(e)}")
        return False


# Global flag for unique job generation
GENERATE_UNIQUE_JOBS = False


def submit_all_jobs(
    api_key: str,
    server_url: str,
    role_data: Dict[str, Any]
) -> bool:
    """Submit jobs for all platforms"""
    print_section("Submitting Jobs for All Platforms")
    
    session_id = role_data.get('session_id')
    platforms = role_data.get('platforms', [])
    
    if not platforms:
        print_warning("No platforms in role data")
        return False
    
    submitted_count = 0
    for platform in platforms:
        platform_id = platform.get('id')
        platform_name = platform.get('name')
        display_name = platform.get('display_name')
        
        # Generate dummy jobs for this platform (uses global flag)
        dummy_jobs = generate_dummy_jobs(platform_name, count=3, unique=GENERATE_UNIQUE_JOBS)
        
        # Submit jobs
        if submit_jobs_for_platform(
            api_key,
            server_url,
            session_id,
            platform_id,
            platform_name,
            dummy_jobs
        ):
            submitted_count += 1
        
        # Small delay between submissions
        time.sleep(0.5)
    
    print_success(f"Submitted jobs for {Colors.GREEN}{submitted_count}/{len(platforms)}{Colors.ENDC} platforms")
    return submitted_count == len(platforms)


def complete_session(api_key: str, server_url: str, session_id: str) -> bool:
    """Complete the scrape session and trigger job matching"""
    print_section("Completing Session")
    
    url = f"{server_url}/api/scraper/queue/complete"
    headers = {
        "X-Scraper-API-Key": api_key,
        "Content-Type": "application/json"
    }
    
    payload = {
        "session_id": session_id,
        "session_status": "completed"
    }
    
    try:
        print_info(f"Marking session as completed: {Colors.CYAN}{session_id}{Colors.ENDC}")
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print_success("Session completed successfully")
            print_info(f"Response: {json.dumps(data, indent=2)}")
            
            if 'workflow_triggered' in data:
                print_success("Job matching workflow has been triggered")
            
            return True
        else:
            print_error(f"Failed to complete session: {response.status_code}")
            print_info(f"Response: {response.text}")
            return False
    
    except Exception as e:
        print_error(f"Error completing session: {str(e)}")
        return False


def run_simulation():
    """Run the complete scraper simulation"""
    print_header("Blacklight Scraper Simulation")
    
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Simulate a job scraper for Blacklight",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scraper_simulation.py
  python scraper_simulation.py --api-key your-key-here
  python scraper_simulation.py --server http://api.example.com:5000
  python scraper_simulation.py --unique  # Generate unique jobs each run (no dedup)
        """
    )
    parser.add_argument("--api-key", help="Scraper API key (if not provided, will prompt)")
    parser.add_argument("--server", default="http://localhost:5000", help="Server URL (default: http://localhost:5000)")
    parser.add_argument("--skip-complete", action="store_true", help="Skip session completion step")
    parser.add_argument("--unique", action="store_true", help="Generate unique job IDs (won't be deduplicated)")
    
    args = parser.parse_args()
    
    # Store unique flag globally for job generation
    global GENERATE_UNIQUE_JOBS
    GENERATE_UNIQUE_JOBS = args.unique
    
    # Get API key
    api_key = args.api_key or get_api_key()
    server_url = args.server
    
    print_section("Simulation Configuration")
    print_info(f"Server URL: {Colors.CYAN}{server_url}{Colors.ENDC}")
    print_info(f"API Key: {Colors.CYAN}{api_key[:10]}...{api_key[-5:]}{Colors.ENDC}")
    if args.unique:
        print_warning("Unique mode: Jobs will NOT be deduplicated (new jobs each run)")
    else:
        print_info("Stable mode: Jobs will be deduplicated on re-runs")
    
    # Step 1: Fetch next role
    role_data = fetch_next_role(api_key, server_url)
    if not role_data:
        print_error("Failed to fetch next role - aborting simulation")
        sys.exit(1)
    
    # Step 2: Submit jobs for all platforms
    if not submit_all_jobs(api_key, server_url, role_data):
        print_error("Failed to submit all jobs - aborting simulation")
        sys.exit(1)
    
    # Step 3: Complete session (optional)
    if not args.skip_complete:
        if not complete_session(api_key, server_url, role_data.get('session_id')):
            print_error("Failed to complete session")
            sys.exit(1)
    
    # Summary
    print_section("Simulation Complete")
    print_success("Scraper simulation workflow completed successfully!")
    
    role = role_data.get('role', {})
    print_info(f"Session ID: {Colors.CYAN}{role_data.get('session_id')}{Colors.ENDC}")
    print_info(f"Role ID: {Colors.CYAN}{role.get('id')}{Colors.ENDC}")
    print_info(f"Role Name: {Colors.CYAN}{role.get('name')}{Colors.ENDC}")
    print_info(f"Platforms processed: {Colors.CYAN}{len(role_data.get('platforms', []))}{Colors.ENDC}")
    print_info(f"Total jobs submitted: {Colors.CYAN}{len(role_data.get('platforms', [])) * 3}{Colors.ENDC}")
    
    print(f"\n{Colors.GREEN}{Colors.BOLD}✨ Next Steps:{Colors.ENDC}")
    print_info("1. Check the Dashboard for the new session")
    print_info("2. Monitor the Inngest dashboard for workflow execution")
    print_info("3. Verify jobs were imported in the database")
    print_info("4. Check logs: ./deploy.sh logs")
    
    print(f"\n{Colors.BOLD}Thank you for testing! 🎉{Colors.ENDC}\n")


if __name__ == "__main__":
    try:
        run_simulation()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Simulation interrupted by user{Colors.ENDC}")
        sys.exit(0)
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        sys.exit(1)
