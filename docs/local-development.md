# Local Development — enterprise-rag-knowledge-assistant

## Prerequisites

- Windows 11 with WSL2
- Docker Desktop with WSL integration enabled
- [uv](https://docs.astral.sh/uv/getting-started/installation/) inside WSL2
- Node.js 22+ only when the repository owner chooses to run the frontend

Verify the backend toolchain from WSL2 before starting:

```bash
uname -a                 # should include microsoft-standard-WSL2
docker version           # both Client and Server sections must be present
docker compose version
python --version         # Python 3.12+
uv --version
```

If `docker version` shows only the client or cannot reach `/var/run/docker.sock`, start Docker
Desktop on Windows and enable WSL integration for this distribution. Ollama is optional as a host
installation because the repository provides the `docker-compose.ollama.yml` slice below.

## WSL2 memory limit

On the target 8 GB machine, open `%UserProfile%\.wslconfig` from PowerShell:

```powershell
notepad $env:USERPROFILE\.wslconfig
```

Set the following values, save the file, then restart WSL2 and Docker Desktop:

```ini
[wsl2]
memory=3GB
swap=1GB
```

```powershell
wsl --shutdown
```

After reopening WSL2, run `free -h` and confirm the memory limit is close to 3 GB. Do not run
heavy tasks in parallel. The agent does not start or build the frontend locally; use FastAPI's
`http://localhost:8000/docs` for local verification. The repository owner may run the frontend
manually when inspecting the UI.

## Quick start (golden path)

This is the full path from a fresh clone to a real, cited answer — every step is required, in
order. It uses the local Ollama endpoint. Only the designated public sample PDFs introduced in
Stage 3 may be sent to an external API; all other repository or user data must stay local.

```bash
# 1. Clone and set up
git clone <this-repo>
cd enterprise-rag-knowledge-assistant
./scripts/bootstrap.sh   # or: make setup

# 2. Bring up the app + db + MinIO + a containerized Ollama, then pull both models once:
docker compose -f deploy/local/docker-compose.yml \
  -f deploy/local/docker-compose.override.yml \
  -f deploy/local/docker-compose.ollama.yml up -d
docker compose -f deploy/local/docker-compose.yml \
  -f deploy/local/docker-compose.override.yml \
  -f deploy/local/docker-compose.ollama.yml exec ollama ollama pull qwen2.5:0.5b
docker compose -f deploy/local/docker-compose.yml \
  -f deploy/local/docker-compose.override.yml \
  -f deploy/local/docker-compose.ollama.yml exec ollama ollama pull all-minilm
curl http://localhost:11434/api/version   # sanity check: Ollama is reachable

# 3. Confirm the four services are running
docker compose -f deploy/local/docker-compose.yml \
  -f deploy/local/docker-compose.override.yml \
  -f deploy/local/docker-compose.ollama.yml ps

# 4. Create the schema (idempotent — safe to re-run)
make migrate

# 5. Ingest the sample knowledge base
make ingest
# expected: "done: 4 ingested, 0 unchanged, 0 skipped"

# 6. Ask a real question
curl -s localhost:8000/query -X POST -H 'Content-Type: application/json' \
  -d '{"question": "How often are database backups taken?"}'
```

Expected response shape — note `grounded: true` and a `citations` entry pointing at the source
document/chunk, not just prose:

```json
{
  "question": "How often are database backups taken?",
  "answer": "Database backups are taken daily...",
  "grounded": true,
  "citations": [
    {"document": "database-backup-policy.md", "chunk_id": 1, "similarity": 0.71}
  ]
}
```

Ask something the sample knowledge base doesn't cover (e.g. `"What is our parental leave
policy?"`) and confirm `grounded: false` with an empty `citations` list and the insufficient-
evidence message — this is FR-007, not a bug.

```bash
# 7. Run the complete backend check
./scripts/check.sh

# 8. Stop the complete stack, including Ollama
docker compose -f deploy/local/docker-compose.yml \
  -f deploy/local/docker-compose.override.yml \
  -f deploy/local/docker-compose.ollama.yml down
```

## Docker workflow (`make dev`)

`make dev` runs the app via Docker Compose, with source bind-mounted and `uvicorn --reload` so
code changes are picked up without a rebuild:

```bash
make dev    # start
make down   # stop
```

If you don't already have an Ollama reachable at `localhost:11434`, add the `docker-compose.ollama.yml`
slice (step 2 above) — otherwise `make ingest` / `/query` will fail with a connection-refused error
against `LLM_BASE_URL`.

## Product UI workflow (Phase 2, no CLI needed)

An alternative golden path that doesn't touch `make ingest` at all:

```bash
make dev   # backend + Postgres + MinIO

cd frontend
npm install
cp .env.local.example .env.local   # first time only
npm run dev   # http://localhost:3000
```

Then in the browser: **Upload** a `.md`/`.txt` file → go to **Documents**, click **Ingest** next
to it (status moves `uploaded` → `ingesting` → `ingested`, or `failed` with a reason if the LLM
provider isn't reachable) → go to **Ask** and ask a question, inspect the grounded answer and its
citations. See [ADR-0011](adr/0011-phase2-stack.md) for why this stack (Next.js + MinIO).

## Native workflow (fastest inner loop, no Docker)

```bash
uv sync
cp .env.example .env   # first time only
uv run uvicorn enterprise_rag_knowledge_assistant.main:app --reload
```

## Testing

```bash
docker compose -f deploy/local/docker-compose.yml \
  -f deploy/local/docker-compose.override.yml up -d db minio
./scripts/check.sh   # Ruff, mypy, and all pytest tests
make test-unit      # unit tests only
```

## Linting / type-checking

```bash
make lint
make fmt   # auto-fix
```

## The full local CI-quality check

```bash
./scripts/check.sh   # the same backend command CI runs
# `make ci` is a compatibility alias for the same script.
```

The separate CI frontend job runs `npm ci`, `npm run lint`, and `npm run build`. The agent does not
run these frontend commands on the constrained local machine.

## Common issues

| Symptom | Likely cause | Fix |
|---|---|---|
| `uv: command not found` | uv not installed | Install per the prerequisites link above |
| `docker version` cannot connect to the daemon | Docker Desktop is stopped or WSL integration is disabled | Start Docker Desktop and enable this WSL distribution under Docker Desktop settings |
| Docker cannot pull `minio/minio:latest` | Upstream community images are no longer publicly distributed | Pull the pinned `pgsty/minio:RELEASE.2026-08-04T00-00-00Z` image used by Compose and CI |
| Port 8000 already in use | Another instance still running | `make down`, or stop whatever else is on 8000 |
| `.env` missing values after adding a new setting | `.env` predates the new field in `config.py` | Compare against `.env.example` and add the missing key |
| `make ingest` fails with `httpx.ConnectError: Connection refused` on `localhost:11434` | No Ollama reachable at `LLM_BASE_URL` | Bring up the `docker-compose.ollama.yml` slice (step 2 of Quick start) and pull the models |
| `/query` always returns `grounded: false` for a question you know is covered | Index is empty or `RETRIEVAL_SIMILARITY_THRESHOLD` too high | Check `curl localhost:8000/health` for `indexed_chunks`; re-run `make ingest` if 0 |
| `POST /documents/upload` returns a connection error, or `/documents/{id}/ingest` always fails | MinIO not reachable at `MINIO_ENDPOINT` | Confirm `make dev` is up (`docker ps` should show a `minio` container); check `curl localhost:9000/minio/health/live` |
| Upload succeeds but ingest always returns `status: "failed"` | No LLM provider reachable (same root cause as the CLI's connection-refused case) | Same fix — bring up `docker-compose.ollama.yml` and pull the models; check `ingestion_error` in the response and the app's server logs for the real traceback |
| Frontend can't reach the backend (`Failed to fetch`) | `NEXT_PUBLIC_API_URL` unset/wrong, or CORS | Confirm `frontend/.env.local` points at the backend URL and `CORS_ALLOWED_ORIGINS` (backend `.env`) includes the frontend's origin (defaults already match `localhost:3000`/`localhost:8000`) |
