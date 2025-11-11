#!/usr/bin/env python3
"""
Test script to manually send an Inngest event
Run this after starting the Flask app to test if Inngest is working
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.inngest import inngest_client

def test_inngest_event():
    """Send a test invitation event"""
    print("=" * 60)
    print("Testing Inngest Event Sending")
    print("=" * 60)
    
    try:
        # Send test event
        print("\n1. Sending test event 'email/invitation'...")
        result = inngest_client.send_event({
            "name": "email/invitation",
            "data": {
                "invitation_id": 999,
                "tenant_id": 1
            }
        })
        
        print(f"✅ Event sent successfully!")
        print(f"   Result: {result}")
        
        print("\n2. Check the Inngest dashboard at: http://localhost:8288")
        print("   You should see the event in the 'Events' tab")
        print("   And a run should appear in the 'Runs' tab")
        
    except Exception as e:
        print(f"❌ Failed to send event: {e}")
        print(f"   Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        
    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_inngest_event()
