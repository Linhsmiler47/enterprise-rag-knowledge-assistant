# Architecture — Enterprise RAG Knowledge Assistant

## Context

A single FastAPI service backed by PostgreSQL/pgvector, answering questions grounded in a small
internal knowledge base, using a local (or optionally external) LLM through a narrow provider
boundary.

## Current architecture

```
Client
  │  HTTP
  ▼
FastAPI (src/enterprise_rag_knowledge_assistant/)
  │
  ├── POST /query ──► retrieval.py ──► pgvector similarity search ──► answering.py ──► providers.py (LLM)
  │                                                                                        │
  └── GET /live, /ready, /health ──► db.py (reachability + index content check)            │
                                                                                             ▼
                                                                              Ollama (local, default) or
                                                                              OpenAI-compatible external API
```

Ingestion (operator-triggered, not an HTTP endpoint — see "Non-goals" in `product.md`):

```
data/sample/*.md,*.txt (or any directory)
  │
  ▼
ingestion.py: load ──► chunking.py: chunk ──► providers.py: embed ──► pgvector: store
                                                                          (idempotent per file,
                                                                           content-hash keyed)
```

## Major components

| Component | Responsibility |
|---|---|
| `main.py` | App bootstrap, router registration |
| `config.py` | Single configuration boundary |
| `providers.py` | `LLMProvider` — one OpenAI-compatible client for both embeddings and chat; `get_llm_provider()` FastAPI dependency |
| `db.py` | Engine/session management, `init_db()`, `check_db_reachable()`, `get_db()` FastAPI dependency |
| `models.py` | `Document`, `Chunk` ORM models (pgvector `Vector(384)` column) |
| `chunking.py` | Paragraph-aware text splitter |
| `ingestion.py` | Idempotent ingest pipeline: load → chunk → embed → store |
| `retrieval.py` | Cosine-similarity top-k retrieval + evidence-sufficiency threshold |
| `answering.py` | Builds the grounded prompt, calls the LLM, or returns "insufficient evidence" without calling it |
| `api/routes/query.py` | `POST /query` |
| `api/routes/health.py` | `/live`, `/ready`, `/health` |
| `cli.py` | `init-db`, `ingest` — wired to `make migrate` / `make ingest` |
| `scripts/evaluate.py` | Evaluation harness — see `evaluation.md` |

## Diagrams

[`docs/diagrams/`](diagrams/) has visual versions of the architecture above and the
`POST /query`/ingestion flows, plus a roadmap diagram that explicitly separates what's implemented
(v0.1, solid) from what isn't (v0.2+, dashed). See [`docs/diagrams/README.md`](diagrams/README.md)
for the current/future convention and the current source-only status (SVG export is a documented
manual step — not automatable in the environment this change was produced in).

## Major decisions

See [`adr/`](adr/):

- [ADR-0001](adr/0001-initial-architecture.md) — start minimal, design for extension (from the canonical template)
- [ADR-0002](adr/0002-llm-provider-boundary.md) — LLM/embedding provider boundary
- [ADR-0003](adr/0003-ingestion-format-scope.md) — Markdown/text-only ingestion scope
- [ADR-0004](adr/0004-vector-only-retrieval-baseline.md) — vector-only retrieval, no hybrid/reranking yet
- [ADR-0005](adr/0005-evaluation-approach.md) — simple harness over RAGAS
- [ADR-0006](adr/0006-azure-container-apps.md) — Azure Container Apps as deployment target
- [ADR-0007](adr/0007-demo-persistence-cost-tradeoff.md) — demo vs. production persistence tradeoff
- [ADR-0008](adr/0008-guardrail-baseline.md) — guardrail baseline (input/retrieval/generation/output)
- [ADR-0009](adr/0009-hosting-strategy-for-personal-demo.md) — hosting strategy for a personal
  low-traffic demo (**Proposed**, not yet approved/deployed)

## Known constraints

- Local generation quality is bounded by the small local model (`qwen2.5:0.5b`) — see the
  disclosed failure mode in `evaluation.md`.
- No PDF/Office ingestion (ADR-0003).
- No multi-document synthesis — retrieval returns top-k chunks from possibly different documents,
  but the eval set only exercises single-document answers.
- Single trusted knowledge base, no access control (product.md non-goals).

## Potential future evolution

Everything below is roadmap, not current architecture — see also `product.md`'s non-goals and
[`docs/diagrams/roadmap.excalidraw`](diagrams/roadmap.excalidraw) for the visual version.

### v0.2 — Retrieval quality

Hybrid retrieval (dense + keyword), reranking, metadata filtering, expanded/regression-tested
evaluation set.

### v0.3 — Ingestion evolution

Asynchronous ingestion, event-driven architecture, PDF/Office parsing. Kafka only if a real
workload/value case justifies it — not by default.

### v0.4 — Observability / LLMOps

OpenTelemetry tracing, prompt/evaluation tracing, cost/token monitoring.

### v0.5 — Platform

Kubernetes/Helm — only if a learning or scale objective justifies it (the incubating workspace's
ADR-0003 sets containers-first; Container Apps remains the default here regardless).

### v0.6 — MCP

Expose the knowledge base as an MCP server so external agent clients (e.g. Claude Desktop) can
query it directly.

### v0.7 — A2A readiness

Document and expose capabilities suitable for another portfolio project (e.g. a future Data
Quality Copilot) to query this project's knowledge base via an explicit API contract — never via
direct code/database coupling. See the workspace's `docs/conventions/project-integration.md`.
