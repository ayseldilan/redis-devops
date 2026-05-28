"""
Tests for the render intake service.

Some tests need a real Redis (marked `integration`). They will be
skipped automatically if Redis is not reachable at REDIS_HOST:REDIS_PORT.
The CI pipeline you set up should make sure those tests actually run
somewhere, not silently skip.
"""

from unittest.mock import patch

import pytest
import redis
from fastapi.testclient import TestClient

from app.main import app, r as redis_client


client = TestClient(app)


def _redis_available() -> bool:
    try:
        redis_client.ping()
        return True
    except redis.RedisError:
        return False


needs_redis = pytest.mark.skipif(
    not _redis_available(),
    reason="Redis is not reachable \u2014 integration tests skipped.",
)


# ---------- unit-ish tests (no Redis required) ----------

def test_healthz_returns_503_when_redis_down():
    with patch.object(redis_client, "ping", side_effect=redis.ConnectionError("nope")):
        resp = client.get("/healthz")
    assert resp.status_code == 503
    assert resp.json()["redis"] == "unreachable"


def test_create_job_validation_rejects_empty_vehicle_id():
    resp = client.post(
        "/jobs",
        json={"vehicle_id": "", "paint_code": "RED01", "angle_degrees": 0},
    )
    assert resp.status_code == 422


def test_create_job_validation_rejects_bad_angle():
    resp = client.post(
        "/jobs",
        json={"vehicle_id": "v-1", "paint_code": "RED01", "angle_degrees": 999},
    )
    assert resp.status_code == 422


# ---------- integration tests (need Redis) ----------

@needs_redis
def test_healthz_ok_when_redis_up():
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "redis": "ok"}


@needs_redis
def test_create_and_fetch_job_roundtrip():
    create = client.post(
        "/jobs",
        json={"vehicle_id": "vehicle-42", "paint_code": "BLU09", "angle_degrees": 45},
    )
    assert create.status_code == 201
    job_id = create.json()["job_id"]
    assert len(job_id) == 32

    fetched = client.get(f"/jobs/{job_id}")
    assert fetched.status_code == 200
    body = fetched.json()
    assert body["vehicle_id"] == "vehicle-42"
    assert body["paint_code"] == "BLU09"
    assert body["angle_degrees"] == 45
    assert body["status"] == "queued"


@needs_redis
def test_unknown_job_returns_404():
    resp = client.get("/jobs/does-not-exist")
    assert resp.status_code == 404
