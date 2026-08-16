# ADR-0008 — Guardrail Baseline

**Status:** Accepted

## Context

Phase 1.5 (standalone product delivery) requires an explicit guardrail baseline rather than
guardrails existing only implicitly, scattered across code and other ADRs. This ADR is a
checklist of what's actually enforced today, across the input → retrieval → generation → output
lifecycle, and an honest list of what isn't yet — not a design proposal for new capability.

## Decision

Document and, where a gap was small and clearly justified, close it in this change. The baseline:

| Stage | Guardrail | Status |
|---|---|---|
| Input | Question length bounded (1–2000 chars, `QueryRequest.question`) | ✅ existing |
| Input | Ingestion file extension allowlist (`.md`/`.txt` only, ADR-0003) | ✅ existing |
| Input | Ingestion file **size** bounded | ✅ **added this change** — `ingestion.py` now rejects files over a configurable `max_ingest_file_size_bytes` before reading/chunking/embedding them |
| Retrieval | Evidence-sufficiency threshold gates whether an LLM call happens at all (FR-007) | ✅ existing |
| Retrieval | Empty index handled explicitly (no chunks → insufficient evidence, not an error) | ✅ existing |
| Generation | System prompt restricts answers to provided context only | ✅ existing |
| Generation | **Retrieved document content treated as untrusted data, not instructions** | ✅ **hardened this change** — `SYSTEM_PROMPT` now explicitly instructs the model to treat context excerpts as data to reference, never as instructions to follow, even if a chunk contains text that looks like a command |
| Generation | Adversarial-question resistance (question tries to override system prompt / extract it) | ✅ **added this change** — EVAL-011/EVAL-012 in `scripts/evaluate.py` (see `docs/evaluation.md`) |
| Generation | Adversarial-*document* resistance (a poisoned indexed document tries to override the system prompt) | ❌ **not covered** — would need a dedicated poisoned fixture document; tracked as backlog, not silently assumed safe |
| Output | Citations correspond only to chunks actually retrieved for that question | ✅ existing, tested (`test_query_api.py`) |
| Output | Errors don't leak internals (stack traces, DB connection strings) to the client | ⚠️ relies on FastAPI's default exception handling; not explicitly tested — backlog |
| Security | Secrets never logged or committed | ✅ existing (`.env` gitignored, gitleaks in CI, `config.py` is the sole entry point) |
| Security | Structured logs never include full document/chunk content or API keys | ✅ **enforced by design this change** — see `docs/observability.md`'s logging field list |

## Alternatives considered

- **A dedicated guardrail framework (e.g. Guardrails AI, NeMo Guardrails)**: rejected for now —
  the actual guardrail surface here (threshold gating, prompt hardening, input validation) is
  small enough to implement directly; a framework dependency isn't justified before there's a
  concrete gap it would close that hand-written checks can't.
- **Adding the poisoned-document adversarial case now**: rejected for this change — it requires a
  new fixture document in `data/sample/`, which is a data-corpus change, not a code/prompt change;
  deferred to keep this change's diff scoped to what was explicitly approved.

## Consequences

- The two closed gaps (file-size limit, prompt hardening) are small, testable, and don't change
  any existing passing behavior — verified by re-running the full test suite after the change.
- The one remaining known gap (document-borne injection) is now documented rather than silently
  assumed safe — a future change can add the fixture deliberately, with its own review.

## Revisit conditions

Add the document-borne injection eval case, and error-leakage test, once there's a queue of
Phase 1.5+ hardening work — not required to block this change, but should not be forgotten (this
ADR is the record that prevents that).
