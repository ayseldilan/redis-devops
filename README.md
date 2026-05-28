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
