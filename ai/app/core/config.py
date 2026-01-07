"""Application configuration using Pydantic Settings."""

import os
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    env: str = "dev"

    # API Security
    api_key: str = "dev-secret"

    # OpenAI
    openai_api_key: str = ""
    openai_embed_model: str = "text-embedding-3-small"
    openai_chat_model: str = "gpt-4o-mini"

    # Embeddings Provider
    embeddings_provider: Literal["openai", "local"] = "openai"

    # LLM Provider
    llm_provider: Literal["openai", "ollama", "vllm"] = "openai"
    ollama_model: str = "llama3"
    ollama_host: str = "http://localhost:11434"

    # Azure OpenAI (optional)
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    embeddings_deployment: str = ""
    chat_deployment: str = ""

    # Qdrant
    qdrant_url: str = "http://qdrant:6333"
    qdrant_api_key: str = ""
    collection_name: str = "clinical_knowledge_v1"

    # Crawling
    crawl_base: str = "https://www.ncbi.nlm.nih.gov/books/NBK/"  # Example: NCBI Bookshelf / Guidelines
    rate_limit_rps: float = 0.5

    # Retrieval
    similarity_cutoff: float = 0.22
    top_k: int = 40
    top_n: int = 3

    # Legal
    legal_disclaimer: str = (
        "WARNING: This system provides clinical decision support using AI and is NOT a diagnostic tool. "
        "Outputs must be verified by a qualified healthcare professional. Do not rely solely on this system for patient care."
    )

    # Logging
    log_level: str = "INFO"

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.env.lower() == "prod"

    @property
    def is_local_embeddings(self) -> bool:
        """Check if using local embeddings."""
        return self.embeddings_provider == "local"

    @property
    def is_local_llm(self) -> bool:
        """Check if using local LLM."""
        return self.llm_provider in ("ollama", "vllm")


# Global settings instance
settings = Settings()


