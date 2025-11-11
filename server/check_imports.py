#!/usr/bin/env python
"""Quick import check before migration"""
import sys

print("Checking imports...")

try:
    print("1. Checking models...")
    from app.models.candidate_invitation import CandidateInvitation
    from app.models.invitation_audit_log import InvitationAuditLog
    from app.models.candidate_document import CandidateDocument
    print("   ✅ Models OK")
    
    print("2. Checking services...")
    from app.services.invitation_service import InvitationService
    from app.services.document_service import DocumentService
    from app.services.email_service import EmailService
    print("   ✅ Services OK")
    
    print("3. Checking schemas...")
    from app.schemas.invitation_schema import InvitationCreateSchema
    from app.schemas.document_schema import DocumentUploadSchema
    print("   ✅ Schemas OK")
    
    print("4. Checking routes...")
    from app.routes import invitation_routes
    print("   ✅ Routes OK")
    
    print("\n✅ All imports successful! Ready to migrate.")
    sys.exit(0)
    
except Exception as e:
    print(f"\n❌ Import error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
