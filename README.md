# enterprise-rag-knowledge-assistant

**Status:** L0 — Idea *(update as the project matures — see `docs/product.md` for the maturity
progression this follows)*

Grounded question-answering over internal engineering knowledge, with citations

## Problem

See [`docs/product.md`](docs/product.md) for the full problem statement, goals, non-goals, and
user stories.

## Architecture

See [`docs/architecture.md`](docs/architecture.md). Currently: a single FastAPI service, no
external dependencies — see [ADR-0001](docs/adr/0001-initial-architecture.md).

## Quick start

```bash
./scripts/bootstrap.sh
make dev
curl localhost:8000/health
```

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
- [`docs/adr/`](docs/adr/) — architecture decisions

## Roadmap / future extensions

See the "Extension points" section of [`docs/architecture.md`](docs/architecture.md) — capability
is added when the product needs it, not speculatively.
