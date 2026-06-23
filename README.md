# Render Job Intake

A small HTTP service that accepts render-job requests and tracks their state in Redis.

This README is intentionally sparse — **filling it in is part of the take-home task.**
See the brief you were sent for full details. At a minimum you should add sections for:

- How to run it (one command, ideally)
- Architecture (a small diagram)
- Decisions you made and why
- What you would do with more time

## Endpoints

| Method | Path             | Description                          |
|--------|------------------|--------------------------------------|
| GET    | `/healthz`       | Health check, 503 if Redis is down   |
| POST   | `/jobs`          | Create a render job                  |
| GET    | `/jobs/{job_id}` | Fetch a job by ID                    |

Example:

```bash
curl -X POST http://localhost:8000/jobs \
  -H 'Content-Type: application/json' \
  -d '{"vehicle_id":"v-42","paint_code":"BLU09","angle_degrees":45}'
```

## Configuration

| Env var          | Default     | Notes                                  |
|------------------|-------------|----------------------------------------|
| `REDIS_HOST`     | `localhost` |                                        |
| `REDIS_PORT`     | `6379`      |                                        |
| `REDIS_PASSWORD` | unset       |                                        |
| `JOB_TTL_SECONDS`| `3600`      | TTL on stored jobs                     |
| `LOG_LEVEL`      | `INFO`      |                                        |

## Running the tests

```bash
pip install -r requirements.txt
pytest
```

Some tests require a reachable Redis and will be skipped otherwise.


## How to Run

```bash
docker compose up --build

Then visit: http://localhost:8000/healthz 

'
## How to Stop

docker compose down

## Architecture 

┌─────────┐     HTTP      ┌─────────────┐     Redis protocol     ┌─────────┐
│  User   │ ────────────► │   FastAPI   │ ─────────────────────► │  Redis  │
│         │               │   (API)     │                        │         │
│         │ ◄──────────── │   Container │ ◄───────────────────── │Container│
└─────────┘   JSON        └─────────────┘                        └─────────┘

Flow summary:

The user sends HTTP requests to the FastAPI container.

The API stores and retrieves job state from Redis.

Docker Compose provides a shared network so the API can reach Redis via its service name.


## Decisions: 
1. Base image: python:3.12-slim -Smaller than full image, still has everything needed.
2. Non-root user - Security best practice. If the container is compromised, the attacker doesn't have root. 
3. Healthcheck strategy - Redis healthcheck uses redis-cli ping (most reliable). API healthcheck reuses the existing /healthz endpoint rather than adding a separate TCP check. 
4. Docker Compose depends_on with condition: service_healthy - Ensures API only starts after Redis is actually accepting connections, not just 'started.'
5. Commit SHA as image tag in CI - Makes images traceable to exact code. "Latest" is an anti-pattern in production. 

## What I Would Do With More Time
Add a multi-stage build to shrink the Docker image significantly
Push the Docker image to a container registry (GHCR push was attempted but needs package permissions setup)
Add Kubernetes manifests for local deployment with kind/minikube
Add Prometheus metrics endpoint and Grafana dashboard
Add Nginx reverse proxy with TLS termination

Running the tests 
pip install -r requirements.txt
pytest

