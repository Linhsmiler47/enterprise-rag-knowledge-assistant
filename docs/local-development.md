# Local Development — enterprise-rag-knowledge-assistant

## Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Docker (for the containerized workflow / `make build`)

## Quick start

```bash
git clone <this-repo>
cd enterprise-rag-knowledge-assistant
./scripts/bootstrap.sh   # or: make setup
make dev
```

Then:

```bash
curl localhost:8000/health
```

## Docker workflow (`make dev`)

`make dev` runs the app via Docker Compose, with source bind-mounted and `uvicorn --reload` so
code changes are picked up without a rebuild:

```bash
make dev    # start
make down   # stop
```

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
