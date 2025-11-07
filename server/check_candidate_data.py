#!/usr/bin/env python
"""
Quick script to check candidate data in database
"""
import sys
from app import create_app, db
from app.models.candidate import Candidate

def check_candidate(candidate_id):
    """Check candidate data in database"""
    app = create_app()
    
    with app.app_context():
        candidate = db.session.get(Candidate, candidate_id)
        
        if not candidate:
            print(f"❌ Candidate {candidate_id} not found")
            return
        
        print(f"\n✓ Candidate {candidate_id}: {candidate.full_name}")
        print(f"  Tenant ID: {candidate.tenant_id}")
        print(f"  Email: {candidate.email}")
        print(f"  Phone: {candidate.phone}")
        print(f"  Location: {candidate.location}")
        print(f"  Current Title: {candidate.current_title}")
        print(f"  Total Experience: {candidate.total_experience_years} years")
        
        print(f"\n📚 Education Entries: {len(candidate.education or [])}")
        if candidate.education:
            for i, edu in enumerate(candidate.education, 1):
                print(f"  {i}. {edu.get('degree')} - {edu.get('institution')}")
        
        print(f"\n💼 Work Experience Entries: {len(candidate.work_experience or [])}")
        if candidate.work_experience:
            for i, exp in enumerate(candidate.work_experience, 1):
                print(f"  {i}. {exp.get('title')} at {exp.get('company')}")
                print(f"     {exp.get('start_date')} - {exp.get('end_date')}")
        else:
            print("  ⚠️ No work experience data found!")
        
        print(f"\n🔧 Skills: {len(candidate.skills or [])}")
        if candidate.skills:
            print(f"  {', '.join(candidate.skills[:10])}{'...' if len(candidate.skills) > 10 else ''}")
        
        print(f"\n🎓 Certifications: {len(candidate.certifications or [])}")
        if candidate.certifications:
            for cert in candidate.certifications:
                print(f"  - {cert}")
        
        print(f"\n📄 Resume File: {candidate.resume_file_path}")
        print(f"   Uploaded: {candidate.resume_uploaded_at}")
        print(f"   Parsed: {candidate.resume_parsed_at}")
        
        # Check parsed_resume_data
        if candidate.parsed_resume_data:
            parsed_work = candidate.parsed_resume_data.get('work_experience', [])
            print(f"\n🔍 Parsed Resume Data - Work Experience: {len(parsed_work)}")
            if parsed_work:
                print("   ✓ Work experience data exists in parsed_resume_data")
            else:
                print("   ❌ No work experience in parsed_resume_data")
        else:
            print("\n❌ No parsed_resume_data found")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python check_candidate_data.py <candidate_id>")
        sys.exit(1)
    
    candidate_id = int(sys.argv[1])
    check_candidate(candidate_id)
