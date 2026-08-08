"""LLM/embedding provider boundary.

Deliberately narrow: both "ollama" (local, default) and "openai" (external) speak the same
OpenAI-compatible HTTP API, so one client class handles both — only base_url/api_key/model
differ, all set via config.py. Switching providers is a config change, never a code change.
See docs/adr/0002-llm-provider-boundary.md.
"""

from functools import lru_cache

from openai import OpenAI

from enterprise_rag_knowledge_assistant.config import Settings, get_settings


class LLMProvider:
    def __init__(self, settings: Settings) -> None:
        self._client = OpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key)
        self._chat_model = settings.llm_chat_model
        self._embedding_model = settings.llm_embedding_model

    def embed(self, text: str) -> list[float]:
        response = self._client.embeddings.create(model=self._embedding_model, input=text)
        return response.data[0].embedding

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self._client.embeddings.create(model=self._embedding_model, input=texts)
        return [item.embedding for item in response.data]

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        response = self._client.chat.completions.create(
            model=self._chat_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
        )
        content = response.choices[0].message.content
        return content or ""


@lru_cache
def get_llm_provider() -> LLMProvider:
    """FastAPI dependency -- overridden with a fake in tests via app.dependency_overrides."""
    return LLMProvider(get_settings())
