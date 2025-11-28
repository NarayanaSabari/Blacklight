#!/bin/sh
set -e

# Replace PORT_PLACEHOLDER in nginx config with actual PORT environment variable
# Cloud Run sets PORT environment variable (default 8080)
PORT=${PORT:-8080}

# Use sed to replace the placeholder with actual port
sed -i "s/PORT_PLACEHOLDER/$PORT/g" /etc/nginx/conf.d/default.conf

echo "Starting nginx on port $PORT"

# Execute the CMD
exec "$@"
