# syntax=docker/dockerfile:1

# ---- builder: compile/collect Python dependencies -------------------------
FROM python:3.12-slim AS builder

WORKDIR /app

# build-essential is only needed to build a few packages' native
# extensions; it lives in this stage and never reaches the runtime image.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# --prefix installs into an isolated tree we copy wholesale into the
# runtime stage, instead of shipping pip's cache or apt's build tools.
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- runtime: small, non-root, only what's needed to run --------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    WEB_CONCURRENCY=1

WORKDIR /app

# libgomp1 is a runtime dependency pulled in transitively by
# sentence-transformers/torch; curl is used by the HEALTHCHECK below.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local

RUN groupadd -r aicompany && useradd -r -g aicompany -d /app -s /usr/sbin/nologin aicompany

COPY --chown=aicompany:aicompany . .

# Created here (not relied on being present in the build context /
# .dockerignore excludes their contents) so the app has somewhere to
# write on first boot even before any volume is mounted.
RUN mkdir -p uploads logs qdrant_data database \
    && chown -R aicompany:aicompany uploads logs qdrant_data database

USER aicompany

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

# WEB_CONCURRENCY controls uvicorn worker count. Defaults to 1, which is
# safe with the zero-config embedded Qdrant store (see
# backend/rag/vectorstore.py -- embedded mode locks its storage directory
# to a single process). Raise it in docker-compose.yml/your orchestrator
# only once QDRANT_URL points at a real Qdrant server, since that's what
# makes multiple worker processes against the same data safe.
CMD ["sh", "-c", "uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --workers ${WEB_CONCURRENCY}"]