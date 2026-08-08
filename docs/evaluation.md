# Evaluation

Real, measured results from `make eval` (`scripts/evaluate.py`), run against the live system —
real PostgreSQL/pgvector, real Ollama (`qwen2.5:0.5b` chat, `all-minilm` embeddings), the sample
knowledge base in `data/sample/`. Not the test fakes used in CI (see
[ADR-0005](adr/0005-evaluation-approach.md) for why those are separate).

## Why a simple harness instead of RAGAS

A framework like RAGAS adds real value once an LLM-as-judge and a larger eval set are in play.
For a 10-case v1 set with a locally-run model, a transparent harness that measures exactly what
`docs/product.md`'s acceptance criteria require — and that anyone can read in five minutes — was
judged more valuable than a framework dependency that would need its own justification. See
[ADR-0005](adr/0005-evaluation-approach.md).

## Eval set

10 curated questions (`scripts/evaluate.py::EVAL_SET`) against the four sample documents:
8 answerable (with a known correct source document and expected answer keywords) and 2
deliberately unanswerable (topics absent from the knowledge base — parental leave policy,
microservice language standard).

## Results — run on 2026-08-08

| Metric | Result |
|---|---|
| Groundedness accuracy (grounded=True/False matches expectation) | **10/10 (100%)** |
| Retrieval hit-rate (citation points at the correct source document) | **8/8 (100%)** |
| Answer keyword presence (answer contains an expected fact keyword) | **8/8 (100%)** |
| Latency — min | 0.05s (insufficient-evidence cases short-circuit before calling the LLM) |
| Latency — max | 6.56s (first real generation call — cold start) |
| Latency — avg | 2.93s |

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

- 10 cases is enough to validate the harness and catch gross regressions, not enough to be
  statistically meaningful. Expanding this is explicit v0.2 scope.
- All questions are single-hop, single-document — no case requires synthesizing across multiple
  documents.
- The embedding model (`all-minilm`, 384-dim) is small and English-only; a real production
  knowledge base with more nuanced or multilingual content would need re-evaluation with a larger
  embedding model.
