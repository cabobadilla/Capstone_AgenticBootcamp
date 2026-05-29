"""
Central configuration loaded from .env via pydantic-settings.
A single `settings` singleton is imported across all modules — no os.environ calls elsewhere.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── LLM provider ─────────────────────────────────────────────────────────
    anthropic_api_key: str

    # ── Embeddings (OpenAI text-embedding-3-small, closed decision v2) ────────
    openai_api_key: str

    # ── Observability (LangSmith ON from MVP, closed decision v2) ────────────
    langsmith_api_key: str = ""
    langsmith_project: str = "ai-tutor"
    langsmith_tracing: bool = True  # maps to LANGSMITH_TRACING env var

    # ── Optional: Voyage AI (not primary in v2 stack) ────────────────────────
    voyage_api_key: str = ""

    # ── Local paths ───────────────────────────────────────────────────────────
    chroma_persist_dir: Path = Path("./data/chroma")
    student_models_dir: Path = Path("./data/students")
    packs_dir: Path = Path("./packs")

    # ── Pack & session defaults ───────────────────────────────────────────────
    default_pack_id: str = "cca-f"
    default_student_id: str = "default"

    # ── Cost guard (warn if a session exceeds this many tokens) ───────────────
    max_session_tokens: int = 50_000

    # ── Agent model choices (per spec v2 §8) ─────────────────────────────────
    # Sonnet for reasoning agents; Haiku for the lightweight Updater-only tasks
    model_primary: str = "claude-sonnet-4-6"
    model_lightweight: str = "claude-haiku-4-5-20251001"

    # ── RAG retrieval defaults ────────────────────────────────────────────────
    retrieval_top_k: int = 5  # top-5 chunks per query (spec v2 §17 cost control)
    embedding_model: str = "text-embedding-3-small"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        # extra fields in .env are silently ignored
        extra="ignore",
    )

    def ensure_dirs(self) -> None:
        """Create local data directories if they don't exist yet."""
        for d in (self.chroma_persist_dir, self.student_models_dir):
            d.mkdir(parents=True, exist_ok=True)


# Module-level singleton — import this everywhere: `from ai_tutor.config import settings`
settings = Settings()
