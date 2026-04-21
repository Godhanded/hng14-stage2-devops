# HNG14 Stage 2 — Job Processor (Containerised)

A job-processing system made up of four services:

| Service | Description | Port |
|---------|-------------|------|
| `frontend` | Node.js / Express — submit & track jobs | 3000 (host) |
| `api` | Python / FastAPI — create jobs, serve status | internal |
| `worker` | Python — picks up and processes jobs | internal |
| `redis` | Queue & job-state store | internal only |

---

## Prerequisites

| Tool | Minimum version |
|------|----------------|
| Docker Engine | 24.x |
| Docker Compose (plugin) | 2.x (`docker compose`) |
| Git | any |

No cloud accounts are required. Everything runs locally.

---

## Quick start (clean machine)

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/hng14-stage2-devops.git
cd hng14-stage2-devops
```

### 2. Create your `.env` file

```bash
cp .env.example .env
```

Edit `.env` and set a real password for Redis (any string works locally):

```
REDIS_PASSWORD=changeme
FRONTEND_PORT=3000
```

### 3. Build and start the stack

```bash
docker compose up -d --build
```

This builds all three service images and starts them in the correct order:

```
redis → api → worker
redis → api → frontend
```

Each service starts only **after its dependency has passed its health check** — not just started.

### 4. Verify a successful startup

```bash
docker compose ps
```

Expected output (all services `healthy`):

```
NAME         IMAGE          STATUS                   PORTS
redis        redis:7.2-...  Up X seconds (healthy)
api          devops-api     Up X seconds (healthy)   
worker       devops-worker  Up X seconds (healthy)
frontend     devops-front   Up X seconds (healthy)   0.0.0.0:3000->3000/tcp
```

### 5. Open the dashboard

Navigate to **http://localhost:3000** in your browser.

- Click **Submit New Job** — you will see a job ID appear.
- The status will update from `queued` → `completed` in ~2 seconds.

---

## Useful commands

```bash
# View logs for all services
docker compose logs -f

# View logs for one service
docker compose logs -f api

# Check health status
docker compose ps

# Stop and remove containers (keeps volumes)
docker compose down

# Stop and remove containers + volumes
docker compose down -v

# Rebuild a single service after code change
docker compose up -d --build api
```

---

## Running unit tests locally

```bash
cd api
pip install -r requirements.txt -r requirements-test.txt
python -m pytest tests/ -v --cov=. --cov-report=term-missing
```

---

## CI/CD pipeline

The GitHub Actions workflow (`.github/workflows/ci.yml`) runs on every push and enforces this strict order:

```
lint → test → build → security-scan → integration-test → deploy
```

| Stage | What it does |
|-------|-------------|
| **lint** | flake8 (Python), eslint (JS), hadolint (Dockerfiles) |
| **test** | pytest with Redis mocked; uploads HTML coverage report as artifact |
| **build** | Builds all three images, pushes to local registry + GHCR; uploads tarballs as artifacts |
| **security-scan** | Trivy scans all images; fails on any CRITICAL CVE; uploads SARIF to GitHub Security |
| **integration-test** | Brings full stack up in the runner; submits a job; polls until `completed`; tears down |
| **deploy** | *(main branch only)* SSH rolling update — new container must pass health check before old is stopped |

A failure in any stage prevents all subsequent stages from running.

### Required GitHub secrets for deploy

Set these in **Settings → Secrets and variables → Actions**:

| Secret | Value |
|--------|-------|
| `DEPLOY_HOST` | IP or hostname of your server |
| `DEPLOY_USER` | SSH username on the server |
| `DEPLOY_SSH_KEY` | Private SSH key (the server must have the public key in `~/.ssh/authorized_keys`) |
| `REDIS_PASSWORD` | Redis password used on the server |

---

## Environment variables reference

| Variable | Used by | Description | Default |
|----------|---------|-------------|---------|
| `REDIS_PASSWORD` | redis, api, worker | Password for Redis auth | *(required)* |
| `REDIS_HOST` | api, worker | Redis hostname inside Docker network | `redis` |
| `REDIS_PORT` | api, worker | Redis port | `6379` |
| `API_URL` | frontend | Full URL of the API service | `http://api:8000` |
| `FRONTEND_PORT` | compose | Host port to expose the frontend on | `3000` |

---

## Architecture

```
Browser
  │
  ▼
frontend :3000 ──POST /submit──▶ api :8000 ──LPUSH "job"──▶ redis
  │                                 │                           │
  └──GET /status/:id────────────────┘                     BRPOP "job"
                                                               │
                                                           worker
                                                     (sleeps 2s, sets status=completed)
```

All services run on the `app-network` Docker bridge. Redis is **not** exposed on the host.
