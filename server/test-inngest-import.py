#!/usr/bin/env python3
"""
Test if Inngest can be imported and registered
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("Testing Inngest Import and Registration")
print("=" * 60)
print()

# Test 1: Check if inngest package is installed
print("1. Checking if 'inngest' package is installed...")
try:
    import inngest
    version = getattr(inngest, '__version__', 'unknown')
    print(f"   ✅ inngest package found (version: {version})")
except ImportError as e:
    print(f"   ❌ inngest package NOT installed!")
    print(f"   Error: {e}")
    print("   Fix: pip install inngest==0.4.5")
    sys.exit(1)
print()

# Test 2: Check if Inngest client can be imported
print("2. Checking if inngest_client can be imported...")
try:
    from app.inngest import inngest_client
    print(f"   ✅ inngest_client imported successfully")
    print(f"   App ID: {inngest_client.app_id}")
except Exception as e:
    print(f"   ❌ Failed to import inngest_client")
    print(f"   Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
print()

# Test 3: Check if functions can be imported
print("3. Checking if Inngest functions can be imported...")
try:
    from app.inngest.functions import INNGEST_FUNCTIONS
    print(f"   ✅ Functions imported successfully")
    print(f"   Number of functions: {len(INNGEST_FUNCTIONS)}")
    for i, func in enumerate(INNGEST_FUNCTIONS, 1):
        # Try different attributes to get function ID
        fn_id = getattr(func._opts, 'id', None) or getattr(func._opts, 'fn_id', None) or f"function-{i}"
        print(f"      {i}. {fn_id}")
except Exception as e:
    print(f"   ❌ Failed to import functions")
    print(f"   Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
print()

# Test 4: Try to create Inngest serve blueprint
print("4. Checking if Inngest serve can be created...")
try:
    from flask import Flask
    from inngest.flask import serve as inngest_serve
    
    # Create a minimal Flask app for testing
    test_app = Flask(__name__)
    inngest_serve(
        test_app,
        inngest_client,
        INNGEST_FUNCTIONS,
    )
    print(f"   ✅ Inngest serve configured successfully")
except Exception as e:
    print(f"   ❌ Failed to create Inngest blueprint")
    print(f"   Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
print()

# Test 5: Check if Flask app has the blueprint registered
print("5. Checking if Flask app has Inngest registered...")
try:
    from app import create_app
    app = create_app()
    
    # Check if blueprint is registered
    inngest_registered = any('inngest' in str(bp) for bp in app.blueprints.values())
    
    if inngest_registered:
        print(f"   ✅ Inngest blueprint is registered in Flask")
        print(f"   Registered blueprints: {list(app.blueprints.keys())}")
    else:
        print(f"   ❌ Inngest blueprint NOT found in Flask")
        print(f"   Registered blueprints: {list(app.blueprints.keys())}")
        
    # Try to get the endpoint
    with app.app_context():
        try:
            from flask import url_for
            inngest_url = url_for('inngest.index', _external=False)
            print(f"   Inngest endpoint: {inngest_url}")
        except Exception as e:
            print(f"   ⚠️  Could not generate inngest URL: {e}")
            
except Exception as e:
    print(f"   ❌ Failed to check Flask app")
    print(f"   Error: {e}")
    import traceback
    traceback.print_exc()
print()

print("=" * 60)
print("Diagnosis Complete")
print("=" * 60)
