"""
Central settings loaded from environment variables / .env file.

All modules import from here — never read os.environ directly elsewhere.
Using pydantic-settings so every field is type-checked and validated at startup.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide configuration.

    Values are read from the environment or a .env file in the project root.
    Pydantic validates types and raises a clear error at import time if a
    required variable is missing — fail fast rather than fail silently.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        # Extra fields in .env are ignored so adding new vars doesn't break old deploys.
        extra="ignore",
    )

    # --- LLM / Embeddings ---
    openai_api_key: str = Field(..., description="OpenAI API key")
    # Demo model for generation and grading (fast + cheap).
    llm_model: str = Field(default="gpt-4o-mini")
    # 3072-dim multilingual embeddings; swap for BAAI/bge-m3 in production.
    embedding_model: str = Field(default="text-embedding-3-large")
    embedding_dimensions: int = Field(default=3072)

    # --- Reranker ---
    cohere_api_key: str = Field(..., description="Cohere API key")
    reranker_model: str = Field(default="rerank-multilingual-v3.0")
    # Retrieve broadly, rerank aggressively (see TRAPS.md TRAP 8).
    retrieval_top_k: int = Field(default=50)
    reranker_top_k: int = Field(default=8)

    # --- Observability ---
    langsmith_api_key: str = Field(default="", description="Optional; tracing disabled if empty")
    langsmith_project: str = Field(default="legal-rag-nl")

    # --- Infrastructure ---
    qdrant_url: str = Field(default="http://localhost:6333")
    qdrant_collection: str = Field(default="legal_docs")
    redis_url: str = Field(default="redis://localhost:6379")

    # --- Semantic cache ---
    # >= 0.97 required for fiscal/legal data — year-versioned queries must NOT
    # hit a stale cache entry from a prior year (see TRAPS.md TRAP 5).
    semantic_cache_threshold: float = Field(default=0.97, ge=0.97, le=1.0)
    semantic_cache_ttl_seconds: int = Field(default=86400)  # 24 hours

    # --- Corpus versioning ---
    # Bump this string whenever new legislation is ingested so that all cached
    # answers (which cite a specific corpus snapshot) are automatically invalidated.
    corpus_version: str = Field(default="v1")


# Module-level singleton — import this everywhere.
settings = Settings()
