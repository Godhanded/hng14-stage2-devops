# syntax=docker/dockerfile:1
# Stage 1: install dependencies
FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: lean runtime image
FROM python:3.12-slim
RUN useradd -r -u 1001 -g root appuser
WORKDIR /app
COPY --from=builder /install /usr/local
COPY worker.py .
USER appuser
# Health check: the worker writes a heartbeat timestamp to /tmp/worker_heartbeat
# every loop iteration. We fail if the file is older than 60 seconds.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c \
    "import time; t=float(open('/tmp/worker_heartbeat').read()); exit(0 if time.time()-t<60 else 1)" \
    || exit 1
CMD ["python", "worker.py"]
