# =============================================================================
# Blacklight Backend - Flask API Server
# Optimized for Google Cloud Run deployment with Auto-Scaling
# =============================================================================

FROM python:3.11-slim AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download spaCy model
RUN python -m spacy download en_core_web_sm

# =============================================================================
# Production stage
# =============================================================================
FROM python:3.11-slim AS production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpoppler-cpp-dev \
    poppler-utils \
    libmagic1 \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r blacklight && useradd -r -g blacklight blacklight

WORKDIR /app

# Copy installed packages from builder (site-packages includes spaCy model)
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=blacklight:blacklight . .

# Create directories for uploads and ensure correct permissions
RUN mkdir -p /app/storage/uploads /app/uploads && \
    chown -R blacklight:blacklight /app

# Switch to non-root user
USER blacklight

# Expose port (Cloud Run uses PORT env var, default 8080)
EXPOSE 8080

# Health check (disabled for Cloud Run - it has its own)
# HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
#     CMD curl -f http://localhost:${PORT:-8080}/api/health || exit 1

# =============================================================================
# Gunicorn Configuration for Cloud Run Auto-Scaling
# =============================================================================
# - workers: 2 (Cloud Run recommends 1-4 for 1 CPU)
# - threads: 8 (handle concurrent requests per worker)
# - worker-class: gthread (threaded workers for I/O bound tasks)
# - timeout: 0 (Cloud Run handles timeouts, disable Gunicorn's)
# - keep-alive: 5 (Cloud Run load balancer keeps connections)
# - max-requests: 1000 (restart workers to prevent memory leaks)
# =============================================================================
CMD exec gunicorn \
    --bind :${PORT:-8080} \
    --workers 2 \
    --threads 8 \
    --worker-class gthread \
    --worker-tmp-dir /dev/shm \
    --timeout 0 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --access-logfile - \
    --error-logfile - \
    --capture-output \
    --enable-stdio-inheritance \
    --log-level debug \
    "wsgi:app"
