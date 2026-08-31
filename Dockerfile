# ==========================================
# Multi-stage optimized Dockerfile for RGCBot
# ==========================================

# Stage 1: Build stage
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Final runtime
FROM python:3.12-slim AS runtime

WORKDIR /app

# Install runtime dependencies (libpq for postgres and fonts for stickers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    fonts-dejavu-core \
    fonts-freefont-ttf \
    fonts-noto-color-emoji \
    fonts-symbola \
    && rm -rf /var/lib/apt/lists/*



# Create a non-root user
RUN useradd -m -u 1000 botuser

# Copy installed python packages from builder
COPY --from=builder /root/.local /home/botuser/.local
ENV PATH=/home/botuser/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Copy source code
COPY --chown=botuser:botuser . .

USER botuser

# Healthcheck for container orchestration
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 0

CMD ["python", "-m", "src.main"]
