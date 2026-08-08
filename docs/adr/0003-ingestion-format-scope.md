# ADR-0003 — Ingestion Format Scope: Markdown/Text Only (v1)

**Status:** Accepted

## Context

Real enterprise knowledge lives in many formats (PDF, Office documents, wiki exports, Markdown).
Supporting all of them well (layout-aware PDF extraction, table handling, OCR for scans) is a
substantial engineering effort on its own — the "every file format" trap flagged explicitly in
the workspace's own approved planning.

## Decision

v1 ingestion supports `.md` and `.txt` only (`ingestion.SUPPORTED_EXTENSIONS`). Any other
extension is skipped with a log message (FR-003), never crashes ingestion of the rest of the
directory.

This is a legitimate, common enterprise case: internal runbooks, wikis, and READMEs are very
often already Markdown or plain text — this isn't a toy restriction, it's a real, common source
format.

## Alternatives considered

- **PDF support from day one** (via `pypdf`/`unstructured`): rejected for v1 — meaningfully
  larger dependency footprint and real parsing-quality tradeoffs (layout, tables, scanned pages)
  that deserve their own evaluation, not a rushed first pass bundled into the initial pilot.
- **Support everything via a generic "text extraction" library**: rejected — such libraries
  still produce format-specific quality issues; claiming universal support without evaluating
  each format would be dishonest about actual quality.

## Consequences

- The sample knowledge base (`data/sample/`) is entirely Markdown, so this scope isn't a
  demonstrated limitation in the current demo — but it is a real limitation for any team whose
  knowledge lives in PDF/Office formats today.
- `docs/product.md` states this explicitly as a non-goal, not an oversight.

## Revisit conditions

Add PDF/Office parsing as v0.3 roadmap (see `architecture.md`) once there's a concrete document
set to validate extraction quality against — not speculatively.
