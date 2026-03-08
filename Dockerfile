# syntax=docker/dockerfile:1
# LexNorm - Production Dockerfile
# Uses uv for fast dependency installation (see: https://docs.astral.sh/uv/guides/integration/docker/)

# ---- Builder stage ----
    FROM python:3.13-slim-bookworm AS builder

    # Install build deps (paddlepaddle wheels may need compilation)
    RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
        && rm -rf /var/lib/apt/lists/*
    
    COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
    
    WORKDIR /src
    
    ENV UV_LINK_MODE=copy
    ENV UV_NO_DEV=1
    
    # Install dependencies first (better layer caching)
    RUN --mount=type=cache,target=/root/.cache/uv \
        --mount=type=bind,source=uv.lock,target=uv.lock \
        --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
        uv sync --locked --no-install-project --no-editable
    
    # Copy application code
    COPY . /src
    
    RUN --mount=type=cache,target=/root/.cache/uv \
        uv sync --locked --no-editable
    
    # ---- Runtime stage ----
    FROM python:3.13-slim-bookworm AS runtime
    
    # PaddleOCR / OpenCV runtime libraries
    RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1-mesa-glx \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
        libgomp1 \
        && rm -rf /var/lib/apt/lists/*
    
    # Create non-root user for security
    RUN groupadd --gid 1000 appgroup \
        && useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser
    
    WORKDIR /src
    
    # Copy virtual environment and app from builder
    COPY --from=builder --chown=appuser:appgroup /src/.venv /src/.venv
    COPY --from=builder --chown=appuser:appgroup /src/src /src/src
    COPY --from=builder --chown=appuser:appgroup /src/alembic.ini /src/alembic.ini
    COPY --from=builder --chown=appuser:appgroup /src/alembic /src/alembic
    COPY --from=builder --chown=appuser:appgroup /src/scripts /src/scripts
    
    ENV PATH="/src/.venv/bin:$PATH"
    ENV PYTHONUNBUFFERED=1
    
    USER appuser
    
    EXPOSE 8000
    
    CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]