# =============================================================================
# Blacklight Backend - Flask API Server
# Optimized for VM deployment with Docker Compose
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

# Create directories for uploads, credentials and ensure correct permissions
RUN mkdir -p /app/storage/uploads /app/uploads /app/credentials && \
    chown -R blacklight:blacklight /app

# Switch to non-root user
USER blacklight

# Expose port 5000 for VM deployment
EXPOSE 5000

# Health check for Docker Compose
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT:-5000}/api/health || exit 1

# =============================================================================
# Gunicorn Configuration for VM Deployment
# =============================================================================
# - workers: 4 (2 * CPU cores + 1, adjust based on your VM)
# - threads: 4 (handle concurrent requests per worker)
# - worker-class: gthread (threaded workers for I/O bound tasks)
# - timeout: 120 (2 min timeout for long operations like resume parsing)
# - keep-alive: 5 (connection keep-alive)
# - max-requests: 1000 (restart workers to prevent memory leaks)
# - graceful-timeout: 30 (graceful shutdown time)
# =============================================================================
CMD exec gunicorn \
    --bind 0.0.0.0:${PORT:-5000} \
    --workers ${GUNICORN_WORKERS:-4} \
    --threads ${GUNICORN_THREADS:-4} \
    --worker-class gthread \
    --worker-tmp-dir /dev/shm \
    --timeout ${GUNICORN_TIMEOUT:-120} \
    --graceful-timeout 30 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --access-logfile - \
    --error-logfile - \
    --capture-output \
    --enable-stdio-inheritance \
    --log-level ${LOG_LEVEL:-info} \
    "wsgi:app"
