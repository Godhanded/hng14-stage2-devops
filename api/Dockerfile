# syntax=docker/dockerfile:1
# Stage 1: install dependencies into an isolated prefix so they can be
# copied without bringing build tools into the final image.
FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: lean runtime image
FROM python:3.12-slim
RUN useradd -r -u 1001 -g root appuser
WORKDIR /app
COPY --from=builder /install /usr/local
COPY main.py .
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c \
    "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" \
    || exit 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
