# ================================================================
# Dockerfile — Voice-Vision Assistant for Blind
# ================================================================
# Multi-stage build: system deps + Python packages
#
# Build:  docker build -t voice-vision-assistant .
# Run:    docker run -p 8000:8000 -p 8081:8081 --env-file .env voice-vision-assistant
# ================================================================

FROM python:3.11-slim AS base

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libtesseract-dev \
    libzbar0 \
    libgl1-mesa-glx \
    libglib2.0-0 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Create non-root application user
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

# Python dependencies (cached layer)
COPY requirements.txt requirements-extras.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -r requirements-extras.txt

# Copy source
COPY . .

RUN mkdir -p /app/data /app/.runtime/logs /app/.runtime/cache /app/qr_cache \
    && chown -R appuser:appuser /app/data /app/.runtime /app/qr_cache
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import httpx; r=httpx.get('http://localhost:8000/health'); assert r.status_code==200" || exit 1

EXPOSE 8000 8081

# Default: run API server + agent
CMD ["bash", "-c", "uvicorn apps.api.server:app --host 0.0.0.0 --port 8000 & python -m apps.realtime.entrypoint start"]
