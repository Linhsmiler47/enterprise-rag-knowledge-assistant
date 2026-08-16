# Observability Baseline

This is a **structured logging baseline**, not a full observability platform. There is no
OpenTelemetry tracing, no metrics backend (Prometheus/Grafana), no log aggregation pipeline
(ELK/Loki), and no distributed tracing here yet — those are explicit v0.4 roadmap
(`docs/architecture.md`), out of scope for Phase 1.5. What exists today is enough to answer "what
happened on this request?" from `docker logs` / the deployment platform's log stream, and nothing
more.

## What's logged today

`answering.py::answer_question()` emits exactly one structured JSON log line (`logging.info`) per
call, regardless of outcome:

```json
{
  "event": "query_answered",
  "outcome": "grounded",
  "error_category": null,
  "retrieved_chunk_count": 3,
  "evidence_sufficient": true,
  "llm_provider": "ollama",
  "chat_model": "qwen2.5:0.5b",
  "embedding_model": "all-minilm",
  "retrieval_seconds": 0.0412,
  "generation_seconds": 1.883,
  "total_seconds": 1.9265
}
```

| Field | Meaning |
|---|---|
| `outcome` | `"grounded"` \| `"insufficient_evidence"` \| `"error"` |
| `error_category` | `null` on success, else `"retrieval_error"` or `"generation_error"` |
| `retrieved_chunk_count` | How many chunks came back from `retrieve()` |
| `evidence_sufficient` | Whether the similarity threshold was cleared (FR-007) |
| `llm_provider` / `chat_model` / `embedding_model` | Which provider/model answered this request |
| `retrieval_seconds` / `generation_seconds` / `total_seconds` | Latency breakdown — lets you tell a slow retrieval apart from a slow generation, which `docs/evaluation.md`'s harness-level latency alone can't |

`ingestion.py` and `cli.py` keep their existing plain-text `logging.info`/`logging.warning` lines
(ingested/unchanged/skipped/oversized per file) — not restructured in this change; they're
operator-facing CLI output, not the request-path observability this baseline targets.

## What is never logged

Per [ADR-0008](adr/0008-guardrail-baseline.md): the question text, the answer text, and any
document/chunk content are never included in these log lines — only counts, flags, timings, and
model identifiers. API keys and other secrets are never logged anywhere in this codebase (they
flow only through `config.py` into the provider client, never through `logging`).

## How to use this today

```bash
make dev
# ... make a query ...
docker compose -f deploy/local/docker-compose.yml logs app | grep query_answered
```

Each line is valid JSON (grep the surrounding uvicorn log line for the JSON payload) — parseable
with `jq` if you pipe the raw JSON portion, though no log-shipping pipeline packages that up
automatically yet.

## What this doesn't give you (honestly)

- No cross-request tracing/correlation ID — can't yet follow one request across retrieval →
  generation as a single trace object (would need at minimum a request ID threaded through, which
  is a reasonable v0.4/OpenTelemetry-adjacent next step, not done here).
- No aggregation — "average generation_seconds over the last hour" requires reading raw logs
  yourself; no metrics endpoint or dashboard exists.
- No alerting on error rate or latency.
- No sampling/redaction policy beyond "never log content" — at low request volume this is fine;
  it would need revisiting before any real production traffic.

## Diagram

[`docs/diagrams/observability-baseline.excalidraw`](diagrams/observability-baseline.excalidraw)
shows this baseline (top row, solid) against the future OpenTelemetry platform it's explicitly not
yet (bottom row, dashed).

## Revisit conditions

Add request correlation IDs and a `/metrics` endpoint (or OTel SDK) once there's an actual
consumer for them (a real deployment with more than a handful of daily requests, or a concrete
debugging need this log format can't satisfy) — not preemptively. See `docs/architecture.md`'s
v0.4 roadmap entry.
