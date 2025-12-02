#!/bin/bash
set -e

# Create inngest database for Inngest server
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE inngest;
    GRANT ALL PRIVILEGES ON DATABASE inngest TO $POSTGRES_USER;
EOSQL

echo "Inngest database created successfully"
