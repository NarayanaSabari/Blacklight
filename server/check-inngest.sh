#!/bin/bash
# Inngest Troubleshooting Script
# Run this to diagnose Inngest integration issues

echo "========================================"
echo "Inngest Integration Diagnostics"
echo "========================================"
echo ""

# 1. Check if Inngest dev server is running
echo "1. Checking if Inngest dev server is running..."
if curl -s http://localhost:8288/health > /dev/null 2>&1; then
    echo "   ✅ Inngest dev server is running at http://localhost:8288"
else
    echo "   ❌ Inngest dev server is NOT running"
    echo "      Start it with: inngest dev"
    exit 1
fi
echo ""

# 2. Check if Flask app is running
echo "2. Checking if Flask app is running..."
if curl -s http://localhost:5000/health > /dev/null 2>&1; then
    echo "   ✅ Flask app is running at http://localhost:5000"
else
    echo "   ❌ Flask app is NOT running"
    echo "      Start it with: flask run or ./run-local.sh"
    exit 1
fi
echo ""

# 3. Check if Inngest endpoint is accessible
echo "3. Checking if Inngest endpoint is registered..."
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/api/inngest)
if [ "$response" = "200" ] || [ "$response" = "405" ]; then
    echo "   ✅ Inngest endpoint accessible at /api/inngest"
else
    echo "   ❌ Inngest endpoint NOT accessible (HTTP $response)"
    echo "      Check Flask logs for Inngest registration errors"
fi
echo ""

# 4. Check Flask logs for Inngest registration
echo "4. Checking environment variables..."
if [ -f ".env" ]; then
    echo "   .env file found"
    if grep -q "INNGEST_DEV=true" .env; then
        echo "   ✅ INNGEST_DEV=true (development mode)"
    else
        echo "   ⚠️  INNGEST_DEV not set or false"
    fi
    
    if grep -q "INNGEST_BASE_URL" .env; then
        inngest_url=$(grep "INNGEST_BASE_URL" .env | cut -d'=' -f2)
        echo "   ✅ INNGEST_BASE_URL=$inngest_url"
    fi
    
    if grep -q "INNGEST_SERVE_ORIGIN" .env; then
        serve_origin=$(grep "INNGEST_SERVE_ORIGIN" .env | cut -d'=' -f2)
        echo "   ✅ INNGEST_SERVE_ORIGIN=$serve_origin"
    fi
else
    echo "   ⚠️  No .env file found, using defaults"
fi
echo ""

# 5. Test sending an event
echo "5. Testing event sending..."
echo "   Run: python test_inngest_event.py"
echo ""

# 6. Next steps
echo "========================================"
echo "Next Steps:"
echo "========================================"
echo "1. Open Inngest dashboard: http://localhost:8288"
echo "2. Check 'Apps' tab - should show 'blacklight-hr'"
echo "3. Check 'Functions' tab - should show 8 functions"
echo "4. Test creating an invitation to trigger an event"
echo "5. Check 'Events' tab for incoming events"
echo "6. Check 'Runs' tab for function executions"
echo ""
echo "If functions are not showing up:"
echo "- Restart Flask app"
echo "- Check Flask logs: docker-compose logs app"
echo "- Look for: 'Inngest: Registered X functions'"
echo ""
echo "If events are not triggering runs:"
echo "- Verify event name matches: 'email/invitation'"
echo "- Check Flask logs for '[INNGEST]' messages"
echo "- Verify INNGEST_SERVE_ORIGIN points to Flask"
echo ""
