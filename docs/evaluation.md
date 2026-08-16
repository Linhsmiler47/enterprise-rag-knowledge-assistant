# Evaluation

Real, measured results from `make eval` (`scripts/evaluate.py`), run against the live system —
real PostgreSQL/pgvector, real Ollama (`qwen2.5:0.5b` chat, `all-minilm` embeddings), the sample
knowledge base in `data/sample/`. Not the test fakes used in CI (see
[ADR-0005](adr/0005-evaluation-approach.md) for why those are separate).

## Phase 2 evaluation impact

`make eval` is unchanged and keeps ingesting via the CLI/directory path — evaluation
reproducibility shouldn't depend on the UI. Per the Phase 2 approval, the only addition is a
spot-check (not a new automated benchmark) that citations still resolve correctly for a document
that entered through *upload* rather than the CLI: verified via
`test_query_after_upload_ingestion_cites_uploaded_document` (automated, `tests/integration/`,
fake LLM provider) and, separately, a live manual check against the real containerized stack
(Postgres + MinIO + app) confirming an uploaded document reaches `status: "ingested"` and its
citation appears correctly in a live `/query` response. The v0.1 baseline below is untouched.

## Why a simple harness instead of RAGAS

A framework like RAGAS adds real value once an LLM-as-judge and a larger eval set are in play.
For a 10-case v1 set with a locally-run model, a transparent harness that measures exactly what
`docs/product.md`'s acceptance criteria require — and that anyone can read in five minutes — was
judged more valuable than a framework dependency that would need its own justification. See
[ADR-0005](adr/0005-evaluation-approach.md).

## RAG KPI / metric framework

A layered view of what "quality" means for this system, and which layer each existing/planned
metric belongs to. This is a reorganization of what the harness already measures, plus an honest
accounting of what it *doesn't yet* measure — no numbers below are invented; anything not
currently measurable says so explicitly.

| Layer | Metric | Measured today? | Source |
|---|---|---|---|
| Retrieval | Hit-rate (correct source document cited) | ✅ | `scripts/evaluate.py` |
| Retrieval | Retrieval-only latency (isolated from generation) | ❌ not yet | needs the timing split added in this change (see below) |
| Retrieval | Recall@K / ranked-relevance metrics (MRR, NDCG) | ❌ not yet | blocked on a dataset with multiple labeled-relevant chunks per question; current cases label one expected document each, not a ranked relevance set |
| Generation | Groundedness (answer matches expected answerable/not) | ✅ | `scripts/evaluate.py` |
| Generation | Answer keyword presence (proxy for factual correctness) | ✅ | `scripts/evaluate.py` |
| Generation | Unsupported-elaboration rate | ⚠️ partial — caught once by manual read (EVAL-004 below), not by an automated check | no metric yet |
| Abstention | Correct refusal rate (unanswerable question → insufficient-evidence response) | ✅ | folded into groundedness accuracy today (2/2 unanswerable cases) |
| Abstention | False-refusal rate (answerable question wrongly refused) | ✅ | folded into groundedness accuracy today (0/8 so far) |
| Guardrail | Prompt-injection resistance (question tries to override system instructions) | ✅ *(new this change)* | `scripts/evaluate.py` — see EVAL-011/012 below |
| Operational | End-to-end latency | ✅ | `scripts/evaluate.py` |
| Operational | Retrieval-only / generation-only latency split | ❌ not yet | needs the timing split added in this change |
| Operational | Indexed chunk/doc count, error rate by category | ❌ not yet | needs the structured logging added in this change — see `docs/observability.md` |

Retrieval-only/generation-only latency and structured operational fields are being added to the
application's logging in this change (`docs/observability.md`), but are not yet aggregated back
into this evaluation report — that aggregation is future work, not claimed here.

## Eval set

12 curated questions (`scripts/evaluate.py::EVAL_SET`), organized by category:

| Category | Cases | Purpose |
|---|---|---|
| Direct factual (answerable) | EVAL-001 – EVAL-008 | Retrieval hit-rate + groundedness against the 4 sample documents |
| Unanswerable | EVAL-009, EVAL-010 | Abstention — confirms no fabricated answer for out-of-corpus questions |
| Prompt injection (question-borne) | EVAL-011, EVAL-012 | Guardrail — confirms an adversarial question can't override the system prompt or extract it |

The prompt-injection category tests only injection carried in the *user's question*. Injection
carried inside a *retrieved document* (a poisoned knowledge-base entry) is a related but distinct
risk — not yet covered by a dataset case, since it requires a dedicated fixture document rather
than a question change; tracked as backlog, not silently assumed safe (see
`docs/adr/0008-guardrail-baseline.md`).

## Results — run on 2026-08-08 (EVAL-001 – EVAL-010, 10 cases)

| Metric | Result |
|---|---|
| Groundedness accuracy (grounded=True/False matches expectation) | **10/10 (100%)** |
| Retrieval hit-rate (citation points at the correct source document) | **8/8 (100%)** |
| Answer keyword presence (answer contains an expected fact keyword) | **8/8 (100%)** |
| Latency — min | 0.05s (insufficient-evidence cases short-circuit before calling the LLM) |
| Latency — max | 6.56s (first real generation call — cold start) |
| Latency — avg | 2.93s |

**EVAL-011 and EVAL-012 (prompt injection) were added in this change and have not yet been run
against the live system in this environment** (no local Ollama/Docker stack available here — see
`docs/observability.md`'s note on where this work was done). They are covered by the CI unit test
suite's fake-provider path (asserting the system prompt is never overridden), but the *live*
groundedness/latency numbers above predate them. Re-run `make eval` after pulling this change and
update this table with the 12-case result — do not treat the 10/10 figure above as covering the
new cases.

Full per-case output (question, answer, latency) is reproducible by running `make eval` — not
reproduced here beyond the summary to avoid this document going stale relative to the actual
harness.

## What this does and doesn't prove

**Proves:** on a small, clean, single-domain sample set, the vector-retrieval-only baseline
(ADR-0004) reliably retrieves the correct document, and the "insufficient evidence" path (FR-007)
correctly refuses to answer questions the knowledge base doesn't cover — it was never observed to
fabricate an answer for the two unanswerable cases across repeated runs.

**Does not prove:** performance on a larger, messier, multi-domain knowledge base; behavior under
ambiguous questions with partial evidence; retrieval quality once documents have overlapping or
contradictory content. These are exactly the conditions hybrid retrieval/reranking (v0.2 roadmap)
would be evaluated against.

## Observed failure mode (disclosed, not hidden)

For EVAL-004 ("How should I roll back a bad production deployment?"), while the citation and
core answer were correct, `qwen2.5:0.5b` occasionally pads its answer with invented
implementation detail not present in the source context (e.g., a fabricated YAML snippet) — the
grounded *facts* were correct, but the model added unrequested elaboration beyond the retrieved
evidence. This is a known limitation of a 0.5B-parameter local model, not a retrieval failure —
the correct chunks were retrieved and cited; the generation step over-elaborated. Documented here
rather than cleaned up out of the record. A larger chat model (still local, e.g. a 3B-parameter
model, or `LLM_PROVIDER=openai`) would be the first thing to try if this needs tightening — see
the v0.2 roadmap in `architecture.md`.

## Limitations of the eval set itself

- 12 cases is enough to validate the harness and catch gross regressions, not enough to be
  statistically meaningful. Expanding this is explicit v0.2 scope.
- All questions are single-hop, single-document — no case requires synthesizing across multiple
  documents.
- The embedding model (`all-minilm`, 384-dim) is small and English-only; a real production
  knowledge base with more nuanced or multilingual content would need re-evaluation with a larger
  embedding model.
