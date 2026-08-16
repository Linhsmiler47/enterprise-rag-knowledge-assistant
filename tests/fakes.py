"""Deterministic fake LLM provider for integration tests.

Integration tests run against a real Postgres/pgvector (available as a CI service container),
but do NOT depend on a live Ollama/OpenAI endpoint -- that would make CI slow and flaky for no
benefit, per docs/conventions and the workspace's "don't make CI depend on external services"
guidance. The embedding is a real (if crude) bag-of-words hash so that word-overlapping texts
retrieve as more similar than unrelated ones -- meaningful enough to test retrieval logic without
a real model. Real-model behavior is exercised separately by `make eval` (see docs/evaluation.md).
"""

import hashlib
import math
import re

from enterprise_rag_knowledge_assistant.models import EMBEDDING_DIM

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _fake_embed_one(text: str) -> list[float]:
    vec = [0.0] * EMBEDDING_DIM
    tokens = _TOKEN_RE.findall(text.lower())
    for token in tokens:
        idx = int(hashlib.sha256(token.encode()).hexdigest(), 16) % EMBEDDING_DIM
        vec[idx] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


class FakeLLMProvider:
    def __init__(self, canned_answer: str = "Based on the provided context, here is the answer."):
        self._canned_answer = canned_answer
        self.chat_calls: list[tuple[str, str]] = []

    @property
    def provider_name(self) -> str:
        return "fake"

    @property
    def chat_model(self) -> str:
        return "fake-chat"

    @property
    def embedding_model(self) -> str:
        return "fake-embed"

    def embed(self, text: str) -> list[float]:
        return _fake_embed_one(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [_fake_embed_one(t) for t in texts]

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        self.chat_calls.append((system_prompt, user_prompt))
        return self._canned_answer
