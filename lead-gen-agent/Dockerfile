# ─── Stage 1: Build ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ─── Stage 2: Runtime ────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

LABEL maintainer="AI Lead Gen Agent"
LABEL description="AI-powered B2B lead generation — CLI + REST API"
LABEL version="1.0.0"

# Security: run as non-root
RUN useradd -m -u 1000 -s /bin/bash appuser

WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source
COPY --chown=appuser:appuser . .

# Install the package itself (entry points only, deps already installed)
RUN pip install --no-cache-dir -e . --no-deps

# Create writable data directories
RUN mkdir -p /app/data /app/exports /app/demo/output \
    && chown -R appuser:appuser /app

USER appuser

# Use /app/data for the SQLite database
ENV DATABASE_URL=/app/data/leads.db
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

EXPOSE 3000

# Health check — polls /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:3000/health')" \
        || exit 1

# Default: run API server. Override with docker run ... agent <command>
CMD ["agent", "serve", "--host", "0.0.0.0", "--port", "3000"]
