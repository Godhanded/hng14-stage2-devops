# FIXES.md — Bug Report & Changelog

Every issue found in the starter repository, documented with file, line, problem, and fix.

---

## Fix 1 — `api/main.py:8` — Redis host hardcoded as `localhost`

**Problem:**  
```python
r = redis.Redis(host="localhost", port=6379)
```
`localhost` resolves to the container's own loopback interface. Inside Docker, the Redis service is reachable by its service name (`redis`), not `localhost`. The API would fail to connect to Redis on every request.

**Fix:**  
Read the host from the `REDIS_HOST` environment variable and default to `"redis"` (the Compose service name):
```python
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD)
```

---

## Fix 2 — `api/main.py:8` — Redis password from `.env` never used

**Problem:**  
The `.env` file sets `REDIS_PASSWORD=supersecretpassword123`, but the code never reads this variable or passes it to `redis.Redis()`. If Redis is configured with a password, all API requests would fail with authentication errors.

**Fix:**  
Added `REDIS_PASSWORD = os.getenv("REDIS_PASSWORD") or None` and passed it to `redis.Redis(password=REDIS_PASSWORD)`.

---

## Fix 3 — `api/main.py:21` — 404 response returned with HTTP 200 status

**Problem:**  
```python
if not status:
    return {"error": "not found"}   # HTTP 200 — wrong!
```
Returning a JSON error body with a `200 OK` status is incorrect REST semantics. Clients cannot detect failure by inspecting the HTTP status code.

**Fix:**  
Raise an `HTTPException` with the proper status code:
```python
from fastapi import HTTPException
...
if not status:
    raise HTTPException(status_code=404, detail="Job not found")
```

---

## Fix 4 — `api/main.py` — No `/health` endpoint

**Problem:**  
Docker `HEALTHCHECK` and `depends_on: condition: service_healthy` both require a health probe. No such endpoint existed, so any container orchestration relying on health checks would report the service as permanently unhealthy.

**Fix:**  
Added a `GET /health` endpoint that pings Redis and returns `{"status": "ok"}` (HTTP 200) or raises HTTP 503 if Redis is unreachable.

---

## Fix 5 — `worker/worker.py:6` — Redis host hardcoded as `localhost`

**Problem:**  
Same issue as Fix 1, but in the worker. `redis.Redis(host="localhost", ...)` fails inside a container where Redis is a separate service.

**Fix:**  
```python
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD)
```

---

## Fix 6 — `worker/worker.py:6` — Redis password not used

**Problem:**  
Same as Fix 2. The worker's `redis.Redis(...)` call had no `password` argument, causing authentication failures against a password-protected Redis.

**Fix:**  
Added `REDIS_PASSWORD = os.getenv("REDIS_PASSWORD") or None` and passed it to the Redis constructor.

---

## Fix 7 — `worker/worker.py:4` — `signal` imported but never used (no graceful shutdown)

**Problem:**  
```python
import signal   # imported…
# …but no signal handlers were ever registered.
```
The worker loop runs `while True:` forever. When Docker sends `SIGTERM` (e.g., on `docker compose down`), the process is killed immediately without finishing in-flight jobs, which can leave jobs stuck in `queued` state permanently.

**Fix:**  
Registered handlers for `SIGTERM` and `SIGINT` that set a `running = False` flag, allowing the loop to drain cleanly:
```python
running = True

def handle_shutdown(signum, frame):
    global running
    running = False

signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)

while running:
    ...
```

---

## Fix 8 — `worker/worker.py` — No health-check mechanism

**Problem:**  
Docker's `HEALTHCHECK` instruction needs a way to determine if the worker is alive and processing. A crashed-but-still-running worker (e.g., stuck in a deadlock) would be invisible to the orchestrator.

**Fix:**  
Added a `write_heartbeat()` function that writes the current Unix timestamp to `/tmp/worker_heartbeat` on every loop iteration. The `HEALTHCHECK` in the Dockerfile reads this file and fails if the timestamp is older than 60 seconds.

---

## Fix 9 — `frontend/app.js:6` — API URL hardcoded as `http://localhost:8000`

**Problem:**  
```javascript
const API_URL = "http://localhost:8000";
```
`localhost` inside the frontend container refers to the frontend container itself, not the API service. Every call to `/submit` and `/status/:id` would time out or connect-refuse.

**Fix:**  
Read from the environment:
```javascript
const API_URL = process.env.API_URL || 'http://api:8000';
```
The Compose file injects `API_URL=http://api:8000`.

---

## Fix 10 — `frontend/app.js` — No `/health` endpoint

**Problem:**  
No health probe existed for the frontend, making Docker `HEALTHCHECK` and `depends_on: condition: service_healthy` impossible.

**Fix:**  
Added:
```javascript
app.get('/health', (req, res) => {
  res.json({ status: 'ok' });
});
```

---

## Fix 11 — `api/.env` — Real credentials committed to the repository

**Problem:**  
```
REDIS_PASSWORD=supersecretpassword123
APP_ENV=production
```
A file containing real secrets was tracked in git. Anyone who clones the repository has access to these credentials. This also violates the task rules ("`.env` must never appear in your repository or git history").

**Fix:**  
- Added `.env` and `.env.*` (excluding `.env.example`) to `.gitignore`.
- Removed `api/.env` from git tracking (`git rm --cached api/.env`).
- Created `.env.example` with placeholder values to document required variables.

---

## Fix 12 — `api/requirements.txt` — No version pinning

**Problem:**  
```
fastapi
uvicorn
redis
```
Unpinned dependencies mean the installed versions can change between builds, breaking reproducibility and potentially introducing incompatibilities or security regressions without any code change.

**Fix:**  
Pinned all production dependencies to known-good versions:
```
fastapi==0.111.0
uvicorn==0.30.1
redis==5.0.4
httpx==0.27.0
```

---

## Fix 13 — `worker/requirements.txt` — No version pinning

**Problem:**  
Same issue as Fix 12. `redis` alone, with no version, allows silent upgrades.

**Fix:**  
```
redis==5.0.4
```

---

## Summary table

| # | File | Line | Issue | Fix |
|---|------|------|-------|-----|
| 1 | `api/main.py` | 8 | `localhost` hardcoded — fails in Docker | Env var `REDIS_HOST` defaulting to `"redis"` |
| 2 | `api/main.py` | 8 | Redis password ignored | `REDIS_PASSWORD` env var passed to `redis.Redis` |
| 3 | `api/main.py` | 21 | 404 body returned as HTTP 200 | `raise HTTPException(status_code=404, ...)` |
| 4 | `api/main.py` | — | No `/health` endpoint | Added `GET /health` with Redis ping |
| 5 | `worker/worker.py` | 6 | `localhost` hardcoded — fails in Docker | Env var `REDIS_HOST` defaulting to `"redis"` |
| 6 | `worker/worker.py` | 6 | Redis password ignored | `REDIS_PASSWORD` env var passed to `redis.Redis` |
| 7 | `worker/worker.py` | 4 | `signal` imported but never used | Registered `SIGTERM`/`SIGINT` handlers for graceful shutdown |
| 8 | `worker/worker.py` | — | No health-check mechanism | Heartbeat file written each loop iteration |
| 9 | `frontend/app.js` | 6 | `localhost:8000` hardcoded — fails in Docker | `process.env.API_URL` with `http://api:8000` default |
| 10 | `frontend/app.js` | — | No `/health` endpoint | Added `GET /health` |
| 11 | `api/.env` | — | Real secrets committed to git | Removed from tracking; added to `.gitignore` |
| 12 | `api/requirements.txt` | — | No version pinning | All deps pinned to specific versions |
| 13 | `worker/requirements.txt` | — | No version pinning | `redis==5.0.4` |
