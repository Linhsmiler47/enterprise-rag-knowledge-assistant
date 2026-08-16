# Local Development — enterprise-rag-knowledge-assistant

## Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Docker (for the containerized workflow / `make build`)

## Quick start (golden path)

This is the full path from a fresh clone to a real, cited answer — every step is required, in
order. It assumes an OpenAI-compatible LLM/embedding endpoint; the default is a local Ollama.

```bash
# 1. Clone and set up
git clone <this-repo>
cd enterprise-rag-knowledge-assistant
./scripts/bootstrap.sh   # or: make setup

# 2. Get an LLM/embedding provider running (skip if LLM_PROVIDER=openai with a real key in .env)
#    Bring up the app + db + a containerized Ollama, then pull the two models once:
docker compose -f deploy/local/docker-compose.yml \
  -f deploy/local/docker-compose.override.yml \
  -f deploy/local/docker-compose.ollama.yml up -d
docker exec local-ollama-1 ollama pull qwen2.5:0.5b
docker exec local-ollama-1 ollama pull all-minilm
curl http://localhost:11434/api/version   # sanity check: Ollama is reachable

# 3. Start the app (if not already up from step 2)
make dev

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
# 7. Run the test suite
make test

# 8. Stop
make down
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

## Native workflow (fastest inner loop, no Docker)

```bash
uv sync
cp .env.example .env   # first time only
uv run uvicorn enterprise_rag_knowledge_assistant.main:app --reload
```

## Testing

```bash
make test        # full suite with coverage
make test-unit    # unit tests only
```

## Linting / type-checking

```bash
make lint
make fmt   # auto-fix
```

## The full local CI-quality check

```bash
make ci   # lint + test + build — the same target CI runs
```

## Common issues

| Symptom | Likely cause | Fix |
|---|---|---|
| `uv: command not found` | uv not installed | Install per the prerequisites link above |
| Port 8000 already in use | Another instance still running | `make down`, or stop whatever else is on 8000 |
| `.env` missing values after adding a new setting | `.env` predates the new field in `config.py` | Compare against `.env.example` and add the missing key |
| `make ingest` fails with `httpx.ConnectError: Connection refused` on `localhost:11434` | No Ollama reachable at `LLM_BASE_URL` | Bring up the `docker-compose.ollama.yml` slice (step 2 of Quick start) and pull the models |
| `/query` always returns `grounded: false` for a question you know is covered | Index is empty or `RETRIEVAL_SIMILARITY_THRESHOLD` too high | Check `curl localhost:8000/health` for `indexed_chunks`; re-run `make ingest` if 0 |
