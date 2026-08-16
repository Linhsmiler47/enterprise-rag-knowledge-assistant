# Product — Enterprise RAG Knowledge Assistant

The product/problem view — what this project is *for*, not how it's built. See
[`architecture.md`](architecture.md) for the engineering view.

> **Guardrail:** don't confuse a product requirement with a technology wishlist. "The system must
> return evidence/source references with an answer" is a requirement. "The system must use
> Kubernetes" is not — that's a technology decision, and belongs in `architecture.md` /
> `adr/`, justified on its own, not smuggled in here as if the product needed it.

## Problem

Engineering teams accumulate internal knowledge — runbooks, onboarding guides, incident response
policies, architecture notes — as scattered Markdown/text documents across wikis and repos. New
team members, and even experienced engineers, waste time searching multiple locations, and often
can't tell whether the document they found is current. Keyword search returns *documents*, not
*answers*, and gives no way to verify why an answer is correct.

## Target users

Engineers and technical staff on a small-to-mid-size engineering team who need fast, verifiable
answers to operational questions ("what's our database backup policy?", "how do I roll back a
bad deploy?") without hunting through multiple documents.

## Goals

- Answer natural-language questions using only the team's own indexed documents.
- Every answer shows which document(s) it came from.
- Clearly say "insufficient evidence" rather than inventing a plausible-sounding answer when the
  indexed knowledge doesn't cover the question.
- Be usable by someone who has never seen the codebase: `clone → setup → ingest → ask` (CLI) or
  `clone → setup → upload → ingest → ask` (product UI, Phase 2 — no CLI required).

## Non-goals

Still true as of Phase 2:

- Not a general-purpose chatbot — it only answers from indexed documents.
- Not a multi-turn conversational agent — single-question, single-answer.
- Not a document *authoring* tool — it indexes existing documents, it doesn't help write them.
- No PDF/Office document parsing — Markdown and plain text only (see
  [ADR-0003](adr/0003-ingestion-format-scope.md); Phase 3 scope, not started).
- No access control / multi-tenancy — assumes a single trusted knowledge base/user.
- No hybrid search, reranking, or query rewriting — see
  [ADR-0004](adr/0004-vector-only-retrieval-baseline.md) (Phase 4 scope, not started).
- No dashboards, user accounts, or document editing in the product UI (Phase 2 non-goals — see
  `docs/adr/0011-phase2-stack.md`).

## Main use cases

1. An operator points the system at a folder of internal Markdown/text documents (CLI), **or** a
   user uploads a document through the product UI; either way the system ingests, chunks,
   embeds, and stores it.
2. A user asks a question in plain language and receives an answer grounded in the indexed
   documents, with citations pointing to the specific source document(s).
3. A user asks something the knowledge base doesn't cover, and the system says so instead of
   guessing.
4. A user uploads a document through the UI, sees its status, and triggers ingestion themselves
   — without ever running a CLI command (Phase 2).

## User stories

```
US-001 — Knowledge ingestion
As a knowledge worker,
I want supported documents to be indexed,
so that their content becomes searchable.

US-002 — Grounded question answering
As a user,
I want answers grounded in indexed enterprise knowledge,
so that I can trust the response reflects our actual documentation.

US-003 — Source attribution
As a user,
I want the response to show supporting sources,
so that I can inspect the evidence myself.

US-004 — Insufficient evidence
As a user,
I want the system to indicate when evidence is insufficient,
rather than confidently inventing an answer.

US-005 — Operational health
As an operator,
I want to know whether the service and its database are ready,
so that I can trust an "unavailable" answer isn't silently swallowed as "no evidence."

US-006 — Document upload (Phase 2)
As a non-technical user,
I want to upload a document through a web UI,
so that I don't need CLI/terminal access to add knowledge to the system.

US-007 — Document management (Phase 2)
As a user,
I want to see my uploaded documents and their ingestion status,
so that I know whether a document is actually searchable yet, or why it isn't.

US-008 — Manual ingestion trigger (Phase 2)
As a user,
I want to explicitly trigger ingestion of an uploaded document,
so that upload and indexing are separate, inspectable steps rather than one opaque action.
```

## Acceptance criteria

```
US-001
- Given a directory of .md/.txt files, running ingestion stores a chunk + embedding
  per section in the database
- Re-running ingestion on the same document does not create duplicate chunks (idempotent)
- An unsupported file type is skipped with a clear log message, not a crash

US-002
- Given a question whose answer exists in the indexed documents, the API returns a natural-
  language answer that reflects that content
- The answer is generated only from retrieved chunks, not the model's general knowledge
  (checked in evaluation, not just asserted)

US-003
- Every successful answer includes at least one source reference (document name + chunk id)
- Source references correspond to chunks that were actually retrieved for that question

US-004
- Given a question with no relevant indexed content, the API returns an explicit
  "insufficient evidence" response instead of a fabricated answer
- This behavior is covered by an evaluation case, not just a code comment

US-005
- /ready returns 503 if the database is unreachable
- /health reports whether the vector index currently has any indexed content

US-006
- Given a supported file (.md/.txt) under the size limit, uploading it through the UI stores the
  original file and creates a document record with status "uploaded"
- An unsupported file type or oversized file is rejected with a clear error, not a crash
- Uploading identical content twice does not create a duplicate document (idempotent, same
  content-hash philosophy as CLI ingestion)

US-007
- The Documents page lists every uploaded/ingested document with its current status
- A failed ingestion shows a reason, never a raw stack trace or internal path
- Deleting a document removes it (and its chunks) from future answers/citations

US-008
- Triggering ingestion on an "uploaded" document transitions it through ingesting -> ingested
  (with a chunk count) or ingesting -> failed (with a reason)
- Triggering ingestion again on an already-ingested document is a no-op, not a duplicate index
- A grounded answer after upload-ingestion cites the uploaded document by its display name
```

## Success criteria

- A new developer can go from `git clone` to a working ingest + answered question using only
  free/local components (no paid API key required).
- The evaluation harness (`docs/evaluation.md`) shows measured, non-zero retrieval hit-rate and
  groundedness on a small curated question set — not aspirational numbers.
- The project reaches L4 (portfolio-ready): a third party can understand what it does, how it
  works, how it's tested, how it's evaluated, and how it deploys, from the repo alone.

## Where this goes next

Phase 2 (this document's US-006/007/008) is the product UI/upload/storage phase. See "Potential
future evolution" at the end of [`architecture.md`](architecture.md) for Phase 3+ (multi-format
ingestion, advanced retrieval, guardrail/eval hardening, and beyond) — none of it is in Phase 2
scope.

`docs/srs.md`, `docs/evaluation.md`, `docs/runbook.md`, and `docs/deployment.md` are all present
for this project (unlike the template baseline) because it has reached the maturity level that
justifies them.
