# Software Requirements Specification

This project has reached the maturity level that justifies formal requirements (see
`docs/product.md`'s "Where this goes next"). Kept useful, not bureaucratic — requirements
describe outcomes/constraints, not technology choices (those belong in ADRs).

## Functional requirements

| ID | Requirement |
|---|---|
| FR-001 | The system must ingest `.md`/`.txt` documents from a directory, chunking and storing each chunk with its embedding. |
| FR-002 | Re-ingesting an unchanged document must not create duplicate chunks (content-hash-based idempotency). |
| FR-003 | An unsupported file type must be skipped with a clear log message, not raise an unhandled error. |
| FR-004 | `POST /query` must accept a natural-language question and return an answer plus source references. |
| FR-005 | The generated answer must be produced only from retrieved chunk content, not the model's unconstrained general knowledge. |
| FR-006 | Every citation in a response must correspond to a chunk actually retrieved for that question (document name + chunk id). |
| FR-007 | When retrieval similarity for all candidate chunks falls below a configured threshold, the system must return an explicit "insufficient evidence" response instead of generating an answer. |
| FR-008 | `/health` must report whether the vector index currently holds any content; `/ready` must report database reachability; `/live` must report process liveness. |

## Non-functional requirements

| ID | Requirement |
|---|---|
| NFR-001 | The full local stack must run via `make dev` using only local/free components — no paid API key required for development or CI. |
| NFR-002 | Switching the LLM/embedding provider (local vs. external) must require only configuration changes, never source code changes. |
| NFR-003 | Answer latency (question → response, 3-chunk context, local model, commodity hardware) is measured and recorded in `docs/evaluation.md` — target is a demo-usable experience (single-digit seconds), not a hard SLA. |
| NFR-004 | Secrets (API keys) must never be logged or committed; they are consumed only through the project's configuration boundary (`config.py`). |
| NFR-005 | The container image must run as a non-root user and expose functioning health/readiness endpoints suitable for an orchestrator or load balancer. |
| NFR-006 | Ingestion input must be validated for file extension and size before processing (basic defense against malformed/oversized uploads). |
| NFR-007 | Any cloud demo deployment must stay within a small documented monthly cost guardrail (see `docs/deployment.md`). |

## Traceability

| Story | Requirement | Validation |
|---|---|---|
| US-001 | FR-001 | integration test — ingestion end-to-end |
| US-001 | FR-002 | integration test — re-ingest idempotency |
| US-001 | FR-003 | unit test — unsupported extension |
| US-002 | FR-004, FR-005 | API test + evaluation case (groundedness) |
| US-003 | FR-006 | API test — citation correctness |
| US-004 | FR-007 | evaluation case — deliberately unanswerable question |
| US-005 | FR-008 | unit test (`/live`) + integration test (`/ready`, `/health` with DB) |

This is a lightweight traceability table, not a requirements-management system — it exists to
demonstrate discipline, not to generate paperwork overhead.
