# ADR-0004 — Vector-Only Retrieval Baseline

**Status:** Accepted

## Context

Production RAG systems often use hybrid retrieval (dense vector + keyword/BM25), reranking, and
query rewriting to improve accuracy. Implementing all of that before having any measured baseline
would mean optimizing blind — no way to know which technique actually helps *this* knowledge base
and question set.

## Decision

v1 retrieval is plain cosine-similarity top-k search over pgvector (`retrieval.py`) — no hybrid
search, no reranking, no query rewriting. A configurable similarity threshold
(`retrieval_similarity_threshold`) determines whether retrieved evidence is sufficient to attempt
an answer at all (FR-007).

The measured baseline (`docs/evaluation.md`: 100% retrieval hit-rate on the 10-case eval set)
gives a real number to compare future retrieval improvements against — that comparison is the
actual point of establishing a baseline first.

## Alternatives considered

- **Hybrid search from day one**: rejected — no baseline to prove it helps, and it roughly
  doubles retrieval-path complexity (a keyword index alongside the vector index, a fusion
  strategy) for unmeasured benefit on a 4-document sample set.
- **Reranking from day one**: rejected — same reasoning; adds a second model call per query with
  unmeasured benefit at this scale.

## Consequences

- Retrieval quality on a larger, messier, or multi-domain knowledge base is unproven — the
  eval set explicitly does not claim otherwise (see `evaluation.md`'s "what this doesn't prove").
- Architecture doesn't preclude adding hybrid/reranking later — `retrieve()`'s return type
  (`list[RetrievedChunk]`) is already the right shape to insert a reranking step in front of.

## Revisit conditions

Add hybrid retrieval/reranking as v0.2 roadmap once the eval set is large/varied enough that a
measured accuracy gap actually shows up — not preemptively.
