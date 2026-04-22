# syntax=docker/dockerfile:1
FROM python:3.12-alpine AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-alpine
RUN addgroup -S appgroup && adduser -S -u 1001 appuser -G appgroup
WORKDIR /app
COPY --from=builder /install /usr/local
COPY worker.py .
USER appuser
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c \
    "import time; t=float(open('/tmp/worker_heartbeat').read()); exit(0 if time.time()-t<60 else 1)" \
    || exit 1
CMD ["python", "worker.py"]
