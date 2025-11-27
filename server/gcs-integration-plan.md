# GCS Integration Plan — Candidate Documents & Resumes

## Summary
Goal: Integrate Google Cloud Storage (GCS) as the canonical backend for storing all candidate documents (resumes, id_proof, work authorization, certificates, other). This covers both document CRUD and resume upload + parsing workflows.

User decisions captured:
- Use GCS for both candidate documents and resumes.
- Add explicit fields: `resume_file_key` and `resume_storage_backend` to the `Candidate` model (rather than reusing `resume_file_path`).
- Clearing existing DB / files; no migration is required by us (you'll clear existing data and start fresh on GCP).
- Credential strategy to be decided later (Workload Identity or secret manager recommended).
- No special region or data residency requirements at the moment.

---

## Key Highlights of Current Repo
- `FileStorageService` supports local FS and GCS. See:
```server/app/services/file_storage.py#L36-124
# FileStorageService.__init__ and _init_gcs logic
```

- Document upload uses `FileStorageService` and `DocumentService`, so documents are already GCS-ready:
```server/app/services/document_service.py#L20-48
# DocumentService.upload_document uses FileStorageService.upload_file(...)
```

- Resume upload & parsing currently rely on legacy local behavior:
```server/app/services/candidate_service.py#L1-32
# CandidateService uses LegacyResumeStorageService()

server/app/services/candidate_service.py#L72-88
# This upload_and_parse_resume extracts text using a local path:
extracted = TextExtractor.extract_from_file(file_path)
```

- Inngest resume parsing workflow expects a local path:
```server/app/inngest/functions/resume_parsing.py#L64-92
resume_text = await ctx.step.run('extract-resume-text', lambda: _extract_resume_text(candidate.resume_file_path))
```

- Public onboarding routes parse based on `document.file_path` (local):
```server/app/routes/public_document_routes.py#L144-154
text = extract_text_from_file(document.file_path)
```

- `CandidateDocument` model supports `file_key` + `storage_backend`. Candidate model currently uses `resume_file_path` and `resume_file_url` for resume data.

---

## High-level Implementation Plan (Step-by-step)

### 1) Configuration & Secrets
- Use the `FileStorageService` configurable backend: set `STORAGE_BACKEND=gcs` in production.
- Provide the bucket & credentials:
  - `GCS_BUCKET_NAME`
  - `GCS_PROJECT_ID` (optional but recommended)
  - `GCS_CREDENTIALS_PATH` (path to JSON file) or `GCS_CREDENTIALS_JSON` (env var). NOTE: avoid storing JSON in code.
- Removal of any checked in credentials:
  - Remove `blacklight-bucket.json` from the repo and purge if necessary using history rewrite tools.
  - Add `blacklight-bucket.json` to `.gitignore`.

> Credentials approach: Provide env or secrets in CI/CD. Workload Identity is recommended for GKE/Cloud Run.

---

### 2) DB Schema Changes
- Add new columns to `candidates`:
  - `resume_file_key` (String(1000), nullable)
  - `resume_storage_backend` (String(20), default 'local' or 'gcs')
- Keep `resume_file_path` and `resume_file_url` for backward compatibility (optional).
- Update `Candidate` model accordingly:
  - `resume_file_key = db.Column(String(1000))`
  - `resume_storage_backend = db.Column(String(20), default='local')`

Rationale: `file_key` design is consistent with `CandidateDocument` (`file_key` + `storage_backend`). This makes the resume handling explicit and consistent.

Because you plan to clear everything and start fresh, we can apply schema and default values and then populate them on new uploads.

---

### 3) Code Changes — Implementation Tasks

A. `server/app/services/file_storage.py` (FileStorageService)
- Add helper function:
```python
def download_to_temp(self, file_key: str) -> Tuple[str, Optional[str]]:
    """
    Download a file (GCS or local) to a local temporary path for libraries that need file paths.
    Returns (temp_file_path, error|null)
    """
```
- Implementation notes:
  - For GCS: use `download_as_bytes()` on `Blob`, write bytes to `tempfile.NamedTemporaryFile(delete=False)` and return the path.
  - For local: `local_path / file_key` is already reachable; return the path and no error.
  - Ensure `tempfile` files are removed after use.

B. `server/app/services/candidate_service.py` (CandidateService)
- Replace `LegacyResumeStorageService` usage:
```python
# old
self.file_storage = LegacyResumeStorageService()

# new
self.file_storage = FileStorageService()
```
- Modify `upload_and_parse_resume` to:
  - Use `self.file_storage.upload_file(..., document_type='resume')`.
  - Populate `resume_file_key` and `resume_storage_backend` rather than relying on `resume_file_path`.
  - For parsing: If `resume_storage_backend == 'gcs'` or `resume_file_key` not a local path, call `file_storage.download_to_temp(...)` to obtain a local temp path for `TextExtractor`.
  - Ensure temp path cleanup after parsing.

C. `server/app/inngest/functions/resume_parsing.py`
- Replace usage of raw `candidate.resume_file_path` by logic:
  - If `Candidate.resume_storage_backend == 'gcs'` or candidate.resume_file_path is missing:
    - Use `FileStorageService.download_to_temp(candidate.resume_file_key)` to get a local path, then call `TextExtractor.extract_from_file(local_path)`.
  - Ensure the temp file is removed.

D. `server/app/routes/public_document_routes.py`
- After `DocumentService.upload_document(...)`, `document` object will have `file_key` and `storage_backend` fields:
  - Use `FileStorageService.download_to_temp(document.file_key)` and pass path into `TextExtractor.extract_from_file`.
  - Clean up temp file after parsing.

E. `server/app/services/document_service.py`
- `DocumentService` already uses `FileStorageService`. Ensure it sets `file_key` and `storage_backend` for `CandidateDocument` rows.

F. `server/app/routes/candidate_routes.py`:
- Where route sets `candidate.resume_file_path = upload_result['file_path']`, update to:
  - Set `resume_file_key = upload_result['file_key']` and `resume_storage_backend = upload_result['storage_backend']`.
  - Optionally set `resume_file_url` to a signed URL for convenience.

G. File & behavior consistency:
- Any code that used `resume_file_path` should now prefer `resume_file_key` + `resume_storage_backend` and fall back to `resume_file_path` for legacy records.

---

### 4) Clear Existing Local Files / DB (As you requested "start fresh")
If you are wiping local storage and data:
- Remove local uploads folder (do this after DB backups or confirmation):
  - `rm -rf server/uploads/*` (use carefully)
- Clear DB tables (if necessary) or use a fresh DB instance for new deployment.
- Ensure production DB cleanup is validated (backup first).

Because you plan to reset, we do NOT need a migration script for existing local files.

---

### 5) Tests & QA
- Unit tests:
  - For `FileStorageService`: upload, download, signed url generation, delete using mock/stub GCS client.
  - For `download_to_temp`, confirm correct temp file creation and cleanup.
- Integration tests:
  - Full upload -> parse -> candidate creation flow using GCS test bucket/credentials or emulator.
- Inngest workflows:
  - Test parse-resume with a remote `file_key` (download to temp + parse flow).
- Frontend verification:
  - For `GET /api/documents/:id/url` and candidate endpoints, ensure the UI fetches signed URLs and downloads correctly.

---

### 6) Deployment Plan & Rollout (Safe approach)
1. Add new schema (adding `resume_file_key` and `resume_storage_backend`) and update code paths to support both local and GCS behavior.
2. Deploy the updated code (staging) and test with `STORAGE_BACKEND=gcs`.
3. Ensure `FileStorageService._init_gcs` runs correctly with provided credentials.
4. Confirm resume upload and parsing works for GCS in staging (download to temp and parse).
5. After smoke tests and validation in staging, deploy to production and switch `STORAGE_BACKEND=gcs`.
6. Delete legacy local files only after confirming the entire system is stable.

---

### 7) Security & Best Practices
- Remove any committed credentials: `blacklight-bucket.json` must be removed from the repo and `server/.gitignore` updated.
- Use secret management (CI secrets, Cloud secret manager) or Workload Identity (GKE/Cloud run) in production.
- Ensure the GCS bucket is private: deny public object access and use signed URLs served by the application for direct downloads.
- Consider adding lifecycle policies to GCS to manage older objects and storage costs.

---

### 8) Monitoring & Logging
- Add metrics for:
  - Upload counts (per tenant),
  - Upload errors,
  - Signed URL generation,
  - Storage backend errors.
- Enable GCS access logging / audit logging for the bucket as needed.

---

### 9) Checklist for Implementation (Actionable)
- [ ] Add `resume_file_key` and `resume_storage_backend` to `models/candidate.py` + migration.
- [ ] Implement `FileStorageService.download_to_temp()` & tests.
- [ ] Replace `LegacyResumeStorageService` references in `CandidateService` with `FileStorageService`.
- [ ] Update `CandidateService.upload_and_parse_resume` to store `resume_file_key`.
- [ ] Update `parse-resume` workflow to download to local path (for `TextExtractor`).
- [ ] Update `public_document_routes.py` to use `download_to_temp` and support `document.file_key` parsing.
- [ ] Remove `blacklight-bucket.json` from repo and add `.gitignore` entry.
- [ ] Add or update staging & CI GCS secrets.
- [ ] Add tests for GCS flows and temp download.
- [ ] Clear local storage and DB in staging as a rehearsal, then in production (since you’ll start fresh).
- [ ] Deploy, set `STORAGE_BACKEND=gcs` and verify.

---

## Example Implementation Snippets

**Suggested download_to_temp helper (high level):**
```
# server/app/services/file_storage.py
def download_to_temp(self, file_key: str, suffix: Optional[str] = None) -> Tuple[str, Optional[str]]:
    import tempfile
    content, content_type, error = self.download_file(file_key)
    if error or not content:
        return None, error or "Failed to download content"
    suffix = suffix or "." + (file_key.split('.')[-1] if '.' in file_key else "bin")
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp_file.write(content)
    tmp_file.flush()
    tmp_file.close()
    return tmp_file.name, None
```

**CandidateService resume upload & parse change:**
```
# server/app/services/candidate_service.py
self.file_storage = FileStorageService()

# Upload
upload_result = self.file_storage.upload_file(file=file, tenant_id=tenant_id, document_type='resume', candidate_id=candidate_id)
# Save to DB:
candidate.resume_file_key = upload_result['file_key']
candidate.resume_storage_backend = upload_result['storage_backend']

# Parsing:
if candidate.resume_storage_backend == 'gcs' or not os.path.exists(candidate.resume_file_path):
    local_path, err = self.file_storage.download_to_temp(candidate.resume_file_key)
    if not local_path:
        # handle error
else:
    local_path = candidate.resume_file_path

parsed = TextExtractor.extract_from_file(local_path)
# cleanup if local_path is temp
```

**Parsing in Inngest:**
```
# server/app/inngest/functions/resume_parsing.py
if candidate.resume_storage_backend == 'gcs':
    path, err = FileStorageService().download_to_temp(candidate.resume_file_key)
    text = TextExtractor.extract_from_file(path)
    # cleanup temp
else:
    text = TextExtractor.extract_from_file(candidate.resume_file_path)
```

---

## Final Notes / Next Steps
- I'll prepare the exact code changes, migration files, tests, and optionally a small management script for clearing the old `server/uploads` directory and purging DB tables (if you want me to implement this next).
- Please confirm:
  - That you want me to start by adding the new DB fields & the `download_to_temp` method, then update resume upload/parse logic.
  - Where you'd prefer credentials to be configured for staging/production once decided (Workload Identity recommended).
- Once you confirm, I’ll proceed with an implementation PR for the following in sequence:
  1. Schema changes (migration).
  2. `FileStorageService.download_to_temp` & tests.
  3. CandidateService adjustments to use `FileStorageService`.
  4. Inngest parsing updates & tests.
  5. Public onboarding & other small updates.
  6. CI/CD update steps and README updates.

If you want, I can also create a short `server/manage.py` command to remove all existing files and optionally to drop candidate documents if needed as part of resetting the environment (since you plan to clear everything before GCS usage).

---

## Cloud Run + GCS: Production Best Practices & Streaming for Large Files

This section contains recommended code and architectural changes to make your application production-ready on Cloud Run using GCS for all storage and streaming-based transfers so the service does not OOM during large uploads/downloads.

### Decision: Remove Local Storage
You indicated we should remove local storage and rely exclusively on GCS for file storage. Our plan will adopt this and assume the following:
- `STORAGE_BACKEND` will be `gcs` in production (prefer default or env-driven behavior).
- We'll still support local backend in dev (e.g., `STORAGE_BACKEND=local`) for developer convenience.
- All code that previously relied on local file paths will be updated to use `file_key` + `storage_backend` semantics and will leverage `FileStorageService` (GCS) utilities for read/write/download.
- `LegacyResumeStorageService` is deprecated and removed once we verify all workflows use `FileStorageService`.

### IAM & Cloud Run Service Account
- Cloud Run won't use JSON service account files in production: use the Cloud Run service identity:
  - Identify the Cloud Run Service Account (found in Cloud Run > Service details > Security).
  - Grant it `Storage Object Admin` (or a narrower role as needed) in IAM to allow read/write/delete blob operations.
  - If you still need to generate signed URLs from Cloud Run, grant the `Service Account Token Creator` role as necessary on the service account (to sign tokens).

### Python Client Best Practices
- Always create the `storage.Client()` instance globally (module-level) so the client is reused across requests:
```python
import os
from google.cloud import storage

# Global Client - shared for Cloud Run instance life span
storage_client = storage.Client()
bucket_name = os.environ.get("GCS_BUCKET_NAME", "my-app-bucket")
bucket = storage_client.bucket(bucket_name)
```

### Streaming Uploads (avoid loading entire file into RAM)
- Streaming avoids large memory usage and these patterns work with Flask, FastAPI, etc.
- Using `blob.open('w', chunk_size=...)` writes in a streaming way:
```python
from flask import Flask, request, jsonify
from google.cloud import storage
import os

app = Flask(__name__)
client = storage.Client()
bucket = client.bucket(os.environ.get("GCS_BUCKET_NAME"))

@app.route('/api/documents/upload', methods=['POST'])
def upload_large_file():
    """
    Stream the request body directly to a GCS blob to avoid loading into memory.
    Use request.stream.read() (Wsgi) or async stream alternatives for async frameworks.
    """
    filename = request.form.get('filename') or request.args.get('filename')
    if not filename:
        return jsonify({"error": "filename required"}), 400

    # Build a safe file key for multi-tenant store, e.g. `tenants/{tenant_id}/documents/{filename}`
    file_key = f"tenants/{request.form.get('tenant_id')}/documents/{filename}"
    blob = bucket.blob(file_key)

    # Configure a suitable chunk_size for streaming (e.g. 1MB)
    chunk_size = 1024 * 1024

    # `blob.open("w")` returns a file-like object that directly streams to GCS
    with blob.open("w", content_type=request.headers.get('Content-Type'), chunk_size=chunk_size) as gcs_file:
        while True:
            chunk = request.stream.read(4096)
            if not chunk:
                break
            gcs_file.write(chunk)

    return jsonify({"status": "uploaded", "file_key": file_key}), 201
```

### Streaming Downloads
- Avoid streaming the whole blob into memory; instead stream to the response with a generator:
```python
@app.route('/api/documents/download')
def download_large_file():
    file_key = request.args.get('file_key')
    blob = bucket.blob(file_key)

    def stream_blob():
        with blob.open("rb") as gcs_file:
            while True:
                chunk = gcs_file.read(4096)
                if not chunk:
                    break
                yield chunk

    return app.response_class(stream_blob(), mimetype='application/octet-stream')
```

### Signed URLs (Frontend Direct Access) — Offload to GCS
- Generate signed URLs for client direct download/upload to avoid proxy costs:
```python
import datetime

def generate_secure_link(file_key, method="GET", expires_minutes=15):
    blob = bucket.blob(file_key)
    url = blob.generate_signed_url(
        version="v4",
        expiration=datetime.timedelta(minutes=expires_minutes),
        method=method,
    )
    return url
```
- For direct uploads from browser, use `method="PUT"` or a proper form-based signed URL.

### Handling Resume Parsing (Temp File)
- Parsing libraries (pdfplumber, PyMuPDF, python-docx) typically operate on a local file path; implement a helper to stream to a temp file:
```python
import tempfile
from app.services.file_storage import FileStorageService

file_service = FileStorageService()

def download_to_temp_for_parsing(file_key):
    content, content_type, error = file_service.download_file(file_key)
    if error:
        raise RuntimeError(error)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_key.split('.')[-1]}")
    tmp.write(content)
    tmp.flush()
    tmp.close()
    return tmp.name
```
- You may instead prefer streaming `blob.open('rb')` and writing to a temporary file in blocks to keep memory usage minimal if `download_file` returns bytes.

### Delete Local Storage: Implementation Details
If we remove local storage entirely (per your preference), steps to follow:
- Remove references to legacy local directories and `server/uploads` logic.
- Replace any leftover `file_path` usages with `file_key` + `storage_backend` semantics (Candidate/resume store only `file_key` for remote storage).
- Replace or remove `LegacyResumeStorageService` and standardize on `FileStorageService`.
- Update parsing workflow:
  - Always use `download_to_temp_for_parsing()` for library parsing needs (for both immediate and async parsing).
- Update model fields:
  - Ensure `Candidate` uses `resume_file_key`/`resume_storage_backend`.
  - Ensure `CandidateDocument` uses `file_key`+`storage_backend`.
- Adjust UI usage:
  - Where the frontend previously requested direct /api/documents/download, prefer `/api/documents/{id}/url` to fetch signed URLs. For large downloads use direct signed URL instead of proxying through Cloud Run.
- Cleanup steps:
  - Remove `uploads/` folder and ensure `.gitignore` no longer includes such a folder if it remains.
  - Remove code modules purely related to local storage support (`LegacyResumeStorageService` if we decide to deprecate it completely).

### Production / Dev Credentials Strategy
- Production (Cloud Run): use Workload Identity (recommended) so services acquire credentials automatically; no JSON key file is required.
- Development (local): use `GCS_CREDENTIALS_JSON` or `GCS_CREDENTIALS_PATH` env var or `gcloud auth application-default login` for local testing.
- Do not commit JSON keys to the repository and ensure any legacy JSON file is removed and rotated if needed.

### Small Additions (resilience)
- Use `blob.patch()` or `blob._properties` for metadata if necessary.
- Confirm the `Google Cloud Storage` library is installed in requirements: `google-cloud-storage>=2.0.0`.
- Optionally add auto-retry wrappers / idempotency key for retries with large uploads.

---

## Recommendations / Final Thoughts
- This approach (GCS-only, streaming, signed URLs & Workload Identity on Cloud Run) is aligned with Cloud Native best practices, especially for large file handling and security:
  - Streams avoid OOM issues on Cloud Run.
  - Signed URLs minimize application bandwidth and cost.
  - Workload Identity avoids secret distribution issues and improves security posture.
- Implementation priority:
  1. Replace local reads/writes in the backend using `FileStorageService` streaming APIs.
  2. Implement `FileStorageService.download_to_temp()` for parser compatibility.
  3. Remove or deprecate `LegacyResumeStorageService` after code verification.
  4. Switch `STORAGE_BACKEND` to `gcs` in production and modernize the DB fields as discussed.
  5. Configure roles/permissions for the Cloud Run service account and set up CI secrets for development / staging.
## Implementation Phases — Execution Plan

If you approve, we'll initiate the implementation in structured phases to ensure safe rollout and minimal disruption. Because you plan to clear all existing data and use GCS exclusively, we can proceed without an incremental migration strategy — but we'll still preserve backward-compatibility code paths for development until we're confident.

Phase 1 — Prepare & Configure
- Add `google-cloud-storage>=2.0.0` to `server/requirements.txt`.
- Add new DB fields to `candidates`: `resume_file_key` (String(1000)) and `resume_storage_backend` (String(20), default 'gcs'). Create an Alembic migration to add these fields.
- Update `.env.example` with `STORAGE_BACKEND=gcs`, `GCS_BUCKET_NAME`, and `GCS_PROJECT_ID`.
- Ensure Cloud Run: assign your Cloud Run service account `Storage Object Admin` (or narrower permissions as needed) — this enables read, write, delete to the bucket. If you want Cloud Run to sign URLs, also give `Service Account Token Creator`.

Phase 2 — Core Storage Abstraction & Streaming
- Implement `FileStorageService.download_to_temp()` helper using streaming to avoid memory pressure.
- Rework `FileStorageService.upload_file()` to handle streaming uploads to GCS (i.e., `blob.open()` or `resumable` methods), ensuring it does not call `.read()` on the entire file.
- Remove or deprecate the `LegacyResumeStorageService` and ensure `FileStorageService` is the single upstream for all file operations.

Phase 3 — Candidate & Document Flows
- Update `CandidateService` to use `FileStorageService` exclusively for resume upload and to populate `resume_file_key` + `resume_storage_backend`.
- Update `DocumentService` to continue using streaming `upload_file()` for document uploads and ensure `CandidateDocument` receives `file_key` and `storage_backend`.
- Update `public_document_routes` and other relevant routes to use `download_to_temp(file_key)` when server-side parsing is required.

Phase 4 — Parsing & Inngest Integration
- Update the Inngest resume parse workflow to use the `download_to_temp` helper and ensure all parsing libraries operate using temporary file paths (still streaming to a temporary local file).
- Ensure temporary files are closed and cleaned up after parsing.

Phase 5 — Signed URLs & Direct Client Uploads
- Add endpoints to issue signed upload and download URLs (e.g., `/api/documents/upload-url` for direct client uploads using signed PUT URLs).
- Retain a server-side fallback: a streaming route to upload files to GCS via backend in case the client cannot use signed upload.

Phase 6 — Tests, Staging & Smoke Tests
- Add tests:
  - Unit tests for streaming GCS code and `download_to_temp`.
  - Integration tests for upload & parse pipeline using GCS (test bucket or emulator).
- Validate a staging environment using `STORAGE_BACKEND=gcs`, verify signed URLs, streaming behavior, and parse workflows.

Phase 7 — Production Switch & Cleanup
- Deploy the updated code, point Cloud Run environment variables to the correct bucket.
- Confirm application uses GCS for uploads/uploads and that `resume_file_key` is populated for new uploads.
- After successful verification in production, remove local upload directories, deprecate `resume_file_path` references, and optionally remove `LegacyResumeStorageService`.
- Rotate any service account keys if the `blacklight-bucket.json` was used and removed previously; ensure it is not stored in repo and remove from history if it was ever in repo.

---

## Review Checklist (for each phase)
Use this checklist when reviewing code and during pre-merge checks.

Phase 1 — Config & IAM
- [ ] `google-cloud-storage` added to `requirements.txt`.
- [ ] Environment variables for GCS (`GCS_BUCKET_NAME`, `GCS_PROJECT_ID`) documented in `.env.example`.
- [ ] Cloud Run service account is assigned `Storage Object Admin` at least.
- [ ] If Cloud Run signs URLs, the service account has `Service Account Token Creator` privileges if necessary.

Phase 2 — FileStorageService & Streaming
- [ ] Ensure `storage.Client()` is instantiated globally in `FileStorageService`.
- [ ] Implement streaming upload (e.g., `blob.open('w')` with chunked writes) to avoid loading entire file into RAM.
- [ ] Implement `download_to_temp` helper using streaming writes to a temporary file.
- [ ] Unit tests for `upload_file` and `download_to_temp` are present and pass.

Phase 3 — Use `FileStorageService` everywhere
- [ ] All uploads flow through `FileStorageService` (no local-only fallback in prod).
- [ ] `CandidateService` uses `file_key` and `resume_file_key` fields properly.
- [ ] `LegacyResumeStorageService` references are removed, or at minimum, marked deprecated and unused in prod.
- [ ] All Document uploads use streaming.

Phase 4 — Parsing / Inngest
- [ ] `Inngest` parsing uses `download_to_temp` when parsing remote `file_key`.
- [ ] Parsers (PyMuPDF, pdfplumber, python-docx) work correctly when parsing files from temp files.
- [ ] All temp files are cleaned up after parsing.

Phase 5 — Signed URL / Direct Uploads
- [ ] `GET /api/documents/{id}/url` and `GET /api/documents/upload-url` generate signed URLs (PUT/GET) correctly.
- [ ] Direct client uploads to signed PUT URLs are validated (CORS, content-type, object ACLs if needed).
- [ ] For file uploads that still use server endpoint, streaming uploads work as expected.

Phase 6 — Testing & Staging
- [ ] Integration tests for uploads and parsing passing for large files (simulated).
- [ ] Upgrade staging to `STORAGE_BACKEND=gcs` and confirm behavior.
- [ ] Logging & monitoring: track upload errors, parse errors, memory/CPU anomalies in Cloud Run.

Phase 7 — Post-deploy Cleanup
- [ ] Remove `LegacyResumeStorageService` and old local directories if it's safe and verified.
- [ ] Remove any committed JSON credentials from repo and history (`blacklight-bucket.json`).
- [ ] Clean up old uploads (if needed) or migrate as per your workflow.

---

## Review & Final Questions
- Confirm that you want the plan implemented in this order (Phase 1 → 7).
- Confirm any specific preferences for:
  - Signed URL expiration: default 15 minutes (we used it in examples).
  - Whether you want direct client uploads via signed URLs (recommended) or still want server-proxied uploads in some cases.
  - The production IAM policy for minimal privileges if you prefer narrower roles than `Storage Object Admin`.
- If confirmed, I’ll proceed to implement Phase 1 (requirements + migration + minimal service changes) and then Phase 2 (streaming / `download_to_temp`), produce PRs for each phase, and attach tests and verification steps for each PR.

