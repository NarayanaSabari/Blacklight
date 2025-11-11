#!/bin/bash

# Script to manually sync Inngest with your local Flask app
# Run this after starting your Flask app and Inngest dev server

echo "Syncing Inngest with Flask app..."
echo "Flask app should be running at: http://localhost:5000"
echo "Inngest dev server should be running at: http://localhost:8288"
echo ""

# Use curl to trigger the Inngest dev server to discover your app
curl -X PUT \
  http://localhost:8288/dev/register \
  -H "Content-Type: application/json" \
  -d '{
    "url": "http://host.docker.internal:5000/api/inngest",
    "deployId": "local-dev"
  }'

echo ""
echo "Sync complete! Check http://localhost:8288 to see if your app appears."
