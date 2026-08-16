# ADR-0011 — Phase 2 Stack: Next.js + MinIO

**Status:** Accepted

## Context

Phase 2's business question is whether a non-technical user can upload documents, manage them,
and ask grounded questions through a product UI, without the CLI. That requires two new pieces
the v0.1 backend doesn't have: a web UI, and somewhere to store the original uploaded files
(the backend only ever stored derived chunks/embeddings, never the source file itself).

## Decision

**UI: Next.js (App Router, TypeScript), minimal.** Three pages (Upload, Documents, Ask), a thin
`fetch`-based API client (`frontend/lib/api.ts`), no state-management library, no component
library, no authentication, no dashboards.

**Storage: MinIO**, as a new local Docker Compose service, holding raw uploaded files. PostgreSQL
keeps everything it already held (document metadata, ingestion status, chunks, pgvector
embeddings) — MinIO only adds the one thing Postgres was never meant to hold well: file blobs.

## Alternatives considered

**UI:**
- **Streamlit**: rejected — fastest to build, but reads as a prototype; the project's existing
  ADR/SRS/evaluation discipline is explicitly building a "real product" portfolio story that a
  Streamlit UI would undercut.
- **Gradio**: rejected — strong for single-model demos, weak for document management (list,
  status, delete) which is half of Phase 2's actual scope.
- **Plain FastAPI HTML templates**: rejected — no meaningful advantage over Next.js for this
  scope, and a real frontend framework is a stronger, more representative portfolio signal.

**Storage:**
- **Local filesystem**: rejected — simplest, but not container-portable in the way the rest of
  this stack already is (app/db both run as containers with volumes; a bind-mounted upload
  directory would be the odd one out), and doesn't carry the same story: MinIO speaks the same S3
  API that Azure Blob/AWS S3 do, so swapping to a real cloud object store later is a config
  change, not a rewrite — the same provider-boundary philosophy as `providers.py` (ADR-0002).
- **PostgreSQL `bytea`**: rejected — mixes raw file storage into the same database that holds
  the vector index; not how a real document-management system would be built, and no benefit at
  this scale to justify the mixing.
- **Cloud object storage now**: rejected — pulls in a cloud dependency before ADR-0010's
  local-first decision would allow it.

## Consequences

- A new local service dependency (MinIO) joins Postgres/Ollama — another thing that must be
  running for the product path to work (documented in `docs/local-development.md`, with the same
  "service unreachable" troubleshooting pattern already used for Ollama).
- A second toolchain (Node/npm) enters the repo and CI (`frontend/`, a new `frontend` CI job) —
  real added surface area, accepted because it's the toolchain a product-quality UI actually
  requires.
- The `Document` data model changes from filename-uniqueness to `object_key`-uniqueness to
  support uploads (see `models.py`, `docs/architecture.md`) — a direct consequence of adding a
  second ingestion entry point (upload) alongside the CLI's.
- Local/dev-only MinIO credentials (`.env.example`) are never valid credentials for anything but
  a developer's own machine or CI service container — no real deployment uses them (ADR-0010).

## Revisit conditions

Revisit the UI choice only if the product's frontend needs outgrow "three simple pages" (Phase 2
non-goals already rule out dashboards/auth for now). Revisit storage only if a Phase 10 cloud
deployment specifically needs a managed object store swap — expected to be a config change given
MinIO's S3-API compatibility, not a new ADR by itself unless something unexpected forces a design
change.
