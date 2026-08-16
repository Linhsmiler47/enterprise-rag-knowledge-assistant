# enterprise-rag-knowledge-assistant

**Status:** L4 — Portfolio-ready (locally runnable, CI/CD + IaC defined and validated, not yet
deployed) *(see `docs/product.md` for the maturity progression this follows)*

Grounded question-answering over internal engineering knowledge, with citations

## Problem

See [`docs/product.md`](docs/product.md) for the full problem statement, goals, non-goals, and
user stories.

## Architecture

See [`docs/architecture.md`](docs/architecture.md). Currently: a single FastAPI service, no
external dependencies — see [ADR-0001](docs/adr/0001-initial-architecture.md). Diagrams (current
vs. future, clearly labeled) are in [`docs/diagrams/`](docs/diagrams/).

## Quick start

```bash
./scripts/bootstrap.sh
make dev             # start app + Postgres/pgvector
make migrate         # create schema + pgvector extension
make ingest           # index data/sample/*.md
curl -s localhost:8000/query -X POST -H 'Content-Type: application/json' \
  -d '{"question": "How often are database backups taken?"}'
```

Requires an OpenAI-compatible LLM/embedding endpoint reachable at `LLM_BASE_URL` (defaults to a
local Ollama at `localhost:11434`) — see [`docs/local-development.md`](docs/local-development.md)
for the Ollama setup step if you don't already have one running.

Full instructions: [`docs/local-development.md`](docs/local-development.md).

## Testing

```bash
make test
```

## Docker

```bash
make build
docker run -p 8000:8000 enterprise-rag-knowledge-assistant:latest
```

## CI

`.github/workflows/ci.yml` runs `make ci` (lint + test + build) on every pull request and push to
`main`. `.github/workflows/security.yml` runs dependency audit, secret scanning, and a filesystem
vulnerability scan.

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
