# enterprise-rag-knowledge-assistant

**Status:** L4 — Portfolio-ready (locally runnable, CI/CD + IaC defined and validated, not yet
deployed) *(see `docs/product.md` for the maturity progression this follows)*

Extracted to a standalone repository and validated against real GitHub-hosted runners on
2026-08-16. The current backend check is `./scripts/check.sh` (Ruff, mypy, and all pytest tests);
the frontend remains a separate CI job. Azure deployment remains prepared, not executed — see
[ADR-0009](docs/adr/0009-hosting-strategy-for-personal-demo.md) and
[`docs/deployment.md`](docs/deployment.md).

Grounded question-answering over internal engineering knowledge, with citations

## Problem

See [`docs/product.md`](docs/product.md) for the full problem statement, goals, non-goals, and
user stories.

## Architecture

See [`docs/architecture.md`](docs/architecture.md). Currently: a FastAPI service backed by
PostgreSQL/pgvector and MinIO, plus an OpenAI-compatible LLM/embedding endpoint. The authoritative
query and ingestion diagrams are the Mermaid diagrams in `docs/architecture.md`.

## Quick start

```bash
./scripts/bootstrap.sh

# Start app + PostgreSQL/pgvector + MinIO + the optional local Ollama slice.
docker compose -f deploy/local/docker-compose.yml \
  -f deploy/local/docker-compose.override.yml \
  -f deploy/local/docker-compose.ollama.yml up -d --build
docker compose -f deploy/local/docker-compose.yml \
  -f deploy/local/docker-compose.override.yml \
  -f deploy/local/docker-compose.ollama.yml exec ollama ollama pull qwen2.5:0.5b
docker compose -f deploy/local/docker-compose.yml \
  -f deploy/local/docker-compose.override.yml \
  -f deploy/local/docker-compose.ollama.yml exec ollama ollama pull all-minilm

make migrate          # create schema + pgvector extension
make ingest           # index data/sample/*.md
curl -s localhost:8000/query -X POST -H 'Content-Type: application/json' \
  -d '{"question": "How often are database backups taken?"}'
```

Requires an OpenAI-compatible LLM/embedding endpoint reachable at `LLM_BASE_URL` (defaults to a
local Ollama at `localhost:11434`). Use local Ollama for the current corpus. Only the designated
public sample PDFs introduced in Stage 3 may be sent to an external API; no other repository or
user data may leave the machine. See [`docs/local-development.md`](docs/local-development.md).

Full instructions: [`docs/local-development.md`](docs/local-development.md).

On the target Windows 11/WSL2 machine, limit WSL2 to 3 GB in `%UserProfile%\.wslconfig` and do
not run or build the frontend while running backend checks. The exact setup and restart commands
are in [`docs/local-development.md`](docs/local-development.md).

## Product UI (Phase 2)

Upload, manage, and ask questions about documents without the CLI:

```bash
make dev                      # backend + Postgres + MinIO
cd frontend && npm install && npm run dev   # http://localhost:3000
```

Upload → Documents (trigger ingest) → Ask. The CLI (`make ingest`) still works for
operator/CI/eval use — the UI doesn't replace it, it adds a path that doesn't need one. See
[`docs/adr/0011-phase2-stack.md`](docs/adr/0011-phase2-stack.md).

## Testing

```bash
./scripts/check.sh
```

## Docker

```bash
make build
docker run -p 8000:8000 enterprise-rag-knowledge-assistant:latest
```

## CI

`.github/workflows/ci.yml` runs two independent jobs on every pull request and push to `main`:
`ci` (`./scripts/check.sh` — Ruff + mypy + pytest, with Postgres + MinIO service containers) and `frontend`
(`npm ci && npm run lint && npm run build`). `.github/workflows/security.yml` runs dependency
audit, secret scanning, and a filesystem vulnerability scan.

## Documentation

- [`docs/product.md`](docs/product.md) — problem, goals, user stories
- [`docs/architecture.md`](docs/architecture.md) — system design, extension points
- [`docs/local-development.md`](docs/local-development.md) — full local setup
- [`docs/evaluation.md`](docs/evaluation.md) — evaluation harness, KPI framework, measured results
- [`docs/observability.md`](docs/observability.md) — structured logging baseline
- [`docs/diagrams/`](docs/diagrams/) — current vs. future architecture diagrams
- [`docs/adr/`](docs/adr/) — architecture decisions

## Roadmap / future extensions

See [`docs/diagrams/roadmap.excalidraw`](docs/diagrams/roadmap.excalidraw) and the "Potential
future evolution" section of [`docs/architecture.md`](docs/architecture.md) — capability is added
when the product needs it, not speculatively.
