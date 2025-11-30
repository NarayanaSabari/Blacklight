# Credentials Directory

Place your GCS credentials JSON file here as `gcs-credentials.json`.

**Important:** This file should NEVER be committed to git!

## Setup

1. Download your GCS service account key from Google Cloud Console
2. Rename it to `gcs-credentials.json`
3. Place it in this directory

The docker-compose will mount this file into the backend container at `/app/credentials/gcs-credentials.json`.
