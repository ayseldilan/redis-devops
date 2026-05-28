"""
Render job intake service.

Tiny mock of a piece of internal tooling: clients POST a vehicle
configuration and we hand back a job ID that they can poll for status.
The actual rendering happens elsewhere; this service only tracks the
job lifecycle in Redis.
"""

import logging
import os
import uuid
from typing import Optional

import redis
from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel, Field

logger = logging.getLogger("render_intake")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD") or None
JOB_TTL_SECONDS = int(os.getenv("JOB_TTL_SECONDS", "3600"))

app = FastAPI(title="Render Job Intake", version="0.1.0")

# Module-level client. socket_connect_timeout keeps the healthcheck
# snappy when Redis is unreachable instead of hanging the worker.
r = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
)


class JobRequest(BaseModel):
    vehicle_id: str = Field(..., min_length=1, max_length=64)
    paint_code: str = Field(..., min_length=1, max_length=32)
    angle_degrees: int = Field(0, ge=0, le=359)


class JobResponse(BaseModel):
    job_id: str
    status: str
    vehicle_id: str
    paint_code: str
    angle_degrees: int


def _job_key(job_id: str) -> str:
    return f"job:{job_id}"


@app.get("/healthz")
def healthz(response: Response) -> dict:
    """
    Liveness + readiness in one. Returns 503 if Redis is unreachable
    so an orchestrator can route traffic away.
    """
    try:
        r.ping()
    except redis.RedisError as exc:
        logger.warning("Redis ping failed: %s", exc)
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "degraded", "redis": "unreachable"}
    return {"status": "ok", "redis": "ok"}


@app.post("/jobs", status_code=status.HTTP_201_CREATED, response_model=JobResponse)
def create_job(req: JobRequest) -> JobResponse:
    job_id = uuid.uuid4().hex
    payload = {
        "job_id": job_id,
        "status": "queued",
        "vehicle_id": req.vehicle_id,
        "paint_code": req.paint_code,
        "angle_degrees": str(req.angle_degrees),
    }
    try:
        r.hset(_job_key(job_id), mapping=payload)
        r.expire(_job_key(job_id), JOB_TTL_SECONDS)
    except redis.RedisError as exc:
        logger.error("Failed to persist job %s: %s", job_id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="storage unavailable",
        )
    return JobResponse(
        job_id=job_id,
        status="queued",
        vehicle_id=req.vehicle_id,
        paint_code=req.paint_code,
        angle_degrees=req.angle_degrees,
    )


@app.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str) -> JobResponse:
    try:
        data = r.hgetall(_job_key(job_id))
    except redis.RedisError as exc:
        logger.error("Failed to read job %s: %s", job_id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="storage unavailable",
        )
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
    return JobResponse(
        job_id=data["job_id"],
        status=data["status"],
        vehicle_id=data["vehicle_id"],
        paint_code=data["paint_code"],
        angle_degrees=int(data["angle_degrees"]),
    )
