# TechKraft Candidate Review Dashboard

This is a small internal app for the recruitment team at TechKraft. The idea is straightforward: reviewers can look through candidates, leave scores, and see a lightweight AI-generated summary, while admins get a bit more context, including internal notes and all reviewer feedback.

It is meant to feel like a practical tool rather than a polished product demo, which is why the setup is simple and the workflow stays focused on a few core tasks.

## What the app does

- Review candidates from a shared list
- Submit scores by category
- Generate a mock AI summary for each candidate
- Let admins create new candidates and archive old ones
- Keep reviewer access limited so people only see what they should

## Tech stack

- Backend: FastAPI, SQLAlchemy (async), SQLite, JWT auth
- Frontend: React + Vite
- Containerization: Docker Compose

## Project layout

```text
/
├── docker-compose.yml
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── auth.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── routers/
│   │   └── services/
│   └── tests/
└── frontend/
    └── src/
```

## Getting started

### With Docker (recommended)

If you want the quickest path, use Docker Compose.

```bash
docker compose up --build
```

Once it is running:

- Backend: http://localhost:8000
- Frontend: http://localhost:5173
- API docs: http://localhost:8000/docs

A default admin account is created on first startup using the environment values in the backend config. The defaults are:

- email: admin@techkraft.io
- password: admin12345

### Running locally without Docker

Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

## How the flow works

1. A reviewer signs in and lands on the candidate list.
2. They can open a candidate and submit scores in a few categories.
3. The app can generate a summary for that candidate, which appears after a short delay.
4. Admins can create candidates, view internal notes, and archive candidates without removing the record entirely.

## Access rules

There are two roles in the app:

- Reviewer: can submit scores and view only their own scores
- Admin: can see all scores, view internal notes, create candidates, and archive them

Registration is intentionally limited. The server always creates a new user as a reviewer, so there is no way for a client to self-assign admin access.

## Notes on behavior

- Candidate deletion is soft rather than hard. The record is archived instead of being removed completely.
- The AI summary is a mocked placeholder for demo purposes, not a real model integration.
- The real-time update stream exists as a stretch feature and is implemented in memory for the local demo.

## Running tests

```bash
cd backend
source .venv/bin/activate
pytest -q
```

## Example API calls

Register a reviewer:

```bash
curl -X POST localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"reviewer1@techkraft.io","password":"password123","name":"Reviewer One"}'
```

Log in as the seeded admin:

```bash
curl -X POST localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@techkraft.io","password":"admin12345"}'
```

Create a candidate (admin only):

```bash
curl -X POST localhost:8000/candidates \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"name":"Ada Lovelace","email":"ada@example.com","role_applied":"Backend Engineer","skills":["Python","SQL"]}'
```

## A few practical notes

This project was built as a compact internal tool, so it favors clarity and speed over full production polish. The backend is straightforward, the frontend stays lightweight, and the data model is intentionally small.
