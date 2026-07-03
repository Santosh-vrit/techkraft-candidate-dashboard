# TechKraft Candidate Review Dashboard

An internal tool for TechKraft's recruitment team to manage candidate assessments:
reviewers score candidates and view AI-generated summaries, admins get full
visibility including internal notes and every reviewer's scores.

- **Backend**: FastAPI + SQLAlchemy (async) + SQLite, JWT auth
- **Frontend**: React + Vite
- **Containerization**: Docker Compose (backend on `:8000`, frontend on `:5173`)

## Project structure

```
/
├── docker-compose.yml
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .env.example
│   ├── app/
│   │   ├── main.py            # FastAPI app, CORS, startup (create tables + seed admin)
│   │   ├── config.py          # pydantic-settings from env
│   │   ├── database.py        # async engine/session
│   │   ├── models.py          # SQLAlchemy models (User, Candidate, Score)
│   │   ├── schemas.py         # Pydantic request/response schemas
│   │   ├── auth.py            # password hashing, JWT, RBAC dependencies
│   │   ├── routers/
│   │   │   ├── auth.py        # /auth/register, /auth/login
│   │   │   └── candidates.py  # /candidates ...
│   │   └── services/
│   │       ├── candidate_service.py  # search/filtering, scoring, mock AI summary
│   │       └── events.py             # in-memory pub/sub for SSE
│   └── tests/
│       ├── conftest.py
│       ├── test_api.py
│       └── test_auth_rbac.py
└── frontend/
    ├── Dockerfile
    ├── .env.example
    └── src/
        ├── api/client.js
        ├── context/AuthContext.jsx
        ├── pages/{Login,CandidateList,CandidateDetail}.jsx
        └── components/Navbar.jsx
```

## Setup & run

### Option A — Docker Compose (recommended)

```bash
cp backend/.env.example backend/.env       # optional, defaults work out of the box
docker compose up --build
```

- Backend: http://localhost:8000 (docs at http://localhost:8000/docs)
- Frontend: http://localhost:5173

A default admin account is seeded on first startup from `ADMIN_EMAIL` /
`ADMIN_PASSWORD` (defaults: `admin@techkraft.io` / `admin12345`).

### Option B — Run locally without Docker

Backend (requires Python 3.11+):

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Frontend (requires Node 18+):

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

### Running tests

```bash
cd backend
source .venv/bin/activate
pytest -q
```

7 tests covering: candidate creation, list filtering by skill, soft-delete
behavior, score validation, reviewer-cannot-see-another-reviewer's-scores,
reviewer-cannot-see-internal-notes/create-candidates, and unauthenticated
requests being rejected.

## Example API calls

```bash
# Register a reviewer (role is always "reviewer", regardless of what's sent)
curl -X POST localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"reviewer1@techkraft.io","password":"password123","name":"Reviewer One"}'

# Log in as the seeded admin
TOKEN=$(curl -s -X POST localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@techkraft.io","password":"admin12345"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# Create a candidate (admin only)
curl -X POST localhost:8000/candidates \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"Ada Lovelace","email":"ada@example.com","role_applied":"Backend Engineer","skills":["Python","SQL"]}'

# List candidates with filters + pagination
curl "localhost:8000/candidates?status=new&skill=Python&offset=0&limit=20" \
  -H "Authorization: Bearer $TOKEN"

# Submit a score
curl -X POST localhost:8000/candidates/<candidate_id>/scores \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
  -d '{"category":"Technical Skills","score":5,"note":"Excellent"}'

# Trigger the mock AI summary (returns immediately, completes ~2s later)
curl -X POST localhost:8000/candidates/<candidate_id>/summary -H "Authorization: Bearer $TOKEN"

# Poll for the result
curl localhost:8000/candidates/<candidate_id> -H "Authorization: Bearer $TOKEN"

# Stream live score/summary updates for a candidate (stretch goal, SSE)
curl -N localhost:8000/candidates/<candidate_id>/stream -H "Authorization: Bearer $TOKEN"
```

## Role-based access control

- **Registration** (`POST /auth/register`) has no `role` field in its request
  schema at all — the server always creates the user with `role=reviewer`.
  There is no code path that lets a client set its own role.
- **reviewer**: can submit scores, sees only their own scores on a candidate,
  cannot view or edit `internal_notes`, cannot create/delete candidates.
- **admin**: sees every reviewer's scores, can view/edit `internal_notes`,
  can create candidates and archive (soft-delete) them.
- A seeded admin account (`ADMIN_EMAIL` / `ADMIN_PASSWORD` env vars) is the
  only way to get an admin account — matching the idea that admin
  provisioning happens out-of-band, not through public self-registration.

## Soft delete

`DELETE /candidates/{id}` never removes a row. It sets `status="archived"`
and stamps `deleted_at`. All list/detail queries filter on
`deleted_at IS NULL`, so archived candidates disappear from normal views
while the row (and its score history) is preserved for audit purposes.

## Debugging Signal

The snippet in the prompt:

```python
def search_candidates(status, keyword, page, page_size):
    all_candidates = db.execute("SELECT * FROM candidates").fetchall()
    filtered = [c for c in all_candidates if c["status"] == status]
    # ... also filter by keyword in Python ...
    offset = (page - 1) * page_size
    return filtered[offset : offset + page_size]
```

**What's wrong:** it loads the *entire* `candidates` table into application
memory on every request, then does status/keyword filtering and pagination
in Python instead of in SQL. The `status` index on the table is never used
because there's no `WHERE` clause — the database can't apply it to a query
that has none.

**Why it matters at scale:** with 100 rows this is invisible. With 500k
candidates it means every list request pulls the full table across the
network/socket into the app process, filters most of it away, and repeats
that full scan on every single page turn. Memory and latency scale with
total table size, not with result size — pagination stops actually saving
any work. It's also a correctness risk: two concurrent requests can see
different "pages" of a shifting in-memory list if writes happen between
calls, and there's no `LIMIT`, so a single slow query can hold a connection
open far longer than necessary.

**Correct approach** (what `search_candidates` does in
[`backend/app/services/candidate_service.py`](backend/app/services/candidate_service.py)):
push every filter into the `WHERE` clause and let SQLite/Postgres use its
indexes, then apply `OFFSET`/`LIMIT` in the query itself:

```python
conditions = [Candidate.deleted_at.is_(None)]
if status:
    conditions.append(Candidate.status == status)
if keyword:
    conditions.append(or_(Candidate.name.ilike(f"%{keyword}%"), Candidate.email.ilike(f"%{keyword}%")))

query = select(Candidate).where(*conditions)
total = await db.scalar(select(func.count()).select_from(query.subquery()))
rows = await db.execute(query.offset(offset).limit(limit))
```

This way the database only ever returns the rows that satisfy the filter,
in the page size requested, using the indexes defined on `status` and
`role_applied`.

## Architecture Decision Records

### ADR 1 — FastAPI + SQLAlchemy async over Flask/Django

**Context:** needed a Python API framework with first-class async support,
automatic request validation, and low ceremony for a 2.5-hour-scoped
take-home that still needed to demonstrate production patterns (JWT auth,
background tasks, SSE).

**Decision:** FastAPI with SQLAlchemy 2.0's async engine (`aiosqlite`) rather
than Flask (sync-first, would need Celery/threads to fake the "async LLM
call") or Django (batteries-included ORM/admin is overkill for 3 entities
and fights async patterns).

**Trade-off:** FastAPI's ecosystem for things like migrations is thinner
than Django's — we don't get `django-admin` for free, and had to hand-roll
RBAC dependencies instead of using a mature package. In exchange we got
native `async def` route handlers, `BackgroundTasks` for the mock LLM call,
and `StreamingResponse` for the SSE stretch goal, all without extra
infrastructure (no message broker needed for a single-process demo).

### ADR 2 — SQLite for storage, not DynamoDB or Postgres

**Context:** the prompt allowed "DynamoDB-style or SQLite." The candidate
model is relational (candidates have scores, scores belong to reviewers) and
needs ad-hoc filtering (status + role + skill + keyword combined), which
maps naturally onto SQL and awkwardly onto a single-table NoSQL design with
hand-rolled GSIs.

**Decision:** SQLite via SQLAlchemy's async ORM, with indexes on
`candidates.status`, `candidates.role_applied`, and `scores.candidate_id`
(and a unique index on `email`).

**Trade-off:** SQLite has no native array/contains operator, so filtering
candidates by `skill` uses SQLite's `json_each()` table-valued function
against a JSON column — functional, but a real Postgres deployment would
use a proper `text[]` column with a GIN index (or a normalized
`candidate_skills` join table) for that filter to scale cleanly. We also
skipped Alembic migrations in favor of `create_all()` on startup, which is
fine for a single-file SQLite demo but would need a real migration tool the
moment the schema needs to evolve under existing data.

### ADR 3 — Background task + polling for the mock AI summary, not a blocking `await`

**Context:** `POST /candidates/{id}/summary` "simulates an async LLM call
(2s delay)" and the spec explicitly requires the frontend to show a loading
state rather than a blank page.

**Decision:** the endpoint sets `ai_summary_status="pending"` and returns
`202 Accepted` immediately, scheduling the actual 2-second "LLM call" as a
FastAPI `BackgroundTask`. The frontend polls `GET /candidates/{id}` every
~1.2s while status is `pending` and renders a spinner; a stretch-goal SSE
endpoint (`/candidates/{id}/stream`) pushes the same event without polling.

**Trade-off:** polling is simpler to reason about and test than SSE/websockets,
but it's not truly real-time and adds request volume proportional to the
number of open detail pages. The SSE endpoint solves that but is in-memory
and single-process only (`app/services/events.py`) — a multi-worker
deployment would need Redis pub/sub (or a managed equivalent) to fan
events out across processes. We kept both so the trade-off is visible
rather than papered over: polling for the required path, SSE for the
stretch goal, neither pretending to be a queue-backed job system a real
LLM integration would need (real IDs, retries, backpressure).

## Known limitations (honestly acknowledged)

- No Alembic migrations — schema changes require a fresh SQLite file in
  this iteration.
- SSE pub/sub (`app/services/events.py`) is in-memory and only works
  correctly with a single backend process/worker.
- Skill filtering uses SQLite's `json_each()`, which works for demo data
  volumes but isn't the shape a large-scale relational skill search would
  use in Postgres.
- No refresh-token rotation — JWTs are long-lived (8h) bearer tokens with
  no revocation list, acceptable for an internal tool demo but not for a
  production system with the same threat model as a customer-facing app.
- The frontend has no automated tests (only backend `pytest`); UI
  correctness was verified manually via a scripted Playwright walkthrough
  during development (login → create candidate → score → AI summary
  loading/completed states → admin notes), not committed as a test suite.
- `docker compose build` was written and reviewed carefully (standard
  slim-Python / slim-Node multi-stage-free Dockerfiles, matching ports),
  but could not be pulled/built end-to-end in the development sandbox used
  to prepare this submission — Docker Hub image pulls stalled there (even
  `docker pull hello-world` hung), which points to sandbox network
  restrictions rather than a bug in the Dockerfiles. Both services were
  instead fully verified running natively (`uvicorn` + `vite`) on the same
  ports the compose file exposes, including a scripted end-to-end browser
  walkthrough. Please run `docker compose up --build` in a normal
  environment to confirm; the Dockerfiles/compose file follow standard,
  well-tested patterns.

## Learning reflection

This was my first time wiring SQLite through SQLAlchemy's *async* engine
(`aiosqlite`) end-to-end with FastAPI's dependency-injected sessions rather
than the more common sync `Session` — the `greenlet`-based bridging that
makes `await` work over a fundamentally synchronous DB driver was new to me
and worth understanding rather than treating as a magic requirement.
Given more time, I'd explore replacing the polling-based AI summary status
check with the SSE stream end-to-end in the frontend (it's implemented
server-side as a stretch goal but the UI still polls), and I'd back the SSE
pub/sub with Redis so it survives multiple backend workers instead of only
working in-memory on a single process.

## Responsibility & detail checklist

- [x] No real credentials committed — only `.env.example` files with dummy
      values (`backend/.env.example`, `frontend/.env.example`); `.env` is
      gitignored.
- [x] README ports match `docker-compose.yml` (backend `8000`, frontend `5173`).
- [x] Mock AI summary shows a loading spinner while pending and an error
      banner on failure, not a blank page (`CandidateDetail.jsx`).
- [x] Deletes are soft (`status="archived"` + `deleted_at`), never a hard
      `DELETE FROM candidates`.
- [x] Registration hardcodes `role="reviewer"` server-side; the request
      schema has no `role` field for a client to spoof.
