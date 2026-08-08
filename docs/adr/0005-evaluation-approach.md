# ADR-0005 — Evaluation Approach: Simple Harness Over RAGAS

**Status:** Accepted

## Context

`docs/product.md` requires measurable evaluation (retrieval hit-rate, groundedness). RAGAS and
similar frameworks are the common industry choice, but typically require an LLM-as-judge call per
metric per case — for a 10-case v1 set running against a local 0.5B model, that adds real
complexity and another point of failure (judge-model availability/cost) for marginal benefit over
directly checking the properties the acceptance criteria actually require.

## Decision

`scripts/evaluate.py` is a small, transparent, dependency-light harness: a curated list of
`EvalCase`s (question, expected answerable/not, expected source document, expected answer
keywords), run against the *live* system (real DB, real provider — not test fakes), measuring
groundedness accuracy, retrieval hit-rate, keyword presence, and latency directly — no
LLM-as-judge, no external eval service.

Results are recorded as real numbers in `docs/evaluation.md`, run on a specific date, with
disclosed failure modes — not aspirational or fabricated.

## Alternatives considered

- **RAGAS**: rejected for v1 — adds an LLM-judge dependency and configuration surface that isn't
  justified at 10 cases; revisit once the eval set is large enough that manual keyword/citation
  checks stop scaling.
- **No evaluation, just manual spot-checking**: rejected — `docs/product.md`'s success criteria
  explicitly require measured, non-aspirational numbers; unstructured spot-checking wouldn't be
  reproducible or trackable across changes.

## Consequences

- `make eval` is fast (~30s for 10 cases with a 0.5B local model) and has zero external
  dependencies beyond the already-running local stack.
- The harness measures exactly what the acceptance criteria in `product.md`/`srs.md` require
  (groundedness, citation correctness, insufficient-evidence handling) — nothing more
  sophisticated than needed, nothing less than required.
- Does not produce nuanced quality scores (e.g. faithfulness/relevancy on a continuous scale) that
  RAGAS-style frameworks provide — a real tradeoff, not free.

## Revisit conditions

Adopt RAGAS or a similar framework once the eval set grows large enough (dozens+ of cases,
multiple domains) that keyword/citation matching stops being a reliable enough signal — that's an
explicit v0.2 trigger, not an indefinite deferral.
