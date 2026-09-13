# AI Code Review Agent

This project is a FastAPI-based GitHub webhook service that reviews pull requests with Gemini and posts review feedback back to GitHub.

It is designed to receive GitHub webhook payloads, fetch the changed files for a PR, run a code review flow, and then publish findings as inline comments or PR-level comments while keeping the webhook response fast.

## What it does

When a pull request is opened, synchronized, reopened, or edited:

1. GitHub sends a webhook to `/webhook/github`.
2. The app validates the signature if `GITHUB_WEBHOOK_SECRET` is configured.
3. The payload is parsed defensively, including form-encoded `payload=` payloads.
4. The app extracts the repo name and PR number.
5. It fetches PR files from the GitHub API.
6. It filters changed files to reviewable extensions.
7. A background worker runs the review.
8. The result is posted to GitHub as either:
   - inline review comments on the changed file/line, or
   - a fallback PR-level comment when the line cannot be mapped to diff metadata.

## Current architecture

```text
GitHub PR event
    │
    ▼
FastAPI webhook endpoint
    │
    ├─ verify signature
    ├─ parse payload
    ├─ fetch PR metadata
    └─ enqueue review task
    │
    ▼
Background worker (workers.review_worker)
    │
    ├─ fetch PR files
    ├─ prepare review inputs
    ├─ run LangGraph review flow
    ├─ build final review result
    └─ post comments to GitHub
    │
    ▼
PostgreSQL / SQLAlchemy storage
    └─ review metadata + status + results
```

## Tech stack

- Python
- FastAPI
- Uvicorn
- SQLAlchemy
- PostgreSQL
- Alembic
- Redis
- GitHub REST API
- LangChain
- LangGraph
- Gemini / Google GenAI
- FAISS (used in the RAG/retrieval flow)
- httpx

## Project structure

```text
code-review-agent/
├── backend/
│   ├── agents/
│   │   ├── bug_agent.py
│   │   ├── security_agent.py
│   │   ├── performance_agent.py
│   │   ├── maintainability_agent.py
│   │   └── testing_agent.py
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   ├── common/
│   │   └── logger.py
│   ├── database/
│   │   ├── connection.py
│   │   ├── models.py
│   │   ├── review_storage_service.py
│   │   └── dependencies.py
│   ├── evaluation/
│   ├── graph/
│   │   ├── nodes.py
│   │   ├── review_graph.py
│   │   └── state.py
│   ├── infrastructure/
│   │   ├── connection.py
│   │   ├── queue.py
│   │   └── redis.py
│   ├── rag/
│   │   ├── document_loader.py
│   │   ├── github_document_loader.py
│   │   ├── retriever.py
│   │   ├── vector_store.py
│   │   └── documents/
│   ├── routes/
│   │   ├── github_webhook.py
│   │   ├── health.py
│   │   └── review_router.py
│   ├── schemas/
│   │   ├── ai_review_schema.py
│   │   ├── review_schema.py
│   │   └── github.py
│   ├── services/
│   │   ├── code_review_service.py
│   │   ├── diff_service.py
│   │   ├── github_api_service.py
│   │   ├── github_review_service.py
│   │   ├── github_webhook_service.py
│   │   └── review_service.py
│   ├── workers/
│   │   └── review_worker.py
│   ├── main.py
│   └── reviews/
├── .env
├── .gitignore
├── alembic.ini
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── start.sh
├── README.md
└── venv/
```

## Review flow

The review service currently uses an LLM-based pipeline with specialized review nodes and a final synthesis pass. The final result is normalized and then converted into GitHub comments.

The app also includes deduplication checks to avoid posting the same summary or inline comment multiple times.

## Environment variables

Create a `.env` file in the project root or set the following environment variables before running the app:

```env
DATABASE_URL=postgresql://user:password@host:5432/code_review_agent
REDIS_URL=redis://localhost:6379/0
GITHUB_TOKEN=your_github_token
GITHUB_WEBHOOK_SECRET=your_webhook_secret
GEMINI_API_KEY=your_gemini_api_key
```

Notes:

- `GITHUB_WEBHOOK_SECRET` is optional in code; if it is missing, signature validation is skipped.
- `GEMINI_API_KEY` is required for the review pipeline to run.
- `DATABASE_URL` is required for the SQLAlchemy models and Alembic migrations.

## Local setup

### 1. Create a virtual environment

```bash
python -m venv .venv
```

On Windows:

```powershell
.venv\Scripts\Activate.ps1
```

On macOS/Linux:

```bash
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run database migrations

```bash
alembic upgrade head
```

### 4. Start the API

From the project root:

```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Start the worker

In a separate terminal:

```bash
cd backend
python -m workers.review_worker
```

### 6. Health check

```text
GET /health
```

## Webhook endpoint

The app exposes the GitHub webhook at:

```text
POST /webhook/github
```

GitHub PR events are parsed and handled from the webhook body. The app currently supports pull request actions such as `opened`, `synchronize`, `reopened`, and `edited`.

## Docker / startup script

The repository includes a `start.sh` script for startup:

```bash
./start.sh
```

The script runs Alembic and starts the worker plus the FastAPI app.

## Current project status

This repo is currently a working FastAPI + GitHub webhook + AI review prototype. It includes:

- webhook parsing and verification
- PR file extraction
- review queue/background execution
- GitHub comment posting
- deduplication checks
- SQLAlchemy persistence for review tracking
- review status endpoints

It is not a full production queue system yet, but the core webhook-to-review-to-GitHub flow is in place.

## Security notes

- Webhook signatures are checked using HMAC-SHA256 when a secret is configured.
- Secrets are expected to be loaded from environment variables.
- GitHub API operations use the configured token.
- Avoid committing `.env` files or real keys to version control.

## Useful references

- GitHub webhook route: `backend/routes/github_webhook.py`
- Review worker: `backend/workers/review_worker.py`
- Review logic: `backend/services/review_service.py`
- GitHub comment helpers: `backend/services/github_review_service.py`
- Database model: `backend/database/models.py`

## License

This project currently does not define a license file. If you intend to publish it publicly, add a license before distribution.

## 👩‍💻 Author

**Sireesha**

Built as a hands-on project to explore **backend engineering, GenAI,
multi-agent systems, RAG, distributed job processing, and production
deployment**.
