#!/bin/bash
# Test Inngest Connection and Registration

echo "=========================================="
echo "Testing Inngest Connection"
echo "=========================================="
echo ""

# 1. Check if Flask is running
echo "1. Testing Flask app..."
if curl -s http://localhost:5000/health > /dev/null 2>&1; then
    echo "   ✅ Flask is running on http://localhost:5000"
else
    echo "   ❌ Flask is NOT running!"
    echo "   Start Flask first: ./run-local.sh"
    exit 1
fi
echo ""

# 2. Check if Inngest endpoint is accessible
echo "2. Testing Inngest endpoint on Flask..."
response=$(curl -s -w "\n%{http_code}" http://localhost:5000/api/inngest)
http_code=$(echo "$response" | tail -n 1)
body=$(echo "$response" | head -n -1)

if [ "$http_code" = "200" ] || [ "$http_code" = "405" ]; then
    echo "   ✅ Inngest endpoint is accessible (HTTP $http_code)"
    echo "   Response preview: ${body:0:100}..."
else
    echo "   ❌ Inngest endpoint returned HTTP $http_code"
    echo "   Response: $body"
    exit 1
fi
echo ""

# 3. Check if Inngest dev server is running
echo "3. Testing Inngest dev server..."
if curl -s http://localhost:8288/health > /dev/null 2>&1; then
    echo "   ✅ Inngest dev server is running on http://localhost:8288"
else
    echo "   ❌ Inngest dev server is NOT running!"
    echo "   Start it: docker-compose -f docker-compose.local.yml up -d inngest"
    exit 1
fi
echo ""

# 4. Test if Inngest can reach Flask from inside container
echo "4. Testing if Inngest container can reach Flask..."
docker exec blacklight-inngest-local wget -q -O - http://host.docker.internal:5000/health > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "   ✅ Inngest container can reach Flask via host.docker.internal"
else
    echo "   ❌ Inngest container CANNOT reach Flask via host.docker.internal"
    echo "   This is the problem!"
fi
echo ""

# 5. Try manual registration
echo "5. Attempting manual registration..."
register_response=$(curl -s -w "\n%{http_code}" -X PUT http://localhost:8288/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "url": "http://host.docker.internal:5000/api/inngest",
    "appId": "blacklight-hr"
  }')

register_code=$(echo "$register_response" | tail -n 1)
register_body=$(echo "$register_response" | head -n -1)

if [ "$register_code" = "200" ] || [ "$register_code" = "201" ]; then
    echo "   ✅ Manual registration successful!"
    echo "   Response: $register_body"
else
    echo "   ⚠️  Registration returned HTTP $register_code"
    echo "   Response: $register_body"
fi
echo ""

# 6. Try triggering auto-discovery
echo "6. Triggering auto-discovery by hitting Flask endpoint from Inngest container..."
docker exec blacklight-inngest-local wget -q -O - http://host.docker.internal:5000/api/inngest 2>&1 | head -n 5
echo ""

echo "=========================================="
echo "Results:"
echo "=========================================="
echo "Now check: http://localhost:8288"
echo "- Apps tab should show: blacklight-hr"
echo "- Functions tab should show: 8 functions"
echo ""
echo "If still not showing, check Flask logs for:"
echo "  'Inngest: Registered X functions'"
echo ""
