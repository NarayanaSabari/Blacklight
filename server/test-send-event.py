#!/usr/bin/env python3
"""
Test sending an event to Inngest
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment
from dotenv import load_dotenv
load_dotenv()

print("=" * 60)
print("Testing Event Sending to Inngest")
print("=" * 60)
print()

print(f"INNGEST_DEV: {os.getenv('INNGEST_DEV')}")
print(f"INNGEST_BASE_URL: {os.getenv('INNGEST_BASE_URL')}")
print()

try:
    from app.inngest import inngest_client
    import inngest
    
    print(f"✅ Inngest client loaded")
    print(f"   App ID: {inngest_client.app_id}")
    print(f"   Is Production: {inngest_client._mode}")
    print()
    
    print("Sending test event 'email/invitation'...")
    result = inngest_client.send_sync(
        inngest.Event(
            name="email/invitation",
            data={
                "invitation_id": 999,
                "tenant_id": 999,
                "test": True
            }
        )
    )
    
    print(f"✅ Event sent successfully!")
    print(f"   Result: {result}")
    print()
    
    print("Check the Inngest Dev Server at http://localhost:8288")
    print("You should see a new run for the 'send-invitation-email' function")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("=" * 60)
