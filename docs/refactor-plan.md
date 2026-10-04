# Stage 1 Code Walkthrough and Refactor Plan

## Purpose and scope

This document records how the backend works on 2026-10-04, where documentation and code differ,
and a sequence of small behavior-preserving refactors. Stage 1 changes documentation only. Every
code step below requires separate approval and must be implemented and committed independently.

The review covered `docs/architecture.md`, `docs/product.md`, `docs/evaluation.md`,
`docs/observability.md`, ADR-0001 through ADR-0011, the backend source, backend tests, CI
workflows, `scripts/check.sh`, and `scripts/evaluate.py`. Existing ADR content was not edited.

## Current request path: `POST /query`

1. `main.py` creates the FastAPI application and registers the query router. Its lifespan only
   marks the process ready; schema creation remains an operator action.
2. `api/routes/query.py::QueryRequest` rejects questions outside 1–2000 characters. FastAPI
   injects a SQLAlchemy `Session` from `db.py::get_db()` and a cached `LLMProvider` from
   `providers.py::get_llm_provider()`.
3. `api/routes/query.py::query()` reads the current `Settings` and calls
   `answering.py::answer_question()`. The route translates internal dataclasses into the public
   Pydantic response model; it contains no retrieval policy itself.
4. `answer_question()` starts latency timers and calls `retrieval.py::retrieve()`.
5. `retrieve()` calls `LLMProvider.embed(question)`. The provider uses the OpenAI-compatible
   embeddings endpoint configured by one shared base URL/API key.
6. `retrieve()` asks PostgreSQL/pgvector for the `retrieval_top_k` chunks ordered by cosine
   distance, joins each chunk to its document, converts distance to similarity, and returns
   `RetrievedChunk` values.
7. `answer_question()` checks whether any result reaches `retrieval_similarity_threshold`. If
   none does, it returns the fixed insufficient-evidence message with `grounded=false` and no
   citations. This branch deliberately does not call the chat model, saving latency/quota and
   preventing an unsupported answer.
8. If evidence is sufficient, only chunks at or above the threshold are placed in the prompt.
   `_build_user_prompt()` labels each excerpt with document name and chunk ID, then
   `LLMProvider.chat()` sends the hardened system prompt and user prompt to the configured chat
   completion endpoint.
9. Citations are built from exactly the same filtered chunks used as context. The route returns
   the question, generated answer, `grounded=true`, and citations.
10. Every exit from `answer_question()` logs one JSON outcome payload containing counts, model
    names, timing, and error category. It intentionally excludes question, answer, and document
    content. There is currently no request ID and no separate embed/search/generate event.

The main design choice is a useful one: HTTP validation/serialization, retrieval, answer policy,
and provider I/O live in separate modules. The evidence gate sits before generation, so refusal
does not depend on the chat model obeying a prompt. The important current limitation is that chat
and embedding share one concrete provider configuration even though the target stack needs two
different endpoints.

## Current ingestion paths

### CLI path

1. `cli.py` handles `ingest <directory>`, creates a provider and database session, and calls
   `ingestion.py::ingest_directory()`.
2. `ingest_directory()` iterates only direct files in sorted order and calls `ingest_file()`.
3. `ingest_file()` rejects unsupported extensions and oversized files before reading content.
   It reads UTF-8 text, hashes it, and uses the filename as the CLI document's `object_key`.
4. An unchanged object key plus content hash returns `unchanged`. Changed content deletes the
   old `Document`; relationship cascade removes its chunks when the transaction commits.
5. `chunking.py::chunk_text()` groups paragraphs to a character limit and hard-splits a single
   oversized paragraph. `LLMProvider.embed_batch()` embeds the resulting strings.
6. `ingest_file()` creates an already-`ingested` `Document`, calls `_store_chunks()`, and commits
   the document and chunks together.

This path is simple and idempotent for a flat directory. One bad UTF-8 file or provider error
currently aborts the directory run; the `failed` value documented by `IngestResult.status` is not
produced by the CLI path.

### Upload/API path

1. `api/routes/documents.py::upload_document()` sanitizes the display filename, validates the
   extension, then reads the complete upload into memory and checks empty/maximum size.
2. It hashes raw bytes and returns the first existing `Document` with the same content hash. For
   new content, it writes raw bytes to a server-generated MinIO key, creates a PostgreSQL
   `Document` with `status=uploaded`, and commits it.
3. `trigger_ingestion()` returns immediately for an already-ingested document. Otherwise it
   fetches the MinIO object, decodes UTF-8, and calls `ingest_uploaded_document()`.
4. `ingest_uploaded_document()` first commits `status=ingesting`, deletes any previous chunks,
   repeats the chunk/embed operations used by the CLI path, calls `_store_chunks()`, changes the
   status to `ingested`, and commits.
5. An exception rolls back chunk changes, then commits a sanitized `failed` state while the full
   exception stays in server logs. Fetch/decode failures are handled in the router with the same
   client-safe principle.
6. Deletion removes the MinIO object first, then deletes the database document; ORM cascade
   deletes chunks.

MinIO and PostgreSQL cannot share a transaction. The current ordering is understandable for a
small local product, but failures can leave an orphaned object after upload or remove the object
before a database delete fails. The two ingestion paths also share only `_store_chunks()`; their
chunk/embed orchestration is duplicated.

## Documentation and decision mismatches

| Priority | Documented claim or decision | Actual code/repository state | Disposition |
|---|---|---|---|
| Resolved before Stage 2 | Earlier policy allowed external APIs to receive only the three designated public PDFs, while Stage 2 evaluates the current Markdown corpus with Gemini. | The owner confirmed that every document in this learning project is public and may be sent to external APIs. Internal company documents and personal data must never enter the repository or corpus. | Resolved in `AGENTS.md`; Stage 2 may evaluate `data/sample/*.md` with Gemini. |
| High | Later item 13 defers image publishing until the core stages finish. | `.github/workflows/release.yml` already pushes images to GHCR for `v*.*.*` tags and creates a release. | Decide whether this legacy workflow should be disabled until item 13. It was not changed in Stage 1. |
| High | CI runs on every push and pull request. | `.github/workflows/ci.yml` runs on pull requests and pushes to `main`, not pushes to every branch. | Clarify whether “every push” means every branch; then change the trigger in a dedicated CI commit if required. |
| High | `LLMProvider` is described as switchable by configuration alone. | One client/base URL/API key serves both chat and embeddings; Gemini chat plus Ollama embeddings cannot be expressed. `Vector(384)` is also fixed in the ORM. | ADR-0002's default is scheduled to be superseded in Stage 2. Treat provider/config separation as Stage 2 design work, not a hidden refactor. |
| High | `product.md` says ingestion stores a chunk “per section.” | `chunk_text()` has no Markdown section parser or section metadata; it uses blank-line paragraphs and character limits. | Correct the requirement wording or add real section behavior in its scheduled stage. Do not claim section-aware ingestion today. |
| Medium | `evaluation.md` calls citation matching “retrieval hit-rate.” | `scripts/evaluate.py` derives the result from final citations after thresholding and generation, not directly from ranked retrieval output. It cannot calculate MRR. | Stage 2 should separate retrieval evaluation from answer generation and add labeled rank data. Preserve old results as historical data. |
| Medium | `evaluation.md` presents the harness as a useful gate. | `run_eval()` records `CHECK` cases but always exits with status 0. | Add a non-zero failure exit as an explicit Stage 2 behavior change, alongside subset and retrieval-only modes. |
| Medium | `observability.md` discusses a future OpenTelemetry/metrics platform. | `AGENTS.md` now explicitly prohibits OpenTelemetry, Jaeger, Prometheus, Grafana, Elasticsearch, and new monitoring services. | Update observability roadmap wording when that document is next in scope; extend standard Python logging only. |
| Medium | Architecture previously said both ingest paths shared a chunk/embed/store core. | Only `_store_chunks()` is shared; both functions call `chunk_text()` and `embed_batch()` independently. | Corrected in `architecture.md`; consolidation is proposed below. |
| Low | README says CI has two jobs named `ci` and `frontend`. | CI now has `backend`, `docker`, and `frontend` jobs. | Update README in the next documentation scope; Stage 1 did not authorize editing it. |
| Low | Configuration comments link chunking/retrieval to ADR-0002/0003, and `.env.example` links providers to ADR-0001. | The governing records are ADR-0003 for chunking, ADR-0004 for retrieval, and ADR-0002 for providers. | Correct comments in a documentation-only cleanup commit after approval. |

The planned roadmap supersessions are not accidental mismatches: Stage 2 will supersede the
default-Ollama portion of ADR-0002, Stage 3 will supersede ADR-0003, and Stage 5 will supersede
ADR-0004. Those changes require new ADRs; the old ADR text must remain as historical evidence.

## Code inventory and risk ranking

### High risk

- `chunk_text()` can emit a chunk larger than `chunk_size` when a normal accumulated paragraph is
  followed by one oversized paragraph. It also has no validation for `overlap >= chunk_size`,
  which can make the hard-split range invalid. Existing tests cover an oversized paragraph only
  when it is the first/only paragraph.
- Upload/DB operations have no compensation across MinIO and PostgreSQL. Tests do not simulate a
  database failure after `put_object()` or after `delete_object()`.
- Content hash is not unique in the database. Concurrent identical uploads can pass the initial
  query and create duplicates; the current test is sequential only.
- The provider boundary does not validate returned embedding count/dimension. A model/config
  mismatch reaches pgvector/SQLAlchemy late, after external work has already occurred.
- `scripts/evaluate.py` has no unit tests and cannot fail its process for bad cases, so it is not
  yet a reliable regression gate.

### Medium risk

- `query()` is declared `async` but calls synchronous database and provider clients directly.
  A slow embedding/chat request blocks the event-loop worker. This is tolerable for the current
  local single-user workload, but it is an important concurrency constraint.
- The upload route reads the full body before enforcing the size limit. This is already disclosed
  and acceptable locally, but it must be revisited before internet-facing use.
- `status=ingesting` is committed before embedding. A process crash can leave that status until a
  user manually calls the ingest endpoint again; there is no automatic stale-job detection or
  recovery and no test for the manual retry path.
- An empty string returned by the chat provider is still reported as `grounded=true` with
  citations. Provider exceptions are logged, but malformed successful responses are not tested.
- Integration fixtures skip when PostgreSQL or MinIO is unavailable. Therefore
  `scripts/check.sh` can return success without running the full integration suite outside CI;
  the command does not distinguish an intentional unit-only run from a missing required service.
- Test uploads leave most generated objects in the MinIO bucket. Database rows are truncated, but
  object storage has no matching per-test cleanup.
- Error response non-leakage is listed as a gap in ADR-0008 and still lacks an API test.

### Low risk / maintainability

- `Settings.embedding_dimensions` is never used to define or validate the ORM vector dimension;
  `models.EMBEDDING_DIM` is the actual value. This looks configurable but is not.
- `Settings.host` and `Settings.port` are not consumed by application startup; Docker/uvicorn
  arguments currently own those values.
- `RetrievedChunk.chunk_index` is populated but unused by prompt construction, citations, or the
  API response. It may become useful for PDF metadata, but it is dead data in the current flow.
- `EvalCase.notes` contains useful explanations but the harness never prints or otherwise reads
  it.
- `_content_hash()` is only a string-to-bytes wrapper over `content_hash_bytes()`.
- `has_sufficient_evidence()` performs one threshold pass, followed immediately by a second pass
  in `answer_question()` to select qualifying chunks. A single helper returning qualifying chunks
  would make the invariant explicit.
- Structured logging has two local implementations (`answering._log_outcome()` and
  `documents._log_event()`) with different fields. Stage 2 must extend the existing logging path,
  not create a third system.

### Dead code, duplication, and abstraction assessment

- **Dead or currently unused:** `Settings.embedding_dimensions`, `Settings.host`,
  `Settings.port`, `RetrievedChunk.chunk_index`, and `EvalCase.notes` have no runtime consumer in
  the flow they appear to configure or describe. Some may be useful in a scheduled later stage,
  but that does not make the current surface truthful.
- **Duplicated logic:** CLI/API chunk-and-embed orchestration, the two threshold passes in
  `answer_question()`, and the two unrelated JSON logging helpers are the main duplication. The
  repeated TestClient fixture setup is small and readable; it does not yet justify a fixture
  factory.
- **Thin/extra abstractions:** `_content_hash()` and `has_sufficient_evidence()` add names without
  owning a meaningful policy independently of their caller. They are safe cleanup candidates.
- **Abstractions worth keeping:** `LLMProvider`, `ObjectStorage`, `answer_question()`, and
  `retrieve()` isolate external I/O or a real business rule. The repository currently has no
  service/repository class hierarchy to remove. Adding generic repositories, a parser registry,
  or a pipeline framework now would be the larger over-abstraction risk.

## Missing tests, ordered by value

1. Chunking boundary cases: an accumulated paragraph followed by an oversized paragraph; zero,
   equal, and greater-than-size overlap; exact boundary lengths.
2. Provider contract failures: wrong embedding count, wrong dimension, empty chat output, and
   429 retry behavior when Stage 2 adds retry.
3. MinIO/PostgreSQL partial failures and cleanup for upload/delete.
4. Concurrent duplicate upload and concurrent/repeated ingestion state transitions.
5. A check that required integration services cause the full check to fail rather than silently
   skip, while a separately named unit-only command remains available.
6. Evaluation harness unit tests for case selection, retrieval-only mode, hit rate@k, MRR, and
   non-zero exit on failed expectations (Stage 2).
7. Structured logging tests for request ID propagation, one event per required step, summary
   fields, and absence of secrets/content (Stage 2).
8. CLI invalid UTF-8/provider failure behavior and whether one bad file should stop the directory.
9. Error responses that prove stack traces, connection strings, object keys, and raw provider
   errors are not returned to clients.
10. Threshold boundary behavior (`similarity == threshold`) and ordering/citation correspondence
    with multiple documents.

## Deprecation warning from `TestClient`

Importing the currently locked Starlette test client emits this exact message:

```text
StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
```

Current locked versions are FastAPI 0.141.1, Starlette 1.5.0, and httpx 0.28.1. This warning does
not currently fail tests, but leaving it unresolved risks a future Starlette release removing the
fallback.

Proposed handling, in its own approved commit:

1. Add a small test/dependency compatibility spike using the existing `TestClient` fixtures.
2. Replace the development dependency `httpx` with the Starlette-recommended `httpx2` package,
   regenerate `uv.lock`, and change imports only if the installed FastAPI/Starlette API requires
   it. Do not suppress the warning.
3. Run one unit TestClient case, all API integration cases, then `scripts/check.sh`; confirm the
   warning is absent and all 40 tests execute rather than skip.
4. If FastAPI does not yet support that dependency combination, pin the last mutually supported
   FastAPI/Starlette/httpx set temporarily and record the pin reason. Do not blindly upgrade or
   silence warnings.

This is intentionally not implemented in Stage 1.

## Proposed behavior-preserving refactor sequence

Each step is independently reviewable and ends with `scripts/check.sh`. No step changes retrieval
ranking, prompt text, API schemas, status transitions, or evaluation numbers.

### R1 — Characterize current boundaries

- Add focused tests for current threshold/filter behavior and the two ingest paths producing the
  same chunk contents/embeddings for the same Markdown text.
- Add failure-path tests that pin current transaction/status behavior before moving functions.
- Keep known bugs (chunk boundary, storage compensation) out of characterization assertions;
  handle them as explicit bug fixes after the refactor.
- Commit only tests.

### R2 — Consolidate chunk and embed preparation

- Add one private ingestion helper that accepts decoded text, provider, and chunk settings and
  returns chunk strings plus embeddings.
- Make `ingest_file()` and `ingest_uploaded_document()` call it while retaining their distinct
  validation, document creation, status, and transaction responsibilities.
- Keep `_store_chunks()` as the single persistence loop; do not introduce parser registries or a
  generic pipeline framework before PDF requirements exist.

### R3 — Make evidence qualification single-source

- Replace the boolean-only `has_sufficient_evidence()` plus second list comprehension with one
  helper that returns qualifying chunks in retrieval order.
- Preserve inclusive `>= retrieval_similarity_threshold` behavior and the no-LLM refusal branch.
- Keep SQL retrieval and answer generation in their current modules.

### R4 — Thin the document router without adding a repository framework

- Extract upload/ingest/delete orchestration into a small document service module. Routes should
  own HTTP validation/status translation; the service should own MinIO + SQLAlchemy sequencing.
- Continue passing the SQLAlchemy `Session`, `ObjectStorage`, and provider explicitly. A repository
  class adds indirection without a second persistence implementation and is not justified yet.
- Keep `answering.py` as the query service and `retrieval.py` as the retrieval boundary; they are
  already appropriately separated.

### R5 — Remove or make truthful low-value surfaces

- Correct stale ADR references in code/config comments.
- Either remove unused configuration/data fields or wire them to a real owner; do not retain
  settings that only appear configurable. Treat `embedding_dimensions` separately in Stage 4
  because making it functional requires a schema migration.
- Update README CI job names and evaluation/observability wording only when those documents are
  explicitly in scope.

### R6 — Resolve test-client compatibility

- Apply the dedicated `httpx2` compatibility step above after confirming the supported dependency
  combination.
- Keep this separate from application refactors so a dependency-induced test failure has one
  obvious cause.

## Deliberately deferred behavior changes

The following are real work, but mixing them into a behavior-preserving refactor would hide their
impact: chunker boundary fixes; MinIO/database compensation; fail-fast full-check service
requirements; async/off-thread provider execution; stale-ingestion recovery; provider response
validation; Gemini/Ollama configuration split and 429 retry; request-correlated logging; retrieval
metrics; and evaluation exit semantics. Each belongs to a separately approved bug fix or its
scheduled stage with before/after tests and evaluation where applicable.

No refactor step should introduce LangChain, LangGraph, LlamaIndex, a repository framework,
background workers, or new observability services.
