# Architecture — Enterprise RAG Knowledge Assistant

## Context

A FastAPI backend (+ an optional Next.js product UI, Phase 2) backed by PostgreSQL/pgvector for
metadata/chunks/embeddings and MinIO for raw uploaded files, answering questions grounded in a
small internal knowledge base, using a local (or optionally external) LLM through a narrow
provider boundary. External APIs may receive only the designated public sample PDFs; all other
repository and user data stays local.

## Current architecture

### Query flow

```mermaid
flowchart TD
    Request[POST /query JSON] --> Validate[QueryRequest validates question length]
    Validate --> Dependencies[FastAPI injects DB session and LLMProvider]
    Dependencies --> Route[query.query]
    Route --> Answer[answering.answer_question]
    Answer --> Retrieve[retrieval.retrieve]
    Retrieve --> Embed[LLMProvider.embed question]
    Embed --> Search[Cosine-distance top-k query]
    Search --> DB[(PostgreSQL + pgvector<br/>Chunk joined to Document)]
    DB --> Results[RetrievedChunk list with similarity]
    Results --> Evidence{Any chunk meets<br/>similarity threshold?}
    Evidence -- No --> Refuse[Return fixed insufficient-evidence answer<br/>without calling chat model]
    Evidence -- Yes --> Filter[Keep only chunks meeting threshold]
    Filter --> Prompt[Build context and question prompt]
    Prompt --> Generate[LLMProvider.chat]
    Generate --> Cite[Create citations from the same filtered chunks]
    Cite --> Response[QueryResponse: answer, grounded=true, citations]
    Refuse --> Ungrounded[QueryResponse: grounded=false, no citations]
    Answer -. one outcome log .-> Log[JSON payload via Python logging]
```

### Ingestion flow

The CLI and upload entry points perform the same high-level operations, but currently duplicate
the chunk/embed orchestration. Only `_store_chunks()` is shared; this is tracked in
[`refactor-plan.md`](refactor-plan.md).

```mermaid
flowchart TD
    subgraph CLI[CLI path]
        Command[cli ingest directory] --> Directory[ingestion.ingest_directory]
        Directory --> File[ingestion.ingest_file per file]
        File --> FileGuard{Supported extension<br/>and within size limit?}
        FileGuard -- No --> Skip[Log and return skipped]
        FileGuard -- Yes --> Read[Read UTF-8 and hash content]
        Read --> Changed{Same object key<br/>and content hash?}
        Changed -- Yes --> Unchanged[Return unchanged]
        Changed -- No --> Replace[Delete prior Document if present]
        Replace --> CliChunk[chunk_text]
        CliChunk --> CliEmbed[LLMProvider.embed_batch]
        CliEmbed --> CliStore[Create Document and call _store_chunks]
        CliStore --> CliCommit[Commit ingested Document and Chunks]
    end

    subgraph Upload[Upload/API path]
        UploadRequest[POST /documents/upload] --> UploadGuard[Validate extension, body size,<br/>and duplicate content hash]
        UploadGuard --> Raw[(Store raw bytes in MinIO)]
        Raw --> Uploaded[(Create Document status=uploaded)]
        Uploaded --> Trigger[POST /documents/id/ingest]
        Trigger --> Fetch[Fetch bytes from MinIO and decode UTF-8]
        Fetch --> IngestUpload[ingestion.ingest_uploaded_document]
        IngestUpload --> Ingesting[Commit status=ingesting]
        Ingesting --> UploadChunk[Delete prior chunks, then chunk_text]
        UploadChunk --> UploadEmbed[LLMProvider.embed_batch]
        UploadEmbed --> UploadStore[Call _store_chunks]
        UploadStore --> UploadCommit[Commit status=ingested and Chunks]
        IngestUpload -. exception .-> Failed[Rollback, then commit status=failed]
    end

    CliCommit --> Database[(PostgreSQL + pgvector)]
    UploadCommit --> Database
```

## Major components

| Component | Responsibility |
|---|---|
| `main.py` | App bootstrap, router registration, CORS |
| `config.py` | Single configuration boundary |
| `providers.py` | `LLMProvider` — one OpenAI-compatible client for both embeddings and chat; `get_llm_provider()` FastAPI dependency |
| `storage.py` | `ObjectStorage` — MinIO/S3-compatible client for uploaded files; `get_storage()` FastAPI dependency (Phase 2) |
| `db.py` | Engine/session management, `init_db()`, `check_db_reachable()`, `get_db()` FastAPI dependency |
| `models.py` | `Document` (object_key-unique, status lifecycle), `Chunk` ORM models (pgvector `Vector(384)` column) |
| `chunking.py` | Paragraph-aware text splitter |
| `ingestion.py` | CLI and upload ingestion orchestration; both call `_store_chunks()`, but currently duplicate chunk/embed steps |
| `retrieval.py` | Cosine-similarity top-k retrieval + evidence-sufficiency threshold |
| `answering.py` | Builds the grounded prompt, calls the LLM, or returns "insufficient evidence" without calling it; structured request logging |
| `api/routes/query.py` | `POST /query` |
| `api/routes/documents.py` | `POST /documents/upload`, `GET /documents`, `GET/DELETE /documents/{id}`, `POST /documents/{id}/ingest` (Phase 2) |
| `api/routes/health.py` | `/live`, `/ready`, `/health` |
| `cli.py` | `init-db`, `ingest` — wired to `make migrate` / `make ingest` |
| `scripts/evaluate.py` | Evaluation harness — see `evaluation.md` |
| `scripts/check.sh` | One-command backend verification: Ruff, mypy, then the complete pytest suite |
| `frontend/` | Next.js product UI (Upload/Documents/Ask) — see `docs/adr/0011-phase2-stack.md` |

## Diagrams

The Mermaid query and ingestion diagrams above are the source of truth for current behavior.
[`docs/diagrams/`](diagrams/) contains older Excalidraw views retained as historical visual
artifacts; they may be stale and are not updated under the current roadmap. See
[`docs/diagrams/README.md`](diagrams/README.md) for that convention.

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
- [ADR-0010](adr/0010-local-first-product-development.md) — local-first product development;
  cloud deployment deferred to Phase 10
- [ADR-0011](adr/0011-phase2-stack.md) — Phase 2 stack: Next.js + MinIO

## Known constraints

- Local generation quality is bounded by the small local model (`qwen2.5:0.5b`) — see the
  disclosed failure mode in `evaluation.md`.
- No PDF/Office ingestion (ADR-0003; Phase 3).
- No multi-document synthesis — retrieval returns top-k chunks from possibly different documents,
  but the eval set only exercises single-document answers.
- Single trusted knowledge base, no access control (product.md non-goals).
- Upload size protection is best-effort (checked after the full body is read, not streamed) —
  acceptable for a local-first, non-internet-facing tool (ADR-0008).
- Document-borne prompt injection (a poisoned indexed document, as opposed to an adversarial
  question) is not yet covered by a dedicated eval case (ADR-0008's known gap).
- No cloud deployment yet — local-first by explicit decision, not oversight (ADR-0010).
- `Settings.embedding_dimensions` is descriptive only today; the database column remains fixed at
  `Vector(384)` in `models.py`. A model/dimension change therefore requires a schema migration and
  full re-ingestion.
- Chat and embeddings share one `LLMProvider` client, base URL, and API key. The current boundary
  cannot yet route answer generation to Gemini while keeping embeddings on local Ollama.
- Query logging emits one JSON outcome payload but has no request ID or per-step events. The
  target request-correlated logging shape is Stage 2 work, not current behavior.
- Local agent work targets an 8 GB Windows 11 machine with WSL2 limited to 3 GB. Backend checks
  run sequentially, and the frontend is not started or built locally.
- Local development and CI pin the frozen community image
  `pgsty/minio:RELEASE.2026-08-04T00-00-00Z` because upstream MinIO community container images
  are no longer publicly pullable. It preserves the current S3-compatible MinIO boundary but is
  a development/test dependency, not a production hosting recommendation.

## Roadmap and current learning stages

Everything below is roadmap, not current architecture. The active learning plan in `AGENTS.md`
uses **Stage** while this document keeps the older architecture **Phase** names. When they
conflict, `AGENTS.md` wins. The Excalidraw roadmap is a historical artifact and may be stale; the
mapping below is authoritative.

### Phase 1 — Grounded RAG Backend v0.1 (done)

*Can users receive evidence-backed answers from a trusted internal knowledge base?* Markdown/text
ingestion, vector retrieval, grounded generation, citations, insufficient-evidence handling,
evaluation baseline, CI/security baseline.

### Phase 2 — Product UI + Document Upload + Open-Source Storage (done)

*Can a non-technical user upload documents, manage them, trigger ingestion, and ask questions
through a product UI?* Next.js UI, MinIO storage, document management API — this change.

### Stages 0–2 — Stabilize, understand, and measure (no architecture phase)

Stage 0 stabilized local checks and CI. Stage 1 documents the code as it exists and proposes
behavior-preserving refactors. Stage 2 changes answer generation to Gemini by configuration,
extends the existing Python logging, and establishes a reproducible evaluation baseline with
retrieval metrics. These stages were added after the original Phase 1–10 roadmap.

### Phase 3 / Stage 3 — PDF ingestion

*Can the product ingest and cite the selected public PDF corpus on the constrained development
machine?* Docling parses PDF to cached Markdown in a separate step; PDF chunks retain document,
section, and page metadata and exclude References. DOCX, PPTX, remote connectors, and a generic
parser registry are not part of this stage.

### Phase 4 / Stages 4–6 — Embedding, hybrid retrieval, and reranking

*When the corpus grows and terminology becomes ambiguous, can the system still retrieve the best
evidence?* Stage 4 moves to local `nomic-embed-text` embeddings with a configurable 768-dimension
schema. Stage 5 adds PostgreSQL English full-text search and fuses keyword/vector ranks with RRF,
only after a larger corpus demonstrates a measured gap. Stage 6 adds a small CPU cross-encoder
reranker and compares Gemini generation with an optional roughly 1B-parameter Ollama model.

### Phase 5 — Guardrails, Evaluation, and Observability Hardening

*Can the team detect, debug, and prevent poor answers, hallucinations, prompt injection, latency
problems, and regression?* Extends the ADR-0008/`docs/observability.md` baseline: layered KPI
framework, retrieval/generation/abstention/operational metrics, a versioned eval dataset, a real
release gate.

### Phase 6 — Document Intelligence / Multimodal RAG

*Can the product answer questions when information is embedded in scanned documents, tables,
diagrams, or images?* OCR, layout-aware parsing, table extraction, multimodal retrieval.

### Phase 7 / Later items 7, 10, and 11 — Advanced RAG and agents

*Do measured failures justify more retrieval paths or tool use?* Item 7 evaluates query rewriting,
multi-query, and HyDE in plain Python. Item 10 adds routing, tool calling, and text-to-SQL in plain
Python. Item 11 reimplements only the agent portion with LangGraph on a separate branch and
compares it with the plain version. Each technique is retained only when evaluation improves.

### Phase 8 / Later item 8 — Multi-turn questions

*Can a follow-up question be rewritten into a standalone retrieval query?* Store conversation
history and resolve follow-up context before retrieval. Durable personalized memory is not in the
approved scope.

### Later item 9 — RBAC (not mapped to an existing phase)

Role-based document access remains a current product non-goal. If approved later, filtering must
happen inside PostgreSQL retrieval and tests must prove a user cannot retrieve unauthorized
chunks; `product.md` and a new ADR must change first.

### Phase 9 / Later item 12 — Retrieval interoperability

*Can an external agent call this system's retrieval through a stable boundary?* Expose retrieval
as an MCP server. Multi-agent collaboration and A2A are not part of the approved item.

### Phase 10 / Later item 13 — Container delivery and cloud release

*Can the completed local product be packaged and released with controlled cost?* On merge to
`main`, CI builds and pushes the Docker image to GitHub Container Registry. Real cloud deployment
follows ADR-0009 and ADR-0010 only after an explicit decision and cost estimate; no cloud action
is implied by this roadmap.
