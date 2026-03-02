# ================================================================
# Dockerfile — Voice-Vision Assistant for Blind
# ================================================================
# Two-stage build:
#   builder  — installs all Python dependencies into /install
#   runtime  — copies only the compiled packages; no build tools
#
# Build:  docker build -f deployments/docker/Dockerfile -t voice-vision-assistant .
# Run:    docker run -p 8000:8000 -p 8081:8081 --env-file .env voice-vision-assistant
# ================================================================

# ----------------------------------------------------------------
# Stage 1: builder
# Installs system build tools + Python packages into /install
# ----------------------------------------------------------------
FROM python:3.11-slim AS builder

# Install system build-time deps only
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy dependency manifests first (maximise layer cache)
COPY requirements.txt requirements-extras.txt ./

# Install into an isolated prefix so we can COPY it to runtime cleanly
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt \
    && pip install --no-cache-dir --prefix=/install -r requirements-extras.txt


# ----------------------------------------------------------------
# Stage 2: runtime
# Lean image — no build tools, no dev dependencies
# ----------------------------------------------------------------
FROM python:3.11-slim AS runtime

LABEL org.opencontainers.image.title="Voice & Vision Assistant for Blind" \
      org.opencontainers.image.description="Real-time accessibility assistant for blind users" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.licenses="Proprietary"

# Runtime system dependencies only (no *-dev packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libzbar0 \
    libgl1-mesa-glx \
    libglib2.0-0 \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root application user
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

# Copy compiled Python packages from builder (no pip, no build tools)
COPY --from=builder /install /usr/local

# Copy source code (clean architecture layout — no tests, no scripts)
COPY core/        ./core/
COPY application/ ./application/
COPY infrastructure/ ./infrastructure/
COPY shared/      ./shared/
COPY apps/        ./apps/
COPY configs/     ./configs/
COPY models/      ./models/
COPY data/        ./data/

# Runtime directories with correct ownership
RUN mkdir -p .runtime/logs .runtime/cache /app/data /app/qr_cache \
    && chown -R appuser:appuser /app

USER appuser

# Health check — lightweight HTTP probe on the API port
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -sf http://localhost:8000/health || exit 1

EXPOSE 8000 8081

# Default: run API server + realtime agent
CMD ["bash", "-c", \
    "uvicorn apps.api.server:app --host 0.0.0.0 --port 8000 & \
     python -m apps.realtime.entrypoint start"]
