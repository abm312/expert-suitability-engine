# Expert Suitability Engine — Job Architecture for Long-Running Analysis

Production-ready, minimal design for 5–10 minute search/analysis jobs. Optimized for simplicity, demos, and low ops overhead.

---

## 1. Recommended Architecture

| Component | Responsibility | Where it runs |
|-----------|----------------|---------------|
| **Web API** (FastAPI) | Enqueue jobs, serve job status/results, serve read-only endpoints (creators, metrics, filters). Does **not** run `search_creators`. | Vercel serverless (short requests only) or a single long-lived app (Railway, Render, Fly). |
| **Background worker** | Single process: poll Postgres for pending jobs, run `CreatorService.search_creators`, write progress and results back to DB. | One service: Fly.io, Railway, or a small VM. |
| **Postgres** (Supabase or equivalent) | Source of truth: jobs table, progress/results, plus existing `creators`, `videos`, etc. | Existing Supabase/Postgres. |
| **Frontend** (Next.js) | Submit search → get `job_id` → poll `GET /jobs/{job_id}` until completed/failed → show results or error. | Vercel (unchanged). |

**Separation:** The web layer only creates and reads job records. The worker is the only process that executes `search_creators` and updates job state. No message queue; Postgres is the queue.

---

## 2. Job Lifecycle

Four states; transitions are linear.

```
pending → running → completed
                 → failed
```

- **pending**: Row created by API; worker has not claimed it.
- **running**: Worker has claimed the job and is executing `search_creators`.
- **completed**: Worker finished; `result` (and optionally `result_summary`) stored.
- **failed**: Worker caught an exception; `error_message` stored.

Only the worker transitions `pending → running` and `running → completed | failed`. The API never sets `running` or writes results.

---

## 3. Web API: Enqueue Jobs

**New/updated endpoints:**

- **`POST /api/v1/search`** (enqueue only)  
  - Body: current `SearchRequest` (topic_query, topic_keywords, metrics, filters, limit, offset).  
  - Action: Insert a row into `jobs` with `type='search'`, `payload=<serialized request>`, `status='pending'`.  
  - Response: `{ "job_id": "<uuid>" }` (and optionally `status: "pending"`).  
  - No call to `CreatorService.search_creators` in this handler.

- **`GET /api/v1/jobs/{job_id}`**  
  - Returns job record: `id`, `status`, `progress` (e.g. `{ "step": "scoring", "details": "..." }`), `result` (full search response when completed), `error_message` (when failed), `created_at`, `updated_at`.

- **`GET /api/v1/progress`**  
  - **v1:** Deprecate or keep only for “current job” if you retain a single-job UX shortcut. Prefer **per-job** progress via `GET /jobs/{job_id}` so multiple users/tabs work and demos stay clear.

Implementation detail: re-use your existing `SearchRequest` schema; store `request.model_dump()` (or JSON) in `jobs.payload`. The worker will deserialize and pass it to `search_creators`.

---

## 4. Background Worker: Poll and Execute

Single long-running process (e.g. `python -m app.worker`).

**Loop (every few seconds, e.g. 2–5):**

1. **Claim a job:**  
   `UPDATE jobs SET status = 'running', started_at = NOW(), updated_at = NOW() WHERE id = (SELECT id FROM jobs WHERE status = 'pending' ORDER BY created_at ASC LIMIT 1 FOR UPDATE SKIP LOCKED) RETURNING id, payload, type;`  
   If no row returned, sleep and repeat.

2. **Execute:**  
   - If `type == 'search'`: deserialize `payload` to `SearchRequest`, get a DB session, call `creator_service.search_creators(db, request, progress_callback=...)`.  
   - Progress callback: `UPDATE jobs SET progress = <json>, updated_at = NOW() WHERE id = <job_id>` (no status change).

3. **Finish:**  
   - On success: `UPDATE jobs SET status = 'completed', result = <full response>, progress = NULL (or final message), updated_at = NOW() WHERE id = <job_id>`.  
   - On exception: `UPDATE jobs SET status = 'failed', error_message = <str(e)>, updated_at = NOW() WHERE id = <job_id>`.

Use one worker process (one loop) so ordering is simple and you avoid duplicate execution. For v1, no need for multiple workers or concurrency; you can add a `LIMIT 1` and single-job execution.

---

## 5. Frontend: Track Job Progress

1. **Submit:**  
   `POST /api/v1/search` with `SearchRequest` → receive `{ job_id }`.

2. **Poll:**  
   Every 1–2 seconds call `GET /api/v1/jobs/{job_id}` until `status` is `completed` or `failed`.

3. **Display:**  
   - While `pending` or `running`: show `progress.step` and `progress.details` (reuse your existing `PROGRESS_STEPS` mapping and UI).  
   - `completed`: set results from `response.result` (same shape as current `SearchResponse`).  
   - `failed`: show `response.error_message`.

4. **Optional:**  
   - Persist `job_id` in URL (e.g. `?job=uuid`) so refreshes and demos can “resume” viewing the same job.  
   - Timeout after N minutes and show “Job is still running; you can keep this page open or come back later.”

No WebSockets or Server-Sent Events in v1; polling is enough and keeps the stack simple.

---

## 6. Deployment Options for the Worker

- **Fly.io:** One small VM (e.g. `shared-cpu-1x`, 256MB). Run the worker as the main process; scale to 1 instance. Good free tier and clear “one worker service” story for demos.  
- **Railway:** One service from the same repo; run `python -m app.worker` (or `uvicorn` for API and a separate worker process if you colocate). Simple CLI and dashboard.  
- **Render:** Background worker type; same idea: one process, same codebase, connects to your Postgres.  
- **Small VPS (e.g. DigitalOcean, Hetzner):** Run worker in a systemd unit or Docker container; point `DATABASE_URL` to your Supabase/Postgres.

Use the same `DATABASE_URL` and (if needed) API keys as the web app so the worker can call YouTube and OpenAI.

---

## 7. What NOT to Build in v1

- **No Kafka, Redis Queue, or other message broker:** Postgres + `FOR UPDATE SKIP LOCKED` is the queue.  
- **No multiple worker processes** (no horizontal scaling of workers yet); one worker keeps ordering and behavior easy to reason about.  
- **No retries or dead-letter queue:** On failure, job stays `failed`; optional “retry” button can re-enqueue a new job with same payload later.  
- **No priority or scheduling:** FIFO by `created_at` is enough.  
- **No WebSockets/SSE:** Polling `GET /jobs/{job_id}` is sufficient.  
- **No job cancellation:** Worker runs to completion or failure; cancellation can be a later improvement.  
- **No cleanup job:** Old completed/failed jobs can be pruned later (e.g. daily cron); not required for initial ship.

---

## Summary for ESE

- **API:** `POST /search` creates a `jobs` row and returns `job_id`; `GET /jobs/{job_id}` returns status, progress, and result.  
- **Worker:** One process polls `jobs` where `status = 'pending'`, claims with `running`, runs `CreatorService.search_creators`, then sets `completed` or `failed` with result or error.  
- **Frontend:** POST search → poll `GET /jobs/{job_id}` → show progress from `progress`, then results or error from `result` / `error_message`.  
- **Database:** Add a `jobs` table (id, type, status, payload, progress, result, error_message, created_at, updated_at, started_at).  
- **Deploy:** Web on Vercel (or one app host); worker on Fly.io, Railway, or a small VM, with same Postgres and env as the API.

This keeps long-running analysis out of serverless, preserves a single background service, and gives you a clean, demo-friendly story: “Search returns immediately; a worker does the heavy work; the UI polls until the job is done.”
