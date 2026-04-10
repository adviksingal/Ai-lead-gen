# ─── Stage 1: Build frontend ─────────────────────────────────────────────────
FROM node:22-slim AS frontend-builder

WORKDIR /frontend

COPY frontend/package*.json ./
RUN npm ci --silent

COPY frontend/ ./
RUN npm run build

# ─── Stage 2: Build Python deps ──────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ─── Stage 3: Runtime ────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

LABEL maintainer="AI Lead Gen Agent"
LABEL description="AI-powered B2B lead generation — web dashboard + CLI + REST API"
LABEL version="1.0.0"

# Security: run as non-root
RUN useradd -m -u 1000 -s /bin/bash appuser

WORKDIR /app

# Copy Python site-packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source (excludes node_modules via .dockerignore)
COPY --chown=appuser:appuser . .

# Copy built frontend from frontend-builder
COPY --from=frontend-builder --chown=appuser:appuser /frontend/dist /app/frontend/dist

# Install the package entry points
RUN pip install --no-cache-dir -e . --no-deps

# Create writable data directories
RUN mkdir -p /app/data /app/exports /app/demo/output \
    && chown -R appuser:appuser /app

USER appuser

ENV DATABASE_URL=/app/data/leads.db
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

EXPOSE 3000

# Health check — polls /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:3000/health')" \
        || exit 1

# Default: run API + serve frontend from port 3000
CMD ["agent", "serve", "--host", "0.0.0.0", "--port", "3000"]
