"""Single configuration boundary.

Every environment-driven value the application needs enters through this module. Application
code should import `settings` from here, never call `os.getenv()` directly elsewhere.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "enterprise-rag-knowledge-assistant"
    app_env: str = "local"
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    database_url: str = "postgresql+psycopg://rag:rag@localhost:5432/rag"

    # LLM/embedding provider boundary (see providers.py). "ollama" and "openai" both speak the
    # OpenAI-compatible API — only base_url/api_key/model differ. See ADR-0001.
    llm_provider: str = "ollama"
    llm_base_url: str = "http://localhost:11434/v1"
    llm_api_key: str = "ollama"  # Ollama ignores this; required by the OpenAI client shape.
    llm_chat_model: str = "qwen2.5:0.5b"
    llm_embedding_model: str = "all-minilm"
    embedding_dimensions: int = 384

    # Chunking (see ADR-0002 / architecture.md)
    chunk_size_chars: int = 800
    chunk_overlap_chars: int = 100

    # Retrieval (see ADR-0003)
    retrieval_top_k: int = 4
    retrieval_similarity_threshold: float = 0.3

    # Guardrails (see ADR-0008)
    max_ingest_file_size_bytes: int = 1_000_000  # 1 MB — generous for internal Markdown/text docs

    # Object storage for uploaded documents (see ADR-0011). Any S3-compatible endpoint works
    # identically -- only endpoint/keys differ, same provider-boundary philosophy as providers.py.
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "ragminio"
    minio_secret_key: str = "ragminio123"  # dev-only default, see .env.example
    minio_bucket: str = "documents"
    minio_secure: bool = False

    # CORS for the local Next.js dev server (see frontend/, docs/adr/0011-phase2-stack.md).
    cors_allowed_origins: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
