#!/bin/sh
set -e

# Replace ${PORT} in nginx config with actual PORT environment variable
export PORT=${PORT:-8080}

# Use envsubst to replace environment variables in nginx config
envsubst '${PORT}' < /etc/nginx/conf.d/default.conf > /etc/nginx/conf.d/default.conf.tmp
mv /etc/nginx/conf.d/default.conf.tmp /etc/nginx/conf.d/default.conf

# Execute the CMD
exec "$@"
