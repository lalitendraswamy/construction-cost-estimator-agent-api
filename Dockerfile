# syntax=docker/dockerfile:1.7
# ---------- builder: resolve and build wheels ----------
FROM python:3.12-slim AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip wheel --wheel-dir /wheels .

# ---------- runtime: small, non-root ----------
FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONUTF8=1 \
    APP_ENV=production LOG_JSON=true PORT=8000
RUN useradd --create-home --uid 10001 app
WORKDIR /app
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels
COPY data ./data
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import os,urllib.request,sys; sys.exit(0 if urllib.request.urlopen(f'http://localhost:{os.environ[\"PORT\"]}/health/live').status==200 else 1)"
# PORT is injected by the platform (Render, Railway, Cloud Run); defaults to 8000 locally.
# --forwarded-allow-ips: trust the platform proxy's X-Forwarded-For so per-IP rate limiting
# sees the real client IP, not the load balancer's.
CMD ["sh", "-c", "exec uvicorn estimator_agent.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
