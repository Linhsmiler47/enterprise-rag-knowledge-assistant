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
- Be usable by someone who has never seen the codebase: `clone → setup → ingest → ask`.

## Non-goals (v1)

- Not a general-purpose chatbot — it only answers from indexed documents.
- Not a multi-turn conversational agent — v1 is single-question, single-answer.
- Not a document *authoring* tool — it indexes existing documents, it doesn't help write them.
- No PDF/Office document parsing in v1 — Markdown and plain text only (see
  [ADR-0003](adr/0003-ingestion-format-scope.md)).
- No access control / multi-tenancy — v1 assumes a single trusted knowledge base.
- No hybrid search, reranking, or query rewriting in v1 — see
  [ADR-0004](adr/0004-vector-only-retrieval-baseline.md).

## Main use cases

1. An operator points the system at a folder of internal Markdown/text documents; the system
   ingests, chunks, embeds, and stores them.
2. A user asks a question in plain language and receives an answer grounded in the indexed
   documents, with citations pointing to the specific source document(s).
3. A user asks something the knowledge base doesn't cover, and the system says so instead of
   guessing.

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
```

## Success criteria

- A new developer can go from `git clone` to a working ingest + answered question using only
  free/local components (no paid API key required).
- The evaluation harness (`docs/evaluation.md`) shows measured, non-zero retrieval hit-rate and
  groundedness on a small curated question set — not aspirational numbers.
- The project reaches L4 (portfolio-ready): a third party can understand what it does, how it
  works, how it's tested, how it's evaluated, and how it deploys, from the repo alone.

## Where this goes next

See "Future roadmap" at the end of [`architecture.md`](architecture.md) for v0.2+ (hybrid
retrieval, async ingestion, observability, MCP, A2A) — none of it is in v1 scope.

`docs/srs.md`, `docs/evaluation.md`, `docs/runbook.md`, and `docs/deployment.md` are all present
for this project (unlike the template baseline) because it has reached the maturity level that
justifies them.
