# =============================================================================
# Core HIS — Multi-stage production Dockerfile
# Base: python:3.11-slim | Principle of least privilege (non-root runtime)
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1 — Builder: compile wheels with build-time dependencies only
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        libffi-dev \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip wheel --wheel-dir /wheels -r requirements.txt


# -----------------------------------------------------------------------------
# Stage 2 — Runtime: minimal image, non-root user, production entrypoint
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_HOME=/app \
    APP_USER=hisapp \
    APP_UID=1001 \
    APP_GID=1001 \
    PYTHONPATH=/app

WORKDIR ${APP_HOME}

# Runtime OS libraries (PostgreSQL client, WeasyPrint/Pango/Cairo stack)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq5 \
        libcairo2 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf-2.0-0 \
        libffi8 \
        shared-mime-info \
        fontconfig \
        fonts-dejavu-core \
        curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid ${APP_GID} ${APP_USER} \
    && useradd --uid ${APP_UID} --gid ${APP_GID} \
        --home-dir ${APP_HOME} --shell /usr/sbin/nologin \
        --no-log-init ${APP_USER}

# Install Python dependencies from pre-built wheels (no compiler in runtime)
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* \
    && rm -rf /wheels

# Application source — owned by non-root user
COPY --chown=${APP_USER}:${APP_USER} . .

USER ${APP_USER}

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -f http://127.0.0.1:8000/health || exit 1

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--proxy-headers", "--forwarded-allow-ips", "*"]
