# ADR-0002 — LLM/Embedding Provider Boundary

**Status:** Accepted

## Context

`strategy/PORTFOLIO_TECH_STACK.md` (workspace root) argues for LLM-provider portability — the
application shouldn't be locked to one vendor. We have no paid API credentials available, but
want the system to work end-to-end without one, while still supporting a real external provider
later without code changes.

## Decision

`LLMProvider` wraps the `openai` Python SDK, configured entirely via `config.py`
(`llm_base_url`, `llm_api_key`, `llm_chat_model`, `llm_embedding_model`). Both the default local
provider (Ollama, which exposes an OpenAI-compatible API at `/v1`) and an external provider
(real OpenAI) use the exact same client class — only configuration differs. Switching providers
is `LLM_PROVIDER`/`LLM_BASE_URL`/`LLM_API_KEY` changes, never a code change.

Default: `ollama`, `qwen2.5:0.5b` (chat), `all-minilm` (embeddings, 384-dim) — both small enough
to run on commodity hardware without a GPU.

## Alternatives considered

- **A full multi-provider abstraction framework** (separate SDKs/adapters per vendor): rejected
  — every provider we'd realistically use (Ollama, OpenAI, and most others) speaks the same
  OpenAI-compatible wire protocol; a framework abstracting *that* away would be solving a problem
  we don't have.
- **LangChain/LlamaIndex provider abstraction**: rejected for v1 — pulls in a large dependency
  tree for a boundary that's ~40 lines of code without it. Revisit if orchestration complexity
  (agents, multi-step chains) grows enough to justify the dependency.
- **Hardcoding OpenAI only**: rejected — would make local development and CI depend on a paid
  API key, violating NFR-001.

## Consequences

- `embed()`/`embed_batch()`/`chat()` are the entire provider surface. Any OpenAI-compatible
  endpoint (Ollama, OpenAI, and others) works without modification.
- Embedding dimension (384) is coupled to the specific embedding model
  (`all-minilm`) via `models.EMBEDDING_DIM`; changing embedding model requires a matching schema
  change (re-embed existing content) — not just a config flip. This is a real, disclosed
  limitation, not hidden.
- Tests never call a live provider (see [ADR-0005](0005-evaluation-approach.md)) — `FakeLLMProvider`
  implements the same three-method interface.

## Revisit conditions

If a provider that doesn't speak the OpenAI-compatible API becomes necessary (e.g. a
vendor-specific SDK required for a feature this boundary can't express), add a second adapter
class behind the same three-method interface — don't generalize preemptively before that's real.
