"""Unit tests for the FastAPI job-processing API.

Redis is mocked at import time so no real Redis connection is required.
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# Patch redis.Redis *before* main is imported so the module-level
# `r = redis.Redis(...)` receives the mock instance instead of trying
# to open a real connection.
_mock_redis = MagicMock()
with patch("redis.Redis", return_value=_mock_redis):
    from main import app  # noqa: E402

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_redis_mock():
    """Reset all mock state between tests."""
    _mock_redis.reset_mock()
    _mock_redis.ping.side_effect = None
    _mock_redis.hget.side_effect = None
    yield


# ---------------------------------------------------------------------------
# POST /jobs
# ---------------------------------------------------------------------------

def test_create_job_returns_job_id():
    """A successful POST /jobs must return a UUID job_id."""
    _mock_redis.lpush.return_value = 1
    _mock_redis.hset.return_value = 1

    response = client.post("/jobs")

    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    # UUIDs are 36 characters: 8-4-4-4-12
    assert len(data["job_id"]) == 36


def test_create_job_pushes_to_redis():
    """POST /jobs must enqueue the job ID and set its status to 'queued'."""
    _mock_redis.lpush.return_value = 1
    _mock_redis.hset.return_value = 1

    response = client.post("/jobs")
    job_id = response.json()["job_id"]

    _mock_redis.lpush.assert_called_once_with("job", job_id)
    _mock_redis.hset.assert_called_once_with(f"job:{job_id}", "status", "queued")


# ---------------------------------------------------------------------------
# GET /jobs/{job_id}
# ---------------------------------------------------------------------------

def test_get_job_returns_status_when_found():
    """GET /jobs/{id} must return the job ID and decoded status."""
    _mock_redis.hget.return_value = b"queued"

    response = client.get("/jobs/test-job-id")

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == "test-job-id"
    assert data["status"] == "queued"


def test_get_job_returns_404_when_not_found():
    """GET /jobs/{id} must return HTTP 404 when the job does not exist."""
    _mock_redis.hget.return_value = None

    response = client.get("/jobs/nonexistent-id")

    assert response.status_code == 404


def test_get_completed_job_status():
    """GET /jobs/{id} must correctly decode a 'completed' status."""
    _mock_redis.hget.return_value = b"completed"

    response = client.get("/jobs/some-job")

    assert response.status_code == 200
    assert response.json()["status"] == "completed"


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

def test_health_returns_ok_when_redis_reachable():
    """GET /health must return 200 when Redis ping succeeds."""
    _mock_redis.ping.return_value = True

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_returns_503_when_redis_down():
    """GET /health must return 503 when Redis is unreachable."""
    _mock_redis.ping.side_effect = Exception("connection refused")

    response = client.get("/health")

    assert response.status_code == 503
